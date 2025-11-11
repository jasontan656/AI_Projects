# Rise Telemetry & Logging Overhaul（草案）

## 1. 背景 & 目标
- 现状：日志调用散落在 interface_entry/foundational_service/CLI，事件名与字段完全不统一，Debug 级别在 console/文件均不可控，Prompt/响应等关键数据也未系统记录。
- 目标：构建统一的 Telemetry 事件契约，借助 structlog + Rich 渲染，实现“Debug 级别写文件 + Debug 级别在 console 可控降噪 + Prompt/回复可复现”的全链路观测。
- 范围：
  1. Interface Entry（HTTP middleware、Telegram 路由、runtime）
  2. Foundational Service（队列、重试、遥测总线）
  3. Business Service/Logic（Workflow/prompt/publish 流程）
  4. CLI Tools（Rabbit/Stream 工具）
- 非范围：`project_utility.logging`/`project_utility.tracing` 基础能力保留，仅在内部扩展 emitter。

## 2. Telemetry 架构蓝图
### 2.1 事件契约
```yaml
TelemetryEvent:
  event_type: str  # 统一命名，示例：http.request / telegram.send / queue.retry / workflow.stage / prompt.render
  level: str       # debug/info/warn/error
  timestamp: str   # ISO8601，默认 project_utility.clock.philippine_iso()
  request_id: str? # 可空
  workflow_id: str?
  stage: str?      # workflow/stage name
  span_id: str?    # 对接 TraceSpan
  payload: dict    # 业务字段（prompt, response, latency, token_usage ...）
  sensitive: list[str]  # 需截断/脱敏的字段键
```
- 所有模块禁止直接 `log.info("event", extra=...)`，改为 `telemetry.emit(event_type, level="info", **fields)`。
- Prompt/回复等敏感字段进入 `payload.prompt_text/payload.reply_text`，并在 `sensitive` 标出，由 renderer 自动截断或 mask。

### 2.2 输出通道
| 通道 | 描述 | 等级策略 |
| --- | --- | --- |
| Rich Console Renderer | `project_utility.logging` 扩展 `_RichConsoleHandler`，加载 Telemetry Renderer，对 DEBUG 事件默认折叠，仅在 `--telemetry-console-level=debug` 时展开 | 默认 INFO+，可通过 env 调低 |
| JSONL File Sink | 新增 `_TelemetryJsonlHandler`，写入 `var/logs/telemetry.jsonl`，永远记录 DEBUG+ 并保留 payload 全量；对 `sensitive` 字段做 base64/截断 | Debug 永久开启 |
| Alert Handler | 继承 `_RichAlertHandler`，仅针对 WARN+ 事件，支持 `_ALERT_SUPPRESSION` 去抖；输出 request_id/workflow_id 方便定位 | WARN+ |
| OpenTelemetry Gateway（预留） | 通过 structlog processor 将事件转成 OTLP span/event（可选） | N/A |

### 2.3 处理链 (structlog)
```python
import structlog

shared = [
    structlog.processors.TimeStamper(fmt="%Y-%m-%dT%H:%M:%S.%fZ"),
    structlog.processors.add_log_level,
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]

structlog.configure(
    processors=shared + [TelemetryEventNormalizer(), TelemetryRouter()],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```
- `TelemetryEventNormalizer`：负责补齐 schema、拆分 payload/sensitive。
- `TelemetryRouter`：根据 event.level 分发到 console/jsonl/alert handler。

## 3. 分层落地计划
### 3.1 Interface Entry 层
- **HTTP Middleware (`src/interface_entry/http/middleware.py`)**：用 `telemetry.emit("http.request", level="info", path=..., status=..., latency_ms=...)` 替代 `_logger.info`。`signature_status` 仍保留，但标记为 `payload.signature_status`。
- **Telegram Handler (`src/interface_entry/telegram/handlers.py`)**：
  - 发送前 emit `telegram.prompt`（包含 prompt preview、attachments）。
  - 发送后 emit `telegram.send`（chat_id, latency, retries）。
  - 异常路径 emit `telegram.error`，等级按重试次数控制。
