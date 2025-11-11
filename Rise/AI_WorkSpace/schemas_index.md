# Schema 索引

_生成时间：2025-11-11T16:04:45+00:00_

## rise-project-utility（rise）

### Project Utility Layer

- `src/project_utility/tracing.py` · `class TraceSpan` · 29 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class TraceSpan:     name: str     attributes: Dict[str, Any] = field(default_factory=dict)
- `src/project_utility/context.py` · `class ContextBridge` · 19 行 · 装饰器: dataclass
  - 说明：ContextVar-backed helper that guarantees a request identifier is always available.
  - 片段：class ContextBridge:     """ContextVar-backed helper that guarantees a request identifier is always available.""" 

### One-off Utility Layer

- `src/one_off/sources/service_crawler/dedupe_pdfs.py` · `class PdfDoc` · 18 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class PdfDoc:     path: Path     classification: str
- `src/one_off/sources/service_crawler/rename_attachments.py` · `class Attachment` · 15 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class Attachment:     path: Path     service_name: str
- `src/one_off/registry.py` · `class ScriptMetadata` · 8 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class ScriptMetadata:     command: str     module: str
- `src/one_off/sources/service_crawler/fetch_forms.py` · `class Attachment` · 5 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class Attachment:     url: str     title: str
- `src/one_off/_typer_stub.py` · `class Argument` · 4 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class Argument:     default: Optional[Any] = None     nargs: Optional[int] = None
- `src/one_off/sources/service_crawler/update_prices.py` · `class FeeRecord` · 4 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class FeeRecord:     service: str     url: str

### Foundational Service Layer

- `src/foundational_service/contracts/envelope.py` · `class CoreEnvelope(BaseModel)` · 147 行 · 基类: BaseModel
  - 说明：（无 docstring，参考片段）
  - 片段：class CoreEnvelope(BaseModel):     metadata: Metadata     payload: Payload
- `src/foundational_service/persist/task_envelope.py` · `class TaskEnvelope` · 95 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class TaskEnvelope:     task_id: str     type: str
- `src/foundational_service/persist/rabbit_bridge.py` · `class RabbitConfig` · 31 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class RabbitConfig:     url: str     exchange: str = os.getenv("RABBITMQ_EXCHANGE", "rise.tasks.durable")
- `src/foundational_service/persist/task_envelope.py` · `class RetryState` · 26 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class RetryState:     count: int = 0     max: int = 3
- `src/foundational_service/contracts/envelope.py` · `class ExtFlags(BaseModel)` · 15 行 · 基类: BaseModel
  - 说明：（无 docstring，参考片段）
  - 片段：class ExtFlags(BaseModel):     reply_to_bot: Optional[bool] = None     intent_hint: Optional[str] = None
- `src/foundational_service/contracts/envelope.py` · `class Telemetry(BaseModel)` · 11 行 · 基类: BaseModel
  - 说明：（无 docstring，参考片段）
  - 片段：class Telemetry(BaseModel):     request_id: Optional[str] = None     trace_id: Optional[str] = None

### Interface / Entry Layer

- `src/interface_entry/runtime/public_endpoint.py` · `class PublicEndpointProbe` · 47 行 · 装饰器: dataclass
  - 说明：Perform lightweight HEAD checks to confirm webhook reachability.
  - 片段：class PublicEndpointProbe:     """Perform lightweight HEAD checks to confirm webhook reachability.""" 
- `src/interface_entry/http/workflows/dto.py` · `class WorkflowResponse(BaseModel)` · 20 行 · 基类: BaseModel
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowResponse(BaseModel):     id: str = Field(..., alias="workflowId")     name: str
- `src/interface_entry/runtime/capabilities.py` · `class CapabilityProbe` · 16 行 · 装饰器: dataclass
  - 说明：Descriptor for a capability checker coroutine.
  - 片段：class CapabilityProbe:     """Descriptor for a capability checker coroutine.""" 
