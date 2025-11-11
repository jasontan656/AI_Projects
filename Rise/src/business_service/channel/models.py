from __future__ import annotations

"""Channel configuration domain models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional

DEFAULT_WORKFLOW_MISSING_MESSAGE = "Workflow unavailable, please contact the operator."
DEFAULT_TIMEOUT_MESSAGE = "Workflow timeout, please try again."

__all__ = [
    "WorkflowChannelPolicy",
    "ChannelBindingOption",
    "ChannelBindingRuntime",
]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class WorkflowChannelPolicy:
    workflow_id: str
    channel: str
    encrypted_bot_token: str
    bot_token_mask: str
    webhook_url: str
    wait_for_result: bool = True
    workflow_missing_message: str = DEFAULT_WORKFLOW_MISSING_MESSAGE
    timeout_message: str = DEFAULT_TIMEOUT_MESSAGE
    metadata: Mapping[str, Any] = field(default_factory=dict)
    updated_by: Optional[str] = None
    updated_at: datetime = field(default_factory=_now_utc)
    secret_version: int = 1

    def to_document(self) -> MutableMapping[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "channel": self.channel,
            "encrypted_bot_token": self.encrypted_bot_token,
            "bot_token_mask": self.bot_token_mask,
            "webhook_url": self.webhook_url,
            "wait_for_result": self.wait_for_result,
            "workflow_missing_message": self.workflow_missing_message,
            "timeout_message": self.timeout_message,
            "metadata": dict(self.metadata),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at,
            "secret_version": self.secret_version,
        }

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> "WorkflowChannelPolicy":
        return cls(
            workflow_id=str(doc["workflow_id"]),
            channel=str(doc.get("channel", "telegram")),
            encrypted_bot_token=str(doc.get("encrypted_bot_token", "")),
            bot_token_mask=str(doc.get("bot_token_mask", "")),
            webhook_url=str(doc.get("webhook_url", "")),
            wait_for_result=bool(doc.get("wait_for_result", True)),
            workflow_missing_message=str(
                doc.get("workflow_missing_message") or DEFAULT_WORKFLOW_MISSING_MESSAGE
            ),
            timeout_message=str(doc.get("timeout_message") or DEFAULT_TIMEOUT_MESSAGE),
            metadata=dict(doc.get("metadata") or {}),
            updated_by=doc.get("updated_by"),
            updated_at=doc.get("updated_at") or _now_utc(),
            secret_version=int(doc.get("secret_version", 1)),
        )

    @classmethod
    def new(
        cls,
        *,
        workflow_id: str,
        channel: str,
        encrypted_bot_token: str,
        bot_token_mask: str,
        webhook_url: str,
        wait_for_result: bool,
        workflow_missing_message: str,
        timeout_message: str,
        metadata: Mapping[str, Any],
        actor: Optional[str],
        secret_version: int,
    ) -> "WorkflowChannelPolicy":
        now = _now_utc()
        return cls(
            workflow_id=workflow_id,
            channel=channel,
            encrypted_bot_token=encrypted_bot_token,
            bot_token_mask=bot_token_mask,
            webhook_url=webhook_url,
            wait_for_result=wait_for_result,
            workflow_missing_message=workflow_missing_message,
            timeout_message=timeout_message,
            metadata=dict(metadata),
            updated_by=actor,
            updated_at=now,
            secret_version=secret_version,
        )

    @property
    def masked_token(self) -> str:
        return self.bot_token_mask


@dataclass(slots=True)
class ChannelBindingOption:
    workflow_id: str
    workflow_name: str
    published_version: int
    channel: str
    status: str
    is_enabled: bool
    is_bound: bool = False
    policy: Optional[WorkflowChannelPolicy] = None
    health: Mapping[str, Any] = field(default_factory=dict)
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    kill_switch: bool = False


@dataclass(slots=True)
class ChannelBindingRuntime:
    workflow_id: str
    channel: str
    policy: WorkflowChannelPolicy
    version: int