- **Runtime Capabilities / Supervisors**：所有 capability 状态改写为 `telemetry.emit("capability.state", level="warning", capability=name, status="degraded", detail=...)`。

### 3.2 Foundational Service 层
- **队列 (`redis_queue.py`)**：enqueue/dequeue/retry 事件映射至 `queue.enqueue`、`queue.ack`、`queue.retry`，payload 包含 task_id/workflow_id/retry_count。
- **Worker (`worker.py`)**：任务执行成功/失败分别发 `queue.task_completed` / `queue.task_failed`（携带 traceback 摘要）。
- **Telemetry Bus (`telemetry/bus.py`)**：从主动 logging 转为被动消费 `TelemetryEvent`，负责 Rich 可视化（Tree、Table、Prompt preview）。

### 3.3 Business Service & Logic
- **Workflow Service (`business_service/workflow/service.py`)**：
  - 在 publish/rollback 入口新增 `trace_span("workflow.publish", workflow_id=..., actor=...)`，span 内 emit `workflow.publish` 事件（diff 摘要）。
  - Prompt binding 缺失等错误用 `telemetry.emit("workflow.validation", level="error", missing_stages=[...])` 取代 `log.warning`。
- **Workflow Orchestrator**：对每个 stage emit `workflow.stage`（prompt=preview, output=preview, duration, token_usage）。

### 3.4 CLI Tools
- CLI 若继续使用，直接调用 `telemetry.emit` 输出到 console（Rich Renderer 会渲染），避免散落 `print/logging`。
- 若脚本已废弃，则整文件删除，杜绝 legacy 噪音。

## 4. Debug 数据可视化策略
- **Prompt/Response 预览**：
  - Console：`preview(text, length=200, escape_markdown=True)`。
  - File：全量文本 + `checksum`，便于比对。
- **数据流跟踪**：通过 `request_id`+`span_id` 将 http.request -> workflow.stage -> queue.enqueue -> telegram.send 串联，可在 Rich console 中降噪显示“流水线视图”。
- **Debug 切换**：引入 env `TELEMETRY_CONSOLE_LEVEL`, `TELEMETRY_FILE_LEVEL`，可在生产将 console = INFO, file = DEBUG。

## 5. 成功路径与核心流程
1. **启动**：`configure_logging()` 加载 structlog + 新 handler；`TelemetryEmitter` 单例注入到 interface_entry/foundational_service。
2. **请求生命周期**：
   - Middleware emit http.request
   - Workflow / prompt emit workflow.*
   - 队列 emit queue.*
   - Telegram emit telegram.*
3. **事件分发**：`TelemetryRouter` 把事件写到 Rich/JSONL/Alert，多路输出保持同步。
4. **调试体验**：开发者在 console 看到折叠后的流水线摘要，需要细节时展开事件或打开 JSONL。

## 6. 失败模式 & 防御
| 情况 | 风险 | 对策 |
| --- | --- | --- |
| 事件 payload 含敏感信息未标记 | Prompt/回复泄露 | `TelemetryEventNormalizer` 默认把 `prompt_text`, `reply_text` 视为 sensitive，未显式声明也会截断；同时 JSONL 文件需设置权限。 |
| 事件过量导致 CPU 飙升 | structlog 处理链消耗 | 支持 `TELEMETRY_EVENT_FILTER` 表达式（例如只保留 workflow.*），并允许 runtime 动态调控 console level。 |
| 旧日志仍散落 | 迁移不彻底 | 编写 AST 脚本（延用 `log_usage_report`）对 `log.` 调用给出 lint 警告，CI 阶段禁止新增旧式日志。 |
| trace_span 与 telemetry 重复 | 双写 | 让 `TraceSpan.__aenter__/__aexit__` 内部直接 emit `trace.*`，并将 logging handler 降到最低，避免重复消息。 |
| CLI 不兼容新 emitter | 运行无输出 | CLI 初始化时调用 `configure_logging`，并提供 `--console-level` 选项。 |

