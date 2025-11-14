# Schema 索引

_生成时间：2025-11-13T14:28:45+00:00_

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
- `src/foundational_service/contracts/channel_events.py` · `class ChannelBindingEvent` · 46 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class ChannelBindingEvent:     channel: str     workflow_id: str
- `src/foundational_service/contracts/channel_events.py` · `class WebhookCredentialRotatedEvent` · 40 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class WebhookCredentialRotatedEvent:     workflow_id: str     channel: str
- `src/foundational_service/contracts/channel_events.py` · `class ChannelBindingHealthEvent` · 31 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class ChannelBindingHealthEvent:     channel: str     workflow_id: str
- `src/foundational_service/persist/rabbit_bridge.py` · `class RabbitConfig` · 31 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class RabbitConfig:     url: str     exchange: str = os.getenv("RABBITMQ_EXCHANGE", "rise.tasks.durable")

### Interface / Entry Layer

- `src/interface_entry/runtime/public_endpoint.py` · `class PublicEndpointProbe` · 47 行 · 装饰器: dataclass
  - 说明：Perform lightweight HEAD checks to confirm webhook reachability.
  - 片段：class PublicEndpointProbe:     """Perform lightweight HEAD checks to confirm webhook reachability.""" 
- `src/interface_entry/http/workflows/dto.py` · `class WorkflowResponse(BaseModel)` · 21 行 · 基类: BaseModel
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowResponse(BaseModel):     id: str = Field(..., alias="workflowId")     name: str
- `src/interface_entry/http/channels/dto.py` · `class ChannelBindingConfig(BaseModel)` · 18 行 · 基类: BaseModel
  - 说明：（无 docstring，参考片段）
  - 片段：class ChannelBindingConfig(BaseModel):     botToken: Optional[str] = Field(default=None, description="Telegram bot token (omit to reuse existing)")     webhookUrl: Optional[str] = Field(default=None,…
- `src/interface_entry/http/channels/dto.py` · `class WorkflowChannelRequest(BaseModel)` · 18 行 · 基类: BaseModel
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowChannelRequest(BaseModel):     botToken: Optional[str] = Field(default=None, description="Telegram bot token (omit to reuse existing)")     webhookUrl: Optional[str] = Field(default=Non…
- `src/interface_entry/runtime/capabilities.py` · `class CapabilityProbe` · 16 行 · 装饰器: dataclass
  - 说明：Descriptor for a capability checker coroutine.
  - 片段：class CapabilityProbe:     """Descriptor for a capability checker coroutine.""" 
- `src/interface_entry/http/dependencies.py` · `class AppSettings(BaseSettings)` · 14 行 · 基类: BaseSettings
  - 说明：（无 docstring，参考片段）
  - 片段：class AppSettings(BaseSettings):     model_config = SettingsConfigDict(         extra="allow",

### Business Service Layer

- `src/business_service/conversation/service.py` · `class TelegramConversationService` · 1087 行 · 装饰器: dataclass
  - 说明：面向 Telegram 渠道的业务服务门面。
  - 片段：class TelegramConversationService:     """面向 Telegram 渠道的业务服务门面。""" 
- `src/business_service/workflow/service.py` · `class AsyncWorkflowService` · 164 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class AsyncWorkflowService:     repository: AsyncWorkflowRepository 
- `src/business_service/workflow/models.py` · `class WorkflowDefinition` · 96 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowDefinition:     workflow_id: str     name: str
- `src/business_service/channel/models.py` · `class WorkflowChannelPolicy` · 89 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowChannelPolicy:     workflow_id: str     channel: str
- `src/business_service/pipeline/models.py` · `class PipelineNode` · 75 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class PipelineNode:     node_id: str     name: str
- `src/business_service/conversation/service.py` · `class PipelineNodeGuardService(PipelineGuardService)` · 72 行 · 基类: PipelineGuardService; 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class PipelineNodeGuardService(PipelineGuardService):     pipeline_service: AsyncPipelineNodeService     fallback: PipelineGuardService = field(default_factory=_DefaultPipelineGuardService)

### Business Logic Layer

- `src/business_logic/conversation/telegram_flow.py` · `class TelegramConversationFlow` · 49 行 · 装饰器: dataclass
  - 说明：委派到业务服务层进行会话编排。
  - 片段：class TelegramConversationFlow:     """委派到业务服务层进行会话编排。""" 
- `src/business_logic/knowledge/snapshot_orchestrator.py` · `class KnowledgeSnapshotOrchestrator` · 29 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class KnowledgeSnapshotOrchestrator:     service: KnowledgeSnapshotService 
- `src/business_logic/workflow/models.py` · `class WorkflowExecutionContext` · 25 行 · 装饰器: dataclass
  - 说明：Normalized execution context passed into the orchestrator.
  - 片段：class WorkflowExecutionContext:     """Normalized execution context passed into the orchestrator.""" 
- `src/business_logic/knowledge/models.py` · `class KnowledgeSnapshotState` · 19 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class KnowledgeSnapshotState:     snapshot: Mapping[str, Any]     snapshot_dict: Mapping[str, Any]
- `src/business_logic/conversation/models.py` · `class ConversationResult` · 17 行 · 装饰器: dataclass
  - 说明：（无 docstring，参考片段）
  - 片段：class ConversationResult:     status: ConversationStatus     mode: ConversationMode
- `src/business_logic/workflow/models.py` · `class WorkflowStageResult` · 8 行 · 装饰器: dataclass
  - 说明：Represents the outcome of a single workflow stage execution.
  - 片段：class WorkflowStageResult:     """Represents the outcome of a single workflow stage execution.""" 

## up（up）

### Business Service Layer

- `src/stores/channelPolicy.js` · `defineStore('channelPolicy')` · 15 行
  - 说明：（无 docstring，参考片段）
  - 片段：defineStore("channelPolicy", {   state: () => ({     policy: createChannelPolicy(),
- `src/stores/workflowDraft.js` · `defineStore('workflowDraft')` · 15 行
  - 说明：（无 docstring，参考片段）
  - 片段：defineStore("workflowDraft", {   state: () => ({     workflows: [],
- `src/stores/pipelineDraft.js` · `defineStore('pipelineDraft')` · 10 行
  - 说明：（无 docstring，参考片段）
  - 片段：defineStore("pipelineDraft", {   state: () => createInitialState(),   getters: {
- `src/stores/promptDraft.js` · `defineStore('promptDraft')` · 10 行
  - 说明：（无 docstring，参考片段）
  - 片段：defineStore("promptDraft", {   state: () => createInitialState(),   getters: {
