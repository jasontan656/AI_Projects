# Session Notes 2025-11-10 21:02 CST

## User Intent
- 调研 `session_20251110_0750_telegram_channel_binding.md` 文档的实施状态，确认 bootstrap/app.py 的重构和新的 ChannelBindingMonitor/事件订阅在当前代码中的真实情况，并识别导致“危险中间态”的缺口与风险。
- 当前任务：在新的守卫提示下重新扫描项目，列出 Interface / Foundational / Business Service 层相关的违规与迁移需求，以便后续更新 `session_20251110_0750_telegram_channel_binding.md` 并安全改造 `app.py` 等核心入口。

## Repo Context (Layer-tagged)
- **Interface Layer – `AI_WorkSpace/DevDoc/On/session_20251110_0750_telegram_channel_binding.md`**：目标文档要求统一 Mongo 真源、HTTP 选项接口、运行时事件刷新、Dispatcher 缓存结构、health/kill switch 以及 Redis 事件广播。
- **Interface Layer – `src/interface_entry/bootstrap/app.py:149-780`**：入口文件混合 env 初始化、清理脚本、FastAPI lifespan、ChannelBinding registry、KnowledgeBase loader、Redis/Telemetry 监控与 CLI 逻辑；`_prime_channel_binding_registry()` 缺失定义导致导入即 `IndentationError`，Startup/Shutdown 钩子用同步 lambda 包裹协程无法 `await`。
- **Interface Runtime – `src/interface_entry/runtime/channel_binding_monitor.py`**：实现定期健康巡检但无人实例化，未纳入 lifespan；健康快照只能靠手工 API。
- **Interface HTTP – `src/interface_entry/http/channels/routes.py:91-335`**：路由层直接负责 Redis 发布、健康写入、policy 读写；缺乏容错与后台重放，违反“入口只做协议适配”。
- **Business Service – `src/business_service/channel/registry.py`**：缓存 active workflow 并同步到 dispatcher，但因为 bootstrap 未完成初始化，该层逻辑实际无效。
- **Business Service – `src/business_service/channel/service.py:200-258`**：`_should_include_workflow()` 只要存在 policy 即输出，忽略 workflow 发布状态或 kill switch，高风险。
- **Business Service – `src/business_service/conversation/service.py:302-360`**：`_get_binding_runtime()` 捕获异常后直接回退 `_extract_workflow_id()`，使运行时继续依赖旧 policy，违背“绑定关系为真源”。

## Technology Stack
- Python 3.11、FastAPI + Starlette lifespan、Motor/MongoDB、Redis（asyncio + Pub/Sub）、Aiogram 3.x Dispatcher、Redis Streams Worker、自研 telemetry/knowledge base。

## Search Results
- **FastAPI Lifespan (context7 `/fastapi/fastapi`)**：官方建议用 `FastAPI(lifespan=...)` 管控启动/关闭，`@app.on_event` 已逐步废弃；意味着 `_start_channel_binding_listener` 等必须挂在 async lifespan，不能用同步 lambda。
- **Aiogram Dispatcher (exa docs.aiogram.dev)**：Dispatcher/Router 支持拆分模块化 handler，新的 binding loader 应通过 dispatcher context（`dispatcher.workflow_data[...]`）向运行时注入数据，而非在 HTTP 进程自管缓存。

## Architecture Findings
1. **入口文件不可编译**：`bootstrap/app.py` 缺失 `_prime_channel_binding_registry` 定义，导入即抛 `IndentationError`，HTTP/Telegram 服务无法启动。
2. **事件监听器未运行**：同步 lambda 注册异步协程，Redis Pub/Sub 监听任务从未 `await`，`ChannelBindingEvent` 无法驱动 registry 刷新。
3. **ChannelBindingMonitor 未接入**：没有任何生命周期管理，健康状态与 kill switch 设计流于文档。
4. **事件发布无容错**：HTTP 路由层直接 `redis.publish`，Redis 波动会让 API 报错，违背“fire-and-forget + 重放”的方案。
5. **停用逻辑缺失**：`WorkflowChannelService._should_include_workflow` 与 `ChannelBindingRegistry._select_active_option` 忽略 workflow 发布/启用状态，停用流程仍可能被选择。
6. **会话降级不透明**：`TelegramConversationService` 只要 registry 查找失败就回退旧 policy，与“绑定关系为唯一真源”冲突。
7. **入口层职责过载**：`bootstrap/app.py` 同时承担清理脚本、CLI、配置、监控、运行期任务管理，触犯“入口文件只负责协议适配 + 调用下层”的守卫。

