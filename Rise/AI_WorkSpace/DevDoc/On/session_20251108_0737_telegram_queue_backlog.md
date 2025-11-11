# session_20251108_0737_telegram_queue_backlog

## 背景
- Telegram 渠道此前在缺少 workflow 时直接回复“联系管理员”，并未向队列写入任务，导致消息完全丢失。
- 当前 Redis Streams + Worker 机制只在 `workflow_id` 存在时工作，RabbitMQ mirroring 代码虽在 `persist.rabbit_bridge` 就绪，但尚未纳入入口逻辑。
- 用户现已明确要求：无论 workflow 是否配置、后端是否暂时不可用，都必须把消息写入兜底层（Redis+RabbitMQ），并在后端恢复时自动重放；RabbitMQ 以 quorum queue + persistent message 方式永久保留，只有任务被成功处理或明确丢弃才允许删除。
- 进一步要求：外部渠道的 update 本身就是“对象”，入口不应强行转义或精简；应同时保留**统一封包字段**（channel、chatId、messageId 等元数据）与**原始 Telegram JSON**，由后端的 channel worker 在轮询到任务后自行解释和处理，实现“入口写一次、后台各渠道异步敲门”。

## 统一任务对象（封包 + 原始载荷）
1. **标准字段（供跨渠道治理）**
   - `payload.telemetry.channel`：来源渠道（telegram、http、whatsapp…），作为 channel worker 的筛选键。
   - `payload.metadata.chat_id / convo_id / message_ts`：用于幂等、排队统计、限流。
   - `payload.userText`、`historyChunks`、`policySnapshot`：供 orchestrator/监控快速读取。
   - `context.idempotencyKey`、`context.user`：`telegram:<pending|workflow>:<chat>:<message>`，保证重复 update 不会生成多条任务。
2. **原始对象（rawUpdate/channelPayload）**
   - 在 `TaskEnvelope.payload.channelPayload.raw` 中直接存储 Telegram update 的完整 dict，UTF-8 JSON 化即可，不做二次转义；如有附件，可按 Telegram 原字段（photo/document/voice 等）保留。
   - 存储时需打 `channelPayload.version`，便于后续协议升级。
   - 限制单条原始载荷大小（建议 256 KB）并记录 `telemetry.raw_size_bytes`，超限时写 `raw_truncated=true` 以提示消费端谨慎处理。
3. **示例**
   ```json
   {
     "taskType": "workflow.execute",
     "payload": {
       "channel": "telegram",
       "metadata": {
         "chat_id": "123456",
         "convo_id": "123456:123456",
         "message_id": "7890",
         "timestamp_iso": "2025-11-08T07:30:12Z"
       },
       "userText": "我要联系管理员",
       "historyChunks": [],
       "policy": {...},
       "telemetry": {
         "channel": "telegram",
         "requestId": "req-abc",
         "source": "telegram-bot"
       },
       "channelPayload": {
         "version": "tg.v1",
         "raw": { "... 原始 Telegram update ..." }
       }
     },
     "context": {
       "idempotencyKey": "telegram:pending:123456:7890",
       "traceId": "req-abc",
       "user": {
         "chat_id": "123456",
         "message_id": "7890"
       }
     }
   }
   ```
4. **消费职责**
   - Channel worker（如 Telegram worker）只需按 `payload.telemetry.channel == "telegram"` 轮询，拿到标准字段即可决定路由；若需要 Telegram 特有数据，再解析 `channelPayload.raw`。
   - Workflow 仅作为“是否可立即执行”的附加信息，不再是任务是否入队的前置条件。

## 已对齐事实
1. `TelegramConversationService.process_update` 只在 `_extract_workflow_id` 成功时调用 `TaskSubmitter.submit()`，否则直接返回 ignored，导致“联系管理员”后的消息未入队。路径：`src/business_service/conversation/service.py:127-193,501-512`。
2. Redis 队列和 Worker 链路已完备：`RedisTaskQueue.enqueue()` 写入 stream + task snapshot，`TaskWorker` 消费后通过 `TaskResultBroker.publish()` 通知等待者；`RetryScheduler` 处理重试。路径：`src/foundational_service/persist/redis_queue.py:41-88`、`src/foundational_service/persist/worker.py:166-338`、`src/foundational_service/persist/retry_scheduler.py`。
3. RabbitMQ 已有 durable publisher/consumer 实现，可将 `TaskEnvelope` 镜像到 quorum queue 并在恢复后重新导入，但尚未与入口、worker集成。路径：`src/foundational_service/persist/rabbit_bridge.py:1-146`。
4. RuntimeSupervisor 目前只根据 redis/rabbit capability 状态启停 runtime，并未在启动时检查 backlog，也不会在“队列有积压但依赖仍不可用”时报警。路径：`src/interface_entry/runtime/supervisors.py:82-145`。
5. var/logs 多个档案显示 `task_worker.start/stop` 但没有 `telegram.queue.enqueued`，印证 workflow 缺失时没有任务被入队。

## 成功路径（Success Path & Core Workflow）
1. Telegram handler 接收 update，`process_update` 无论 workflow 是否存在都构造 `TaskEnvelope`：标准字段 + 原始 `channelPayload.raw`，写入 Redis Streams，并通过 `RabbitPublisher` 镜像到 quorum queue（delivery_mode=Persistent，queue=durable quorum）。
2. Redis Worker 启动时若依赖可用，持续消费 `queue:tasks`：
   - 若 workflow 已配置 → 直接调用 orchestrator，成功后标记完成并回写 Telegram。
   - 若 workflow 仍缺失 → 将任务标记 `workflow_pending` 并保持在 Redis + Rabbit backlog（原始 payload 仍可从 `channelPayload.raw` 取回），等待配置完成或手动 resume。
