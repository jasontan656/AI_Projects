# External Entrypoint vs Admin 面板

本节描述 Rise 在 2025-11-08 之后的入口分层，避免再出现 Telegram 直接调用 Workflow Orchestrator 的同步路径。

## 统一外部入口

- **覆盖范围**：Telegram Bot 以及未来的 WhatsApp/Webhook/CLI Agent 等面对终端用户的渠道。
- **交互流程**：入口封包 `TaskEnvelope` → Redis Streams (`queue:tasks`) → Worker → TaskResultBroker。
- **封包字段**：`workflowId`、`userText`、`historyChunks`、`policy`、`coreEnvelope`、`telemetry.channel`、`metadata.chat_id/source`、`context.idempotencyKey`（`telegram:{workflow}:{chat_id}:{message_id}`）。
- **去重规则**：idempotency key 会在 Mongo `workflow_runs` 中 upsert，防止 Telegram 重发导致重复回复。
- **实时 vs 异步**：通过 `policy.entrypoints.telegram.wait_for_result` 控制；异步模式会立即返回排队确认，并由后台协程监听 `AsyncResultHandle` 推送正式回复。

## Admin Panel 角色

- `/api/workflows/apply`、Stage/Prompt/Tool CRUD 等 API 属于 **内部运维工具**，用于配置、调试、回放。
- Admin 请求仍可选择 `waitForResult`，但它们不属于外部流量，失败时应直接暴露错误以提醒开发者修复。
- 文档与代码明确标识：**Admin Panel ≠ 外部入口**，禁止为它补贴兜底队列逻辑。

## 失败策略

| 场景 | Telegram 行为 | 记录/告警 |
| --- | --- | --- |
| Redis 不可用或 enqueue 失败 | 返回 `enqueue_failure_text`（默认“系统繁忙，请稍后重试”），`telemetry.queue_status=enqueue_failed`，指标 `telegram_queue_enqueue_failed_total`+1 | `telegram.queue.enqueue_failed` 日志；告警到运维 |
| workflow 未配置 | `status="ignored"`，但发送 `workflow_missing_text` 提醒用户；指标 `telegram_workflow_missing_total`+1 | `telegram.workflow_missing` |
| Worker 超时 | 自动降级为异步等待，`queue_status=timeout`，后续由后台协程推送最终消息 | `telegram.task_result_timeout` |
| Worker 重试/失败 | 依赖 `RetryTask`；若彻底失败，发送 `async_failure_text`，指标 `telegram_async_failed_total`+1 | `telegram.async.failed` |

## 运维指引

1. **排队监控**：`/internal/tasks/stats` 已合并 HTTP 与 Telegram 任务，可根据 `payload.telemetry.channel` 区分来源。
2. **异步派送**：`AsyncResultHandle` 会封装 waiter 与上下文，`interface_entry/telegram/handlers.py` 的后台任务会在 Worker 成功后推送正式回复并更新 `telegram_async_*` 指标。
3. **清理遗留同步路径**：新增渠道必须复用 `TelegramConversationService._build_task_envelope` 逻辑；禁止直接实例化 `WorkflowOrchestrator`。
4. **策略配置**：`entrypoints.telegram` 支持：
   - `wait_for_result`: bool（默认 `True`）
   - `async_ack_text`
   - `enqueue_failure_text`
   - `workflow_missing_text`
   - `async_failure_text`
   - `wait_timeout_seconds`

> 以上约束写入代码与文档后，CI/Code Review 可以据此拒绝“为了快速上线渠道而直连 Orchestrator”的实现。
