# Session Notes 2025-11-10 23:55 CST

## User Intent
- 依据《session_20251110_0750_telegram_channel_binding.md》要求，逐项核对代码库实际实现情况，判断是否已满足“渠道绑定为真实数据源、运行时动态刷新、健康监控+Kill Switch、事件重放”后才进入测试阶段。

## Repo Context
- `AI_WorkSpace/DevDoc/On/session_20251110_0750_telegram_channel_binding.md:29-220`：定义统一数据源、四个 Channel Binding API、运行时 Registry/Monitor/事件重放流程，以及 11.1 启动拆分、11.2 Monitor 接入、11.3 Publisher/Replay、11.4 Dispatcher 缓存同步等架构要求。
- `src/interface_entry/bootstrap/app.py:301-705`：入口仍串联 env 校验、Aiogram bootstrap、Capability probes、知识库加载、ChannelBindingRegistry 引导与路由注册；引入 `channel_binding_bootstrap`/`runtime_lifespan` 模块但未真正调用（仍引用不存在的 `_prime_channel_binding_registry`，且 `configure_runtime_lifespan` 被调用两次）。
- `src/interface_entry/bootstrap/channel_binding_bootstrap.py:1-88`：新增同步 prime + Redis 监听 + Monitor start/stop，但通过 `app.add_event_handler()` 注册，尚未并入统一 lifespan；`prime_channel_binding_registry()` 未在 app.py 使用。
- `src/interface_entry/http/channels/routes.py:60-220`：新增 `/api/channel-bindings/*` 三个端点与 refresh API，并保留旧 `/workflow-channels/*`；接口层依旧直接 orchestrate `WorkflowChannelService`、Registry refresh 与事件发布。
- `src/interface_entry/runtime/channel_binding_monitor.py:1-73`：实现定期 `list_binding_options()` + Telegram webhook 健康检测，并写回 metadata，但未发布 `channel_binding.health` 事件（doc 11.2 要求）。
- `src/business_service/channel/registry.py:1-123`：Registry 支持 options 缓存、Dispatcher 同步、kill switch 字典；`_select_active_option()` 仅基于 status/killSwitch，不含 workflow 发布状态校验。
- `src/business_service/channel/service.py:1-210`：Service 现在会将 kill switch 闭环写入 workflow metadata，并在 `list_binding_options()` 里计算 `status`，但 `_should_include_workflow()` 依然只检查 workflow.status + enable flag，没引用文档要求的 `channel_bindings` 视图/发布版本过滤。
- `src/business_service/conversation/service.py:110-160 & 772-782`：运行时只在 registry 成功注入时使用 binding，fallback 仍调用 `_extract_workflow_id()`；违背文档“绑定关系为唯一真源”的目标。
- `foundational_service/messaging/channel_binding_event_publisher.py:1-74`、`interface_entry/runtime/channel_binding_event_replayer.py:1-54`：Publisher/重放器已存在，但重放仅在 `_redis_backfill()` 被 RuntimeSupervisor 触发时运行，缺少文档 11.3 约定的独立周期任务。

## Technology Stack
- FastAPI + Starlette lifespan、Aiogram 3.x Dispatcher、Motor/MongoDB、Redis (asyncio、Pub/Sub + List)、RabbitMQ TaskRuntime、自研 telemetry。

## Search Results
- `context7:/fastapi/fastapi` Lifespan 文档：推荐以 `asynccontextmanager` 管理 startup/shutdown，弃用 `@app.on_event`（用于评估 channel binding 监听是否应迁移到统一 lifespan）。
- `exa docs.aiogram.dev`（2024-08-06 & dev-3.x）Dependency Injection 指南：Dispatcher 可通过 `dp["key"] = value` 或初始化 kwargs 注入自定义上下文，支撑文档 11.4 中 `dispatcher.workflow_data["channel_bindings"]` 的设计。

## Architecture Findings
1. **Registry 未实际 prime**：`app.py:520-533` 调用 `_prime_channel_binding_registry()`（旧函数名已删除），捕获 NameError 后将 registry 置空，结果 `set_channel_binding_registry()`、Dispatcher attach、Redis 监听、Monitor/事件重放全被跳过，运行时仍回退到 `_extract_workflow_id()`；直接违背文档“运行时动态挂载”的第 3 项（doc 行 29-33）。
2. **入口拆分未落地**：虽然新增 `channel_binding_bootstrap.py`、`runtime_lifespan.py`，但 `app.py` 依旧 800+ 行且继续维护 capability probes/生命周期钩子，`configure_runtime_lifespan()` 还被调用两次（app.py:568-582），违反 11.1 中“app.py 仅保留壳 + 调用新模块”。
3. **Monitor 未产出 Kill/Health 事件**：`channel_binding_monitor.py` 仅读写 Mongo metadata，不会向 `channel_binding.health` 主题广播，也未在健康=down时触发 kill switch（doc 11.2.2-11.2.3）。
4. **HTTP 层仍承担业务/基础设施职责**：`routes.py:60-220` 内既负责策略校验、Registry refresh，又直接调用 Publisher；doc 11.3 希望 Interface 仅发起命令，容错由 Publisher+后台任务负责，且旧 `/workflow-channels` 接口应逐步淘汰，当前仍提供可直接写入 policy 的老入口，易导致绑定绕过 registry。
5. **事件重放未常驻**：`channel_binding_event_replayer.py` 只有 `replay_pending()`，且 `app.py:555-559` 仅在 Redis backfill 时调用一次，缺少“RuntimeSupervisor 驱动的周期任务”与失败计数监控（doc 11.3.4-11.3.5）。
6. **Conversation fallback 逻辑未关闭**：`TelegramConversationService` 仍允许 policy/workflow payload 决定 workflow（service.py:110-160, 772-782），文档 2.2/3 要求入口只信任 registry + kill switch。
7. **Kill switch 影响不完整**：虽然 registry 缓存了 `kill_switch`，但 ConversationService 并未读取，且 `WorkflowChannelService._select_active_option()` 仅基于 metadata.status + flag；doc 8.2/10.2 期望 runtime 能即时拒绝停用 workflow。
8. **Lifespan 迁移不彻底**：`channel_binding_bootstrap.register_channel_binding_events()` 仍用 `app.add_event_handler` 注册同步 lambda，而 `runtime_lifespan` 的 asynccontextmanager 已可承载这些任务，造成双轨生命周期，增加“危险中间态”风险。

