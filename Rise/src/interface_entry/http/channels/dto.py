from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, Field, model_validator

from interface_entry.http.workflows.dto import WorkflowApplyResult

__all__ = [
    "WorkflowChannelRequest",
    "WorkflowChannelResponse",
    "TelegramChannelMetadata",
    "TelegramHealthResponse",
    "TelegramTestRequest",
    "TelegramTestResponse",
    "ChannelBindingOptionResponse",
    "ChannelBindingDetailResponse",
    "ChannelBindingDiagnosticsResponse",
    "ChannelBindingUpsertRequest",
    "ChannelBindingHealth",
    "ChannelBindingConfig",
]


class TelegramChannelMetadata(BaseModel):
    allowedChatIds: Sequence[str] = Field(default_factory=tuple)
    rateLimitPerMin: int = Field(default=60, ge=1, le=200)
    locale: str = Field(default="zh-CN")


class WorkflowChannelRequest(BaseModel):
    botToken: Optional[str] = Field(default=None, description="Telegram bot token (omit to reuse existing)")
    webhookUrl: Optional[str] = Field(default=None, description="HTTPS webhook endpoint (required when usePolling=false)")
    waitForResult: bool = Field(default=True)
    workflowMissingMessage: str = Field(default="Workflow unavailable, please contact the operator.")
    timeoutMessage: str = Field(default="Workflow timeout, please try again.")
    metadata: TelegramChannelMetadata = Field(default_factory=TelegramChannelMetadata)
    usePolling: bool = Field(default=False)

    @model_validator(mode="after")
    def _validate_mode(self) -> "WorkflowChannelRequest":
        if self.usePolling:
            if self.webhookUrl:
                raise ValueError("webhookUrl must be omitted when usePolling=true")
        else:
            if not self.webhookUrl:
                raise ValueError("webhookUrl is required when usePolling=false")
        return self


class WorkflowChannelResponse(BaseModel):
    workflowId: str
    channel: str = "telegram"
    webhookUrl: str
    waitForResult: bool
    workflowMissingMessage: str
    timeoutMessage: str
    metadata: TelegramChannelMetadata
    maskedBotToken: str
    secretVersion: int
    updatedAt: datetime
    updatedBy: Optional[str] = None
    usePolling: bool = Field(default=False)


class ChannelBindingHealth(BaseModel):
    status: str = "unknown"
    lastCheckedAt: Optional[datetime] = None
    detail: Mapping[str, Any] = Field(default_factory=dict)


class ChannelBindingOptionResponse(BaseModel):
    workflowId: str
    workflowName: str
    channel: str
    status: str
    isChannelEnabled: bool = True
    isBound: bool = False
    publishedVersion: int
    bindingUpdatedAt: Optional[datetime] = None
    bindingUpdatedBy: Optional[str] = None
    health: ChannelBindingHealth = Field(default_factory=ChannelBindingHealth)
    killSwitch: bool = False


class ChannelBindingDetailResponse(ChannelBindingOptionResponse):
    policy: Optional[WorkflowChannelResponse] = None


class ChannelBindingDiagnosticsResponse(BaseModel):
    channel: str
    version: int
    activeWorkflowId: Optional[str] = None
    optionCount: int
    lastRefreshAt: Optional[datetime] = None
    queueLength: int
    deadletterCount: int


class ChannelBindingConfig(BaseModel):
    botToken: Optional[str] = Field(default=None, description="Telegram bot token (omit to reuse existing)")
    webhookUrl: Optional[str] = Field(default=None, description="HTTPS webhook endpoint")
    waitForResult: bool = Field(default=True)
    workflowMissingMessage: str = Field(default="Workflow unavailable, please contact the operator.")
    timeoutMessage: str = Field(default="Workflow timeout, please try again.")
    metadata: TelegramChannelMetadata = Field(default_factory=TelegramChannelMetadata)
    usePolling: bool = Field(default=False)

    @model_validator(mode="after")
    def _validate_mode(self) -> "ChannelBindingConfig":
        if self.usePolling:
            if self.webhookUrl:
                raise ValueError("webhookUrl must be omitted when usePolling=true")
        else:
            if not self.webhookUrl:
                raise ValueError("webhookUrl is required when usePolling=false")
        return self


class ChannelBindingUpsertRequest(BaseModel):
    channel: str = Field(default="telegram")
    enabled: bool = Field(default=True)
    config: Optional[ChannelBindingConfig] = Field(default=None)

    @model_validator(mode="after")
    def _validate_config(self) -> "ChannelBindingUpsertRequest":
        if self.enabled:
            if self.config is None:
                raise ValueError("config is required when enabled=true")
        return self


class TelegramHealthResponse(BaseModel):
    status: str
    lastCheckedAt: datetime
    lastError: Optional[str] = None
    metrics: Mapping[str, Any] = Field(default_factory=dict)


class TelegramTestRequest(BaseModel):
    workflowId: str
    chatId: str
    payloadText: str = Field(default="")
    waitForResult: bool = Field(default=False)
    correlationId: Optional[str] = None


class TelegramTestResponse(BaseModel):
    status: str
    responseTimeMs: int
    telegramMessageId: Optional[str] = None
    errorCode: Optional[str] = None
    traceId: str
    workflowResult: Optional[WorkflowApplyResult] = None
