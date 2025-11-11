# Workflow 可观测性接口补齐方案（session_20251109_0355）

## 背景与现状
- `AI_WorkSpace/Reports/1.md` 已验证 `/api/prompts`、`/api/pipeline-nodes`、`/api/workflows` 等 CRUD 全部畅通，唯一阻塞是前端根据联调文档调用的日志/变量/工具接口在后端尚未实现，导致 404。
- `src/interface_entry/http/workflows/routes.py` 当前仅暴露列表、创建、更新、`/apply` 以及任务查询；DTO (`dto.py`) 中同样缺乏日志或可观测性结构体，意味着需要从 Interface 层到 Business Service 层整体补齐。
- `openspec/PROJECT_STRUCTURE.md` 要求 Interface 层只做协议转换，日志抓取/变量快照逻辑必须封装在 Business Service → Foundational Service（访问 TaskRuntime/Persist）的下行链路中。

## 设计目标
1. 为单个 workflow 提供**实时执行流**与**历史记录**两种可观测能力，覆盖日志内容、变量快照、可用工具集三类元数据。
2. 复用现有 `TaskRuntime` 与 `TaskEnvelope` 数据模型，避免额外消息格式；全部接口输出统一包裹在 `ApiResponse + ApiMeta` 中。
3. 严格遵守层次结构：
   - Interface：新增 4 条 HTTP 路由。
   - Business Service：新增 `WorkflowObservabilityService` 聚合查询入口。
   - Foundational Service：扩展 `Persist`/`TaskRuntime` 读取历史日志、变量、工具信息的查询函数。

## API 设计（Interface 层）
### 1. GET `/api/workflows/{workflow_id}/logs/stream`
- **用途**：SSE 实时推送 workflow 执行事件，供前端日志面板订阅。
- **实现**：
  - `routes.py` 新增 `async def stream_workflow_logs(..., response: StreamingResponse)`，调用 Business Service 返回 async generator。
  - `media_type="text/event-stream"`，每条数据结构：`{"type":"stage.log","stageId":"...","timestamp":169...,"payload":{...}}`，需包含 `requestId` 与 `taskId` 以便客户端关联。
  - 超时策略：Server 保持 30s ping（`event: heartbeat`），无事件时发送 keep-alive，避免浏览器断链。

### 2. GET `/api/workflows/{workflow_id}/logs?taskId=&limit=&since=`
- **用途**：分页检索历史日志。默认最近 50 条，支持 `since`（ISO8601）与 `cursor`（taskId + index）。
- **响应**：
```json
{
  "data": {
    "workflowId": "c9fc7d0e-...",
    "items": [
      {
        "taskId": "task-123",
        "stageId": "stage-ingest",
        "level": "info",
        "message": "Node resolved prompt",
        "metadata": {"usage": {"input": 123,"output": 512}},
        "timestamp": "2025-11-09T03:21:06.123Z"
      }
    ],
    "nextCursor": "task-123#57"
  },
  "meta": {"requestId": "..."}
}
```

### 3. GET `/api/workflows/{workflow_id}/variables`
- **用途**：返回 workflow 最近一次执行（或指定 `taskId`）的变量快照，字段与前端 `workflowMetaService` 契约对齐。
- **响应**：`{"workflowId":...,"taskId":...,"variables":[{"name":"chat_id","type":"string","value":"123"}]}`。

### 4. GET `/api/workflows/{workflow_id}/tools`
- **用途**：回传该 workflow 生效的工具/动作签名，数据源来自 workflow 定义（stage metadata）而非 TaskRuntime，以便前端展示“将调用哪些外部工具”。
- **响应**：`{"workflowId":...,"tools":[{"name":"vector-search","kind":"http","config":{...}}]}`。

## Business / Foundational 层扩展
- **新增 `business_service/workflow_observability.py`**：
  - 方法 `stream_logs(workflow_id: str, actor: ActorContext) -> AsyncIterator[str]`：校验 actor 权限 → 调用 `FoundationalLogReader.iter_log_events` → 包装成 SSE 文本。
  - 方法 `list_logs(workflow_id: str, filters: LogQuery)`：聚合 TaskRuntime queue + 历史持久层（若 snapshot 不存在则回退到 envelope.result.telemetry）。
  - 方法 `get_variables(workflow_id: str, task_id: Optional[str])`：优先读取 TaskRuntime snapshot，找不到则回退 StageResult.telemetry。
  - 方法 `list_tools(workflow_id: str)`：调用 `AsyncWorkflowService.get(workflow_id)`，解析 `metadata["tools"]` 或 stage schema。