### 防御性 / 边界考虑
- 只要 `_prime` 失败就没有任何绑定缓存，HTTP API 仍允许直接写 policy → 生产中会出现“UI 显示绑定但 Bot 仍 missing”；需要在 bootstrap 失败时立即抛错或降级到只读模式。
- Monitor 写入 Mongo 的健康状态没有幂等锁或速率限制，若 Telegram API 抖动可能频繁刷新 causing registry 一直 `kill_switch`，需结合 exponential backoff。
- Publisher 失败仅通过 `meta.warnings` 告知客户端，缺少对 `event_queue` 长度/重放失败的监控；测试前需准备 Redis 故障注入脚本。

## File References
- `src/interface_entry/bootstrap/app.py:301-705` – create_app 全貌、`_prime_channel_binding_registry` 调用、双重 lifespan、事件注册。
- `src/interface_entry/bootstrap/channel_binding_bootstrap.py:1-88` – prime/listener/monitor start-stop 逻辑。
- `src/interface_entry/bootstrap/runtime_lifespan.py:1-74` – asynccontextmanager lifespan 实现。
- `src/interface_entry/runtime/channel_binding_monitor.py:1-73` – Monitor 健康刷新流程。
- `src/interface_entry/runtime/channel_binding_event_replayer.py:1-54` – 事件重放器。
- `src/interface_entry/http/channels/routes.py:60-220` – Channel Binding API 与旧接口共存。
- `src/business_service/channel/registry.py:1-123` – Dispatcher 缓存/kill switch 表现。
- `src/business_service/channel/service.py:1-210` – `list_binding_options()`、`set_channel_enabled()`。
- `src/business_service/conversation/service.py:110-160, 772-782` – Binding provider 注入与 fallback `_extract_workflow_id()`。
- `AI_WorkSpace/DevDoc/On/session_20251110_0750_telegram_channel_binding.md:29-220` – 需求清单。

## Violations & Remediation
1. **Interface Layer – `src/interface_entry/bootstrap/app.py`**
   - Violations: (1) 入口与大量 helper/业务代码混杂；(4) Interface 层直接管理 registry/monitor lifecycle。
   - Remediation: 实际调用 `prime_channel_binding_registry()`、`register_channel_binding_events()` 应迁至 `channel_binding_bootstrap`; `app.py` 仅保留 FastAPI 构建 +模块 wiring；删除重复 `configure_runtime_lifespan()`，并在 `_prime` 失败时终止启动。
2. **Interface Layer – `src/interface_entry/http/channels/routes.py`**
   - Violations: (2) 路由直接操控 registry refresh + 发布事件；(3) 旧 `/workflow-channels` API 仍允许直接写 policy。
   - Remediation: 将 refresh/event 发布改为调用 Business Service / Application Service；标记旧接口只读或移除；若确需兼容，至少写入 doc 风险并限制权限。
3. **Business Service – `src/business_service/conversation/service.py`**
   - Violations: (2) 业务逻辑仍依赖 foundational policy（runtime policy JSON）而非 registry；(3) Binding runtime 与 fallback `_extract_workflow_id()` 同处模块。
   - Remediation: 提供独立 `channel_binding_runtime.py` 负责 registry 交互，ConversationService 只注入接口；移除 `_extract_workflow_id()` fallback 并在 binding 缺失时直接返回维护文本。
4. **Interface Runtime – `src/interface_entry/runtime/channel_binding_monitor.py`**
   - Violations: (4) Monitor 仅在模块内部维护健康，没有向下游事件/registry 抽象汇报。
   - Remediation: 抽出 `ChannelBindingHealthPublisher`（Foundational）并由 Monitor 调用；健康状态变化触发 kill switch + registry refresh，遵守 doc 8/11.2。
## Implementation 2025-11-11T00:45
- `src/interface_entry/bootstrap/app.py`: 实际调用 `prime_channel_binding_registry()`，失败即终止启动；删除遗留 `_prime` 引用、统一由 `channel_binding_lifespan` 挂入 `configure_runtime_lifespan(extra_contexts)`，并移除重复 lifespan 注册与旧事件钩子。
- `src/interface_entry/bootstrap/channel_binding_bootstrap.py`: 提供 `channel_binding_lifespan`，集中启动/停止 Redis 监听、健康 Monitor、事件重放器；新增后台重放任务与 stop hooks。
- `src/interface_entry/bootstrap/runtime_lifespan.py`: 引入 `AsyncExitStack` 支持额外 lifespan contexts，确保 shutdown 顺序涵盖 channel binding 资源。
- `src/interface_entry/runtime/channel_binding_monitor.py`: Monitor 现在可选注入 `ChannelBindingEventPublisher`，在写入健康快照后发布 `operation="health"` 事件，并将快照时间包含在 payload 中。
- `src/business_service/conversation/service.py`: Telegram 会话完全依赖 registry，若 binding 缺失直接返回 workflow missing，移除 `_extract_workflow_id` 兜底。
- `src/interface_entry/http/channels/routes.py`: 旧 `/workflow-channels/*` 端点统一返回 410，防止绕过新渠道绑定 API。
