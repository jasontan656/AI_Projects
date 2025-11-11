# Workflow Builder + Channel Binding 后端落地方案（session_20251110_0040）

## 范围与目标
- **覆盖模块**：Workflow CRUD/发布/回滚、Workflow Channel（Telegram 首版）、日志/变量/工具接口对齐。
- **目标**：提供前端 M1/M2 所需的完整后端契约，消除“前端完成→后端 404/字段缺失”的断层，保证 Workflow 从 Draft → Publish → 渠道可触达的闭环。
- **约束**：遵循 `openspec/PROJECT_STRUCTURE.md`，Interface 层仅做协议/鉴权，业务逻辑沉到 Business Service；无“向后兼容”要求，旧字段可直接升级。

## 核心设计
### 1. Workflow Schema 扩展
- **新增字段**（`business_service/workflow/models.py`）：
  - `status: Literal['draft','published']`（默认 draft）。
  - `node_sequence: tuple[str, ...]` – 前端 `nodeSequence`。
  - `prompt_bindings: tuple[PromptBinding, ...]` – `{ nodeId, promptId }` 列表。
  - `strategy: Mapping[str, Any]` – 重试/timeout/并发等策略。
  - `publish_history: tuple[WorkflowPublishRecord, ...]` – 记录 version、actor、timestamp、diff 摘要。
- **版本管理**：增加 `version`, `published_version`, `pending_changes` 标记，支持并发更新（409）。
- **持久化**：Mongo 集合需存新字段；缺失字段默认值写入 `_sanitize_updates`。

### 2. Workflow HTTP API
| 功能 | Method & Path | 请求 | 响应 | 说明 |
| --- | --- | --- | --- | --- |
| 列表 | `GET /api/workflows` |  | `WorkflowResponse[]` | 增加 status/nodeSequence/strategy/publishMeta 字段 |
| 创建 | `POST /api/workflows` | `WorkflowRequest`（含 nodeSequence 等） | WorkflowResponse | Stage 校验沿用 `_validate_stage_ids` |
| 更新 | `PUT /api/workflows/{id}` | 同上 | WorkflowResponse | 返回 422 若引用缺失 |
| 发布 | `POST /api/workflows/{id}/publish` | `{comment?, targetVersion?}` | WorkflowResponse + 发布记录 | - 校验：status=draft、node/prompt 引用有效；
- 更新 `status='published'`, `version++`, 写入 history |
| 回滚 | `POST /api/workflows/{id}/rollback` | `{targetVersion}` | WorkflowResponse | - 回滚到历史快照；
- 若目标不存在 → 404；
- 回滚后 `status='published'`, version++ |
| 删除 | `DELETE /api/workflows/{id}` |  | 204 | 禁止删除已发布；若强制需 `?force=true` |
| 执行 | `POST /api/workflows/apply` | 已有结构 | 不变 | 参考现有实现 |

### 3. Workflow Channel API（Telegram）
- **数据模型**：`WorkflowChannelPolicy`（`workflow_id`, `channel='telegram'`, `bot_token`, `webhook_url`, `wait_for_result`, `workflow_missing_message`, `timeout_message`, `metadata` {allowedChatIds[], rateLimitPerMin, locale}, `updated_by`, `updated_at`, `secret_version`）。
- **持久化**：Mongo `workflow_channels` 集合，Bot Token 加密/脱敏存储（例如使用 KMS/自研 cipher，至少响应时只返回 masked）。
- **接口**：
| 功能 | Method & Path | Request | Response |
| --- | --- | --- | --- |
| 查询配置 | `GET /api/workflow-channels/{workflowId}?channel=telegram` |  | `{data: channelPolicy}`，若不存在 → 404 |
| 保存配置 | `PUT /api/workflow-channels/{workflowId}` | `channelPolicy` 负载 | `{data: channelPolicy, meta: {version}}` |
| 删除配置 | `DELETE /api/workflow-channels/{workflowId}?channel=telegram` |  | 204；若 workflow 正在运行可返回 409 |
| 健康检查 | `GET /api/channels/telegram/health?workflowId=...&includeMetrics=1` |  | `{status, lastCheckedAt, lastError, metrics}` |
| 发送测试 | `POST /api/channels/telegram/test` | `{workflowId, chatId, payloadText, waitForResult, correlationId?}` | `{status, responseTimeMs, telegramMessageId?, errorCode?, traceId}` |
- **业务逻辑**：
  - 健康检查调用基础设施（Redis/Telegram API），失败时返回 `status='unknown'` 并记录 `traceId`。
  - 测试接口需做频控：使用 Redis 计数，在 60s 内超 3 次返回 429。
  - 保存配置前验证 Token/webhook 格式，并记录审计信息。

### 4. 可观测性接口
- 已有 `/logs/stream` / `/logs?limit=` / `/variables` / `/tools`；需验证返回结构与前端 DevDoc 对齐。
- 额外要求：`WorkflowVariablesResponse` 应包含整洁的 key（`telemetry.*`, `metadata.*`, `coreEnvelope.*`），并限制大小。

