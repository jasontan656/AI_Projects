# Session Notes 2025-11-10 07:50 CST

## User Intent
- 纠正 Telegram 渠道绑定的前后端偏差：前端希望“从后端提供的可选 workflow 列表中选择并启用渠道”，而后端当前实现是“前端自由传 workflowId + 渠道配置”。需要输出开发方案文档，统一绑定流程、运行时装载及接口契约。

## Repo Context
- `src/business_service/channel/service.py` / `repository.py`：仅针对 `workflow_channels` 集合读写 Telegram policy（token/webhook/metadata）。接口以 `workflow_id` path param 为中心，保存成功后并未更新 runtime。
- `src/business_service/conversation/service.py`：`TelegramConversationService.process_update()` -> `_extract_workflow_id(update, policy)`，依赖 runtime policy 提供 `entrypoints.telegram.workflow_id`。缺少任何来自 channel storage 的 fallback，一旦 policy 里没有 workflow_id 就返回 `workflow_missing_text`。
- `src/foundational_service/policy/runtime.py`：默认常量 `DEFAULT_RUNTIME_POLICY` 中不存在 telegram workflow id；仓库内也没有 `config/runtime_policy.json`。系统因此永远找不到 workflow。
- `src/interface_entry/http/channels/routes.py`：对外暴露 `GET/PUT/DELETE /api/workflow-channels/{workflow_id}`；前端必须自己传 `workflowId`，后端不提供可选列表也不做状态聚合。
- `src/project_utility/telemetry.py` + `interface_entry/bootstrap/app.py`：前期已完成 Telemetry/探活改造（HEAD / 返回 200），与本次需求关联：binding 生效后需确保 capability 仍能自检。

## Technology Stack
- Python 3.11 + FastAPI；MongoDB (motor) 存 workflow/policy；Redis 用于队列/worker；Aiogram 处理 Telegram。
- 渠道 policy 目前没有事件总线或 registry，运行时行为完全取决于静态 runtime policy。

## Search Results
- context7 `/websites/core_telegram_bots_api`：Webhook best practices（`setWebhook`, `getWebhookInfo`）。提醒我们 binding 成功后需要定期校验 Telegram 官方状态。
- exa 搜索（multi channel workflow binding design telegram）返回 n8n/Contentful 等多渠道示例，支持“后端提供 integrations 列表 + 前端点选”模式，进一步佐证“由后端给选项”是行业常态。

## Architecture Findings
1. **单向写入**：`WorkflowChannelService` 把渠道配置写入 Mongo，却没有把 binding 信息写回运行时。`TelegramConversationService` 永远盯着 `runtime_policy`，导致 UI 保存≠入口可用。
2. **缺乏 binding registry**：没有组件负责维护 `{channel: workflowId}` 映射，运行时更别谈热更新。
3. **API 契约偏差**：接口命名是 “workflow-channels”，但语义是“给某 workflow 写 Telegram 凭据”。前端如果不知道合法 workflow，只能自己拼 ID；无从保证状态一致。
4. **配置版本冲突**：runtime policy 默认值和 channel policy 是两份独立数据，且目前无人同步。任何一次部署或 `runtime_policy.json` 缺失都会把 binding 置空。

## Proposed Adjustments (详见 DevDoc `session_20251110_0750_telegram_channel_binding.md`)
1. **数据模型**：保留 `workflow_channels` 存敏感配置，额外派生 `channel_bindings` 视图（workflowId + channel + status），供 Admin UI 与 runtime 读取。
2. **API**：新增 `GET /api/channel-bindings/options`（列出可绑定 workflow），`GET /api/channel-bindings/{workflowId}`，`PUT /api/channel-bindings/{workflowId}`（只接受 channel + 启用状态 + channel-specific payload），必要时补 `POST .../refresh`。
3. **服务层**：`WorkflowChannelService` 增加 `list_bindings()` & binding events；新增 `ChannelBindingRegistry` 缓存映射并暴露刷新接口。
4. **运行时**：`bootstrap_aiogram` 启动后加载 binding 到 `dispatcher.workflow_data["channel_bindings"]`，监听更新。`TelegramConversationService` 注入 registry，从 binding 查 workflowId，不再依赖静态 runtime policy。
5. **前端契约**：Admin 渠道设置=选择 workflow + 配置 token/webhook；UI 不再允许手工输入 workflowId。保存成功后 UI 仅展示后端状态（bound/degraded）。

## File References
- `src/business_service/channel/service.py` / `repository.py` / `models.py`
- `src/interface_entry/http/channels/routes.py`
- `src/business_service/conversation/service.py`
- `src/foundational_service/policy/runtime.py`
- DevDoc: `AI_WorkSpace/DevDoc/On/session_20251110_0750_telegram_channel_binding.md`
