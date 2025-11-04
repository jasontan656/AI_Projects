## ADDED Requirements

### Requirement: Telegram Conversation Service API
Business Service MUST expose `TelegramConversationService.process_update(update, policy)` that returns a `ConversationServiceResult` dataclass with:
- `status`: `"handled"` 或 `"ignored"`;
- `mode`: `"stream"`, `"direct"`, `"prompt"`, `"refusal"` 或 `"ignored"`;
- `intent`, `triage_prompt`, `agent_request`, `agent_response`;
- `telemetry`, `agent_bridge`, `agent_bridge_telemetry`;
- `adapter_contract`, `outbound_contract`, `outbound_payload`, `output_payload`, `outbound_metrics`;
- `audit_reason`, `error_hint`, `user_text`, `logging_payload`, `update_type`, `core_envelope`, `legacy_envelope`.

#### Scenario: Returns structured result for standard message
- **GIVEN** Telegram 更新包含文本、聊天元数据且无提示覆盖
- **AND** 运行策略给出 token 预算与版本信息
- **WHEN** 调用 `process_update`
- **THEN** 返回的 `ConversationServiceResult.status="handled"`，`mode` 为 `"stream"` 或 `"direct"`
- **AND** `outbound_contract` 包含 `chat_id`、`parse_mode="MarkdownV2"`、`disable_web_page_preview=True` 及流式缓冲条目
- **AND** `agent_response` 等于经过 Markdown 转义的待发送内容，`telemetry` 暴露请求标识和 chunk 指标，同时 `audit_reason` 为空。

### Requirement: Prompt Short-Circuit Behaviour
When the inbound payload specifies a direct prompt (either via `prompt_id`/variables, or classified as `help`/`refusal`), the service MUST bypass the agents bridge and return a Markdown-escaped response generated from the prompt registry.

#### Scenario: Direct prompt without agent dispatch
- **GIVEN** 归一化后的 core envelope 含 `prompt_id="agent_refusal_policy"`
- **AND** PROMPT_REGISTRY 能够渲染该提示
- **WHEN** 调用 `process_update`
- **THEN** 服务返回 `mode="prompt"`，`agent_response["text"]` 等于渲染结果（已 Markdown 转义）
- **AND** `agent_bridge["mode"]` 标记为 `"prompt_shortcut"` 或 `"prompt_override"`
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