## 成功路径 & 核心流程
1. **Workflow Builder**：
   - 用户通过前端创建 workflow → `POST /api/workflows` 存储 nodeSequence/promptBindings/strategy。
   - 编辑后点击“发布” → `POST /publish` 校验引用 → 状态转为 `published` + 版本记录。
   - 若需回滚，`POST /rollback` 恢复历史快照，并刷新 builder。
2. **渠道绑定**：
   - 前端进入 Channel Tab → `GET /workflow-channels/{id}` 若 404 则空态。
   - 填写 Token/Webhook → `PUT /workflow-channels/{id}` 成功，自动触发健康检查。
   - Health Card 每 30s 调用 `/channels/telegram/health`，状态 up/down/degraded 显示一致；测试按钮调用 `/test` 并返回 traceId。
3. **可观测性**：
   - Workflow 发布后，前端在日志 Tab 调用 `/logs/stream`，实时消费事件；`/variables`、`/tools` 提供上下文浏览。

## 失败模式 & 防御策略
- **引用缺失**：`nodeSequence/promptBindings` 指向不存在的 node/prompt → 发布/保存直接 422，body 带 missing 列表。
- **并发冲突**：`version` 不一致时返回 409（`code: WORKFLOW_VERSION_CONFLICT`），前端可提示“刷新数据”。
- **发布/回滚权限**：需要 ActorContext；若无权限则 403。
- **渠道验证失败**：Bot Token/Webhook 格式错误 → 422；Allowed Chat IDs 非整数 → 422。保存前必须校验。
- **健康检查连挂**：3 次失败后返回 `status='unknown'` 并暂停自动轮询，直到前端调用恢复。
- **测试频控**：超过频率限制返回 429（`CHANNEL_TEST_RATE_LIMIT`），前端需展示冷却时间。
- **敏感信息泄漏**：响应和日志只返回 Token 前 6 +“****”+末尾 4 位；变更 Token 时需重新加密存储。

## 验收约束（GIVEN / WHEN / THEN）
1. **GIVEN** workflow 含合法 nodeSequence/promptBindings，**WHEN** 调用 `POST /api/workflows/{id}/publish`，**THEN** 返回 `status='published'`，`publishHistory` 追加记录，且 `version` 递增。
2. **GIVEN** workflow 已发布，**WHEN** `POST /rollback` 到历史版本，**THEN** 响应包含回滚后的配置，并同步写入历史。
3. **GIVEN** workflow 尚未绑定渠道，**WHEN** `GET /workflow-channels/{id}`，**THEN** 返回 404，前端展示空态。
4. **GIVEN** 用户在 60 秒内调用 `/channels/telegram/test` 第 4 次，**WHEN** 请求到达，**THEN** 返回 429 并附带冷却剩余时间。
5. **GIVEN** 健康检查连续失败 3 次，**WHEN** 前端下次调用 `/health`，**THEN** `status='unknown'` 且 `nextRetryAt` 告知退避时间。
6. **GIVEN** SSE 订阅 `/logs/stream`，**WHEN** Workflow 执行产生日志，**THEN** 前端能在 1s 内收到并渲染（长连接断线需自动重试并抛出事件）。

## 下一步
1. 扩展 `WorkflowDefinition` + Mongo schema → 更新 `AsyncWorkflowRepository` 序列化逻辑。
2. 在 `business_service/workflow/service.py`/新模块实现 publish/rollback 业务方法，Interface 层新增对应路由。
3. 新建 `business_service/channel`（或 workflow_channel）模块：模型 + Repository + Service；再在 Interface 层实现 `/workflow-channels` 路由、`/channels/telegram/*`。
4. 设计加密存储与 traceId 方案，保证 Token 安全与可观测性一致。

## 数据模型与迁移策略
1. **Workflow Definition（Mongo `workflows`）**
   | 字段 | 类型 | 说明 |
   | --- | --- | --- |
   | `workflow_id` | string | 主键，UUID |
   | `name/description` | string | 基础信息 |
   | `stage_ids` | array<string> | 旧字段，保留 |
   | `metadata` | object | 自定义元数据 |
   | `node_sequence` | array<string> | 执行顺序；迁移时若缺失则拷贝 `stage_ids` |
   | `prompt_bindings` | array<object `{node_id,prompt_id}`> | 节点与提示词映射 |
   | `strategy` | object | `retryLimit/timeoutMs/concurrency` 等 |
   | `status` | string | `draft` / `published` |
   | `version` / `published_version` | number | 乐观锁、发布记录 |
   | `publish_history` | array<object> | `{version, action, actor, comment, timestamp, snapshot}` |
   | `created_at/updated_at/updated_by` | 审计字段 |
   - **迁移执行**：
     1. 在 repository `create/update/get` 中新增 `_hydrate_workflow(doc)`，遇到缺失字段自动写默认值；
     2. 提供 one-off 脚本 `one_off/migrations/workflow_schema_upgrade.py`，对所有文档运行 `$set` 补齐字段，避免后续接口大量 fallback；
     3. 旧版本默认 `status='draft'`，`publish_history=[]`。

