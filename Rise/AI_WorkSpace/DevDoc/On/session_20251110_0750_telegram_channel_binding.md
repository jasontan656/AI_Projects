# Telegram 渠道绑定一体化方案（session_20251110_0750）

## 1. 背景
- 前端 Admin 面板已经支持 Workflow/Prompt/Node 的可视化构建，并允许在“渠道设置”中录入 Telegram Bot Token、Webhook、提示语、白名单等参数。
- 现状只把这些参数写入 Mongo 集合 `workflow_channels`，运行时仍依赖 `runtime_policy.entrypoints.telegram.workflow_id` 这样的静态配置。只要 policy 中缺少 workflow_id，`TelegramConversationService` 会直接返回 “未找到对应流程”。
- 业务目标：渠道绑定必须 **由后端列出可选 Workflow**，前端只能选择其一并保存；运行时应以绑定关系为真源，无需手工编辑 runtime policy。

## 2. 现状与缺口
### 2.1 WorkflowChannelService / Repository
- `WorkflowChannelService` 接口：
  - `get_policy(workflow_id, channel)`、`save_policy(workflow_id, payload, channel)`、`delete_policy`。
  - 数据模型 `WorkflowChannelPolicy` 包含 `workflow_id`、`channel`、bot token、webhook、metadata（allowedChatIds 等）。
- 缺陷：
  - 没有持久化 “workflow ↔ 渠道状态” 以外的元信息（如已绑定/可选状态）。
  - 也没有把 `workflow_id` 映射输出给运行时策略。

### 2.2 TelegramConversationService
- 入口只调用 `_extract_workflow_id(update, policy)`，依赖 runtime policy 或 update payload。若未命中，直接走 `_build_workflow_missing_result()`。
- 从未查询 `WorkflowChannelService`，也缺乏“按 chat / 渠道查绑定”的逻辑。

### 2.3 Runtime Policy
- `foundational_service/policy/runtime.py` 默认 payload 不包含 entrypoints.telegram.workflow_id。
- 仓库里也没有 `config/runtime_policy.json` 提供覆盖文件，导致所有环境都回落到默认空配置。

### 2.4 前后端契约偏差
- 前端期待：后端提供 workflow 列表 + 当前绑定状态，前端重新选择并保存即可；保存成功即代表真实入口切换。
- 后端实现：前端自己拼 workflowId 调 PUT，运行时完全无感知。导致“UI 显示已绑定，但入口报未找到流程”的不一致。

## 3. 目标
1. **统一数据源**：以 Mongo 中的 `workflow_channels`（或新增 `channel_bindings`）作为唯一 binding 记录，runtime policy 不再手写 workflow_id。
2. **后端驱动选择**：新增 API 输出可绑定 workflow 清单、当前绑定状态，前端仅做选择/提交。
3. **运行时动态挂载**：FastAPI/Worker 在启动时、以及绑定更新后，自动把 binding 加载/刷新到内存，用于 `_extract_workflow_id()` / runtime router。
4. **多渠道可扩展**：设计成 channel 抽象（telegram / sms / http），避免未来继续硬编码。

## 4. 方案设计
### 4.1 数据模型
| 集合 | 字段 | 说明 |
| --- | --- | --- |
| `workflow_channels`（现存） | `workflow_id`, `channel`, `encrypted_bot_token`, `webhook_url`, `metadata`, `wait_for_result`, `workflow_missing_message`, `timeout_message`, `updated_by`, `updated_at`, `secret_version` | 继续存储敏感配置。 |
| `channel_bindings`（新增视图或逻辑模型） | `workflow_id`, `channel`, `status`(`bound`/`unbound`), `published_version`, `entry_config` | 由服务层组合自 workflow 元信息 + channel policy，供前端/运行时读取。可直接基于 `workflow_channels` 派生（channel=telegram）。 |

### 4.2 API 调整（Interface Layer）
1. `GET /api/channel-bindings/options`
   - 返回所有可绑定 workflow 列表：`workflowId`, `workflowName`, `publishedVersion`, `isBound`, `channel`.
   - 后端根据 workflow 状态 + `workflow_channels` 文档计算 `isBound`。
2. `GET /api/channel-bindings/{workflowId}`
   - 返回该 workflow 的 channel 配置（若存在），用于表单回填。
3. `PUT /api/channel-bindings/{workflowId}`
   - Request body 仅允许 `channel` 和启用标志；后端根据 `channel` 决定是否要求额外字段（Telegram 需要 token/webhook 等）。
   - 保存成功后，向 runtime 发布 “binding changed” 事件（例如 Redis pub/sub，或直接在内存 registry 更新）。
