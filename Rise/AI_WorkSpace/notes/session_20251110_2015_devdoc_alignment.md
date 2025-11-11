# Session Notes 2025-11-10 20:15 CST

## User Intent
- 用户要求核对仓库中“最新一次开发文档”(`AI_WorkSpace/DevDoc/On/session_20251110_0750_telegram_channel_binding.md`)与代码实际落地情况，输出差异、落实点及待补项。

## Repo Context
- `AI_WorkSpace/DevDoc/On/session_20251110_0750_telegram_channel_binding.md:1-260` 规定渠道绑定一体化：统一 `workflow_channels` 数据源、四个 `/api/channel-bindings/*` API、`ChannelBindingRegistry` 缓存/事件、dispatcher 同步结构、健康监控+Kill Switch、事件队列+重放、运行时降级策略、GIVEN/WHEN/THEN 验收以及 11.x 架构分层（app.py 只留壳、lifespan + monitor + publisher + replayer、Business Service 过滤逻辑、ConversationService 去除 runtime policy fallback）。
- `src/interface_entry/bootstrap/app.py:286-660` 现已在 `create_app()` 中调用 `prime_channel_binding_registry()`、注入到 `app.state` 并向 `conversation_service_module` 注册 provider，同时通过 `configure_runtime_lifespan(... extra_contexts=(channel_binding_lifespan,))` 合并新的 lifespan，不过文件仍包含 600+ 行启动细节（能力探针、Aiogram 启动、KnowledgeBase、路由注册等），没有按文档 11.1 将逻辑拆出。
- `src/interface_entry/bootstrap/channel_binding_bootstrap.py:1-141` 新增 `prime_channel_binding_registry()` 同步预热、`channel_binding_lifespan` 启停 Redis 监听、健康监控与事件重放，满足文档对统一生命周期的要求。
- `src/interface_entry/runtime/channel_binding_monitor.py:1-134` 定期 `list_binding_options()`，对每个带 policy 的 workflow 调用 Telegram webhook 健康探测、写回 `record_health_snapshot()` 并通过 `ChannelBindingEventPublisher` 发送 `operation="health"` 事件，但未实现文档 8.1 中的内部 `/channels/telegram/test` 探活以及事件/错误计数驱动，Kill Switch 也仅靠 Service 手动维护。
- `src/foundational_service/messaging/channel_binding_event_publisher.py:1-92` + `src/interface_entry/runtime/channel_binding_event_replayer.py:1-56` 覆盖了文档 11.3 的发布→队列→死信链路，API 端会把 `PublishResult.warnings` 回传。
- `src/business_service/channel/service.py:58-200` 按文档 11.4 实现 `list_binding_options()` 过滤 workflow 状态、metadata enabled、kill switch 与健康状态；`record_health_snapshot()` 写入 `metadata.health`，`set_channel_enabled()` 在停用时自动标记 killSwitch。
- `src/business_service/channel/registry.py:1-166` 提供 `refresh()/handle_event()/attach_dispatcher()`，向 Aiogram dispatcher 注入 `workflow_data['channel_bindings'][channel] = {...}`，但尚无“每 10 分钟全量校验”的定时触发，仅靠事件或调用方刷新。
- `src/interface_entry/http/channels/routes.py:41-320` 新路由与 `POST /refresh` 已落地，旧 `/workflow-channels/*` 返回 410。但当前路由仍直接 orchestrate Service + Registry + Publisher + telemetry，接口层承担较多业务/基础设施逻辑。
- `src/business_service/conversation/service.py:110-360` 运行时完全依赖 `ChannelBindingProvider`，fallback `_extract_workflow_id` 已删除；然而 `_get_binding_runtime()` 获取失败时没有按文档 11.5 先触发一次 `registry.refresh()` + feature flag fallback，也没记录 `binding.version` 失败原因。

## Technology Stack
- FastAPI + Starlette lifespan、Aiogram 3.x Dispatcher、Motor/MongoDB、Redis asyncio(Pub/Sub + List 队列)、RabbitMQ TaskRuntime、Telegram Bot API、项目自研 telemetry/ContextBridge。

