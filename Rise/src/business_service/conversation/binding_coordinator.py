from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Optional, Protocol

from business_service.channel.models import (
    ChannelBindingRuntime,
    ChannelMode,
    WorkflowChannelPolicy,
    DEFAULT_TIMEOUT_MESSAGE,
    DEFAULT_WORKFLOW_MISSING_MESSAGE,
)
from business_service.conversation.config import resolve_entry_config
from business_service.conversation.context_factory import ConversationContext

log = logging.getLogger("business_service.conversation.binding")

_BINDING_REFRESH_TIMEOUT_SECONDS = float(os.getenv("TELEGRAM_BINDING_REFRESH_TIMEOUT", "1.0"))
_BINDING_FALLBACK_FLAG = os.getenv("TELEGRAM_BINDING_FALLBACK_ENABLED", "0").lower() in {"1", "true", "yes", "on"}


class ChannelBindingProvider(Protocol):
    async def get_active_binding(self, channel: str = "telegram") -> Optional[ChannelBindingRuntime]:
        ...

    async def refresh(self, channel: str = "telegram") -> Optional[ChannelBindingRuntime]:
        ...


@dataclass(slots=True)
class BindingCoordinator:
    """Encapsulates binding lookup, fallback, and telemetry snapshot updates."""

    fallback_enabled: Optional[bool] = None
    refresh_timeout_seconds: float = _BINDING_REFRESH_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if self.fallback_enabled is None:
            self.fallback_enabled = _BINDING_FALLBACK_FLAG

    async def resolve_runtime(
        self,
        *,
        provider: Optional[ChannelBindingProvider],
        context: ConversationContext,
    ) -> Optional[ChannelBindingRuntime]:
        runtime = await self._get_binding_runtime(provider)
        if runtime is not None:
            return runtime
        if self.fallback_enabled:
            return self._maybe_use_policy_fallback(context)
        return None

    async def _get_binding_runtime(
        self,
        provider: Optional[ChannelBindingProvider],
    ) -> Optional[ChannelBindingRuntime]:
        if provider is None:
            return None
        try:
            binding = await provider.get_active_binding("telegram")
            if binding:
                return binding
            refreshed = await self._attempt_binding_refresh(provider)
            if refreshed:
                return refreshed
            return None
        except Exception as exc:  # pragma: no cover - defensive logging
            log.warning("telegram.binding.lookup_failed", extra={"error": str(exc)})
            return None

    async def _attempt_binding_refresh(self, provider: ChannelBindingProvider) -> Optional[ChannelBindingRuntime]:
        refresh_fn = getattr(provider, "refresh", None)
        if refresh_fn is None:
            return None
        try:
            await asyncio.wait_for(refresh_fn("telegram"), timeout=self.refresh_timeout_seconds)
        except asyncio.TimeoutError:
            log.warning("telegram.binding.refresh_timeout", extra={"timeout": self.refresh_timeout_seconds})
            return None
        except Exception as exc:
            log.warning("telegram.binding.refresh_failed", extra={"error": str(exc)})
            return None
        return await provider.get_active_binding("telegram")

    def _maybe_use_policy_fallback(self, context: ConversationContext) -> Optional[ChannelBindingRuntime]:
        entrypoints = context.policy.get("entrypoints")
        if not isinstance(entrypoints, Mapping):
            return None
        telegram_entry = entrypoints.get("telegram")
        if not isinstance(telegram_entry, Mapping):
            return None
        workflow_id = telegram_entry.get("workflow_id") or telegram_entry.get("workflowId")
        if not workflow_id:
            return None
        now = datetime.now(timezone.utc)
        policy = WorkflowChannelPolicy(
            workflow_id=str(workflow_id),
            channel="telegram",
            encrypted_bot_token="__fallback__",
            bot_token_mask="__fallback__",
            webhook_url=str(telegram_entry.get("webhook_url") or telegram_entry.get("webhookUrl") or ""),
            wait_for_result=bool(telegram_entry.get("wait_for_result", True)),
            workflow_missing_message=str(
                telegram_entry.get("workflow_missing_text")
                or telegram_entry.get("workflowMissingText")
                or DEFAULT_WORKFLOW_MISSING_MESSAGE
            ),
            timeout_message=str(
                telegram_entry.get("timeout_message") or telegram_entry.get("timeoutMessage") or DEFAULT_TIMEOUT_MESSAGE
            ),
            metadata={},
            updated_by="binding_fallback",
            updated_at=now,
            secret_version=0,
            mode=ChannelMode.WEBHOOK,
        )
        runtime = ChannelBindingRuntime(
            workflow_id=str(workflow_id),
            channel="telegram",
            policy=policy,
            version=-1,
        )
        log.error("telegram.binding.policy_fallback_active", extra={"workflow_id": runtime.workflow_id})
        return runtime

    def record_snapshot(
        self,
        context: ConversationContext,
        *,
        workflow_id: Optional[str],
        version: Optional[int],
        status: Optional[str] = None,
        fallback: bool = False,
        policy: Optional[WorkflowChannelPolicy] = None,
    ) -> None:
        snapshot = dict(context.telemetry.get("binding") or {})
        snapshot["workflow_id"] = workflow_id
        snapshot["version"] = version if version is not None else snapshot.get("version", -1)
        if fallback:
            snapshot["fallback"] = True
        if status:
            snapshot["status"] = status
        if policy is not None and isinstance(policy.metadata, Mapping):
            locale = policy.metadata.get("locale")
            if isinstance(locale, str) and locale.strip():
                snapshot["locale"] = locale.strip().lower()
        context.telemetry["binding"] = snapshot

    def binding_version_hint(self, provider: Optional[ChannelBindingProvider]) -> Optional[int]:
        if provider is None:
            return None
        get_state = getattr(provider, "get_state", None)
        if callable(get_state):
            try:
                state = get_state("telegram")
            except TypeError:
                try:
                    state = get_state()
                except Exception:
                    state = None
            if state is not None:
                return getattr(state, "version", None)
        snapshot_fn = getattr(provider, "snapshot", None)
        if callable(snapshot_fn):
            try:
                snapshot = snapshot_fn()
            except TypeError:
                snapshot = snapshot_fn("telegram")
            if isinstance(snapshot, Mapping):
                data = snapshot.get("telegram")
                if isinstance(data, Mapping):
                    version = data.get("version")
                    if isinstance(version, int):
                        return version
        return None

    def apply_entry_config(self, context: ConversationContext, policy: WorkflowChannelPolicy) -> None:
        context.entry_config = resolve_entry_config(
            context.policy,
            binding_policy=policy,
            defaults=context.entry_config,
        )

    @staticmethod
    def is_chat_allowed(context: ConversationContext, policy: WorkflowChannelPolicy) -> bool:
        metadata = policy.metadata if isinstance(policy.metadata, Mapping) else {}
        allowed = metadata.get("allowedChatIds")
        if not isinstance(allowed, (list, tuple, set)):
            return True
        allowed_ids = {str(item) for item in allowed if item not in {None, ""}}
        if not allowed_ids:
            return True
        if context.chat_id is None:
            return False
        return str(context.chat_id) in allowed_ids


__all__ = ["BindingCoordinator", "ChannelBindingProvider"]
