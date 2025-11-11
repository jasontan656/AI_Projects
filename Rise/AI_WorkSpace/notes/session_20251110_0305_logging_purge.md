# Session Notes 2025-11-10 03:05 CST

## User Intent
- 用户要彻底清点并移除当前项目中所有落地的日志调用，保留 `project_utility.logging` 等工具函数，但删除业务/接口层的 `log.info`/`logger.warning` 等记录点，并重新规划新的日志体系。

## Repo Context
- `src/interface_entry/bootstrap/app.py`: FastAPI 应用入口，`log` 在启动阶段输出几十条事件（service_host_override、startup.clean.segment、task_runtime 状态等），依赖 `project_utility.logging` 生成 Rich 控制台/文件日志，是当前运维观察的主要来源。
- `src/interface_entry/telegram/handlers.py`: Telegram 会话入口，`log.warning`/`log.error`/`log.info` 记录消息发送、重试、异步任务状态，与 `metrics_state` 紧密耦合；删除会导致 Telegram 运行状况失去洞察。
- `src/interface_entry/telegram/routes.py` & `src/interface_entry/telegram/runtime.py`: Webhook 与 runtime 初始化同样大量记录状态码、traceId；与上层 middleware 共同构成触达链路的日志骨干。
- `src/interface_entry/http/middleware.py`: `LoggingMiddleware` 把每个 webhook 请求的 path/method/status/latency 写入 `_logger.info("webhook.request", ...)`，也是用户提到的 404 记录来源。
- `src/interface_entry/runtime/capabilities.py`、`runtime/supervisors.py`、`runtime/public_endpoint.py`: 管理能力探针、监督进程、对外健康检查，均通过 `log.info/log.warning` 表达 capability 状态变化。
- `src/foundational_service/telemetry/bus.py`: Rich telemetry console + JSONL Sink，自带 `_logger` 输出编码失败、镜像写入错误提醒，是工具层的一部分，理论上应保留但其内部还是依赖 logging。
- `src/foundational_service/persist/{redis_queue.py, worker.py, retry_scheduler.py, rabbit_bridge.py}`: 与任务队列/重试相关的模块记录队列消费、错误重试。去除后会难以排查任务堆积。
- `src/business_logic/workflow/orchestrator.py`、`src/business_service/{conversation,knowledge,workflow}.py`: 业务层日志抓取 stage 缺失、知识库加载、workflow prompt 失配等异常，属于“legacy”但仍补偿业务缺陷。
- `tools/` 下的 `rabbit_rehydrator.py`, `stream_mirror_worker.py`, `persist_worker.py`: CLI 工具记录执行状态，虽然可能 legacy，但某些脚本仍需日志反馈，否则运行无提示。
- `project_utility/logging.py` 与 `project_utility/tracing.py`: 提供 Rich Handler、可视化 trace span，是“工具函数”范畴，用户强调要保留。
- `sitecustomize.py`: `_warn_logger.info("warning.suppressed", ...)` 在解释器初始化时提示被压制的 warnings。

## Technology Stack
- Python 3.11（`.venv`），FastAPI + Starlette middleware。
- 日志系统基于 `logging` + `project_utility.logging` 提供的 Rich handler、旋转文件、警报面板，还有 `project_utility.tracing.trace_span` 异步上下文用于记录 span。
- Redis/Mongo/Rabbit 队列组件通过日志汇报状态，前端（Up）依赖这些日志来监控 webhook 请求。

## Search Results
1. **Structlog 文档（context7 `/hynek/structlog`）**：展示如何使用 processor、KeyValue renderer、filter_by_level，实现结构化日志与 thread-local context，说明如果迁移/重构日志需要新的 pipeline。强调 `tmp_bind` 等机制，可替代表层散落日志。
2. **OpenRewrite “Use modernized java.util.logging APIs” 文章（exa 2025-11-03）**：虽然针对 Java，但提醒“旧日志 API 会拖累平台，需要 recipe 统一迁移”——同样适用于当前项目：需要 recipe 化移除 legacy `log.*`，再用统一的新框架接管。

