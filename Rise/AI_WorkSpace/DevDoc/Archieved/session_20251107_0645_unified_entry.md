# session_20251107_0645_unified_entry

## 背景与目标
- 将 HTTP、Telegram、内部脚本等所有入口统一接入 Redis Streams 队列，杜绝直接调用 `WorkflowOrchestrator` 的旁路路径。
- 保障 Mongo/外部 API 故障时的重试、挂起、人工恢复链路一致，不再出现“入口耦合”或幂等策略不对齐的情况。
- 在未大规模使用的入口上线前完成基础设施对齐，确保未来放量时仅需打开配置，而无需再次改造。

## 现状评估（2025-11-07）
### HTTP /api/workflows/apply
- `src/interface_entry/http/workflows/routes.py#L145`：`POST /api/workflows/apply` 已构造 `TaskEnvelope` 入队，并允许 `waitForResult` 阻塞等待 Worker 回传；查询接口 `/api/workflows/tasks/{task_id}` 可回读状态。
- `WorkflowApplyRequest`（`src/interface_entry/http/workflows/dto.py`）包含 `idempotencyKey`、`retryMax`、`coreEnvelope` 等字段，已经满足幂等与上下文要求。

### TelegramConversationService
- `src/business_service/conversation/service.py` 中 `TelegramConversationService.process_update()` 仍直接构造 `WorkflowExecutionContext` 并执行 orchestrator；没有复用 `TaskSubmitter`，也未写入 Redis 队列。
- `behavior_telegram_inbound/outbound` 产出的 `core_envelope` 含有 `chat_id`、`payload.context_quotes` 等信息，可被复用，但当前没有生成 `idempotencyKey`。

### Worker / Runtime
- `TaskRuntime` 在 `src/interface_entry/http/dependencies.py` 的 `application_lifespan()` 中初始化。只有 FastAPI 进程启动时 Worker/RetryScheduler 才会运行。若 Telegram bot 独立部署，队列将缺少消费者。
- `src/foundational_service/persist/redis_queue.py` + `worker.py` 已实现 `XADD/XREADGROUP/XAUTOCLAIM`、挂起管理、Mongo 幂等写入，可直接复用。

## 统一方案
### 任务封包与上下文约束
```json
{
  "taskId": "uuid",
  "type": "workflow.execute",
  "payload": {
    "workflowId": "wf_xxx",
    "userText": "...",
    "historyChunks": ["..."],
    "policy": {...},
    "coreEnvelope": {...},
    "telemetry": {
      "channel": "http|telegram|cli",
      "requestId": "..."
    },
    "metadata": {
      "chat_id": "...",
      "source": "telegram"
    },
    "source": "http|telegram|cli"
  },
  "context": {
    "idempotencyKey": "{channel}:{workflowId}:{chatId}:{ts}",
    "traceId": "ContextBridge.request_id",
    "user": {...},
    "requestId": "..."
  },
  "retry": {"count": 0, "max": 3, "nextAttemptAt": 0},
  "status": "pending"
}
```
- **必填字段**：`workflowId`、`userText`、`historyChunks`（允许空）、`coreEnvelope.metadata.chat_id`、`context.idempotencyKey`。
- **入口自定义**：`telemetry.channel` 区分 HTTP/Telegram；`metadata.source` 可填 `telegram-bot`、`http-api` 等。

### HTTP 入口
1. 保持 `WorkflowApplyRequest` 现有实现，仅补充：若调用者未显式传 `idempotencyKey`，按 `{channel}:{workflowId}:{chatId}:{timestamp}` 自动生成。
2. 探测 `waitForResult` 默认值：对需要实时响应的调用仍可阻塞等待，但需通过 `waitTimeoutSeconds` 防止 ASGI backlog。
3. 在响应中统一返回 `taskId`、`status`、`retry`，方便与 Telegram 等入口共享调试方式。

### Telegram 入口
1. 在 `TelegramConversationService` 中注入 `TaskSubmitter`（可通过 DI 或在 runtime 启动时挂载）。
2. `process_update()` 流程调整：
   - 解析 `workflow_id`、`chat_id`、`user_text`、`history_chunks` 后构造 `TaskEnvelope`。
   - 将 `behavior_telegram_inbound` 的 `core_envelope` 与 `telemetry` 原样塞入 payload，填充 `context.idempotencyKey`。
   - 调用 `TaskSubmitter.submit()` 入队；依据 policy 决定是否 `waitForResult`。若异步回复，则先返回带 `taskId` 的 ACK，再由 Worker 成功后走 `behavior_telegram_outbound`。
3. 失败兜底：若 Redis 不可用，返回 `critical` 日志并提示重试，不得回退为同步 orchestrator。