## Violations & Remediation
1. **Interface Layer – `src/interface_entry/bootstrap/app.py`**
   - *Violations*: (1) 单文件同时包含入口/业务流程与大量 helper；(4) Interface 层自实现大段逻辑而非委托下层。
   - *Remediation*: 
     - 拆出 `bootstrap/channel_binding_bootstrap.py`（Interface 子模块）专门负责 registry/monitor wiring；
     - 拆出 Foundational `foundational_service/runtime/capability_bootstrap.py` 处理 capability probes；
     - CLI/清理逻辑迁至独立工具脚本；
     - Lifespan 统一改为 async context manager，startup/shutdown 钩子不再使用同步 lambda。

2. **Interface Runtime – `src/interface_entry/runtime/channel_binding_monitor.py`**
   - *Violations*: (4) 监控组件未被入口流程管理，造成 interface 层无法委托；
   - *Remediation*: 由新的 bootstrap 模块在 lifespan 中创建/停止 `ChannelBindingMonitor`，并把健康事件推送到 Business Service 层供 registry 使用。

3. **Interface HTTP – `src/interface_entry/http/channels/routes.py`**
   - *Violations*: (2) 路由层直接实现 Redis 发布与容错；(4) HTTP 层承载健康写入、事件重放等业务逻辑；
   - *Remediation*: 将事件发布/重试抽象为 Foundational service（例如 `foundational_service/messaging/channel_binding_event_publisher.py`），路由只调用 service；health 录入转交 `WorkflowChannelService.record_health_snapshot` 的异步任务，并在 HTTP 层捕获异常→返回 degrade 状态。

4. **Business Service – `src/business_service/channel/service.py` 与 `registry.py`**
   - *Violations*: (5) `_should_include_workflow` 忽略启用状态，`registry._select_active_option` 可能选择停用 workflow；
   - *Remediation*: 新增 workflow 发布/启用过滤，支持 kill switch 标记；在 DevDoc 中明确需要额外字段（例如 `status in {'published','active'}` + `channels.telegram.enabled`）才可入列。

5. **Business Service – `src/business_service/conversation/service.py`**
   - *Violations*: (2) 会话层直接 fallback 到 runtime policy，而不是依赖 registry；
   - *Remediation*: 在 DevDoc 中要求实现 binding 缺失时的兜底策略（例如重载 registry、触发告警、拒绝请求），并把旧 policy fallback 列为短期兼容选项，后续删除。

6. **Interface Layer – `AI_WorkSpace/DevDoc/On/session_20251110_0750_telegram_channel_binding.md` (设计债)**
   - *Violations*: 文档未明确列出上述拆分/迁移动作，Implementation 无法照章执行；
   - *Remediation*: 更新文档加入模块划分、迁移步骤、层级标签和“功能保持”的约束，确保后续实现直接遵循。

## File References
- `AI_WorkSpace/DevDoc/On/session_20251110_0750_telegram_channel_binding.md`
- `src/interface_entry/bootstrap/app.py:149-780`
- `src/interface_entry/runtime/channel_binding_monitor.py`
- `src/interface_entry/http/channels/routes.py:91-335`
- `src/business_service/channel/registry.py`
- `src/business_service/channel/service.py:200-258`
- `src/business_service/conversation/service.py:302-360`
## 2025-11-10T22:55 DevDoc Update
- 将 `session_20251110_0750_telegram_channel_binding.md` 新增第 11 章，明确以下迁移：
  1. **Interface**：`bootstrap/app.py` 仅保留壳，ChannelBinding/Redis/Dispatcher 迁入 `bootstrap/channel_binding_bootstrap.py`，lifespan 迁入 `bootstrap/runtime_lifespan.py`。
  2. **Monitor**：startup/shutdown 统一管理 `ChannelBindingMonitor`，健康变化需写 `channel_binding.health` 事件并驱动 registry。
  3. **Foundational**：新增 `foundational_service/messaging/channel_binding_event_publisher.py`，HTTP 路由仅调用抽象层，容错由 Publisher + 重试 worker 承担。
  4. **Business Service**：`WorkflowChannelService`、`ChannelBindingRegistry` 引入 workflow 状态/kill switch 过滤并同步 dispatcher snapshot；`TelegramConversationService` 禁止静默 fallback，改为 refresh + 维护提示 + telemetry。
  5. **Layer Mapping**：附表列出受影响模块所属层级，供 Implementation 按“复制原逻辑→迁移→入口改为调用”执行。
  6. **Success/Failure/Constraints**：补充运行路径、失败场景与新版 GIVEN/WHEN/THEN，确保 Implementation 有明确验收标准。
