# session_20251107_0715_worker_rabbitmq

## 背景与目标
- 在现有 Redis Streams 任务队列上叠加 RabbitMQ 持久兜底层，确保即使 Redis 整个集群离线，任务仍以磁盘复制的形式安全保存并可回灌。
- 继续统一入口层（HTTP / Telegram / CLI），保证所有业务请求先入 Redis，再异步镜像到 RabbitMQ，无“旁路执行”。
- 保持现有 TaskEnvelope、幂等键、状态机，新增 Redis↔RabbitMQ 复制器、独立 Worker runtime 以及回灌策略。
- 约束：不牺牲现有低延迟（Redis），新增层次需做到清晰的失败切换与监控报警。

## 组件拓扑
| 层级 | 组件 | 说明 |
| --- | --- | --- |
| 入口层 | HTTP `/api/workflows/apply`、TelegramConversationService、CLI 工具 | 统一构造 TaskEnvelope，`XADD queue:tasks` 并返回 `taskId`；入口永不直连 orchestrator。 |
| Redis 队列层 | `queue:tasks`（Streams） + `queue:retry`（ZSET） + `queue:suspended`（ZSET） | 提供低延迟消费、重试/挂起状态机；任务状态记录在 Redis。 |
| 镜像层 | RabbitMQ quorum queue：`rise.tasks.quorum`，exchange `rise.tasks.durable` | 通过 Raft 复制确保任务磁盘持久化；所有镜像消息都带 `taskId`、`idempotencyKey`。 |
| 复制器 | Stream Mirror Worker（新建服务） | 从 Redis 读取 pending 任务 → 发布到 RabbitMQ（`publisher_confirms`）；Redis ack 仅在 Rabbit confirm 成功后返回。 |
| 回灌器 | Rabbit Rehydrator（同一服务或独立 cron） | 检测 Redis 异常时从 RabbitMQ 拉取消息并重新 `XADD`，恢复队列。 |
| 执行层 | TaskRuntime + TaskWorker + RetryScheduler | 默认消费 Redis；若 Redis 不可用，可暂时直接从 RabbitMQ 消费（降级模式）。 |
| 监控与运维 | `/internal/tasks/*` + RabbitMQ Prometheus exporter | Redis 指标：`counts.*`, `streamLength`；Rabbit 指标：`messages_ready`, `publish_confirm_latency`, quorum 成员状态。 |

## 数据流程
1. 入口收到请求 → 构造 TaskEnvelope（含 `channel`, `chat_id`, `idempotencyKey = {channel}:{workflowId}:{chatId}:{timestamp}`）→ `XADD queue:tasks`.
2. **Stream Mirror Worker** `XREADGROUP` 批量拉取 → 按顺序向 `rise.tasks.durable` exchange 推送消息（`delivery_mode=2`, `x-queue-type=quorum`），开启 `publisher_confirms`。
3. RabbitMQ 返回 confirm → Mirror Worker 才 `XACK` Redis，确保 Redis 与 Rabbit 状态一致；如 confirm 超时则重试/报警。
4. TaskWorker 按现有逻辑消费 Redis 流，执行 orchestrator、写 Mongo，`mark_completed` 并触发结果回传。
5. Redis 故障时：Mirror Worker 停止 `XACK` 并将任务残留在 Redis pending；Rehydrator 从 Rabbit quorum queue 拉取消息，重新写入 Redis 或直接交由 Worker 执行（需显式切换）。
6. 系统恢复后，Rabbit↔Redis 序列重新同步；`TaskEnvelope.status` 仍以 Redis 为准。

## 关键模块与文件
- `src/foundational_service/persist/redis_queue.py`/`worker.py`：保持不变，新增 hooks 以支持 “Rabbit 再执行” 模式。
- **新增** `src/foundational_service/persist/rabbit_bridge.py`：封装 RabbitMQ 连接、confirm、quorum queue 声明、DLX 配置。
- **新增服务** `tools/stream_mirror_worker.py`：运行 Mirror Worker；读取 Redis Stream、调用 `rabbit_bridge.publish()`。
- **新增服务** `tools/rabbit_rehydrator.py`：监听 Rabbit queue，按需回灌 Redis 或直接驱动 Worker。
- `.env`：新增 `RABBITMQ_URL`, `RABBITMQ_VHOST`, `RABBITMQ_EXCHANGE`, `RABBITMQ_QUEUE`, `RABBITMQ_PREFETCH`.
- `compose/docker`（若有）：扩展 RabbitMQ 配置（`queue_type=quorum`, `x-quorum-initial-group-size=3`, `dead-letter-exchange=rise.tasks.dlx`）。

## 配置与依赖
- 依赖：`aio-pika>=9.4`（或 `pika>=1.3`），安装在 `.venv`；统一封装在 `rabbit_bridge`.
- RabbitMQ 声明参数：
  ```json
  {
    "queue": "rise.tasks.quorum",
    "arguments": {
      "x-queue-type": "quorum",
      "x-quorum-initial-group-size": 3,
      "x-dead-letter-exchange": "rise.tasks.dlx",
      "x-delivery-limit": 5,
      "max-length": 500000,
      "overflow": "reject-publish"
    }
  }
  ```