4. `POST /api/channel-bindings/{workflowId}/refresh`
   - （可选）手动触发 runtime 重新加载 binding，供运维定位。

> 兼容性：现有 `/api/workflow-channels/{workflowId}` 可逐步废弃或转发至新接口，但 dev 阶段可直接替换，避免维持两套契约。

### 4.3 Service Layer 调整
1. `WorkflowChannelService`
   - 新增 `list_bindings(channel: str)`，聚合 workflow 信息 + policy。
   - 保存策略时同步更新本地 registry（见下）。
2. `ChannelBindingRegistry`（新增）
   - 负责缓存 `{channel: {workflow_id: BindingContext}}`。
   - 提供事件接口 `refresh_from_store()`、`get_binding(channel)`。
   - `TelegramConversationService` 不再读 runtime policy，而是注入 `ChannelBindingRegistry` 以查找 workflow_id；若不存在，直接返回 `workflow_missing_text`。

### 4.4 Runtime 装载流程
1. `bootstrap_aiogram()` 完成后：
   - 调用 `WorkflowChannelService.list_bindings("telegram")`，把结果写入 `dispatcher.workflow_data["channel_bindings"]["telegram"]`。
   - 注册一个后台任务监听 binding 更新事件（例如 Redis Pub/Sub `channel_binding.updated`）。
2. `TelegramConversationService.process_update()`：
   - 优先从 registry 查 `workflow_id = bindings.get(chat_id)`（后续若支持 per chat 路由，可以扩展 metadata），否则返回 missing。
3. `WorkflowChannelService.save_policy()`：
   - 完成 upsert 后发出事件（或直接调用 registry.refresh_from_store()）确保 runtime 立即可见。

### 4.5 前端交互（成功路径）
1. 打开渠道设置 → 调用 `GET /api/channel-bindings/options`，渲染下拉列表（仅展示后端允许的 workflow）。
2. 用户选择 workflow 并输入 token/webhook → `PUT /api/channel-bindings/{workflowId}`。
3. 接口成功返回 binding 状态 → 前端刷新健康卡、允许发送测试。
4. Telegram 收到真实消息 → runtime registry 找到 workflowId → 正常进入 workflow/LLM。

### 4.6 失败模式 & 防御
1. **未发布 / 未授权 workflow**：`options` 接口必须过滤掉未发布、未启用的 workflow；否则在 runtime 仍会因 stage 缺失而失败。
2. **channel policy 缺必填字段**：`WorkflowChannelService.save_policy` 应在 service 层验证 token/webhook/allowedChatIds，如果缺失则返回 422，避免 registry 挂载一个不可用 binding。
3. **runtime registry 未刷新**：若事件失败导致 registry 未同步，需要 fallback 机制（例如定期全量 refresh，或 healthz 里暴露 `binding_version` 做监控）。
4. **跨渠道扩展**：设计需允许未来 `channel=slack/sms`；因此 binding 模型不要写死 Telegram 字段，而是把通用字段（workflowId/channel/status）与 channel-specific payload 分离。

### 4.7 约束与验收（GIVEN/WHEN/THEN）
1. **GIVEN** Admin 选择了 workflow “Telegram Greeter Flow”，**WHEN** 向 `/api/channel-bindings/{workflowId}` 发送 `channel=telegram` + token/webhook，**THEN** 接口返回 200 且 `dispatcher.workflow_data["channel_bindings"]["telegram"][workflowId]` 立即可见。
2. **GIVEN** 某 workflow 绑定被删除，**WHEN** Telegram 再次推送消息，**THEN** `TelegramConversationService` 应返回 `workflow_missing_text`，并在 telemetry 中标记 `workflow_status=missing`。
3. **GIVEN** webhook health 探活返回 404，**WHEN** 管理员访问 `GET /api/channel-bindings/options`，**THEN** 对应 workflow 的状态应显示 `degraded`（通过绑定数据 + capability snapshot 组合）。
4. **GIVEN** 绑定列表存在多个 workflow，**WHEN** 前端请求选项，**THEN** 只返回后端标记为 `channel_enabled=true` 的 workflow，避免无控制地拼接 workflowId。

## 5. 后续工作
1. 实现 `ChannelBindingRegistry` + redis 事件通道。
2. 改造 `WorkflowChannelService` 与接口层，删除旧的“自由填写 workflowId”逻辑。
3. 在 DevDoc / Onboarding 中记录“修改渠道 = 修改 binding，而非 runtime policy”，并提供故障排查 checklist（policy 缺 workflowId、binding 未刷新、公网探活失败等）。

