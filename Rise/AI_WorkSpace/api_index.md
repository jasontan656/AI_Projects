# API 索引

_生成时间：2025-11-13T14:28:45+00:00_

## 后端接口（FastAPI）

- `GET /` · `root_probe` · Rise · src/interface_entry/bootstrap/application_builder.py
  - 说明：（无说明）
  - 片段：async def root_probe() -> Dict[str, object]:         snapshot = _capability_snapshot()         return {

- `HEAD /` · `root_probe_head` · Rise · src/interface_entry/bootstrap/application_builder.py
  - 说明：（无说明）
  - 片段：async def root_probe_head() -> Response:         return Response(status_code=status.HTTP_200_OK)

- `GET /healthz` · `healthz` · Rise · src/interface_entry/bootstrap/application_builder.py
  - 说明：（无说明）
  - 片段：async def healthz() -> Dict[str, object]:         snapshot = _capability_snapshot()         state = getattr(app.state, "telegram", None)

- `GET /healthz/startup` · `startup_health` · Rise · src/interface_entry/bootstrap/application_builder.py
  - 说明：（无说明）
  - 片段：async def startup_health() -> Dict[str, object]:         snapshot = _capability_snapshot()         return {

- `GET /healthz/readiness` · `readiness_health` · Rise · src/interface_entry/bootstrap/application_builder.py
  - 说明：（无说明）
  - 片段：async def readiness_health() -> Dict[str, object]:         refresher = getattr(app.state, "capability_refresh", None)         if callable(refresher):

- `GET /internal/memory_health` · `memory_health` · Rise · src/interface_entry/bootstrap/application_builder.py
  - 说明：（无说明）
  - 片段：async def memory_health() -> Dict[str, Any]:         snapshot = getattr(app.state, "memory_snapshot", {})         status = getattr(app.state, "memory_snapshot_status", "unknown")

- `GET /channel-bindings/options` · `list_channel_binding_options` · Rise · src/interface_entry/http/channels/routes.py
  - 说明：（无说明）
  - 片段：async def list_channel_binding_options(     channel: str = Query(default="telegram"),     commands: ChannelBindingCommandService = Depends(get_channel_binding_command_service),

- `GET /channel-bindings/{workflow_id}` · `get_channel_binding` · Rise · src/interface_entry/http/channels/routes.py
  - 说明：（无说明）
  - 片段：async def get_channel_binding(     workflow_id: str,     channel: str = Query(default="telegram"),

- `GET /channel-bindings/diagnostics` · `get_channel_binding_diagnostics` · Rise · src/interface_entry/http/channels/routes.py
  - 说明：（无说明）
  - 片段：async def get_channel_binding_diagnostics(     channel: str = Query(default="telegram"),     registry=Depends(get_channel_binding_registry),

- `PUT /channel-bindings/{workflow_id}` · `upsert_channel_binding` · Rise · src/interface_entry/http/channels/routes.py
  - 说明：（无说明）
  - 片段：async def upsert_channel_binding(     workflow_id: str,     payload: ChannelBindingUpsertRequest,

- `POST /channel-bindings/{workflow_id}/refresh` · `refresh_channel_binding` · Rise · src/interface_entry/http/channels/routes.py
  - 说明：（无说明）
  - 片段：async def refresh_channel_binding(     workflow_id: str,     channel: str = Query(default="telegram"),

- `GET /workflow-channels/{workflow_id}` · `get_workflow_channel` · Rise · src/interface_entry/http/channels/routes.py
  - 说明：（无说明）
  - 片段：async def get_workflow_channel(     workflow_id: str,     channel: str = Query(default="telegram"),

- `PUT /workflow-channels/{workflow_id}` · `save_workflow_channel` · Rise · src/interface_entry/http/channels/routes.py
  - 说明：（无说明）
  - 片段：async def save_workflow_channel(     workflow_id: str,     payload: WorkflowChannelRequest,

- `DELETE /workflow-channels/{workflow_id}` · `delete_workflow_channel` · Rise · src/interface_entry/http/channels/routes.py
  - 说明：（无说明）
  - 片段：async def delete_workflow_channel(     workflow_id: str,     channel: str = Query(default="telegram"),

- `GET /channels/telegram/health` · `telegram_health_check` · Rise · src/interface_entry/http/channels/routes.py
  - 说明：（无说明）
  - 片段：async def telegram_health_check(     workflow_id: str = Query(..., alias="workflowId"),     include_metrics: bool = Query(default=False, alias="includeMetrics"),

- `POST /channels/telegram/test` · `telegram_test_message` · Rise · src/interface_entry/http/channels/routes.py
  - 说明：（无说明）
  - 片段：async def telegram_test_message(     payload: TelegramTestRequest,     service: WorkflowChannelService = Depends(get_workflow_channel_service),

- `PUT /{node_id}` · `update_pipeline_node` · Rise · src/interface_entry/http/pipeline_nodes/routes.py
  - 说明：（无说明）
  - 片段：async def update_pipeline_node(     node_id: str,     payload: PipelineNodeUpdateRequest,

- `DELETE /{node_id}` · `delete_pipeline_node` · Rise · src/interface_entry/http/pipeline_nodes/routes.py
  - 说明：（无说明）
  - 片段：async def delete_pipeline_node(     node_id: str,     background_tasks: BackgroundTasks,

- `PUT /{prompt_id}` · `update_prompt` · Rise · src/interface_entry/http/prompts/routes.py
  - 说明：（无说明）
  - 片段：async def update_prompt(     prompt_id: str,     payload: PromptUpdatePayload,

- `DELETE /{prompt_id}` · `delete_prompt` · Rise · src/interface_entry/http/prompts/routes.py
  - 说明：（无说明）
  - 片段：async def delete_prompt(     prompt_id: str,     background_tasks: BackgroundTasks,

- `PUT /{stage_id}` · `update_stage` · Rise · src/interface_entry/http/stages/routes.py
  - 说明：（无说明）
  - 片段：async def update_stage(     stage_id: str,     payload: StageRequest,

- `DELETE /{stage_id}` · `delete_stage` · Rise · src/interface_entry/http/stages/routes.py
  - 说明：（无说明）
  - 片段：async def delete_stage(     stage_id: str,     service: AsyncStageService = Depends(get_stage_service),

- `PUT /{tool_id}` · `update_tool` · Rise · src/interface_entry/http/tools/routes.py
  - 说明：（无说明）
  - 片段：async def update_tool(     tool_id: str,     payload: ToolRequest,

- `DELETE /{tool_id}` · `delete_tool` · Rise · src/interface_entry/http/tools/routes.py
  - 说明：（无说明）
  - 片段：async def delete_tool(     tool_id: str,     service: AsyncToolService = Depends(get_tool_service),

- `GET /{workflow_id}` · `get_workflow` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def get_workflow(     workflow_id: str,     workflow_service: AsyncWorkflowService = Depends(get_workflow_service),

- `PUT /{workflow_id}` · `update_workflow` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def update_workflow(     workflow_id: str,     payload: WorkflowRequest,

- `POST /{workflow_id}/publish` · `publish_workflow` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def publish_workflow(     workflow_id: str,     payload: WorkflowPublishRequest,

- `POST /{workflow_id}/tests/run` · `trigger_workflow_tests` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def trigger_workflow_tests(     workflow_id: str,     payload: CoverageTestRequest,

- `GET /{workflow_id}/tests/stream` · `stream_workflow_tests` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def stream_workflow_tests(     workflow_id: str,     workflow_service: AsyncWorkflowService = Depends(get_workflow_service),

- `POST /{workflow_id}/rollback` · `rollback_workflow` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def rollback_workflow(     workflow_id: str,     payload: WorkflowRollbackRequest,

- `DELETE /{workflow_id}` · `delete_workflow` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def delete_workflow(     workflow_id: str,     workflow_service: AsyncWorkflowService = Depends(get_workflow_service),

- `POST /apply` · `apply_workflow` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def apply_workflow(     payload: WorkflowApplyRequest,     response: Response,

- `GET /tasks/{task_id}` · `get_task_status` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def get_task_status(task_id: str, runtime: TaskRuntime = Depends(get_task_runtime)) -> ApiResponse[WorkflowApplyResponse]:     envelope = await runtime.queue.get_task(task_id)     if envelope i…

- `GET /{workflow_id}/logs/stream` · `stream_workflow_logs` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def stream_workflow_logs(     workflow_id: str,     actor: ActorContext = Depends(get_actor_context),

- `GET /{workflow_id}/logs` · `list_workflow_logs` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def list_workflow_logs(     workflow_id: str,     limit: int = Query(50, ge=1, le=200),

- `GET /{workflow_id}/variables` · `get_workflow_variables` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def get_workflow_variables(     workflow_id: str,     task_id: Optional[str] = Query(default=None, alias="taskId"),

- `GET /{workflow_id}/tools` · `list_workflow_tools` · Rise · src/interface_entry/http/workflows/routes.py
  - 说明：（无说明）
  - 片段：async def list_workflow_tools(     workflow_id: str,     actor: ActorContext = Depends(get_actor_context),

- `POST /telegram/setup_webhook` · `setup_webhook` · Rise · src/interface_entry/telegram/routes.py
  - 说明：（无说明）
  - 片段：async def setup_webhook(request: Request) -> Response:         body = await request.json()         public_url = body.get("public_url")

- `GET /metrics` · `metrics` · Rise · src/interface_entry/telegram/routes.py
  - 说明：（无说明）
  - 片段：async def metrics() -> Response:         webhook_count = metrics_state.get("webhook_rtt_ms_count", 0)         placeholder_count = metrics_state.get("telegram_placeholder_latency_count", 0)

## 前端服务请求（Up）

- `GET `/api/workflow-channels/${workflowId}?channel=telegram`` · `fetchChannelPolicy` · Up · src/services/channelPolicyClient.js
  - 说明：fetchChannelPolicy
  - 片段：`/api/workflow-channels/${workflowId}?channel=telegram`,
    { method: "GET" }

- `PUT `/api/workflow-channels/${workflowId}`` · `saveChannelPolicy` · Up · src/services/channelPolicyClient.js
  - 说明：saveChannelPolicy
  - 片段：`/api/workflow-channels/${workflowId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  }

- `DELETE `/api/workflow-channels/${workflowId}?channel=telegram`` · `deleteChannelPolicy` · Up · src/services/channelPolicyClient.js
  - 说明：deleteChannelPolicy
  - 片段：`/api/workflow-channels/${workflowId}?channel=telegram`, {
    method: "DELETE",
  }

- `GET `/api/channels/telegram/health?${query.toString()}`` · `fetchChannelHealth` · Up · src/services/channelPolicyClient.js
  - 说明：fetchChannelHealth
  - 片段：`/api/channels/telegram/health?${query.toString()}`,
    { method: "GET" }

- `POST "/api/channels/telegram/test"` · `sendChannelTest` · Up · src/services/channelPolicyClient.js
  - 说明：sendChannelTest
  - 片段："/api/channels/telegram/test", {
    method: "POST",
    body: JSON.stringify({
      workflowId: payload.workflowId,
      chatId: payload.chatId,
      paylo…

- `POST `/api/workflows/${workflowId}/tests/run`` · `runCoverageTests` · Up · src/services/channelPolicyClient.js
  - 说明：runCoverageTests
  - 片段：`/api/workflows/${workflowId}/tests/run`, {
    method: "POST",
    body: JSON.stringify({
      scenarios: Array.isArray(payload.scenarios) ? payload.scenario…

- `POST "/api/channels/telegram/security/validate"` · `validateWebhookSecurity` · Up · src/services/channelPolicyClient.js
  - 说明：validateWebhookSecurity
  - 片段："/api/channels/telegram/security/validate",
    {
      method: "POST",
      body: JSON.stringify(body),
    }

- `GET path` · `requestJson` · Up · src/services/httpClient.js
  - 说明：requestJson
  - 片段：path, options = {}

- `POST "/api/pipeline-nodes"` · `createPipelineNode` · Up · src/services/pipelineService.js
  - 说明：createPipelineNode
  - 片段："/api/pipeline-nodes", {
    method: "POST",
    body: JSON.stringify(body),
  }

- `PUT `/api/pipeline-nodes/${encodeURIComponent(nodeId)}`` · `updatePipelineNode` · Up · src/services/pipelineService.js
  - 说明：updatePipelineNode
  - 片段：`/api/pipeline-nodes/${encodeURIComponent(nodeId)}`,
    {
      method: "PUT",
      body: JSON.stringify(body),
    }

- `GET path` · `listPipelineNodes` · Up · src/services/pipelineService.js
  - 说明：listPipelineNodes
  - 片段：path, { method: "GET" }

- `DELETE `/api/pipeline-nodes/${encodeURIComponent(nodeId)}`` · `deletePipelineNode` · Up · src/services/pipelineService.js
  - 说明：deletePipelineNode
  - 片段：`/api/pipeline-nodes/${encodeURIComponent(nodeId)}`,
    {
      method: "DELETE",
    }

- `GET `/api/prompts${search ? `?${search}` : ""}`` · `listPrompts` · Up · src/services/promptService.js
  - 说明：listPrompts
  - 片段：`/api/prompts${search ? `?${search}` : ""}`,
    { method: "GET" }

- `POST "/api/prompts"` · `createPrompt` · Up · src/services/promptService.js
  - 说明：createPrompt
  - 片段："/api/prompts", {
    method: "POST",
    body: JSON.stringify({
      name,
      markdown,
    }),
  }

- `PUT `/api/prompts/${encodeURIComponent(promptId)}`` · `updatePrompt` · Up · src/services/promptService.js
  - 说明：updatePrompt
  - 片段：`/api/prompts/${encodeURIComponent(promptId)}`,
    {
      method: "PUT",
      body: JSON.stringify(body),
    }

- `DELETE `/api/prompts/${encodeURIComponent(promptId)}`` · `deletePrompt` · Up · src/services/promptService.js
  - 说明：deletePrompt
  - 片段：`/api/prompts/${encodeURIComponent(promptId)}`,
    {
      method: "DELETE",
    }

- `GET `/api/workflows/${workflowId}/variables`` · `listWorkflowVariables` · Up · src/services/workflowMetaService.js
  - 说明：listWorkflowVariables
  - 片段：`/api/workflows/${workflowId}/variables`,
    { method: "GET" }

- `GET `/api/workflows/${workflowId}/tools`` · `listWorkflowTools` · Up · src/services/workflowMetaService.js
  - 说明：listWorkflowTools
  - 片段：`/api/workflows/${workflowId}/tools`,
    { method: "GET" }

- `GET `/api/workflows${search ? `?${search}` : ""}`` · `listWorkflows` · Up · src/services/workflowService.js
  - 说明：listWorkflows
  - 片段：`/api/workflows${search ? `?${search}` : ""}`,
    { method: "GET" }

- `GET `/api/workflows/${workflowId}`` · `getWorkflow` · Up · src/services/workflowService.js
  - 说明：getWorkflow
  - 片段：`/api/workflows/${workflowId}`, {
    method: "GET",
  }

- `POST "/api/workflows"` · `createWorkflow` · Up · src/services/workflowService.js
  - 说明：createWorkflow
  - 片段："/api/workflows", {
    method: "POST",
    body: JSON.stringify(body),
  }

- `PUT `/api/workflows/${workflowId}`` · `updateWorkflow` · Up · src/services/workflowService.js
  - 说明：updateWorkflow
  - 片段：`/api/workflows/${workflowId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  }

- `DELETE `/api/workflows/${workflowId}`` · `deleteWorkflow` · Up · src/services/workflowService.js
  - 说明：deleteWorkflow
  - 片段：`/api/workflows/${workflowId}`, {
    method: "DELETE",
  }

- `POST `/api/workflows/${workflowId}/publish`` · `publishWorkflow` · Up · src/services/workflowService.js
  - 说明：publishWorkflow
  - 片段：`/api/workflows/${workflowId}/publish`,
    {
      method: "POST",
      body: JSON.stringify({
        notes: payload.notes || "",
      }),
    }

- `POST `/api/workflows/${workflowId}/rollback`` · `rollbackWorkflow` · Up · src/services/workflowService.js
  - 说明：rollbackWorkflow
  - 片段：`/api/workflows/${workflowId}/rollback`,
    {
      method: "POST",
      body: JSON.stringify({ version }),
    }
