# 开发功能性需求文档：长耗时可恢复任务编排（Celery + RabbitMQ + Redis + MongoDB）

本文将用户自然语言诉求转化为可落地的功能需求与结构变更决策，严格遵循 BackendConstitution 与官方最佳实践。


## 1. 项目背景与目标

- 任务特征：长耗时、多步 I/O 流水（读库/抓取/清洗/入库），任一步失败不可整体回滚；并发 10–20 个 worker；需要断点续跑与幂等，避免重复处理与分片重叠。
- 可靠性目标：崩溃/重启后可恢复到最近权威进度；消息至少一次投递；全链路具备监控与可观测性。
- 状态分层：
  - 瞬时执行态（Ephemeral）：内存或 Redis，仅用于加速与短期共享，非权威。
  - 消息持久态（Durable Message）：RabbitMQ 承载队列/消息的持久化与确认/重投。
  - 业务权威态（Authoritative）：MongoDB 记录断点/幂等/去重与业务落地数据。

## 2. 范围与非目标

- 范围：以 Celery 为任务执行框架，RabbitMQ 为唯一 Broker，Redis 为缓存/短期态/可选 Result Backend，MongoDB 为权威进度与数据落地。提供最小可用的 API 契约与 Worker 侧实现约束。
- 非目标：
  - 不在进程内（FastAPI BackgroundTasks）承载 >10 分钟或需重试任务。
  - 不以 Redis 充当主库，不绕过 RabbitMQ 直接驱动 Worker。

## 3. 核心功能需求（可验收条目）

1) 任务投递与调度
- 必须提供 API：`POST /task/start`（接收参数并入队，返回 `task_id`）。
- 任务入队到 RabbitMQ 持久化队列（`durable queue + persistent message + publisher confirm`）。
- 支持队列优先级、路由键；失败重试采用指数退避 + 抖动；Worker `prefetch` 可配置。

2) 任务状态与查询
- API：`GET /task/status/{task_id}` 返回 `PENDING|STARTED|RETRY|SUCCESS|FAILURE` 与进度百分比（如有）。
- 可选：`GET /task/result/{task_id}` 在成功后读取结果（若使用 Redis 作为 Result Backend）。禁止同步阻塞等待。

3) 分片策略（至少实现一种，可扩展）
- 范围分片：按主键或时间窗口（如 `id`/`created_at`）切片，每片一个任务；MongoDB 检查点记录片内游标。
- 哈希取模：对稳定键 `hash(key) % N`，不同 worker 消费不同模值；MongoDB 存储模内游标。
- 租约+心跳（Frontier）：领取任务时 `findOneAndUpdate` 写入 `lease_until/taken_by`，定期续租，超时回收。

4) 断点续跑与幂等
- MongoDB 中的检查点集合（如 `TaskCheckpoint`）记录：分片键、游标位置、更新时间、最后错误。
- 去重集合（唯一索引）保证天然幂等，如基于业务主键或任务指纹（`task_fingerprint`）。
- Worker 在处理前检查幂等键；重复则直接 `ack` 并跳过副作用。

5) 错误处理与重试
- Worker 端统一捕获异常并上报；对可重试异常执行指数退避重试；对不可重试异常入 DLQ（Dead Letter Queue）。
- 发布端启用 Publisher Confirm；消费端采用手动 `ack`；未确认消息在崩溃后自动重投。

6) 可观测性与日志
- 统一使用 `Kobe/SharedUtility/RichLogger` 初始化日志（入口一次），业务内使用 `logging.getLogger(__name__)`。
- 暴露关键指标：队列积压、失败率、重试次数、DLQ 深度；记录链路 Trace（OpenTelemetry 可选）。

7) 配置与运行
- 唯一虚拟环境：`Kobe/.venv`；从 `Kobe/.env` 读取连接串（RabbitMQ/Redis/MongoDB）。
- 开发运行：`python -m Kobe.main`；生产运行 `uvicorn Kobe.main:app ...`；Celery Worker `celery -A Kobe.TaskQueue:app worker ...`。

验收标准（节选）：
- `POST /task/start` 返回可用 `task_id`；`/task/status/{id}` 能看到状态变化。
- 强制通过 RabbitMQ 持久化队列；MongoDB 产生可验证的检查点/去重记录。
- Worker 宕机模拟后，未确认消息可被其它 Worker 消费；进度可从 MongoDB 恢复继续。

## 4. 结构/变更决策

根据 `CodebaseStructure.md` 与用户提示，需在 `Kobe/` 下新增 `TaskQueue/` 子模块以承载队列化任务域，理由：
- 与 Web 层（FastAPI）解耦，清晰边界与职责分离。
- 聚合队列、检查点、幂等与任务实现为一处，降低散落风险。

### 4.1 新增目录结构（建议）

放置路径：`Kobe/TaskQueue`（符合“唯一代码库工作目录”约束）

```
D:\AI_Projects\Kobe\TaskQueue\
├── readme.md                  # 模块说明、运行与联调指引、注意事项
├── __init__.py                # Celery 应用初始化（app、队列、路由、重试策略、信号）
├── config.py                  # RabbitMQ/Redis/MongoDB 连接配置（从 .env 读取）
├── schemas.py                 # 任务入参/结果 Pydantic 模型
├── checkpoints\
│   ├── __init__.py
│   └── mongo_checkpoint.py    # 检查点/幂等/去重数据访问封装（PyMongo）
├── strategies\
│   ├── __init__.py
│   ├── range_shard.py         # 范围分片策略
│   ├── hash_mod_shard.py      # 哈希取模策略
│   └── lease_frontier.py      # 租约+心跳策略
├── workers\
│   ├── __init__.py
│   └── ingest_task.py         # 典型长任务：抓取/清洗/入库（示例）
├── api\
│   ├── __init__.py
│   └── routes.py              # /task/start /task/status/{id} /task/result/{id}
├── observability\
│   └── metrics.py             # 指标采集与导出（Prometheus/OpenTelemetry 可选）
└── tests\
    ├── test_idempotency.py
    └── test_checkpoint_resume.py
```