## 6. 系统流程
### 6.1 绑定保存（Admin → API）
1. 前端调用 `GET /api/channel-bindings/options`，只展示 `channel_enabled=true` 且 `workflow.status in {"published","production-ready"}` 的 workflow。
2. 用户选择 workflow，提交 `PUT /api/channel-bindings/{workflowId}`：
   - `enabled=true` 时请求体包含 `channel=telegram` 与 channel-specific payload（token/webhook/metadata）。
   - `enabled=false` 时仅传 `channel` + `enabled`，后端删除 policy 并写入 kill switch。
3. `WorkflowChannelService.save_policy()` 验证字段→写 Mongo→发布 `channel_binding.updated` 事件（payload 含 `workflowId/channel/secretVersion/bindingVersion`）。
4. API 返回 `ChannelBindingDetailResponse`，并将事件推送给：
   - `ChannelBindingRegistry.refresh_from_store()`（本进程）
   - Redis Pub/Sub 订阅者（其他实例/worker）
   - `dispatcher.workflow_data["channel_bindings"][channel][workflowId]`
5. UI 收到响应后刷新列表、调用 `/channels/telegram/health` 验证 webhook 对齐。

### 6.2 运行时消息（Telegram → Worker）
1. aiogram Webhook 收到 update → `TelegramConversationService.process_update()`。
2. 先从 `ChannelBindingRegistry.get_active_binding(channel="telegram")` 获取 binding：
   - 若 binding 指定 whitelist，则校验 `metadata.allowedChatIds`。
   - 若 `wait_for_result=false`，直接走异步 ACK。
3. 构造 `TaskEnvelope`，`payload.workflowId=binding.workflow_id`，并写入 `telemetry.bindingVersion`。
4. Worker 完成后结果写回 Redis、Webhook handler 继续发送回应。
5. 当 binding 被删除或变更，下一条消息读取的新 `bindingVersion` 自动生效。

## 7. Redis 事件与 Dispatcher 缓存
### 7.1 事件主题
- Topic：`channel_binding.updated`
- Payload：
  ```json
  {
    "channel": "telegram",
    "workflowId": "wf_123",
    "bindingVersion": 17,
    "operation": "upsert|delete",
    "publishedVersion": 8,
    "enabled": true
  }
  ```
- 投递策略：`fire-and-forget`，失败时由后台任务重试并在 telemetry 中记录。

### 7.2 Dispatcher 缓存结构
```python
dispatcher.workflow_data["channel_bindings"] = {
    "telegram": {
        "version": 17,
        "active": "wf_123",
        "options": {
            "wf_123": {"status": "bound", "health": "ok", "policy": {...}},
            "wf_456": {"status": "unbound", "health": "unknown"}
        },
        "last_refresh": "2025-11-10T08:15:00Z"
    }
}
```
- 缓存更新路径：启动时全量加载；收到事件后只刷新受影响的 workflow；每 10 分钟做一次全量校验，防止遗漏。
- Worker 侧通过 `dispatcher.workflow_data` 共享 binding，不依赖 HTTP 进程内存。

## 8. 健康监控与 Kill Switch
### 8.1 Health 计算
- 定义 `health.status ∈ {ok, degraded, down, unknown}`，由以下来源合并：
  1. Telegram `getWebhookInfo`: URL 不一致 → `degraded`。
  2. 内部探活：触发 `/channels/telegram/test` 并等待 workflow 结果，超时→`degraded`。
  3. 错误事件：连续 `workflow_missing`/`telegram.queue.enqueue_failed` > 阈值 → `down`。
- 健康快照写入 `policy.metadata.health`，`/options` API 直接返回，供前端标记。

### 8.2 Kill Switch
- `ChannelBindingRegistry` 维护 `kill_switch[channel][workflowId]=True/False`。
- 停用流程：
  1. Admin 发送 `enabled=false`。
  2. Service 删除 policy、设置 kill switch、发布 `channel_binding.updated(operation="delete")`。
  3. Runtime 拒绝所有来自该 workflow 的 Telegram 请求，并返回 `workflow_missing_text`。
- Kill switch 仅由后台任务或运维 CLI 清除，避免误开启。