- **Foundational 扩展**：
  - `foundational_service.persist` 添加 `LogRecord`/`VariableSnapshot` 模型与读写接口；若暂未持久化，可先从 `TaskRuntime.queue.get_task` 的 `result.telemetry` 中解包。
  - 统一在 `TaskRuntime.results` 注册心跳超时，避免 SSE 无界等待。

## 成功路径与核心流程
1. 前端订阅 `/logs/stream`：Interface 层校验 Actor → Business Service 校验 workflow 存在 → Foundational 返回 async generator → SSE 按事件顺序推送，心跳保持连接 → 前端展示实时日志。
2. 用户打开“历史”页：前端调用 `/logs?limit=50`，服务层按 cursor 读取 Persist 日志并返回下一游标；随后调用 `/variables`、`/tools`，分别获取最新变量快照与声明式工具列表。
3. Telegram 测试：当 `/apply` 触发 workflow 后，TaskRuntime 写入执行结果；日志接口读取相同数据源，因此可立即在控制台复现执行轨迹，完成端到端验证。

## 失败模式与防御策略
- **Workflow 不存在或 Actor 无权限**：`stream_logs`、`list_logs`、`get_variables` 全部抛出 `HTTP 404/403`，禁止泄露 workflowId 是否存在的信息（统一返回 `WORKFLOW_NOT_ACCESSIBLE`）。
- **TaskRuntime 中无执行记录**：历史接口返回空数组，并在 `meta.warnings` 加入 `"NO_EXECUTION"`；前端据此展示“暂无执行”。
- **SSE 超时/客户端断开**：Business 层检测 `asyncio.CancelledError`，调用 `FoundationalLogReader.unregister(task_id)` 释放资源；同时每 30s 发送心跳，超出 2 个心跳周期无响应则终止连接。
- **Persist 查询过载**：对 `/logs` 设置 `limit<=200`，并在 Foundational 层使用时间 + taskId 复合索引；若查询窗口过长需返回 `429`，提示缩小窗口。
- **工具列表缺口**：若 workflow metadata 未定义 `tools`，接口返回空数组并附加 `source:"definition"`，提示客户端需 fallback 至 stage 动作说明。

## 约束与验收（GIVEN / WHEN / THEN）
1. **GIVEN** 存在 workflow 且 TaskRuntime 捕获执行日志；**WHEN** 客户端以有效 token 订阅 `/logs/stream`；**THEN** SSE 必须在 1s 内返回 `event: workflow.log` 或 `event: heartbeat`。
2. **GIVEN** workflow 近期执行 N≥1 次；**WHEN** 调用 `/logs?limit=50`；**THEN** 返回 `items` 数量 ≤50 且含按时间倒序排列的 `taskId/stageId`，并提供 `nextCursor`。
3. **GIVEN** `taskId` 无变量记录；**WHEN** 请求 `/variables?taskId=missing`；**THEN** 返回 `variables: []`，`meta.warnings` 包含 `VARIABLE_SNAPSHOT_MISSING`，HTTP 状态仍为 200，便于前端做空态提示。
4. **GIVEN** workflow metadata 中含工具声明；**WHEN** 获取 `/tools`；**THEN** 返回的 `tools[].config` 必须与 workflow 定义一致，且字段受 Actor 权限裁剪（例如不返回密钥）。
5. **GIVEN** Actor 无访问权限；**WHEN** 调用任一可观测性接口；**THEN** 统一返回 `403` 与 `code: WORKFLOW_NOT_ACCESSIBLE`，日志中记录审计事件。

## 后续步骤
1. 编写 `business_service/workflow_observability.py` 与对应 Foundational 读取器，确保与 `TaskRuntime` 解耦。
2. 在 `routes.py`、`dto.py` 增加响应模型与新路由，更新 `interface_entry/http/__init__.py` 以注册 router。
3. 扩展 `AI_WorkSpace/DevDoc/On/session_20251107_0905_log_lifecycle.md` 的依赖图，说明日志落地位置，保持文档一致性。
4. 配合前端在 `logService/workflowMetaService` 中写死的 URL 中启用新路径，完成 E2E 联调。
