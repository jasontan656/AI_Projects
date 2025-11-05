## ADDED Requirements

### Requirement: Conversation Service Facade
Business Service MUST expose `TelegramConversationService.process_update(update, policy)` 并返回 `ConversationServiceResult` dataclass，字段至少包含 `status`、`mode`、`intent`、`agent_request`、`agent_response`、`telemetry`、`adapter_contract`、`outbound_contract`、`outbound_payload`、`outbound_metrics`、`audit_reason`、`error_hint`、`user_text`、`logging_payload`、`update_type`、`core_envelope`、`legacy_envelope`。

#### Scenario: Facade returns typed orchestration bundle
- **GIVEN** 一个 `TelegramConversationService` 实例，以及包含用户文本、上下文摘要和策略预算的 Telegram 更新
- **WHEN** 调用 `await service.process_update(update, policy=policy)`
- **THEN** 结果对象的 `status` 为 `"handled"` 或 `"ignored"`，其余字段都已经是可直接消费的结构（含 Markdown 文本、流式指标与适配器合约），业务逻辑层无需再拼装底层字典。

### Requirement: Legacy Prompt Inputs Must Be Rejected
Conversation Service MUST 拒绝任何携带 `prompt_id` 或 `prompt_variables` 的旧式请求，避免后端重新依赖静态 Prompt Registry。

#### Scenario: Legacy prompt raises error
- **GIVEN** 归一化后的 inbound 载荷含 `prompt_id="agent_refusal_policy"`
- **WHEN** 调用 `process_update`
- **THEN** 服务抛出带有 “legacy prompt” 关键字的异常，并中断会话编排
- **AND** 不会向 LLM 发起请求或构造适配器合约，让调用方及时清理遗留数据。

### Requirement: Adapter Composition Isolated in Business Service
Business Service MUST own the transformation from agent bridge output to transport adapter contracts, ensuring interface layers only receive finalized payloads with streaming metadata.

#### Scenario: Adapter service finalizes outbound contract
- **GIVEN** agent dispatch results with chunks and telemetry
- **WHEN** the adapter service builds the outbound contract
- **THEN** it injects reply metadata, streaming buffers, and Markdown-safe text while recording chunk metrics
- **AND** it validates the contract via foundational toolcalls before returning it to Business Logic.