## 9. 运维排障 Checklist
| 场景 | 诊断步骤 | 处理 |
| --- | --- | --- |
| 绑定后仍提示 workflow missing | 检查 `dispatcher.workflow_data["channel_bindings"]` 是否包含 workflow；订阅日志 `channel_binding.updated` 是否接收；确认 Redis pub/sub 正常 | 手动调用 `/channel-bindings/{workflowId}/refresh`，必要时重启 binding worker |
| Webhook URL mismatch | `GET /channels/telegram/health` 查看 `health.detail.expectedUrl/actualUrl` | 重新设置 Telegram webhook（`setWebhook`），或在 Admin UI 更新目标 URL |
| 连续 enqueue failure | 观察 telemetry `telegram_queue_enqueue_failed_total` 和 Redis 健康；若 Redis 离线，UI 显示 `degraded` | 切换到异步模式，待 Redis 恢复后自动回归 |
| 未发出的 binding 事件 | 检查 `redis-cli PUBSUB NUMSUB channel_binding.updated` 输出；确认后台重试队列 | 手动触发 `refresh` 并重放事件 |

## 10. 扩展验收（GIVEN/WHEN/THEN）
1. **GIVEN** redis pub/sub 运行正常，**WHEN** 两个 FastAPI 实例同时监听 `channel_binding.updated`，**THEN** 所有实例的 `ChannelBindingRegistry.snapshot().version` 在 5 秒内保持一致。
2. **GIVEN** 管理员停用 workflow，**WHEN** Telegram 用户继续发送消息，**THEN** handler 立即返回 `workflow_missing_text`，并记录 `telemetry.bindingVersion` 的新值。
3. **GIVEN** 健康检查检测到 webhook URL 不一致，**WHEN** 前端刷新渠道列表，**THEN** 选项行应显示 `status=degraded` 与 `health.detail`.
4. **GIVEN** `channel_enabled=false` 的 workflow，**WHEN** 前端调用 `/api/channel-bindings/options`，**THEN** 不应出现在列表中，直至重新启用。

## 11. 架构重构计划

### 11.1 启动流程重构（Interface Layer）
1. **模块拆分**：创建 `interface_entry/bootstrap/channel_binding_bootstrap.py` 与 `interface_entry/bootstrap/runtime_lifespan.py`，分别承载 ChannelBinding 装载、Redis 监听、Dispatcher attach 以及 FastAPI lifespan/monitor/capability orchestration。`src/interface_entry/bootstrap/app.py` 仅保留 FastAPI 壳、路由注册与 CLI 入口。
2. **迁移步骤**：先逐段复制 `_prime_channel_binding_registry`、`_start/_stop_channel_binding_listener`、capability probes、runtime supervisor 初始化到新模块，验证通过后将 `app.py` 中的原逻辑替换为对新模块的调用。
3. **行为保持**：保留既有日志事件与启动顺序；若必须调整，须在实现阶段记录原因并提供对照验证（例如启动耗时对比）。

### 11.2 ChannelBindingMonitor 接入（Interface Runtime → Business Service）
1. startup/lifespan 中实例化 `ChannelBindingMonitor(service, registry, telegram_client)` 并存入 `app.state`；shutdown 阶段 `await monitor.stop()`，防止孤儿任务。
2. Monitor 在写入 `WorkflowChannelService.record_health_snapshot` 后，如健康状态变化，向新的消息通道（见 11.3）发送 `channel_binding.health` 事件，供运维与 registry 感知。
3. 当 health 判定为 `down` 或 `kill_switch=True` 时，Monitor 触发 registry refresh 并记录新的 `bindingVersion` 到 `dispatcher.workflow_data`。

### 11.3 事件发布与容错抽象（Foundational Service）
1. 创建 `foundational_service/messaging/channel_binding_event_publisher.py`，提供 `async publish(event) -> PublishResult`，封装 Redis publish、队列入栈、死信落库等细节。
2. Interface HTTP 与 service 层不再直接 `redis.publish`，统一调用 Publisher；Publisher 返回 `status ∈ {sent, queued, failed}`，并在 `meta.warnings` 或 telemetry 中暴露状态。
3. 迁移顺序：复制旧 `_publish_binding_event` 到 Publisher → 新增后台重放任务 → `src/interface_entry/http/channels/routes.py` 中所有 `_publish_binding_event` 调用（upsert/refresh/delete API 共 4 处，搜索关键词 "_publish_binding_event"）改用 Publisher。
4. **数据生命周期**：
   - 首次尝试直接 `redis.publish(channel_binding.updated, payload)`；成功即返回 `sent`。
   - 失败时将事件 JSON 压入 `redis.rpush("rise:channel_binding:event_queue", payload)` 并返回 `queued`，同时记录 telemetry。
   - RuntimeSupervisor 驱动的 `channel_binding_event_replayer` 定期从该 List 弹出事件并重试发布；连续失败超过阈值时写入 Mongo 集合 `channel_binding_deadletter`（字段：event、error、retryCount、lastFailureAt），由运维脚本或 CLI 处理。
