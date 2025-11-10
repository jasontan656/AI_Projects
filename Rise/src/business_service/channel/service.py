from __future__ import annotations

"""Business logic for workflow channel policies."""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional, Sequence
from urllib.parse import urlparse

from business_service.channel.models import (
    DEFAULT_TIMEOUT_MESSAGE,
    DEFAULT_WORKFLOW_MISSING_MESSAGE,
    ChannelBindingOption,
    WorkflowChannelPolicy,
)
from business_service.channel.repository import AsyncWorkflowChannelRepository
from business_service.workflow import AsyncWorkflowRepository, WorkflowDefinition
from project_utility.secrets import get_secret_box, mask_secret

__all__ = ["WorkflowChannelService", "ChannelValidationError"]

BOT_TOKEN_PATTERN = re.compile(r"^\d+:[A-Za-z0-9_-]{20,}$")


@dataclass(slots=True)
class ChannelValidationError(ValueError):
    code: str
    message: str

    def __post_init__(self) -> None:
        ValueError.__init__(self, self.message)


class WorkflowChannelService:
    def __init__(
        self,
        repository: AsyncWorkflowChannelRepository,
        workflow_repository: AsyncWorkflowRepository,
        *,
        secret_env: str = "TELEGRAM_TOKEN_SECRET",
    ) -> None:
        self._repository = repository
        self._workflow_repository = workflow_repository
        self._secret_env = secret_env

    async def get_policy(self, workflow_id: str, channel: str = "telegram") -> WorkflowChannelPolicy:
        policy = await self._repository.get(workflow_id, channel)
        if policy is None:
            raise KeyError(workflow_id)
        return policy

    async def delete_policy(self, workflow_id: str, channel: str = "telegram") -> None:
        found = await self._repository.delete(workflow_id, channel)
        if not found:
            raise KeyError(workflow_id)

    async def list_binding_options(self, channel: str = "telegram") -> Sequence[ChannelBindingOption]:
        workflows = await self._workflow_repository.list_workflows()
        policies = await self._repository.list_by_channel(channel)
        policy_map = {policy.workflow_id: policy for policy in policies}
        options: list[ChannelBindingOption] = []
        for workflow in workflows:
            is_enabled = self._is_channel_enabled(workflow, channel)
            policy = policy_map.get(workflow.workflow_id)
            if not self._should_include_workflow(workflow, is_enabled, policy):
                continue
            status = self._derive_status(policy)
            options.append(self._build_binding_option(workflow, policy, channel, is_enabled, status))
        return options

    async def get_binding_view(self, workflow_id: str, channel: str = "telegram") -> ChannelBindingOption:
        workflow = await self._workflow_repository.get(workflow_id)
        if workflow is None:
            raise KeyError(workflow_id)
        policy = await self._repository.get(workflow_id, channel)
        is_enabled = self._is_channel_enabled(workflow, channel)
        status = self._derive_status(policy)
        if not is_enabled and policy is None:
            status = "unbound"
        return self._build_binding_option(workflow, policy, channel, is_enabled, status)

    async def record_health_snapshot(
        self,
        workflow_id: str,
        channel: str,
        *,
        status: str,
        detail: Optional[Mapping[str, Any]] = None,
        checked_at: Optional[datetime] = None,
    ) -> None:
        policy = await self._repository.get(workflow_id, channel)
        if policy is None:
            return
        metadata = dict(policy.metadata or {})
        health = dict(metadata.get("health") or {})
        checked = checked_at or datetime.now(timezone.utc)
        health["status"] = status
        health["lastCheckedAt"] = checked.isoformat()
        if detail:
            health["detail"] = dict(detail)
        metadata["health"] = health
        policy.metadata = metadata
        policy.updated_at = checked
        await self._repository.upsert(policy)

    async def save_policy(
        self,
        workflow_id: str,
        payload: Mapping[str, Any],
        *,
        actor: Optional[str],
        channel: str = "telegram",
    ) -> WorkflowChannelPolicy:
        existing = await self._repository.get(workflow_id, channel)
        token = payload.get("botToken")
        if not token and existing is None:
            raise ChannelValidationError("BOT_TOKEN_REQUIRED", "botToken is required for new channel policy")
        encrypted, mask, secret_version = await self._resolve_token(existing, token)
        raw_webhook = payload.get("webhookUrl")
        if not raw_webhook and existing is not None:
            raw_webhook = existing.webhook_url
        webhook_url = self._validate_webhook(raw_webhook or "")
        wait_for_result = bool(payload.get("waitForResult", existing.wait_for_result if existing else True))
        workflow_missing_message = str(
            payload.get("workflowMissingMessage")
            or (existing.workflow_missing_message if existing else DEFAULT_WORKFLOW_MISSING_MESSAGE)
        )
        timeout_message = str(
            payload.get("timeoutMessage")
            or (existing.timeout_message if existing else DEFAULT_TIMEOUT_MESSAGE)
        )
        metadata = self._normalize_metadata(payload.get("metadata"), existing.metadata if existing else None)
        policy = WorkflowChannelPolicy.new(
            workflow_id=workflow_id,
            channel=channel,
            encrypted_bot_token=encrypted,
            bot_token_mask=mask,
            webhook_url=webhook_url,
            wait_for_result=wait_for_result,
            workflow_missing_message=workflow_missing_message,
            timeout_message=timeout_message,
            metadata=metadata,
            actor=actor,
            secret_version=secret_version,
        )
        return await self._repository.upsert(policy)

    def decrypt_token(self, policy: WorkflowChannelPolicy) -> str:
        secret_box = get_secret_box(self._secret_env)
        return secret_box.decrypt(policy.encrypted_bot_token)

    async def _resolve_token(
        self,
        existing: Optional[WorkflowChannelPolicy],
        new_token: Optional[str],
    ) -> tuple[str, str, int]:
        if not new_token:
            assert existing is not None
            return existing.encrypted_bot_token, existing.bot_token_mask, existing.secret_version
        if not BOT_TOKEN_PATTERN.match(new_token):
            raise ChannelValidationError("BOT_TOKEN_INVALID", "botToken format is invalid")
        secret_box = get_secret_box(self._secret_env)
        encrypted = secret_box.encrypt(new_token)
        mask = mask_secret(new_token)
        secret_version = (existing.secret_version + 1) if existing else 1
        return encrypted, mask, secret_version

    def _validate_webhook(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ChannelValidationError("WEBHOOK_INVALID", "webhookUrl must be https")
        return url

    def _normalize_metadata(
        self,
        metadata: Optional[Mapping[str, Any]],
        fallback: Optional[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        source = dict(fallback or {})
        incoming = dict(metadata or {})
        allowed = incoming.get("allowedChatIds", source.get("allowedChatIds", []))
        if allowed:
            allowed = [str(item) for item in allowed]
        rate_limit = int(incoming.get("rateLimitPerMin", source.get("rateLimitPerMin", 60)))
        locale = str(incoming.get("locale", source.get("locale", "zh-CN")))
        normalized: MutableMapping[str, Any] = dict(source)
        normalized["allowedChatIds"] = allowed
        normalized["rateLimitPerMin"] = max(1, rate_limit)
        normalized["locale"] = locale
        return normalized

    def _build_binding_option(
        self,
        workflow: WorkflowDefinition,
        policy: Optional[WorkflowChannelPolicy],
        channel: str,
        is_enabled: bool,
        status: str,
    ) -> ChannelBindingOption:
        return ChannelBindingOption(
            workflow_id=workflow.workflow_id,
            workflow_name=workflow.name,
            published_version=workflow.published_version,
            channel=channel,
            status=status,
            is_enabled=is_enabled,
            policy=policy,
            health=self._extract_health(policy),
            updated_at=policy.updated_at if policy else None,
            updated_by=policy.updated_by if policy else None,
        )

    @staticmethod
    def _extract_health(policy: Optional[WorkflowChannelPolicy]) -> Mapping[str, Any]:
        if policy is None:
            return {}
        health = policy.metadata.get("health") if isinstance(policy.metadata, Mapping) else None
        if isinstance(health, Mapping):
            return dict(health)
        return {}

    def _derive_status(self, policy: Optional[WorkflowChannelPolicy]) -> str:
        if policy is None:
            return "unbound"
        health = self._extract_health(policy)
        status = str(health.get("status") or "").lower()
        if status in {"degraded", "down"}:
            return "degraded"
        return "bound"

    @staticmethod
    def _is_channel_enabled(workflow: WorkflowDefinition, channel: str) -> bool:
        metadata = workflow.metadata or {}
        channels_meta = metadata.get("channels")
        if isinstance(channels_meta, Mapping):
            channel_meta = channels_meta.get(channel)
            if isinstance(channel_meta, Mapping):
                enabled = channel_meta.get("enabled")
                if isinstance(enabled, bool):
                    return enabled
        camel_case = metadata.get(f"{channel}Enabled")
        if isinstance(camel_case, bool):
            return camel_case
        legacy = metadata.get("channelEnabled")
        if isinstance(legacy, bool):
            return legacy
        return True

    def _should_include_workflow(
        self,
        workflow: WorkflowDefinition,
        is_enabled: bool,
        policy: Optional[WorkflowChannelPolicy],
    ) -> bool:
        status_allowed = workflow.status in {"published", "production", "active"}
        return policy is not None or (is_enabled and status_allowed)

    async def set_channel_enabled(
        self,
        workflow_id: str,
        channel: str,
        *,
        enabled: bool,
        actor: Optional[str],
    ) -> WorkflowDefinition:
        workflow = await self._workflow_repository.get(workflow_id)
        if workflow is None:
            raise KeyError(workflow_id)
        metadata = dict(workflow.metadata or {})
        channels_meta = dict(metadata.get("channels") or {})
        channel_meta = dict(channels_meta.get(channel) or {})
        channel_meta["enabled"] = enabled
        channel_meta["updatedAt"] = datetime.now(timezone.utc).isoformat()
        channel_meta["updatedBy"] = actor
        channels_meta[channel] = channel_meta
        metadata["channels"] = channels_meta
        updates: MutableMapping[str, Any] = {"metadata": metadata}
        if actor:
            updates["updated_by"] = actor
        return await self._workflow_repository.update(
            workflow_id,
            updates,
            increment_version=False,
        )
