# Rise 后端实时执行与多级缓存重构方案

## 背景与目标
- 现有后端在 Mongo/Redis/外部 API 任一服务故障时会直接失败，无法保障多阶段工作流在生产环境下的可用性。
- 目标：所有业务请求统一进入 Redis 形成任务镜像，再由后台 worker 落地实际业务；Mongo 或外部依赖故障时，任务自动留在 Redis 队列等待重试；重试失败的任务进入挂起队列接受人工/指令恢复。
- 要求：流程实时运行、真实数据写入、所有阶段有监控与幂等保障，确保系统可在生产环境中应对异常。

## 总体架构
```
HTTP/Telegram 请求
        │
        ▼
Task Submitter（FastAPI 层）
        │  XADD queue:tasks
        ▼
Redis Streams / Lists
        │
        ├─ Worker(消费) ── 调用业务逻辑 ── 写 Mongo / 外部 API ── 成功 → XACK & 清理
        │                    │
        │                    └── 失败 → 标记重试信息 → 重新入列或进入 queue:retry
        │
        └─ Retry Scheduler（定时器）── 取 queue:retry 中到期任务 ── 再次 XADD 主队列
                               │
                               └── 重试 3 次仍失败 → queue:suspended（系统/人工恢复）
```
- TaskEnvelope 统一描述任务（类型、payload、上下文、幂等键、重试信息、状态）。
- Worker、Retry Scheduler、Suspended Handler 可与 FastAPI 同进程，也可独立守护进程；通过配置切换。
- Redis 为统一缓存层；Mongo 是最终权威存储；OpenAI 等外部服务由 Worker 直连。

## TaskEnvelope 设计
```json
{
  "taskId": "uuid",
  "type": "workflow.execute",
  "payload": {...},
  "context": {
    "idempotencyKey": "...",
    "traceId": "...",
    "user": {...}
  },
  "retry": {
    "count": 0,
    "max": 3,
    "nextAttemptAt": 0
  },
  "status": "pending",
  "createdAt": "...",
  "updatedAt": "..."
}
```
- `taskId`：全局唯一，用于日志追踪、重复任务检查。
- `context.idempotencyKey`：Mongo/外部 API 幂等写入依据（如 workflowId+stageId+timestamp）。
- `retry.count / max / nextAttemptAt`：Worker 和 Scheduler 依据该信息执行重试或挂起。
- `status`：`pending` → `processing` → `completed` / `retry` / `suspended`。

## 处理流程
1. **提交阶段**
   - FastAPI 层在接收请求后，立即构造 `TaskEnvelope`，写入 Redis Stream（`queue:tasks`），同时返回请求已受理的标识（可选）。
2. **消费阶段**
   - Worker 使用 `XREADGROUP` 从 Stream 消费任务，首次处理将状态改为 `processing`，执行真实业务（工作流 orchestrator、Mongo 写入、外部 API 调用等）。
   - 成功：调用 Mongo 幂等写入 → `XACK` → telemetry 中记录成功事件。
   - 失败：根据错误类型决定策略：
     - Mongo / 外部 API 暂时不可用 → 重新写入 `queue:retry`，设置 `retry.count+1`、`nextAttemptAt = now + backoff(1min/5min/...)`。
     - 业务逻辑不可恢复（如合同缺失） → 直接进入 `queue:suspended`，等待人工干预。
3. **重试调度**
   - Scheduler（可由单独协程+定时器实现）定期扫描 `queue:retry`（ZSET 或 Stream pending），选出到期任务重新写入主队列。
4. **挂起任务处理**
   - 超过 `retry.max` 的任务，转移到 `queue:suspended`；提供内部 API `/internal/tasks/suspended` 给运维查看、批量恢复或丢弃。
5. **状态查询与监控**
   - `/internal/tasks/stats` 返回 pending/processing/retry/suspended 的数量及最新任务，用于监控。
   - Prometheus 指标（选配）：队列长度、处理速率、重试次数、失败率。

