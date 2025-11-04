## ADDED Requirements

### Requirement: Conversation Service Facade
Business Service MUST expose a `TelegramConversationService` facade with a `process_update(update, policy)` coroutine that wraps intent分类、提示准备、代理调度与适配器合约生成，返回一个 `ConversationServiceResult` dataclass 供业务逻辑层直接消费。

#### Scenario: Facade returns typed orchestration bundle
- **GIVEN** 一个 `TelegramConversationService` 实例，以及包含用户文本、上下文摘要和策略预算的 Telegram 更新
- **WHEN** 调用 `await service.process_update(update, policy=policy)`
- **THEN** 它返回的 `ConversationServiceResult` 字段包含 `intent`、`triage_prompt`、`agent_request`、`agent_response`、`telemetry`、`adapter_contract`、`outbound_contract`、`outbound_payload`、`output_payload` 与 `outbound_metrics`
- **AND** 该结果无需业务逻辑层再操作底层字典即可执行 Markdown 转义或流式指标读取。

### Requirement: Prompt Preparation Delegates to Business Assets
Conversation Service MUST centralize prompt rendering through a dedicated component that validates prompt IDs and variables against Business Asset definitions before returning Markdown-safe strings.

#### Scenario: Prompt bundle validated against asset registry
- **GIVEN** the prompt service receives a request referencing `agent_triage_system` and `agent_consult_compose`
- **WHEN** prompts are rendered
- **THEN** the service looks up definitions via the Business Asset registry, validates required variables, and returns a `PromptBundle` dataclass containing the rendered text and original variables
- **AND** missing prompts raise a typed error that includes the prompt id for telemetry.

### Requirement: Adapter Composition Isolated in Business Service
Business Service MUST own the transformation from agent bridge output to transport adapter contracts, ensuring interface layers only receive finalized payloads with streaming metadata.

#### Scenario: Adapter service finalizes outbound contract
- **GIVEN** agent dispatch results with chunks and telemetry
- **WHEN** the adapter service builds the outbound contract
- **THEN** it injects reply metadata, streaming buffers, and Markdown-safe text while recording chunk metrics
- **AND** it validates the contract via foundational toolcalls before returning it to Business Logic.