- `src/interface_entry/http/workflows/dto.py` · `class WorkflowApplyRequest(BaseModel)` · 14 行 · 基类: BaseModel
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowApplyRequest(BaseModel):     workflowId: str = Field(..., description="目标 workflowId")     userText: str = Field("", description="用户输入内容")
- `src/interface_entry/http/channels/dto.py` · `class ChannelBindingUpsertRequest(BaseModel)` · 13 行 · 基类: BaseModel
  - 说明：（无 docstring，参考片段）
  - 片段：class ChannelBindingUpsertRequest(BaseModel):     channel: str = Field(default="telegram")     enabled: bool = Field(default=True)
- `src/interface_entry/http/pipeline_nodes/dto.py` · `class PipelineNodeSnapshot(BaseModel)` · 13 行 · 基类: BaseModel
  - 说明：（无 docstring，参考片段）
  - 片段：class PipelineNodeSnapshot(BaseModel):     id: str     name: str

### Business Service Layer

- `src/business_service/conversation/service.py` · `class TelegramConversationService` · 843 行 · 装饰器: dataclass
  - 说明：面向 Telegram 渠道的业务服务门面。
  - 片段：class TelegramConversationService:     """面向 Telegram 渠道的业务服务门面。""" 
- `src/business_service/workflow/service.py` · `class AsyncWorkflowService` · 164 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class AsyncWorkflowService:     repository: AsyncWorkflowRepository 
- `src/business_service/workflow/models.py` · `class WorkflowDefinition` · 96 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowDefinition:     workflow_id: str     name: str
- `src/business_service/channel/models.py` · `class WorkflowChannelPolicy` · 84 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowChannelPolicy:     workflow_id: str     channel: str
- `src/business_service/pipeline/models.py` · `class PipelineNode` · 75 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class PipelineNode:     node_id: str     name: str
- `src/business_service/workflow/models.py` · `class StageDefinition` · 64 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class StageDefinition:     stage_id: str     name: str

### Business Logic Layer

- `src/business_logic/conversation/telegram_flow.py` · `class TelegramConversationFlow` · 46 行 · 装饰器: dataclass
  - 说明：委派到业务服务层进行会话编排。
  - 片段：class TelegramConversationFlow:     """委派到业务服务层进行会话编排。""" 
- `src/business_logic/knowledge/snapshot_orchestrator.py` · `class KnowledgeSnapshotOrchestrator` · 29 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class KnowledgeSnapshotOrchestrator:     service: KnowledgeSnapshotService 
- `src/business_logic/knowledge/models.py` · `class KnowledgeSnapshotState` · 19 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class KnowledgeSnapshotState:     snapshot: Mapping[str, Any]     snapshot_dict: Mapping[str, Any]
- `src/business_logic/workflow/orchestrator.py` · `class WorkflowExecutionContext` · 18 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowExecutionContext:     workflow_id: str     request_id: str
- `src/business_logic/conversation/models.py` · `class ConversationResult` · 17 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class ConversationResult:     status: ConversationStatus     mode: ConversationMode
- `src/business_logic/workflow/orchestrator.py` · `class WorkflowStageResult` · 6 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowStageResult:     stage_id: str     name: str

## up（up）

### Business Service Layer

- `src/stores/channelPolicy.js` · `defineStore('channelPolicy')` · 15 行
  - 说明：（无 docstring，参考片段）
  - 片段：defineStore("channelPolicy", {   state: () => ({     policy: createEmptyPolicy(),
- `src/stores/workflowDraft.js` · `defineStore('workflowDraft')` · 15 行
  - 说明：（无 docstring，参考片段）
  - 片段：defineStore("workflowDraft", {   state: () => ({     workflows: [],
- `src/stores/pipelineDraft.js` · `defineStore('pipelineDraft')` · 10 行
  - 说明：（无 docstring，参考片段）
  - 片段：defineStore("pipelineDraft", {   state: () => createInitialState(),   getters: {
- `src/stores/promptDraft.js` · `defineStore('promptDraft')` · 10 行
  - 说明：（无 docstring，参考片段）
  - 片段：defineStore("promptDraft", {   state: () => createInitialState(),   getters: {
