from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, Field

__all__ = [
    "WorkflowApplyRequest",
    "WorkflowApplyResponse",
    "WorkflowCoverageStatusResponse",
    "WorkflowRequest",
    "WorkflowResponse",
    "WorkflowPublishRequest",
    "WorkflowRollbackRequest",
    "WorkflowLogItem",
    "WorkflowLogListResponse",
    "WorkflowVariableEntry",
    "WorkflowVariablesResponse",
    "WorkflowToolDescriptor",
    "WorkflowToolsResponse",
    "CoverageTestRequest",
]


class PromptBinding(BaseModel):
    nodeId: str
    promptId: str


class WorkflowPublishRecord(BaseModel):
    version: int
    action: str
    actor: Optional[str] = None
    comment: Optional[str] = None
    timestamp: datetime
    snapshot: Mapping[str, Any] = Field(default_factory=dict)


class WorkflowRequest(BaseModel):
    name: str = Field(..., description="流程名称")
    description: str = Field("", description="流程描述")
    stageIds: Optional[Sequence[str]] = Field(default=None, description="阶段 ID 顺序列表")
    metadata: Optional[Mapping[str, Any]] = Field(default=None, description="自定义元数据")
    nodeSequence: Optional[Sequence[str]] = Field(default=None, description="运行节点顺序")
    promptBindings: Optional[Sequence[PromptBinding]] = Field(default=None, description="节点-提示词绑定")
    strategy: Optional[Mapping[str, Any]] = Field(default=None, description="执行策略")
    status: Optional[str] = Field(default=None, description="workflow 状态")
    version: Optional[int] = Field(default=None, description="用于并发控制的当前版本号")


class WorkflowPublishMeta(BaseModel):
    status: str
    version: int
    publishedVersion: int
    pendingChanges: bool


class WorkflowCoverageStatusResponse(BaseModel):
    status: str
    updatedAt: datetime
    scenarios: Sequence[str] = Field(default_factory=tuple)
    mode: str = "webhook"
    lastRunId: Optional[str] = None
    lastError: Optional[str] = None
    actorId: Optional[str] = None


class WorkflowResponse(BaseModel):
    id: str = Field(..., alias="workflowId")
    name: str
    description: str
    stageIds: Sequence[str] = Field(default_factory=list)
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    nodeSequence: Sequence[str] = Field(default_factory=tuple)
    promptBindings: Sequence[PromptBinding] = Field(default_factory=tuple)
    strategy: Mapping[str, Any] = Field(default_factory=dict)
    status: str = "draft"
    version: int
    publishedVersion: int = Field(default=0, alias="publishedVersion")
    pendingChanges: bool = Field(default=True, alias="pendingChanges")
    historyChecksum: str = Field(default="")
    publishHistory: Sequence[WorkflowPublishRecord] = Field(default_factory=tuple)
    publishMeta: WorkflowPublishMeta
    updatedAt: Any
    updatedBy: Optional[str] = None
    testCoverage: Optional[WorkflowCoverageStatusResponse] = None

    class Config:
        populate_by_name = True


class WorkflowStageResult(BaseModel):
    stageId: str
    name: str
    promptUsed: Optional[str] = None
    outputText: str
    usage: Optional[Mapping[str, Any]] = None


class TaskRetryMetadata(BaseModel):
    count: int = 0
    max: int = 3
    nextAttemptAt: Optional[float] = None


class WorkflowApplyResult(BaseModel):
    finalText: str = Field("", description="最终文本输出")
    stageResults: Sequence[WorkflowStageResult] = Field(default_factory=tuple)
    telemetry: Mapping[str, Any] = Field(default_factory=dict)


class CoverageTestRequest(BaseModel):
    scenarios: Sequence[str] = Field(default_factory=tuple)
    mode: str = "webhook"


class WorkflowApplyRequest(BaseModel):
    workflowId: str = Field(..., description="目标 workflowId")
    userText: str = Field("", description="用户输入内容")
    chatId: Optional[str] = Field(default=None, description="用于幂等写入的 chat_id")
    history: Sequence[str] = Field(default_factory=tuple, description="历史上下文片段")
    policy: Mapping[str, Any] = Field(default_factory=dict, description="执行策略覆盖")
    coreEnvelope: Mapping[str, Any] = Field(default_factory=dict, description="下游 core envelope 元数据")
    telemetry: Mapping[str, Any] = Field(default_factory=dict, description="上游 telemetry")
    metadata: Mapping[str, Any] = Field(default_factory=dict, description="任意附加元数据")
    user: Mapping[str, Any] = Field(default_factory=dict, description="请求用户信息")
    idempotencyKey: Optional[str] = Field(default=None, description="自定义幂等键")
    retryMax: int = Field(default=3, ge=1, le=10, description="最大重试次数")
    waitForResult: bool = Field(default=True, description="是否等待执行完成")
    waitTimeoutSeconds: float = Field(default=20.0, ge=1.0, le=120.0, description="等待结果超时时间")


class WorkflowApplyResponse(BaseModel):
    taskId: str
    status: str
    result: Optional[WorkflowApplyResult] = None
    retry: TaskRetryMetadata = Field(default_factory=TaskRetryMetadata)
    error: Optional[str] = None


class WorkflowPublishRequest(BaseModel):
    comment: Optional[str] = None
    targetVersion: Optional[int] = Field(default=None, ge=1)


class WorkflowRollbackRequest(BaseModel):
    targetVersion: int = Field(..., ge=1)


class WorkflowLogItem(BaseModel):
    taskId: str
    stageId: Optional[str] = None
    stageName: Optional[str] = None
    level: str = "info"
    message: str = ""
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    timestamp: Any
    cursor: str


class WorkflowLogListResponse(BaseModel):
    workflowId: str
    items: Sequence[WorkflowLogItem] = Field(default_factory=tuple)
    nextCursor: Optional[str] = None


class WorkflowVariableEntry(BaseModel):
    name: str
    type: str
    value: Any


class WorkflowVariablesResponse(BaseModel):
    workflowId: str
    taskId: Optional[str] = None
    variables: Sequence[WorkflowVariableEntry] = Field(default_factory=tuple)


class WorkflowToolDescriptor(BaseModel):
    toolId: Optional[str] = None
    name: Optional[str] = None
    kind: Optional[str] = None
    config: Mapping[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    promptSnippet: Optional[str] = None


class WorkflowToolsResponse(BaseModel):
    workflowId: str
    source: str
    tools: Sequence[WorkflowToolDescriptor] = Field(default_factory=tuple)

