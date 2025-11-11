# session_20251108_0215_telegram_queue_unification

## 背景与目标
- **当前问题**：Telegram Bot 作为唯一外部输入，却仍同步直连 `WorkflowOrchestrator`。缺少 workflow 或后端抖动时，直接抛 500，消息既不会入队也无法重试，完全违背“外部输入必须落到队列兜底”的架构方针。
- **legacy 偏差**：为了 Admin Panel（内部 GUI）曾保留 HTTP `/api/workflows/apply` 的同步入口，后来虽然加了 Redis/RabbitMQ，但并未把 Telegram 接入，也没有清理旧路径，导致“外部输入”与“内部工具”共用一套混杂实现，难以 refactor。
- **预期态**：底座只服务外部用户输入（当前即 Telegram，未来可能是 WhatsApp、Webhook、CLI agent 等），所有外部入口必须通过统一封包 → Redis Streams → Worker 的链路；任何 legacy 同步调用都应被删除或迁移到此底座，避免叠加式兼容。
- **目标**：完成 Telegram 入口重构，明确 Admin Panel 仍属内部操作无需兜底；为未来新增外部渠道提供可复用底座，并在文档中把“现状 vs 预期”描清楚，指导开发以删除/替换 legacy 代码而非继续堆砌。

## 核心设计
1. **入口统一封包**：
   - 在 `TelegramConversationService.process_update` 中直接构造 `TaskEnvelope`，字段与 HTTP `/api/workflows/apply` 保持一致：`workflowId`、`userText`、`historyChunks`、`policy`、`coreEnvelope`、`telemetry.channel="telegram"`。
   - `context.idempotencyKey = f"telegram:{workflow_id}:{chat_id}:{message_id}"`，配合 Mongo upsert 防止重复回复。
2. **队列提交**：
   - 通过 `TaskSubmitter.submit()` 调用 `RedisTaskQueue.enqueue()`；若 submit 失败要记录 `telegram.queue.enqueue_failed` 并返回告警文案提醒用户稍后再试。
   - 根据 policy 决定是否 `waitForResult`：若需要实时回复，可 await `runtime.results.register()`；否则先返回 ACK 并由 Worker 成功后调用 outbound 合同发送消息。
3. **Worker 消费**：
   - 复用现有 `WorkflowTaskProcessor`；确保 `telemetry.channel` 贯穿到日志与 `TaskResultBroker`，方便调试。
   - 允许 Telegram 任务与 HTTP 任务共享同一个 `queue:tasks`，通过 `payload.telemetry.channel` 区分来源。
4. **失败兜底**：
   - Worker 故障：依赖 `XAUTOCLAIM` + `RetryScheduler`；入口无需修改。
   - `workflow_id_missing`：在入口处返回 `status="ignored"`，附文案“流程未配置”，避免 Telegram 连续 500。
5. **部署形态**：
   - FastAPI（HTTP Admin 工具）与 Telegram Bot 仅负责入队；至少部署一个独立 Worker 进程常驻，防止入口生命周期影响消费。任何新增外部入口（CLI agent、Webhook、聊天渠道）必须直接调用这套封包层；禁止再出现“为了某渠道快速上线而单独写同步逻辑”的情况。

### Legacy 路径清理要求
- `/api/workflows/apply` 以及其他 Admin Panel API 明确归类为**内部工具**——它们是后端的一部分，用于配置、调试、回放，并不是面向终端用户的“外部输入”。本次重建需要在文档与代码中同时写明这一点，确保未来的 AI/开发扫描仓库时能立即识别：Admin Panel ≠ 外部流量入口。
- 开发时必须逐项确认：
  1. 是否仍有脚本/模块直接实例化 `WorkflowOrchestrator` 并绕过队列——如有必须删除或封装到统一封包函数中。
  2. Admin Panel 若提供“模拟运行”按钮，必须调用同一 HTTP API，而不是写独立逻辑。
  3. 任何新增入口在提交设计前必须声明其“外部 or 内部”属性；仅外部入口可以接入兜底。内部工具在服务停机时应直接失败，以提醒开发修复，而不是悄悄排队等待。

## 成功路径（Success Path & Core Workflow）
1. Telegram 更新抵达 → handler 调用 `conversation_flow.process()`。
2. `process_update` 生成 `TaskEnvelope` 并入队 `queue:tasks`，返回 `taskId` 或同步等待。
3. Worker 读取任务 → 构造 `WorkflowExecutionContext` → 调用 orchestrator → 写 Mongo。
4. Worker 将结果写回 `TaskResultBroker`；若 Telegram 入口在等待，则立即获取结果并通过 `behavior_telegram_outbound` 生成回复；若是异步模式，Worker 成功后触发发送逻辑。
5. `/internal/tasks/*` API 与 metrics 对 HTTP/Telegram 任务一视同仁，可统一监控。

## 失败模式与防御策略
- **Redis 不可用**：入口直接返回“队列不可用，请稍后重试”，日志打 `queue.enqueue_failed`，并触发告警；不得回退为同步执行。
- **缺少 workflow**：入口返回 `status="ignored"`、error_hint=`workflow_missing`，Telegram 仍收到 200；同时记录 metrics `telegram_workflow_missing_total`，提醒管理员补流程。
- **Worker 超时/失败**：利用既有 `RetryTask`，Telegram 同步模式下如超过 `waitTimeoutSeconds`，入口刷新为 202 + `taskId`，可在后台等待 Worker 完成。
- **挂起任务堆积**：继续沿用 `/internal/tasks/suspended` + 手动 `resume/drop`；运维需定期清理。
- **重复 update**：依赖 idempotencyKey + Mongo upsert，避免重复回复。

## 约束与验收 (GIVEN/WHEN/THEN)
1. **GIVEN** Telegram 消息到达且 Redis 正常，**WHEN** `workflow_id` 存在，**THEN** 任务必须入队并在 Worker 成功后向 Telegram 回复一次。
2. **GIVEN** Redis 断开，**WHEN** 入口尝试 `submit`，**THEN** 应立即报告 `queue.enqueue_failed`，且 Telegram 收到提示消息而非超时。
3. **GIVEN** 没有配置 workflow，**WHEN** Telegram 发送消息，**THEN** 入口返回 ignored，日志明确提示“workflow_missing”并增加相关指标。
4. **GIVEN** Worker 被停止，**WHEN** 入口继续入队，**THEN** `queue:tasks` 深度会上升但消息不会丢失，Worker 恢复后能够继续消费。
5. **GIVEN** HTTP 与 Telegram 同时推送大量请求，**WHEN** Redis 仍可用，**THEN** `TaskResultBroker` 能依据 `channel` 正确路由结果，且 `/internal/tasks/stats` 中的计数可区分来源。

## 后续行动
1. 改造 `TelegramConversationService`：接入 `TaskSubmitter`、封包、idempotency、ignored 分支。
2. 更新 Telegram handler：处理同步/异步两种 `waitForResult`，并在日志/metrics 中记录队列事件。
3. 编写 Worker 启动脚本/服务说明，保证至少一个 Worker 常驻。
4. 发布运维手册：如何查看队列状态、处理挂起任务、确认 workflow 配置。
5. 扩展文档到未来接口：确保 Admin Panel、CLI 等新增入口直接复用本底座。