5. **验证要求**：
   - 正常路径：Redis 可用时事件立即广播，Admin API 返回 200 且 `meta.warnings` 为空。
   - Redis 不可用：事件进入队列，API 仍返回 200 但 `meta.warnings=['event_queued']`；Replay 成功后队列长度下降。
   - 若重放仍失败，Mongo deadletter 必须存档并触发告警（日志或 telemetry），确保人工可跟进。

### 11.4 数据过滤与 Dispatcher 同步（Business Service）
1. `WorkflowChannelService.list_binding_options` 仅返回 `workflow.status ∈ {published, production, active}` 且 `workflow.metadata.channels.telegram.enabled=True` 的条目；停用项通过 kill switch 标记。
2. `ChannelBindingRegistry._select_active_option` 排除 `kill_switch=True` 与 `status='unbound'` 的 workflow。刷新成功后写入 `dispatcher.workflow_data`：
   ```
   dispatcher.workflow_data["channel_bindings"] = {
       "layer": "Interface",
       "version": <int>,
       "active": <workflow_id or None>,
       "options": {...},
       "last_refresh": <ISO8601>
   }
   ```
3. Lifespan 完成 Aiogram bootstrap 后立即 attach dispatcher 并同步 snapshot。

### 11.5 会话层降级策略（Business Service）
1. `_get_binding_runtime()` 查找失败时，应 `await registry.refresh()`（带 1s 超时）；如仍无结果，返回维护提示并记录 telemetry `binding.status = "missing"`，不得直接 fallback runtime policy。
2. 为紧急回退保留一个 feature flag 型 fallback，默认关闭；启用时必须在日志中标记 `bindingFallback=true` 并触发告警。
3. Telemetry 中新增 `binding.version`、`binding.activeWorkflowId`，帮助排障。

### 11.6 模块-层级映射
| Module / File | Layer | 责任变更 |
| --- | --- | --- |
| `src/interface_entry/bootstrap/app.py` | Interface | 只负责 FastAPI 壳、路由注册、CLI；其余逻辑迁往新模块 |
| `interface_entry/bootstrap/channel_binding_bootstrap.py` | Interface | 统一处理 registry prime、Redis 监听、Dispatcher attach |
| `interface_entry/bootstrap/runtime_lifespan.py` | Interface | 管控 capability probes、ChannelBindingMonitor、KnowledgeBase Lifespan |
| `foundational_service/messaging/channel_binding_event_publisher.py` | Foundational | 统一 Redis 发布 + `rise:channel_binding:event_queue` 入栈 + Mongo deadletter 归档，并对外暴露 PublishResult |
| `src/business_service/channel/service.py` / `registry.py` | Business Service | 增加 workflow 状态过滤、kill switch、Dispatcher snapshot 同步 |
| `src/business_service/conversation/service.py` | Business Service | 实施 binding 缺失的降级与 telemetry 输出 |

### 11.7 成功路径（Success Path）
1. **启动**：`create_app()` 调用新 lifespan，依次完成 capability probes → ChannelBindingBootstrap → KnowledgeBase，`ChannelBindingMonitor` 运行并产出健康事件。
2. **变更**：Admin 通过 HTTP API 更新绑定；Service 写入 Mongo→Publisher 发事件→所有实例在 5 秒内刷新 registry 与 dispatcher。
3. **运行**：Aiogram handler 始终通过 dispatcher 的 channel bindings 获取 active workflow，kill switch 后即时返回维护提示并记录版本变化。

### 11.8 失败模式与防御
- **Redis 发布失败**：Publisher 返回 `queued/failed`，HTTP 层在 `meta.warnings` 标记“event_queued”，后台重放后更新 `bindingVersion`。
- **Lifespan 组件异常**：若 capability/registry/bootstrap 任一环节抛错，立即退出 startup 并记录 `startup.step`，避免部分初始化的实例接收流量。
- **Binding 缺失**：重试 refresh 仍失败时返回维护文案并触发告警，禁止静默 fallback；若启用 fallback flag，必须记录并尽快回收。

### 11.9 约束与验收（Constraints）
- **GIVEN** 新 lifespan 启用，**WHEN** 应用启动完成，**THEN** `app.state` 中必须存在 `channel_binding_registry`、`channel_binding_monitor`、`runtime_supervisor` 且带 layer 标记。
- **GIVEN** Redis 暂不可用，**WHEN** 更新绑定，**THEN** Publisher 仍返回成功但 `meta.warnings` 标记 `event_queued`，后台重放后 registry 版本前进并写入 telemetry。
- **GIVEN** workflow 被 kill switch，**WHEN** Telegram 消息到达，**THEN** dispatcher 的 `active` 为 `None` 且 handler 返回维护文本，日志记录新 `bindingVersion`。