### Worker/Runtime 解耦
- 新增 `tools/persist_worker.py`（或 `src/interface_entry/bootstrap/worker.py`）作为独立启动脚本，引用 `get_task_runtime()` 并调用 `await runtime.start()`。
- FastAPI 与 Telegram 守护进程各自可以选择是否内嵌 Worker；生产部署至少保持一个独立 Worker 实例，避免队列消费依赖 HTTP 生命周期。

### 监控与运营接口
- 现有 `/internal/tasks/stats`, `/internal/tasks/suspended`, `/internal/tasks/{id}`（`src/foundational_service/persist/controllers.py`）保持不变，但需要在 `TaskEnvelope.payload.telemetry` 中包含 `channel/source`，以便在前端监控中区分入口。
- 为 Telegram 新增 `taskId` 日志串联：`ContextBridge.request_id` ≈ `traceId`，可在 Kibana 直接检索。

## Success Path & Core Workflow
1. 入口（HTTP/Telegram/CLI）解析请求 → 构造 `TaskEnvelope` → `TaskSubmitter.enqueue()` 写入 `queue:tasks`。
2. Worker `TaskWorker.read_group()` 取任务 → `WorkflowTaskProcessor` 构造 `WorkflowExecutionContext` → 执行 orchestrator → Mongo 幂等写入。
3. 成功：`mark_completed` + `TaskResultBroker.publish()` → HTTP 调用直接拿到结果；Telegram 则通过 outbound 合同推送。
4. 失败（可重试）：`RetryTask` → `mark_retry` 写入 `queue:retry`，等待 `RetryScheduler` 再次入主队列。
5. 失败（不可恢复或重试耗尽）：`mark_suspended` → `/internal/tasks/suspended` 暴露详情 → 运维选择 resume/drop。

## Failure Modes & Defensive Behaviors
- **Redis 不可用**：入口直接返回错误并记录 `critical`，防止静默丢弃；可以在 ingress 加 `retry-after` header。
- **Worker 崩溃**：独立 Worker 通过 `XAUTOCLAIM` 接管 pending；启动脚本需检查 `queue:tasks` 长度，超过阈值报警。
- **幂等键缺失**：入口必须在封包阶段校验 `chat_id/workflowId` 是否存在；若缺失，直接返回 400，防止任务进入不可恢复状态。
- **长时间等待**：对启用 `waitForResult` 的入口必须在 ASGI handler 中设置 `waitTimeoutSeconds`，超时后返回202 + taskId，避免连接阻塞。
- **重试风暴**：`WorkflowTaskProcessor.retry_delay()` 可根据 `telemetry.channel` 切换曲线（如 Telegram 每次退避 ×2，HTTP 维持固定序列），以免单一入口耗尽队列容量。
- **挂起任务堆积**：当 `queue:suspended` 超过阈值时，触发告警并强制运维处理；必要时增加自动 drop 规则（如超过 24h 未恢复）。

## 约束与 GIVEN/WHEN/THEN 验收
1. **入口统一**  
   - GIVEN Telegram/HTTP 同时入队，WHEN FastAPI 进程停止但独立 Worker 仍运行，THEN 两类任务依然被消费且 `/internal/tasks/stats` 中 `counts.processing` 持续变化。
2. **幂等一致**  
   - GIVEN 同一 `chat_id` 重复点击，WHEN 入口构造请求，THEN `context.idempotencyKey` 相同且 Mongo `workflow_runs` 不会插入重复记录。
3. **超时降级**  
   - GIVEN 调用方 `waitForResult=true`，WHEN Worker 超过 `waitTimeoutSeconds` 未完成，THEN HTTP 返回 202 + `taskId`，并在完成后可通过 `GET /api/workflows/tasks/{task_id}` 查询。
4. **挂起恢复**  
   - GIVEN `retry.max` 次数耗尽，WHEN Worker `mark_suspended`，THEN `/internal/tasks/suspended` 可列出该任务且 `POST /internal/tasks/{task_id}/resume` 能重新排队。
5. **Redis 故障可观察**  
   - GIVEN Redis 关闭，WHEN 入口尝试入队，THEN 立即抛出错误并在日志中包含 `queue.enqueue_failed` 事件，避免静默丢单。

## 实施优先级
1. Telegram 入口改造（入队 + 可选等待逻辑 + 幂等键生成）。
2. 提供独立 Worker 启动脚本，并更新部署手册。
3. HTTP 入口的默认 `idempotencyKey` 与 `telemetry.channel` 补全；前端/调用方需要适应新响应格式。
4. 监控与告警：对 `queue:tasks`、`queue:retry`、`queue:suspended` 建立指标与阈值。