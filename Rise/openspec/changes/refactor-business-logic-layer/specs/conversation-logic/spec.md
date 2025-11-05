## ADDED Requirements

### Requirement: Telegram Conversation Flow
The Business Logic layer MUST provide a `TelegramConversationFlow.process(update, policy)` coroutine that orchestrates intent detection、代理委派与适配器装配，并将 `TelegramConversationService` 的结果转写为业务逻辑层暴露的 `ConversationResult` dataclass。

#### Scenario: Returns orchestrated result for message
- **GIVEN** a Telegram update payload and runtime policy with token budgets
- **AND** Business Service helpers for intent classification, agent delegation, and adapter shaping are available
- **WHEN** `process` is invoked
- **THEN** the flow produces a structured result containing status, mode, outbound Telegram contract, agent output, telemetry, and audit metadata suitable for transport layers
- **AND** streaming buffer and chunk metrics are populated using Business Service outputs.

### Requirement: Reject Legacy Prompt Overrides
Business Logic MUST 将任何携带 `prompt_id` 的遗留路径视为错误，直接透传 Business Service 抛出的异常或显式终止流程，以保证所有 Prompt 均来自前端配置/数据库。

#### Scenario: Legacy prompt raises error
- **GIVEN** inbound update 包含 `prompt_id`
- **AND** Business Service 抛出 `legacy prompt` 异常
- **WHEN** `TelegramConversationFlow.process` 捕获该异常
- **THEN** 它不会尝试渲染 Prompt，也不会调用 agent delegation，而是把异常上抛给调用方或日志系统以触发 backlog 清理。

### Requirement: Audit and Telemetry Consistency
The conversation flow MUST ensure audit events and telemetry payloads are emitted consistently for every handled message, using Business Service utilities for logging payload composition.

#### Scenario: Audit recorded on refusal
- **GIVEN** the Business Service returns a refusal classification or system tags include `policy_violation`
- **WHEN** the flow completes
- **THEN** it records an audit event with intent, chat id, and reason, updates telemetry with latency/error hints, and returns the enriched metadata to the caller.