## Architecture Findings
- 日志使用分布在 30+ Python 文件，总调用 >100 次；主要集中在 `interface_entry`（启动、middleware、telegram）与 `foundational_service`（队列、遥测）。这些日志不仅是“打印”而是系统状态机一部分，如 capability 管理、清理流程、Telegram 重试等。
- 工具层 (`project_utility.logging/tracing`, `foundational_service.telemetry.bus`) 提供 Rich 控制台与 JSONL sink，是唯一可视化手段，应保留；但上层大量 `log.info` 与 `extra` payload 与这些 handler 紧耦合，简单删除会让控制台空白。
- Middleware `LoggingMiddleware` 与 Telegram handlers 产生日志事件 `webhook.request`, `telegram.handler.*`，外部监控依赖这些关键字；若移除需先定义新的 Telemetry 方案，否则 503/429 无法定位。
- 队列组件的日志（redis_queue, worker, retry_scheduler）是唯一的运行诊断（记录 ack 失败、任务超时），直接删除等于 “盲飞”。需要以新的事件总线或 metrics 取代后再移除。
- 工具/脚本 (`tools/rabbit_rehydrator.py` 等) 仍用于维护 Rabbit/Redis，日志用于 CLI 反馈。若确认这些脚本已废弃，可整体删除脚本而非单删 log。

## Defensive Considerations
- 移除日志前需确认替代的观测手段（如 OpenTelemetry/Structlog pipeline），否则任何 webhook 故障都无法追溯。尤其 interface_entry 层 log.extra 含 request_id / latency，若消失，前端 404/503 诊断成本大增。
- Redis/Mongo/Rabbit 相关日志目前唯一提示外部服务故障；若没有新报警机制，任务丢失难以及时发现。
- Trace span (`project_utility.tracing`) 依赖 log channel `rise.trace` 生成 begin/end 事件；如果不重新接线，trace 功能等同报废。
- `sitecustomize` 里的 `_warn_logger` 负责记录被 suppress 的 warnings，删除会掩盖资源泄漏。

## File References
- `src/interface_entry/bootstrap/app.py`
- `src/interface_entry/http/middleware.py`
- `src/interface_entry/telegram/{handlers.py,routes.py,runtime.py}`
- `src/interface_entry/runtime/{capabilities.py,supervisors.py,public_endpoint.py}`
- `src/foundational_service/{telemetry/bus.py,persist/{redis_queue.py,worker.py,retry_scheduler.py,rabbit_bridge.py}}`
- `src/business_logic/workflow/orchestrator.py`
- `src/business_service/{conversation/service.py,knowledge/snapshot_service.py,workflow/service.py}`
- `src/project_utility/{logging.py,tracing.py}`
- `tools/{rabbit_rehydrator.py,stream_mirror_worker.py,persist_worker.py}`
- `sitecustomize.py`

## Update 2025-11-10 03:20 CST
- 新需求：不是简单删日志，而是重建统一日志体系——需要 Debug 级信息同时写入文件与 console，Rich 负责降噪；希望能追踪到数据流、拼接 prompt、回复内容等细节，并辨识“该写没写”的盲点。
- 现状痛点：日志使用极不一致（少部分模块刷屏，大量关键路径无输出），console 报错信噪比低；需先设计结构化流水线（如 structlog + processors）再迁移。
- 目标能力：
  1. 多路输出（console + file）均支持 Debug 级别。
  2. Rich Renderer 对冗余字段去噪，只保留 request/prompt/result 关键线索。
  3. 必须留有 prompt 与响应内容（可截断），便于业务校验。
  4. 对缺失日志的模块给出补全策略（trace_span 或事件总线）。

## Update 2025-11-10 04:10 CST
- 当前剩余空缺：`foundational_service/telemetry/bus.py` 仍是旧版 Rich 控制台/JSONL sink，未与新 TelemetryEmitter 对接；Alert 去抖/事件过滤也未落实。
- 需落实：
  1. 重新定位 telemetry bus → 消费 TelemetryEmitter 生成的事件，提供 Rich 视图（基于 event_type 分类）和 JSONL 镜像。
  2. 在 emitter 中增加 Alert handler（WARN+ 去抖），以及事件过滤表达式。
  3. CLI/Runtime 已接入 telemetry，下一步无需重复。
