"""Core envelope schema definitions for the Foundational Service Layer.

Migrated from `shared_utility.core.schema` to provide the canonical
CoreEnvelope models for adapters, contracts, and tooling. Compatibility with
legacy flattened payloads remains intact while enforcing the nested structure.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr, ValidationError, model_validator

__all__ = [
    "SchemaValidationError",
    "PayloadTooLarge",
    "Metadata",
    "ContextQuote",
    "Attachment",
    "Payload",
    "ExtFlags",
    "Telemetry",
    "CoreEnvelope",
]


class SchemaValidationError(ValueError):
    """Raised when payload does not comply with CoreEnvelope."""


class PayloadTooLarge(SchemaValidationError):
    """Raised when payload exceeds documented CoreEnvelope limits."""


class Metadata(BaseModel):
    chat_id: str
    convo_id: str
    channel: Literal["telegram", "web", "whatsapp"]
    language: str = Field(pattern=r"^[a-z]{2}(-[A-Z]{2})?$")
    timestamp_iso: Optional[str] = Field(default=None)
    thread_id: Optional[str] = None

    model_config = {"extra": "forbid"}


class ContextQuote(BaseModel):
    speaker: str
    excerpt: str
    role: str = Field(default="user", pattern=r"^(user|assistant|system)$")
    timestamp_iso: Optional[str] = Field(default=None)

    model_config = {"extra": "forbid"}


class Attachment(BaseModel):
    kind: str = Field(pattern=r"^(text|image|file|audio|voice)$")
    source: str
    summary: Optional[str] = None
    mime_size_bytes: Optional[int] = Field(default=None, ge=0)
    checksum_sha256: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    model_config = {"extra": "forbid"}


class Payload(BaseModel):
    user_message: str = Field(min_length=1)
    context_quotes: List[ContextQuote] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)
    system_tags: List[str] = Field(default_factory=list)
    message_ts: Optional[str] = None

    model_config = {"extra": "forbid"}


class ExtFlags(BaseModel):
    reply_to_bot: Optional[bool] = None
    intent_hint: Optional[str] = None
    kb_scope: List[str] = Field(default_factory=list)
    safety_level: str = Field(default="normal", pattern=r"^(normal|sensitive|restricted)$")

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _ensure_defaults(cls, values: "ExtFlags") -> "ExtFlags":
        if not values.kb_scope:
            values.kb_scope = ["global"]
        if not values.safety_level:
            values.safety_level = "normal"
        return values


class Telemetry(BaseModel):
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    latency_ms: Optional[float] = Field(default=None, ge=0)
    validation_ms: Optional[float] = Field(default=None, ge=0)
    status_code: Optional[int] = None
    error_hint: Optional[str] = None
    core_envelope_trim_total: Optional[int] = Field(default=None, ge=0)
    core_envelope_attachment_reject_total: Optional[int] = Field(default=None, ge=0)

    model_config = {"extra": "allow"}


class CoreEnvelope(BaseModel):
    metadata: Metadata
    payload: Payload
    ext_flags: ExtFlags = Field(default_factory=ExtFlags)
    telemetry: Telemetry = Field(default_factory=Telemetry)
    version: Literal["v1.0.0"] = "v1.0.0"

    model_config = {"populate_by_name": True, "extra": "forbid"}

    _trimmed_quotes: int = PrivateAttr(default=0)
    _telemetry_payload: Dict[str, Any] = PrivateAttr(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _ingest_flattened(cls, data: Any) -> Any:
        """Support legacy flattened structures by wrapping into nested envelope."""
        if not isinstance(data, dict):
            return data
        if "metadata" in data and "payload" in data:
            if "_telemetry" in data:
                data = dict(data)
                cls._extract_private_telemetry(data)
            return data
        # Legacy flattened payload (chat_id, user_message, ...)
        if {"chat_id", "convo_id", "channel", "user_message"}.issubset(data.keys()):
            metadata = {
                "chat_id": data.get("chat_id"),
                "convo_id": data.get("convo_id"),
                "channel": data.get("channel"),
                "language": data.get("language"),
                "timestamp_iso": data.get("message_ts"),
                "thread_id": data.get("thread_id"),
            }
            payload = {
                "user_message": data.get("user_message"),
                "context_quotes": data.get("context_quotes", []),
                "attachments": data.get("attachments", []),
                "system_tags": data.get("system_tags", []),
                "message_ts": data.get("message_ts"),
            }
            ext_flags = data.get("ext_flags", {}) or {}
            telemetry = data.get("telemetry", {}) or {}
            version = data.get("version", "v1.0.0")
            converted: Dict[str, Any] = {
                "metadata": metadata,
                "payload": payload,
                "ext_flags": ext_flags,
                "telemetry": telemetry,
                "version": version,
            }
            if "_telemetry" in data:
                converted["_telemetry"] = data["_telemetry"]
            return converted
        return data

    @staticmethod
    def _extract_private_telemetry(data: Dict[str, Any]) -> None:
        telemetry = data.pop("_telemetry", None)
        if telemetry is not None:
            data.setdefault("telemetry", telemetry)

    @model_validator(mode="after")
    def _apply_constraints(self) -> "CoreEnvelope":
        quotes = list(self.payload.context_quotes)
        if len(quotes) > 5:
            self._trimmed_quotes = len(quotes) - 5
            self.payload.context_quotes = quotes[-5:]
        else:
            self._trimmed_quotes = 0
        if not self.payload.message_ts and self.metadata.timestamp_iso:
            self.payload.message_ts = self.metadata.timestamp_iso
        return self

    @classmethod
    def validate_payload(cls, data: Dict[str, Any]) -> "CoreEnvelope":
        try:
            working = dict(data)
            telemetry = working.pop("_telemetry", None)
            model = cls.model_validate(working)
            if len(model.payload.attachments) > 3:
                raise PayloadTooLarge("attachments exceed limit of 3")
            telemetry_dict = telemetry or model.telemetry.model_dump(exclude_none=True)
            model._telemetry_payload = dict(telemetry_dict)
            return model
        except PayloadTooLarge:
            raise
        except ValidationError as exc:
            raise SchemaValidationError(str(exc)) from exc

    @property
    def trimmed_context_quote_count(self) -> int:
        return self._trimmed_quotes

    @property
    def telemetry_payload(self) -> Dict[str, Any]:
        return dict(self._telemetry_payload)

    def attach_telemetry(self, telemetry: Dict[str, Any]) -> None:
        merged = {**self.telemetry.model_dump(exclude_none=True), **telemetry}
        self.telemetry = Telemetry.model_validate(merged)
        self._telemetry_payload = self.telemetry.model_dump(exclude_none=True)

    def to_agent_request(self) -> Dict[str, Any]:
        return {
            "prompt": self.payload.user_message,
            "convo_id": self.metadata.convo_id,
            "language": self.metadata.language,
            "intent_hint": self.ext_flags.intent_hint,
            "system_tags": list(self.payload.system_tags),
            "attachments": [attachment.model_dump() for attachment in self.payload.attachments],
            "kb_scope": list(self.ext_flags.kb_scope),
            "reply_to_bot": self.ext_flags.reply_to_bot,
        }

    def to_logging_dict(self) -> Dict[str, Any]:
        telemetry = {**self.telemetry_payload}
        logging_payload = {
            "chat_id": self.metadata.chat_id,
            "channel": self.metadata.channel,
            "convo_id": self.metadata.convo_id,
            "thread_id": self.metadata.thread_id or self.metadata.chat_id,
            "schema_version": self.version,
            "language": self.metadata.language,
            "context_quote_count": len(self.payload.context_quotes),
            "attachment_count": len(self.payload.attachments),
            "safety_level": self.ext_flags.safety_level,
            "core_envelope_trim_total": self.trimmed_context_quote_count,
            "core_envelope_attachment_reject_total": 0,
        }
        for field in (
            "request_id",
            "prompt_version",
            "doc_commit",
            "latency_ms",
            "validation_ms",
            "status_code",
            "error_hint",
            "stage",
            "trace_id",
        ):
            value = telemetry.get(field)
            if value is not None:
                logging_payload[field] = value
        return logging_payload

    def model_dump_legacy(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)


__all__ = [
    "Attachment",
    "ContextQuote",
    "CoreEnvelope",
    "ExtFlags",
    "Metadata",
    "Payload",
    "PayloadTooLarge",
    "SchemaValidationError",
    "Telemetry",
]