## 7. 验收条件（GIVEN/WHEN/THEN）
1. **GIVEN** 中控以 Debug 级别启动 **WHEN** 触发 Telegram 流程 **THEN** JSONL 中存在完整 prompt/回复、console 仅显示折叠摘要。
2. **GIVEN** Redis 断连 **WHEN** runtime 检测到 capability 降级 **THEN** console Alert 出现一次警告且 60s 内不重复刷屏。
3. **GIVEN** Workflow publish 失败 **WHEN** stage 缺失 **THEN** `workflow.validation` 事件在 console/file 均有记录，payload 列出 missing_stages。
4. **GIVEN** 执行 CLI `rabbit_rehydrator` **WHEN** 运行成功 **THEN** console 呈现 `tools.rabbit_rehydrator.completed` 事件，无 legacy `print`。
5. **GIVEN** 开启 `TELEMETRY_CONSOLE_LEVEL=debug` **WHEN** 处理请求 **THEN** console 会展示全量事件（http -> workflow -> queue -> telegram），便于线上调试。

## 8. 后续任务
- [ ] 实现 `TelemetryEmitter` + structlog 配置模块（project_utility.logging）
- [ ] Interface Entry 层迁移（middleware/telegram/runtime/workflow routes）
- [ ] Foundational Service 队列/worker/rabbit/telemetry bus改造
- [ ] Business 层（workflow/prompt）补齐事件
- [ ] CLI 工具迁移或删除
- [ ] 编写 AST lint / CI hook 阻止新增 legacy `log.*`
# Telemetry Bus → TelemetryEmitter 迁移方案（补充）

## 1. 现状
- `src/foundational_service/telemetry/bus.py` 仍自带 Rich 渲染与 JSONL Writer，依赖 logging 事件（如 `log.warning`）而非新 TelemetryEvent。
- 要求：该模块应该成为新的事件消费/展示层，订阅 `TelemetryEmitter` 输出（或共享 JSONL 文件），提供更细粒度的 console 视图（树形或表格）并实现 Alert 去抖。

## 2. 设计补充
1. **事件来源**：
   - 利用 TelemetryEmitter 的 `_jsonl_sink`，通过 tail/文件读取或直接注入事件回调机制。
   - 规划 `TelemetrySubscriber` 接口：`register_sink(handler: Callable[[TelemetryEvent], None])`，Emitter 在写事件时同步通知订阅者。
   - Telemetry bus 注册自己的 handler，渲染 Rich Tree/Panel，输出到独立 Console。

2. **Alert 去抖**：
   - 将 `_ALERT_SUPPRESSION` 逻辑从旧 logging 迁移到 TelemetryBus，按事件类型 + status code 做窗口抑制。
   - WARN+ 事件 -> Alert Panel；INFO/DEBUG -> 可视化流水线。

3. **Prompt/响应呈现**：
   - 复用 emitter 的 `_mask_payload` 结果，配合 bus 的 `_preview` 辅助函数；设定 `prompt_preview_chars=200`。

4. **实现步骤**：
   - [ ] 在 TelemetryEmitter 中新增 `register_listener(callback)` API。
   - [ ] Telemetry bus 改为注册上述 listener，收到事件后分类渲染：`workflow.*`, `queue.*`, `telegram.*`, `capability.*`, `tools.*`。
   - [ ] 删除 bus 内部的 `_JsonlWriter`/自写 Console handler，改用 emitter 提供的 `Console` 或共享 Sink。

## 3. 防御
- 防止 listener 抛异常导致 emitter 崩溃：listener 执行 wrap try/except。
- 事件量大时 bus 可根据 `event_type` 白名单过滤，避免 Rich 输出阻塞。
- 保留 JSONL 镜像以便离线分析（无需 bus 再次写）。