## Search Results
- **Context7 `/fastapi/fastapi`**：lifespan `@asynccontextmanager` 官方范式；强调替代 `@app.on_event` 并在单点创建/清理资源，有助于评估当前 `configure_runtime_lifespan` 的实现方向。
- **Exa(Search: "FastAPI background task architecture channel binding")**：定位 FastAPI BackgroundTasks 教程（fastapi.tiangolo.com），强调接口返回后再触发任务的做法，可对照本 repo 事件发布 fire-and-forget 的正确性。
- **Web(turn0reddit12, turn0search0, turn0search1, turn0search2, turn0reddit14, turn0reddit15, turn0search3, turn0reddit16)**：多篇 2024-2025 帖子讨论 lifespan 多上下文、测试替换设置、serverless 不触发 lifespan、Redis 异步客户端等，印证项目改用统一 lifespan & Redis async 的合理性，同时提示需要额外测试/配置注入机制。

## Architecture Findings
1. **渠道绑定主流程大体对齐文档**：Prime/Registry/事件发布/重放/Monitor/HTTP API 均存在，对应文件：`app.py:502-552`、`channel_binding_bootstrap.py:1-141`、`channel_binding_event_publisher.py:1-92`、`channel_binding_event_replayer.py:1-56`、`routes.py:53-196`。
2. **ConversationService 降级策略缺口**：`service.py:149-205` 在 binding 缺失时直接返回 `workflow_missing`，没有文档 11.5 所述“立即 refresh + feature flag fallback + telemetry 标记”，也未暴露 `bindingFallback` 指标。
3. **健康监控信号不足**：`channel_binding_monitor.py:65-134` 只使用 Telegram webhook 比较；未结合 `/channels/telegram/test`、enqueue 失败计数、Kill Switch 自动切换，导致文档 8.1/8.2 的多信号合并与自动 Kill Switch 缺位。
4. **定期全量校验缺失**：Registry 仅在事件或 API 刷新时更新，没有文档 7.2 所需“每 10 分钟全量校验”守护线程，长期失序/漏事件无法自动修复。
5. **入口文件仍然肥大**：`app.py:286-660` 继续维护 env 检查、capability probes、Telemetry、KnowledgeBase、路由注册等，未按 11.1 抽离，使 Interface 层仍违反“壳 + wiring”原则。
6. **HTTP 路由承担过多 orchestration**：`routes.py:96-320` 同时负责服务调用、registry 刷新、事件发布、meta.warnings 处理，缺少 Application Service/Command Handler，违背“接口只发起命令”的文档精神。
7. **Kill Switch 闭环只在 Admin 操作触发**：Service `set_channel_enabled()` 会写 metadata，但 Monitor 未在健康=down 时调用，无法达成文档 8.2 中“Monitor 判定 down 自动触发 kill switch/refresh”。

## File References
- `AI_WorkSpace/DevDoc/On/session_20251110_0750_telegram_channel_binding.md:1-260`
- `src/interface_entry/bootstrap/app.py:286-660`
- `src/interface_entry/bootstrap/channel_binding_bootstrap.py:1-141`
- `src/interface_entry/runtime/channel_binding_monitor.py:1-134`
- `src/interface_entry/runtime/channel_binding_event_replayer.py:1-56`
- `src/foundational_service/messaging/channel_binding_event_publisher.py:1-92`
- `src/interface_entry/http/channels/routes.py:41-320`
- `src/business_service/channel/service.py:58-200`
- `src/business_service/channel/registry.py:1-166`
- `src/business_service/conversation/service.py:110-340`

## Violations & Remediation
1. **Interface 层 `src/interface_entry/bootstrap/app.py`（层级：Interface）**：仍混合 env 校验、probe、registry prime、router 注册等大量 helper → 需将 Capability probes、KnowledgeBase 装载、ChannelBinding wiring 迁移到各自模块，仅保留 FastAPI 壳和 wiring。
2. **Interface 层 `src/interface_entry/http/channels/routes.py`**：路由直接 orchestrate Service/Registry/Publisher，违反“入口只发起命令” → 建议抽出 `ChannelBindingCommandService`（Business/Application 层），路由只做 DTO 解析与调用。
3. **Runtime 层 `src/interface_entry/runtime/channel_binding_monitor.py`**：承担健康计算、事件发布、Kill Switch 判定但缺少下层抽象 → 需把 Telegram 探测/信号聚合拆到 Business Service 或 Foundational helper，Monitor 仅编排调用。
## 2025-11-11T00:58Z Implementation Update
- ConversationService (`src/business_service/conversation/service.py`):
  - `_get_binding_runtime` 失败后会尝试 `ChannelBindingRegistry.refresh()`（1s 超时），失败会记录 telemetry。
  - 引入 `TELEGRAM_BINDING_FALLBACK_ENABLED` feature flag；当 registry 仍为空且 flag 打开时，从 runtime policy 构造降级 binding，version=-1 并写入 telemetry.binding.fallback。
  - 绑定缺失时统一走 `_build_binding_missing_result`，telemetry 增加 `workflow_status=missing`。