- Publisher confirm：发布前确保 `channel.confirm_select()`, 对每条消息 await confirm；若 3 秒未确认 → 记录 `rabbit.publisher_timeout`, 重试三次后报警。
- Consumer：prefetch 根据 Worker 并发配置（默认 50）；降级模式下 Worker 直接消费 Rabbit queue 并手动 ack。

## Success Path & Core Workflow
1. 入口 → Redis `queue:tasks`；TaskEnvelope 带 `source`, `channel`, `chat_id`, `idempotencyKey`.
2. Mirror Worker → RabbitMQ（quorum queue）→ confirm 成功 → Redis `XACK`.
3. TaskWorker → orchestrator → Mongo 幂等 upsert → `mark_completed` & `TaskResultBroker.publish`.
4. RabbitMQ 只作镜像，不影响正常延迟；若 Redis 正常，则 Rabbit 仅供灾备。

## Failure Modes & Defensive Behaviors
- **Redis down**：Mirror Worker 发现 `XREADGROUP` 失败 → 切换到 Rabbit-only 模式：入口仍写 Redis（失败则立即报错），Rehydrator 从 Rabbit 读取并通过本地 `TaskWorker` 直接执行；Redis 恢复后回灌 backlog。
- **Rabbit confirm 失败/超时**：Mirror Worker 尝试重发，累计超限则告警并将任务标记 `suspended`（在 Redis 记录 `mirror_failed`). 入口照常写 Redis，但要通知运维 Rabbit 兜底失效。
- **Rabbit quorum 少数派故障**：仍可对外提供 confirm；监控 `messages_unacknowledged` 与 `quorum_leader` 健康，若 quorum 不足需手工恢复节点。
- **重复执行**：`idempotencyKey` + Mongo upsert；Rabbit 回灌时保持相同 `taskId`，Worker 在 `WorkflowRunStorage` 里以 `task_id` 去重。
- **镜像回环**：严禁 Rabbit 消费后又重新投 Rabbit；Rehydrator 仅写 Redis 或直接执行。
- **容量控制**：Redis 继续使用 stream `MAXLEN ~ 5000`，Rabbit 通过 `max-length` 控制磁盘占用，避免无限堆积。

## GIVEN / WHEN / THEN 验收
1. **Redis 正常 + Rabbit 正常**  
   - GIVEN 两个入口（HTTP、Telegram）同时提交，WHEN Redis 与 Rabbit 均在线，THEN `queue:tasks` 无 backlog、`rise.tasks.quorum` `messages_ready` ≈0、任务按原速度完成。
2. **Rabbit confirm 超时**  
   - GIVEN Rabbit quorum 中某节点磁盘抖动，WHEN Mirror Worker 发布消息，THEN 在 3 秒内重试 ≤3 次并写入 `rabbit.publisher_timeout` 告警，不影响 Redis 任务入队；超限后任务进入 `queue:suspended`、`/internal/tasks/suspended` 可查看 `mirror_failed`.
3. **Redis 故障**  
   - GIVEN Redis 实例整体下线，WHEN Rabbit quorum 仍在线，THEN Mirror Worker 停止 `XACK`、Rehydrator 从 Rabbit 拉取并驱动 Worker，将状态写入 Mongo；Redis 恢复后 `rabbit_rehydrator` 将 backlog 重新 `XADD`.
4. **Rabbit 故障**  
   - GIVEN Rabbit 集群不可用，WHEN 入口继续写 Redis，THEN Mirror Worker 记录 `rabbit.enqueue_failed` 并发出告警；任务仍可在 Redis → Worker 正常执行，运维可按需手动导出 Redis Pending 至文件。
5. **回灌一致性**  
   - GIVEN Redis 被清空，WHEN Rehydrator 从 Rabbit 回灌，THEN 所有 TaskEnvelope `idempotencyKey` 与原值一致，Mongo `workflow_runs` 无重复记录。

## 实施步骤
1. 安装依赖：`pip install aio-pika`（进入 `.venv`）。
2. 实现 `rabbit_bridge`（连接池、异步 confirm、声明 exchange/queue）。
3. 编写 `tools/stream_mirror_worker.py`：  
   - `XREADGROUP` → `rabbit_bridge.publish`（await confirm）→ `XACK`;  
   - 捕获异常后重试/告警。
4. 编写 `tools/rabbit_rehydrator.py`：  
   - 订阅 `rise.tasks.quorum`，拉取消息并 `XADD` 回 Redis（或直接送 TaskWorker）；  
   - 支持 CLI 参数：`--mode rehydrate` / `--mode execute`.
5. FastAPI 启动时注入 `set_task_queue_accessors`（已完成）；部署新的 worker 服务。
6. 设置监控仪表：  
   - Redis：`queue_length`, `retry_length`, `suspended_length`;  
   - Rabbit：`messages_ready`, `messages_unack`, `publish_confirm_latency_ms`, `quorum_leader_changes`.
7. 演练：分别拔掉 Redis、Rabbit、单个 Rabbit 节点，验证 GIVEN/WHEN/THEN 条件。

## 后续工作
- 制定 RabbitMQ 备份/回滚手册（`rabbitmqadmin export/import`）。  
- 为 Mirror Worker 与 Rehydrator 加入 `/healthz`，纳入部署编排。  
- 评估是否需要将 Rabbit 变为“长久存储 + 批量重放”以便审计（可追加 `rise.tasks.audit` stream）。  