## 核心模块与文件
- `src/foundational_service/persist/task_envelope.py`：定义数据结构与序列化方法。
- `src/foundational_service/persist/redis_queue.py`：封装 Redis Stream/List 操作（XADD、XREADGROUP、XAUTOCLAIM、XACK）。
- `src/foundational_service/persist/worker.py`：Worker 主循环，实现业务处理与幂等写入。
- `src/foundational_service/persist/retry_scheduler.py`：重试调度器。
- `src/foundational_service/persist/controllers.py`：内部管理 API（查询、恢复、丢弃挂起任务）。
- `src/foundational_service/persist/storage.py`：Mongo 幂等写入封装（`upsert_one(filter=idempotencyKey)`）。
- `src/interface_entry/bootstrap/app.py`：在 lifespan 中启动 Worker/Scheduler；或提供命令行脚本 `python tools/persist_worker.py`。

## Success Path / Core Workflow
1. 用户调用 `/api/workflows/apply` → TaskSubmitter 入队 → Worker 消费 → Orchestrator 执行阶段 → Mongo 写入会话历史/summary → Redis `XACK` → 调用方获得真实 LLM 输出。
2. 若 Mongo 短暂不可用 → Worker 捕获 `ServerSelectionTimeoutError` → 任务重新入 `queue:retry` → Mongo 恢复后重新消费 → 数据最终落库。
3. 前端或外部调用对系统透明：无论任务处于重试或挂起阶段，接口都能获知当前状态（通过内部查询接口或 Webhook 补发）。

## Failure Modes & Defensive Behaviors
- **Redis 连接失败**：TaskSubmitter 记录 `critical` 日志并直接报错（当前不做本地文件兜底）；可在后续扩容或配置 Redis Sentinel/Cluster。
- **Worker 异常退出**：Redis Stream 的 Pending 任务不会丢失；新 Worker 启动后通过 `XAUTOCLAIM` 接手。
- **幂等失败（重复消费）**：所有 Mongo/外部写入必须基于 `idempotencyKey` 使用 `upsert` 或 `ON CONFLICT DO NOTHING`，确保任务重放时不会重复写入。
- **重试耗尽**：进入 `queue:suspended`，运维可通过内部接口重新触发或丢弃；任务背景信息需要完整保留（payload、错误栈、重试记录）。
- **任务堆积**：监控队列长度；达到阈值告警，并允许在内部接口上临时扩容 Worker 实例。
- **Mongo/外部 API 永久失败**：需要人工介入或专用恢复脚本；文档中应明确常见失败代码与处理手册。
- **Redis 宕机**：当前策略下任务会失败；若需更高可靠性，可考虑 Redis 高可用或在文档中说明容灾流程，不建议使用本地文件兜底以免增加复杂度与 I/O 负担。

## GIVEN / WHEN / THEN 验收清单
- **GIVEN** Mongo 正常、Redis 正常，**WHEN** 调用 `/api/workflows/apply`，**THEN** 任务进入 Redis → Worker 执行 → Mongo 落库 → 返回真实 LLM 输出，并且 Redis 中无遗留 pending。
- **GIVEN** Mongo 停机，**WHEN** 调用 `/api/workflows/apply`，**THEN** 任务进入 Redis 并在 Mongo 恢复前保持重试状态，Mongo 恢复后自动完成，最终数据一致。
- **GIVEN** 某任务连续失败 3 次，**WHEN** 达到阈值，**THEN** 任务进入 `queue:suspended`，运维可通过内部接口查看并重新执行或放弃。
- **GIVEN** Worker 进程崩溃，**WHEN** 重新拉起 Worker，**THEN** Redis pending 任务能够被自动接管并继续处理。
- **GIVEN** 队列堆积超过设定阈值，**WHEN** 内部监控检测到异常，**THEN** 触发告警并允许通过内部接口动态扩容 Worker 或暂停新任务。

## 后续行动
1. 实现 TaskEnvelope 与 Redis 队列工具；改造 FastAPI 层统一使用 `task_submit()`。
2. 编写 Worker/Scheduler 模块，并在应用 Lifespan 或独立守护进程中运行。
3. 调整现有 Mongo 写入点（workflow summary、Pipeline、Tool/Stage 等）走 Task → Worker → Mongo 的新路径。
4. 增加内部运维接口和监控指标。
5. 在生产环境模拟 Mongo/外部 API 故障，验证任务重试与挂起机制。

---

> 注：若未来需要 Redis 多实例或地理级高可用，可将 TaskQueue 抽象成接口，支持切换到 Redis Cluster、Kafka 等实现；本方案以“单 Redis 实例 + 任务镜像”作为第一阶段落地策略。