- ChannelBindingMonitor (`src/interface_entry/runtime/channel_binding_monitor.py`):
  - 初次集成 logger，health=status "down" 时自动触发 `WorkflowChannelService.set_channel_enabled(..., enabled=False)`，并发布 `channel_binding.kill_switch` 事件。
  - Kill switch 后强制 registry refresh，避免 stale binding。
- ChannelBindingBootstrap (`src/interface_entry/bootstrap/channel_binding_bootstrap.py`):
  - 新增 validator 背景任务每 600s 全量 `registry.refresh()`，确保事件漏掉时也能恢复。
  - Lifespan 会在 listener/monitor/replayer 之外启动/停止 validator。

防御性说明：
- Refresh 失败或超时会写 warning，避免无限等待；Kill Switch 发布 payload 附带 reason=health_down 供后续审计。
- Fallback runtime version -1，调用方可据此拒绝长期依赖；telemetry.binding.fallback=true 便于监控。
## 2025-11-11T01:45Z Interface Refactor Notes
- 新增 `business_service/channel/command_service.py`：封装 Channel Binding API 的业务编排，接口层不再直接操作 registry/publisher。`ChannelBindingCommandService` 负责 upsert/refresh/list，返回 warnings 供 HTTP meta 透出。
- `interface_entry/http/channels/routes.py` 现通过 `get_channel_binding_command_service` 依赖调用 command service，去除了直接操作 registry/publisher 的逻辑，符合“入口只发命令”要求。
- `interface_entry/http/dependencies.py` 暴露 `get_channel_binding_command_service`，从 FastAPI `app.state` 注入 `ChannelBindingEventPublisher`，确保上下文一致。
- `interface_entry/bootstrap/app.py` 改造成壳文件，只创建 FastAPI 并调用 `configure_application()`；CLI `--clean` 调用 builder 提供的 `perform_clean_startup()`。
- `interface_entry/bootstrap/application_builder.py` 承担原先 `create_app` 的全部逻辑（middlewares、Aiogram bootstrap、KnowledgeBase、lifespan 等）。其中 `perform_clean_startup()` 与 `release_logging_handlers()` 也迁移至此，供 app 壳重用。

缺口追踪：
- 入口瘦身已完成（app.py 仅壳）。
- Channel Binding HTTP handler 已降至薄层。
- 下一步需验证所有文档条目是否已满足（TODO：复查项目结构要求、记录 CHECKLIST）。
## 2025-11-11T02:25Z Health Monitoring Update
- 新增 `business_service/channel/health_store.py`（Redis 驱动）：记录 `workflow_missing`/`enqueue_failed` 错误计数，默认 TTL 15 分钟。
- `TelegramConversationService` 在 workflow missing 与 enqueue 失败时调用 `set_channel_binding_health_store()` 注册的 store，异步累加错误；并在 `_build_binding_missing_result` 中尝试根据 runtime policy 推断 workflowId。
- ChannelBindingMonitor：
  - 引入多信号融合：`_probe_webhook` + `_probe_internal_test`（可配置 `health.probeChatId` 或沿用 `allowedChatIds`）+ Redis 错误计数。
  - `_reduce_status` 统一优先级（down > degraded > ok > unknown），并在状态恢复 `ok` 时自动 reset 错误计数。
  - `status="down"` 时不仅触发 Kill Switch，还重置计数，防止累积。
- ChannelBindingBootstrap 将 `ChannelBindingHealthStore` 注入 `app.state`，ConversationService 与 Monitor 共享，满足文档 8.1 对“内部探活 + 错误事件”要求。

下一步：整理完整 checklist + 基本验证，用于最终验收。
