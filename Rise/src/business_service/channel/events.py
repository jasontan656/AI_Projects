from __future__ import annotations

"""Redis-based channel binding event primitives."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Mapping

CHANNEL_BINDING_TOPIC = "channel_binding.updated"


@dataclass(slots=True)
class ChannelBindingEvent:
    channel: str
    workflow_id: str
    operation: str
    binding_version: int
    published_version: int
    enabled: bool
    secret_version: int | None = None
    actor: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def dumps(self) -> str:
        return json.dumps(
            {
                "channel": self.channel,
                "workflowId": self.workflow_id,
                "operation": self.operation,
                "bindingVersion": self.binding_version,
                "publishedVersion": self.published_version,
                "enabled": self.enabled,
                "secretVersion": self.secret_version,
                "actor": self.actor,
                "payload": dict(self.payload or {}),
                "timestamp": self.timestamp,
            },
            ensure_ascii=False,
        )

    @classmethod
    def loads(cls, raw: Any) -> "ChannelBindingEvent":
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return cls(
            channel=data["channel"],
            workflow_id=data["workflowId"],
            operation=data.get("operation", "upsert"),
            binding_version=int(data.get("bindingVersion", 0)),
            published_version=int(data.get("publishedVersion", 0)),
            enabled=bool(data.get("enabled", True)),
            secret_version=data.get("secretVersion"),
            actor=data.get("actor"),
            payload=data.get("payload") or {},
            timestamp=data.get("timestamp")
            or datetime.now(timezone.utc).isoformat(),
        )
