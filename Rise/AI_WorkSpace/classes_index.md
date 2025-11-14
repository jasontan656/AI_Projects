# 类索引

_生成时间：2025-11-13T14:28:45+00:00_

## rise-project-utility（rise）

### Project Utility Layer

- `src/project_utility/telemetry.py` · `class TelemetryEmitter` · 95 行
  - 说明：（无 docstring，参考片段）
  - 片段：class TelemetryEmitter:     def __init__(self) -> None:         self._jsonl_sink: Optional[_JsonlSink] = None
- `src/project_utility/secrets.py` · `class SecretBox` · 31 行
  - 说明：Lightweight wrapper over Fernet for symmetric secret management.
  - 片段：class SecretBox:     """Lightweight wrapper over Fernet for symmetric secret management.""" 
- `src/project_utility/logging.py` · `class SyncLogHandler(logging.Handler)` · 21 行 · 基类: logging.Handler
  - 说明：Mirror log lines into `current.log` so external watchers can tail startup progress.
  - 片段：class SyncLogHandler(logging.Handler):     """     Mirror log lines into `current.log` so external watchers can tail startup progress.

### One-off Utility Layer

- `src/one_off/_typer_stub.py` · `class Typer` · 56 行
  - 说明：（无 docstring，参考片段）
  - 片段：class Typer:     def __init__(self, *, help: str | None = None) -> None:         self._commands: Dict[str, Callable[..., Any]] = {}
- `src/one_off/_typer_stub.py` · `class BadParameter(Exception)` · 2 行 · 基类: Exception
  - 说明：Raised when CLI arguments are invalid.
  - 片段：class BadParameter(Exception):     """Raised when CLI arguments are invalid."""

### Foundational Service Layer

- `src/foundational_service/persist/redis_queue.py` · `class RedisTaskQueue` · 394 行
  - 说明：（无 docstring，参考片段）
  - 片段：class RedisTaskQueue:     def __init__(         self,
- `src/foundational_service/telemetry/bus.py` · `class TelemetryConsoleSubscriber` · 337 行
  - 说明：Subscribe to TelemetryEmitter events and render them with Rich.
  - 片段：class TelemetryConsoleSubscriber:     """Subscribe to TelemetryEmitter events and render them with Rich.""" 
- `src/foundational_service/messaging/channel_binding_event_publisher.py` · `class ChannelBindingEventPublisher` · 159 行
  - 说明：Publish channel binding events with queue + deadletter fallbacks.
  - 片段：class ChannelBindingEventPublisher:     """Publish channel binding events with queue + deadletter fallbacks.""" 
- `src/foundational_service/persist/worker.py` · `class TaskWorker` · 149 行
  - 说明：（无 docstring，参考片段）
  - 片段：class TaskWorker:     def __init__(         self,
- `src/foundational_service/observability/public_endpoint_probe.py` · `class PublicEndpointSecurityProbe` · 146 行
  - 说明：Evaluate webhook TLS expiry and secret uniqueness.
  - 片段：class PublicEndpointSecurityProbe:     """Evaluate webhook TLS expiry and secret uniqueness.""" 
- `src/foundational_service/telemetry/bus.py` · `class CoverageTestEventRecorder` · 114 行
  - 说明：Write coverage test run events to disk and fan out via SSE-friendly queues.
  - 片段：class CoverageTestEventRecorder:     """Write coverage test run events to disk and fan out via SSE-friendly queues.""" 

### Interface / Entry Layer

- `src/interface_entry/runtime/channel_binding_monitor.py` · `class ChannelBindingMonitor` · 248 行
  - 说明：（无 docstring，参考片段）
  - 片段：class ChannelBindingMonitor:     def __init__(         self,
- `src/interface_entry/runtime/supervisors.py` · `class RuntimeSupervisor` · 188 行
  - 说明：Coordinate task runtime lifecycle and dependency recovery.
  - 片段：class RuntimeSupervisor:     """Coordinate task runtime lifecycle and dependency recovery.""" 
- `src/interface_entry/runtime/capabilities.py` · `class CapabilityRegistry` · 139 行
  - 说明：Thread-safe storage for capability states and probes.
  - 片段：class CapabilityRegistry:     """Thread-safe storage for capability states and probes.""" 
- `src/interface_entry/runtime/channel_binding_event_replayer.py` · `class ChannelBindingEventReplayer` · 92 行
  - 说明：Background helper that replays queued channel binding events.
  - 片段：class ChannelBindingEventReplayer:     """Background helper that replays queued channel binding events.""" 
- `src/interface_entry/middleware/signature.py` · `class SignatureVerifyMiddleware(BaseHTTPMiddleware)` · 66 行 · 基类: BaseHTTPMiddleware
  - 说明：（无 docstring，参考片段）
  - 片段：class SignatureVerifyMiddleware(BaseHTTPMiddleware):     def __init__(self, app: FastAPI, *, webhook_path: str, header_name: str = "X-Telegram-Bot-Api-Secret-Token") -> None:         super().__init__…
- `src/interface_entry/telegram/channel_binding_provider.py` · `class DispatcherChannelBindingProvider(ChannelBindingProvider)` · 47 行 · 基类: ChannelBindingProvider
  - 说明：Read channel binding snapshots directly from aiogram dispatcher workflow_data.
  - 片段：class DispatcherChannelBindingProvider(ChannelBindingProvider):     """Read channel binding snapshots directly from aiogram dispatcher workflow_data.""" 

### Business Service Layer

- `src/business_service/channel/service.py` · `class WorkflowChannelService` · 335 行
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowChannelService:     def __init__(         self,
- `src/business_service/knowledge/snapshot_service.py` · `class KnowledgeSnapshotService` · 329 行
  - 说明：Business-layer service orchestrating knowledge snapshot lifecycle.
  - 片段：class KnowledgeSnapshotService:     """Business-layer service orchestrating knowledge snapshot lifecycle.""" 
- `src/business_service/workflow/observability.py` · `class WorkflowObservabilityService` · 241 行
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowObservabilityService:     def __init__(         self,
- `src/business_service/channel/registry.py` · `class ChannelBindingRegistry` · 197 行
  - 说明：Cache channel binding information for both HTTP and runtime callers.
  - 片段：class ChannelBindingRegistry:     """Cache channel binding information for both HTTP and runtime callers.""" 
- `src/business_service/channel/command_service.py` · `class ChannelBindingCommandService` · 141 行
  - 说明：Application-layer command helper for channel binding mutations.
  - 片段：class ChannelBindingCommandService:     """Application-layer command helper for channel binding mutations.""" 
- `src/business_service/pipeline/repository.py` · `class MongoPipelineNodeRepository` · 118 行
  - 说明：Mongo collection backed repository implementation.
  - 片段：class MongoPipelineNodeRepository:     """Mongo collection backed repository implementation.""" 

### Business Logic Layer

- `src/business_logic/workflow/orchestrator.py` · `class WorkflowOrchestrator` · 161 行
  - 说明：（无 docstring，参考片段）
  - 片段：class WorkflowOrchestrator:     def __init__(         self,

## up（up）

### Interface / Entry Layer

- `src/views/PipelineWorkspace.vue` · `VueComponent<PipelineWorkspace>` · 930 行
  - 说明：<el-container class="workspace-shell">
  - 片段：<template> <el-container class="workspace-shell"> <el-aside width="248px" class="workspace-aside">
- `src/components/WorkflowChannelForm.vue` · `VueComponent<WorkflowChannelForm>` · 611 行
  - 说明：<ChannelFormShell
  - 片段：<template> <ChannelFormShell :published="published"
- `src/components/NodeActionList.vue` · `VueComponent<NodeActionList>` · 506 行
  - 说明：<section class="node-action-list">
  - 片段：<template> <section class="node-action-list"> <div class="node-action-list__toolbar">
- `src/components/WorkflowEditor.vue` · `VueComponent<WorkflowEditor>` · 505 行
  - 说明：<section class="workflow-editor">
  - 片段：<template> <section class="workflow-editor"> <header class="workflow-editor__header">
- `src/components/PromptEditor.vue` · `VueComponent<PromptEditor>` · 495 行
  - 说明：<section :class="['prompt-editor', { 'prompt-editor--full': isFullLayout }]">
  - 片段：<template> <section :class="['prompt-editor', { 'prompt-editor--full': isFullLayout }]"> <header class="prompt-editor__header">
- `src/components/NodeDraftForm.vue` · `VueComponent<NodeDraftForm>` · 454 行
  - 说明：<section :class="['node-draft', { 'node-draft--full': isFullLayout }]">
  - 片段：<template> <section :class="['node-draft', { 'node-draft--full': isFullLayout }]"> <header class="node-draft__header">

### Interface / Entry Layer

- `src/views/PipelineWorkspace.vue` · `VueComponent<PipelineWorkspace>` · 930 行
  - 说明：<el-container class="workspace-shell">
  - 片段：<template> <el-container class="workspace-shell"> <el-aside width="248px" class="workspace-aside">
- `src/components/WorkflowChannelForm.vue` · `VueComponent<WorkflowChannelForm>` · 611 行
  - 说明：<ChannelFormShell
  - 片段：<template> <ChannelFormShell :published="published"
- `src/components/NodeActionList.vue` · `VueComponent<NodeActionList>` · 506 行
  - 说明：<section class="node-action-list">
  - 片段：<template> <section class="node-action-list"> <div class="node-action-list__toolbar">
- `src/components/WorkflowEditor.vue` · `VueComponent<WorkflowEditor>` · 505 行
  - 说明：<section class="workflow-editor">
  - 片段：<template> <section class="workflow-editor"> <header class="workflow-editor__header">
- `src/components/PromptEditor.vue` · `VueComponent<PromptEditor>` · 495 行
  - 说明：<section :class="['prompt-editor', { 'prompt-editor--full': isFullLayout }]">
  - 片段：<template> <section :class="['prompt-editor', { 'prompt-editor--full': isFullLayout }]"> <header class="prompt-editor__header">
- `src/components/NodeDraftForm.vue` · `VueComponent<NodeDraftForm>` · 454 行
  - 说明：<section :class="['node-draft', { 'node-draft--full': isFullLayout }]">
  - 片段：<template> <section :class="['node-draft', { 'node-draft--full': isFullLayout }]"> <header class="node-draft__header">

### Unmapped

- `src/App.vue` · `VueComponent<App>` · 6 行
  - 说明：<router-view />
  - 片段：<template> <router-view /> </template>