2. **Workflow Channel Policy（Mongo `workflow_channels`）**
   | 字段 | 类型 | 说明 |
   | --- | --- | --- |
   | `workflow_id` | string | 与 workflow 关联 |
   | `channel` | string | 目前仅 `telegram` |
   | `bot_token` | string | 明文存储，响应必须 Mask |
   | `webhook_url` | string | HTTPS |
   | `wait_for_result` | bool | 是否同步等待 |
   | `workflow_missing_message` / `timeout_message` | string | 回退文案 |
   | `metadata.allowed_chat_ids` | array<string> | 聊天白名单 |
   | `metadata.rate_limit_per_min` | number | 默认 60 |
   | `metadata.locale` | string | 默认 `zh-CN` |
   | `updated_at/updated_by/secret_version` | 审计字段 |
   - 索引：`uniq_workflow_channel (workflow_id + channel)`；`updated_at` 的 TTL/排序索引用于后台巡检。

## Telegram 客户端与配置
- **环境变量**
  - `TELEGRAM_API_BASE=https://api.telegram.org`。
  - `TELEGRAM_BOT_TOKEN`：默认 Bot，若 workflow 未绑定则禁止测试。
  - `TELEGRAM_HEALTH_CHAT_ID`：健康检查默认 chatId；若未配置则使用 Policy 中第一个 Allowed Chat。
- **客户端实现**
  - 新建 `foundational_service.integrations.telegram_client.TelegramClient`，内部维护 `httpx.AsyncClient(timeout=5s)`。
  - 对外暴露 `async def get_bot_info(token)`, `get_webhook_info`, `send_message(token, chat_id, text, parse_mode, correlation_id)` 等方法。
  - 异常统一转换为自定义错误码：例如 `BOT_FORBIDDEN`, `CHAT_NOT_FOUND`, `RATE_LIMIT`, `NETWORK_FAILURE`；所有错误携带 `trace_id`（源自 `ContextBridge.request_id()`）并写日志。
- **健康检查流程**
  1. `get_bot_info` 校验 token 正确；
  2. `get_webhook_info` 比对 webhook URL；
  3. 可选发送探测消息到 `TELEGRAM_HEALTH_CHAT_ID`，确认链路；
  4. 任何一步失败 → `status='down'`，记录 `lastError`、`traceId`、`nextRetryAt`。
- **测试消息**
  - 请求体：`workflowId`, `chatId`, `payloadText`, `waitForResult`, `correlationId?`。
  - 响应：`{status:'success'|'failed', responseTimeMs, telegramMessageId?, traceId, errorCode?, workflowResult?}`；
  - 当 `waitForResult=true` 时，测试 API 会监听 `WorkflowObservabilityService` 的日志流最长 20s，将 workflow 执行状态附在 response。

## 频控与审计
- **Redis 频控**
  - key: `channel:test:{workflowId}`；TTL 60s；value 统计次数。
  - 前端超过 3 次/分钟立即 429，body 包含 `retryAfterSeconds`。
  - 频控逻辑封装在 `business_service.channel.rate_limit.py`，HTTP 层只进行异常转换。
- **审计记录**
  - 发布、回滚、渠道保存/解绑均写入 `publish_history` 或 `workflow_activity` 集合，格式 `{action, actor, requestId, payload}`。
  - Channel API 返回的 token 永远 Mask（`abc123****wxyz`）；日志中禁止打印明文。
  - 所有接口输出 `meta.requestId`，便于前端与日志关联。

## 验收 / 测试计划
1. **Workflow 发布回滚**
   - 单测覆盖：成功发布、引用缺失（422）、版本冲突（409）、回滚到不存在版本（404）；
   - 集成测试：调用 `/api/workflows/{id}/publish` 并检查 Mongo 文档 `status/publish_history` 是否更新。
2. **Channel CRUD**
   - 单测：校验 Token/Webhook 格式、Allowed Chat IDs 解析、脱敏输出；
   - 集成测试：`PUT/GET/DELETE /workflow-channels/{id}`，断言 Mongodoc 与响应一致。
3. **健康 / 测试**
   - 使用 httpx MockTransport 模拟 Telegram 成功/失败，用例覆盖 rate limit、网络错误、Bot 被封、chat 不存在；
   - 真实 E2E：配置 `.env` 中的 Bot Token + chatId，连续执行“绑定 → 健康 → 测试 → 日志查看”流程，确保 traceId 可定位。
4. **可观测性**
   - SSE 压测：建立日志流并注入 1000 条消息，验证前端能在 1s 内收到、压缩处理；
   - `/variables` `/tools` API 提供稳定结构（telemetry.*、metadata.*、coreEnvelope.*），并限制每个字段大小避免爆炸。
