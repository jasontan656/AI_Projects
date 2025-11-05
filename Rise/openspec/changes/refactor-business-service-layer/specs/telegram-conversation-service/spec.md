## ADDED Requirements

### Requirement: Telegram Conversation Service API
Business Service MUST expose `TelegramConversationService.process_update(update, policy)` that returns a `ConversationServiceResult` dataclass with：
- `status`: `"handled"` 或 `"ignored"`；
- `mode`: `"stream"`、`"direct"` 或 `"ignored"`（如未来扩展可另行更新规范）；
- `intent`、`agent_request`、`agent_response`；
- `telemetry`；
- `adapter_contract`、`outbound_contract`、`outbound_payload`、`outbound_metrics`；
- `audit_reason`、`error_hint`、`user_text`、`logging_payload`、`update_type`、`core_envelope`、`legacy_envelope`。

#### Scenario: Returns structured result for standard message
- **GIVEN** Telegram 更新包含文本、聊天元数据且无提示覆盖
- **AND** 运行策略给出 token 预算与版本信息
- **WHEN** 调用 `process_update`
- **THEN** 返回的 `ConversationServiceResult.status="handled"`，`mode` 为 `"stream"` 或 `"direct"`
- **AND** `outbound_contract` 包含 `chat_id`、`parse_mode="MarkdownV2"`、`disable_web_page_preview=True` 及流式缓冲条目
- **AND** `agent_response` 等于经过 Markdown 转义的待发送内容，`telemetry` 暴露请求标识和 chunk 指标，同时 `audit_reason` 为空。

### Requirement: Reject Legacy Prompt Shortcuts
If inbound payloads still carry `prompt_id`/`prompt_variables` from legacy flows, the service MUST refuse to execute and surface a hard failure so that stale webhook backlog或旧策略被及时清理。

#### Scenario: Legacy prompt raises error
- **GIVEN** 归一化后的 core envelope 含 `prompt_id="agent_refusal_policy"`
- **WHEN** 调用 `process_update`
- **THEN** 服务抛出异常（类型可自定义，但必须终止请求）并在日志中明确提示 legacy prompt 已被移除
- **AND** 不会调用 `behavior_agents_bridge`。

### Requirement: Agent Orchestration Path
For requests without prompt shortcuts and not marked as restricted, the service MUST invoke `behavior_agents_bridge`, attach telemetry/chunk metrics to the result, and surface audit events when refusal tags are detected.

#### Scenario: Streams agent output for unrestricted message
- **GIVEN** 意图分类结果为 `"compose"` 且 ext flags 未标记为受限
- **AND** 运行策略提供 token 阈值
- **WHEN** `process_update` 执行
- **THEN** 服务调用 `behavior_agents_bridge` 并写入 `agent_request["request_id"]`
- **AND** 使用返回的 chunk 指标构建 `outbound_contract["streaming_buffer"]`
- **AND** 当代理输出触发政策告警时，通过 `call_record_audit` 记录审核原因，否则该字段为空。