放置理由：
- `Kobe/` 为项目根；`TaskQueue/` 将“长耗时+可恢复”的跨任务通用能力集中，避免侵入 Web 层；与 `SharedUtility/` 形成清晰分层。

### 4.2 是否需要新增结构：需要

- 现有仓库中未见 `TaskQueue/` 相关目录；为支撑需求必须新增。

## 5. 需修改的现有文件（不在本次变更中直接修改，仅在此明确改动点与原因）

- `Kobe/main.py`
  - 原因：
    - 初始化 RichLogger（`init_logging`, `install_traceback`）。
    - 将 `TaskQueue.api.routes` 注册到 FastAPI 应用，提供 `/task/*` 路由。
  - 类型：能力补充。

- `Kobe/SharedUtility/RichLogger/*`
  - 原因：无功能性修改，仅作为统一日志入口使用。
  - 类型：无须改动。

- `Kobe/.env`（新增或完善示例）
  - 原因：加入 `RABBITMQ_URL`、`REDIS_URL`、`MONGODB_URI`、`PREFETCH_COUNT`、`RETRY_BACKOFF` 等配置键。
  - 类型：配置变更。

## 6. 详细规则与约束

1) Celery 与 RabbitMQ（官方最佳实践优先）
- Broker：RabbitMQ；启用 `durable queue` 与 `delivery_mode=2`；Publisher Confirm 开启。
- 消费：`manual ack`；`prefetch_count` 控并发；失败自动重试，指数退避 `2^n ± jitter`。
- 编排：链路使用 `chain/group/chord`；周期性任务使用 Celery Beat。

2) Redis（短期态/缓存/结果后端）
- 仅作为临时态与可选 Result Backend；严禁承载权威进度。
- 缓存采用分层 key 命名与统一 TTL；写库后优先失效对应缓存键（Write→Invalidate）。

3) MongoDB（权威进度与幂等）
- 集合最小清单（对齐提示“集合拆分”）：
  - `TaskCheckpoint`：记录分片键、片内游标（如 `last_id`/`last_created_at`）、`updated_at`、`last_error`。
  - `TaskDedup`：幂等表，唯一键为业务主键或 `task_fingerprint`，命中即跳过副作用。
  - `PendingTasks`：Frontier/租约队列；字段包含 `task_key`、`lease_until`、`taken_by`、`retry_count`、`payload_ref`。
  - `TaskErrorLog`：持久化错误日志与上下文，支持二次诊断。
  - `RawPayload`：原始大对象指针（对象存储 URL/Key），数据库仅存元信息。
- 索引：
  - `TaskDedup(task_fingerprint)` 唯一索引；
  - `TaskCheckpoint(shard_key, sub_key)` 复合索引；
  - `PendingTasks(task_key)` 唯一索引，`PendingTasks(lease_until)` 过期/回收扫描索引；
  - 其余结合读写路径按需添加覆盖索引。
- 事务：必要时使用会话/事务保障一致性，或采用 Outbox/CDC。

4) API 契约（FastAPI）
- `POST /task/start`：请求体为 `schemas.TaskStart`，返回 `{ task_id }`。
- `GET /task/status/{id}`：返回标准状态枚举与最近进度。
- 禁止同步等待结果；如需结果，使用轮询或回调 Webhook（可选）。

5) 可观测与告警
- 指标：队列积压、消费速率、失败/重试率、DLQ 深度、处理时延 P50/P95。
- 日志：统一 `logging`；不允许 `print()`。
- Trace：与请求链路打通（可选）。

## 7. 补充建议与细化项

- 本地/开发环境提供 `docker-compose` 示例（RabbitMQ/Redis/MongoDB），降低接入成本。
- 任务幂等键生成统一在 `workers` 前置函数中实现，避免分散。
- 结果大对象（如抓取原文）存对象存储，仅存指针到 MongoDB。
- 对外暴露最小 API 面，同时保留扩展点（优先策略注入而非 if-else）。

## 8. 参考规范与一致性说明

- 严格遵守 `CodexFeatured/Common/BackendConstitution.md`：
  - Python 3.10；唯一虚拟环境 `Kobe/.venv`；日志使用 RichLogger；
  - 异步/后台作业必须走 Celery + RabbitMQ；Redis 仅短期态；
  - 提供 `/task/*` 契约；可观测能力必须具备。
- 官方文档优先：Celery、RabbitMQ、Redis、MongoDB、FastAPI、Pydantic；社区实践仅作补充。

## 9. 交付与验收清单

- 新增 `Kobe/TaskQueue` 目录与基础骨架文件（见 4.1）。
- 接口 `/task/start` `/task/status/{id}` 可用并通过最小联调。
- MongoDB 集合与索引策略落地；能证明断点续跑与幂等生效。
- 队列策略（durable/confirm/ack/retry）配置到位；崩溃恢复验证通过。

---

附：本需求文档存放路径符合规范：`CodexFeatured/DevPlans/004_InitialSetup/DemandDescription.md`。