## 2025-11-10T23:25 Implementation Stage 1
- 将 ChannelBinding registry/监听逻辑移动到 `interface_entry/bootstrap/channel_binding_bootstrap.py`，提供 `prime_*` 与事件注册 API，避免 `app.py` 顶层无定义代码造成的语法错误。
- 新增 `interface_entry/bootstrap/runtime_lifespan.py`，抽离原先 `create_app()` 内的 capability monitor + lifespan 组合，通过 `configure_runtime_lifespan()` 注入，后续阶段可继续扩展。
- `src/interface_entry/bootstrap/app.py` 现仅负责组装依赖、调用上述模块，并统一在 `app.state.runtime_supervisor` 设置后配置 lifespan；事件钩子改为引用新模块函数。
- 基本验证：`python -m py_compile src/interface_entry/bootstrap/app.py` 通过，确认语法与导入无误；未运行完整服务启动（需外部 Redis/Mongo 环境）。
## 2025-11-10T23:40 Stage1 Verification
- `python -m py_compile` 通过：`app.py`、`channel_binding_bootstrap.py`、`runtime_lifespan.py` 均无语法问题。
- 当前未启动完整服务或前端（缺乏 Redis/Mongo/Telegram credentials），后续阶段完成后统一进行端到端验证。
## 2025-11-10T23:55 Stage2 Progress
- `channel_binding_bootstrap.py` 现提供 `_build_channel_binding_service()`，`prime_*` 与 monitor 启停，startup/shutdown 自动启动巡检任务并保存到 `app.state.channel_binding_monitor`。
- `register_channel_binding_events(app)` 统一注册 listener 与 monitor，shutdown 顺序：先停监控再停监听。
- `app.py` 仍只需调用 `register_channel_binding_events`，其余逻辑保持不变；监控将在 startup 时由新模块创建，后续阶段可接入健康事件。
- 验证：`python -m py_compile` 覆盖 `app.py` 和 bootstrap 新文件，确保导入和语法正确。
## 2025-11-11T00:05 Stage3 Plan (Foundational Event Publisher)
- **Layer / Modules**: 新增 `foundational_service/messaging/channel_binding_event_publisher.py`（Foundational），负责构造 Redis 发布 + 重试逻辑；`src/interface_entry/http/channels/routes.py`（Interface）改为调用 Publisher；后续若需 worker，则由 RuntimeSupervisor（Interface Runtime）启动定期重放任务。
- **Data Lifecycle**: 事件先尝试 `redis.publish(channel_binding.updated, payload)`；若返回失败或抛异常，将 JSON 推入 `redis.rpush("rise:channel_binding:event_queue", payload)` 并记录 telemetry。后续后台任务从该 List 读取事件、重试 publish，成功后 `lrem` 清除；若重试多次失败则写入 Mongo 集合 `channel_binding_deadletter`（字段：event、error、retryCount、lastFailureAt）。
- **Callers / Migration**: 现有 `_publish_binding_event` 4 个调用点均在 `src/interface_entry/http/channels/routes.py` 的 upsert/delete/refresh API，需要替换为 `ChannelBindingEventPublisher.publish(event)`。文档需标明搜索关键词 `"_publish_binding_event"` 以确保没有遗漏。
- **Validation / Success Criteria**: 
  1. 正常情况下 Redis 发布成功，HTTP API 仍返回 200；
  2. 模拟 Redis 不可用时，事件应堆积到 `rise:channel_binding:event_queue`，HTTP 返回 200 且 `meta.warnings` 提示 `event_queued`；
  3. Replay 任务运行后，队列长度下降、事件被 publish，若仍失败则落入 Mongo deadletter 并触发告警。