3. RuntimeSupervisor 在能力恢复时：
   - 检查 Redis/Rabbit backlog 深度。
   - 若依赖齐备 → 启动 runtime + retry scheduler；必要时从 Rabbit backlog 重新 hydrate 到 Redis。
   - 若依赖缺失且 backlog>0 → 标记 capability degraded，并输出“有未处理消息，服务仍不可用”的告警。
4. Rabbit quorum queue 通过消息持久化保证长期存储，只有当任务在 Redis/worker 层确认完成后才从 Rabbit ack。

## 失败模式与防御
- **workflow 缺失**：任务入队并标记 `workflow_pending`，handler 回复“任务已排队等待配置”，Worker 将其移动到 `suspended`；提供管理 API resume 功能。
- **Redis/Rabbit 不可用**：入口记录 `telegram.queue.enqueue_failed` 并提示用户稍后重试；同时将 update 以本地 fallback 形式写入日志以便人工回放。恢复后 RuntimeSupervisor 自动检查 backlog 并重跑。
- **Rabbit publish 失败**：保持 Redis 任务，但记录 `rabbit_mirror_failed` metric，并将 envelope 置入重试列表；Publisher 使用 confirm + timeout 重试，避免消息丢失。
- **Backlog 超限或磁盘不足**：依赖 Rabbit 内建 disk alarm 与 Redis TTL 监控；当队列深度超过阈值时触发运维告警，并暂停入口接受新任务（返回“系统繁忙”）以保护数据。
- **重复消费**：通过 `idempotencyKey`（`telegram:<workflow|pending>:chat:message`）与 Mongo upsert，保证 Rabbit rehydrate 或 Redis 重试不会重复回复。同一 taskId 的 Rabbit 消息只有在 Redis ack 之后才 ack。
- **原始载荷过大或损坏**：若 `channelPayload.raw` 超出阈值，入口应记录 `raw_truncated=true` 并存储裁剪前的 checksum，防止 worker 误以为 payload 完整；解析失败时，worker 将任务标记 `SUSPENDED` 并附 `error=raw_payload_invalid` 以便人工干预。

## 约束与验收 (GIVEN/WHEN/THEN)
1. **GIVEN** Telegram update 达到入口，**WHEN** Redis/Rabbit 可用，**THEN** 必须同时落地标准字段与 `channelPayload.raw`，并在 `TaskEnvelope` 中写明 `channel=telegram`、`idempotencyKey`。
2. **GIVEN** workflow 未配置或不可用，**WHEN** Telegram 发送消息，**THEN** 任务仍需持久化并被标记 `workflow_pending`，handler 回复“已排队等待配置”，`/internal/tasks/suspended` 可检索同一任务。
3. **GIVEN** 后端重启，**WHEN** RuntimeSupervisor 检测 backlog>0，**THEN** 若依赖可用立即启动 worker 并打印“replaying backlog”，否则将 capability 置为 `degraded` 且输出“有 N 条未处理任务，待依赖恢复”。
4. **GIVEN** Rabbit publish 超过 `publish_timeout`，**WHEN** 出现异常，**THEN** 入口记录 `rabbit.publisher.timeout`、保留 Redis 任务，并在 3 次重试后触发运维告警。
5. **GIVEN** `channelPayload.raw` 超过配置大小上限，**WHEN** 入口截断 payload，**THEN** 必须设置 `telemetry.raw_truncated=true` 并在日志中写入原始长度，便于 worker 判断是否需要人工补偿。
6. **GIVEN** Redis 队列或 Rabbit backlog 深度超过运营阈值，**WHEN** 阈值被触发，**THEN** 系统需要拒绝新任务或切换到“仅排队模式”，同时向运维推送告警。

## 开发草案（后续落地思路）
1. **入口层改造**：
   - `TelegramConversationService` 增加 `_build_pending_envelope()`，在 workflow 缺失时写入队列并返回“已排队待配置”的静态响应。
   - `TaskSubmitter` 注入 `RabbitPublisher`，确保所有 envelope 双写；失败时 fallback 到本地磁盘/日志，并记录 `rabbit.publisher.timeout`。
   - 扩展 `TaskEnvelope` schema，支持 `channelPayload`（存原始对象、版本号、size），并在 `telemetry` 写入 `raw_truncated`、`raw_size_bytes`。
2. **Worker 扩展**：
   - 消费逻辑识别 `workflow_pending`，自动转入 `suspended`；resume 之后仍可访问 `channelPayload.raw` 进行完整处理。
   - 提供 Rabbit rehydrate 协程，把 Rabbit backlog 再次推入 Redis（带幂等检查），并支持按 channel 过滤。
   - 引入 Channel Router（或在 `TaskWorker` 中根据 `payload.telemetry.channel` 分发）以支持多渠道同时消费、并发限速。
3. **监控与自检**：
   - RuntimeSupervisor 加入 backlog 感知与 capability degrade 流程。
   - `/internal/tasks/stats` 返回 Redis stream depth、Rabbit message count、最老任务等待时长，并新增 `channelPayload.raw_truncated_total`、`workflow_pending_total`。
   - 启动日志若 backlog>0，必须输出警告并指导运维处理。
4. **文档/运维**：
   - 更新 DevDoc + Runbook，记录如何确认 Rabbit quorum 参数、如何校验 `channelPayload` 字段、如何清理/恢复 suspended 任务、如何在生产测试中验证兜底链路。

## 下一步
- 与用户确认：Rabbit 作为权威保存是否需要多集群/多 region；以及在 workflow 创建后自动 resume 的触发条件（手动 API 还是监听配置变更）。
- 根据本草案实现代码改动，并补充 e2e 测试（人工/生产验证为准）。