- **Design Freedom**: 事件持久介质固定为 Redis List + Mongo deadletter；如需改用别的存储，必须在未来 DevDoc 明确说明，否则实现阶段默认按此方案执行。
## 2025-11-11T00:25 Stage3 Implementation
- **Foundational**：新增 `foundational_service/messaging/channel_binding_event_publisher.py`，实现 `ChannelBindingEventPublisher` + `PublishResult`，支持 Redis 即发、失败入 `rise:channel_binding:event_queue`，以及 Mongo `channel_binding_deadletter` 归档，配套 `get_channel_binding_event_publisher()` 单例。
- **Runtime**：新增 `interface_entry/runtime/channel_binding_event_replayer.py`，提供 `ChannelBindingEventReplayer.replay_pending()`，在 Redis 恢复（`_redis_backfill`）时由 RuntimeSupervisor 触发，逐条出队并再次 publish，失败则写 deadletter。
- **Bootstrap**：`create_app()` 注入 Publisher/Replayer 到 `app.state`，并在 `_redis_backfill` 中调用 `replay_pending()`，确保 Redis 恢复后自动清队；必要时可扩展后台循环。
- **HTTP Interface**：`src/interface_entry/http/channels/routes.py` 改为使用 `_event_publisher`，Meta.warnings 会合并 Publisher 返回的 `event_queued` / `event_deadletter` 标记，旧 `_publish_binding_event` 函数移除。
- **验证**：`python -m py_compile` 覆盖新/改模块（publisher、replayer、app.py、routes.py），语法与导入全部通过；暂未跑端到端 API（依赖实际 Redis/Mongo/TG 环境）。
## 2025-11-11T00:55 Stage4 Implementation
- **WorkflowChannelService**：`list_binding_options` / `_get_binding_view` 支持 kill switch；新增 `_get_channel_metadata` / `_is_kill_switch_active`，`_derive_status` 输出 `kill_switch` 状态，`_build_binding_option` 记录 `kill_switch` 字段；`set_channel_enabled` 根据 enabled 自动写入/清除 `killSwitch`。
- **ChannelBindingRegistry**：refresh 时缓存 `kill_switch` 映射；Active 选择排除 kill switch 条目；dispatcher snapshot payload 现含 `layer`、`killSwitch`、`active` 等字段；`registry._kill_switch` 用于后续扩展。
- **验证**：`python -m py_compile` 对 `service.py`、`registry.py` 通过；未运行端到端测试（待 Stage5 一并验证）。
## 2025-11-11T01:25 Stage5 Implementation
- `business_service/conversation/service.py`
  - `_get_binding_runtime()`：首次失败时触发 `registry.refresh()`，若仍无 binding，则记录 `binding.status="missing"` 并返回维护提示，不再悄悄回退旧 policy。
  - `process_update()`：当 binding 缺失/kill switch 时，telemetry 中写入 `binding.activeWorkflowId`、`binding.version`、`binding.status` 等字段，方便排障；保留 feature flag 式 fallback（默认关闭）。
- `registry.refresh()` 触发时由于 Stage4 已同步 kill switch + dispatcher snapshot，此处只需消费 `ChannelBindingRuntime.version`。
- 验证：`python -m py_compile src/business_service/conversation/service.py` 通过；完整会话/telemetry 验证留待端到端测试阶段。
## 2025-11-11T01:50 Stage3 Backfill Follow-up
- 暂未实现持续后台重放任务：`ChannelBindingEventReplayer` 仅在 `_redis_backfill` 调用时执行一次，与 DevDoc“后台 worker 持续重放”存在差距。需要在 RuntimeSupervisor 或独立任务中定时调用 `replay_pending()`，确保 `rise:channel_binding:event_queue` 不长期堆积。
- 目前待办：
  1. 决定重放任务挂在哪（RuntimeSupervisor? 新协程?）。
  2. 处理连续失败后的 backoff，避免无限 tight loop。
  3. 运行阶段统一测试 Redis 抖动/恢复后的队列清空效果。
## 2025-11-11T02:15 Event Replay Task
- RuntimeSupervisor 内新增 `ChannelBindingEventReplayer`（单例）与周期任务 `_channel_binding_event_task`，在 startup 时与 capability monitors 一起启动，在 shutdown 时停止。
- 当 Redis 恢复（或定时触发）时，replayer 从 `rise:channel_binding:event_queue` 批量弹出事件，调用 Publisher 重新 publish；失败则推回队列或写入 Mongo deadletter。
- 验证：`python -m py_compile` 对 `channel_binding_event_replayer.py`、`bootstrap/app.py`、`http/dependencies.py` 均通过；端到端 Redis 故障测试待后续执行。
