## ADDED Requirements

### Requirement: Telegram Conversation Flow
The Business Logic layer MUST provide a `TelegramConversationFlow.process(update, policy)` coroutine that orchestrates intent detection, prompt selection, agent delegation, and outbound contract assembly by invoking Business Service primitives.

#### Scenario: Returns orchestrated result for message
- **GIVEN** a Telegram update payload and runtime policy with token budgets
- **AND** Business Service helpers for intent classification, agent delegation, and adapter shaping are available
- **WHEN** `process` is invoked
- **THEN** the flow produces a structured result containing status, mode, outbound Telegram contract, agent output, telemetry, and audit metadata suitable for transport layers
- **AND** streaming buffer and chunk metrics are populated using Business Service outputs.

### Requirement: Prompt Short-Circuit Logic Layer Ownership
The Business Logic flow MUST own prompt short-circuit rules (direct prompts, help/refusal cases), delegating only prompt rendering and markdown escaping to Business Service.

#### Scenario: Direct prompt bypasses agent bridge
- **GIVEN** a message flagged with a prompt override or classified as `help`
- **WHEN** the conversation flow runs
- **THEN** it renders the prompt via Business Service, returns `mode="prompt"`, and skips agent delegation while still emitting telemetry/audit details.

### Requirement: Audit and Telemetry Consistency
The conversation flow MUST ensure audit events and telemetry payloads are emitted consistently for every handled message, using Business Service utilities for logging payload composition.

#### Scenario: Audit recorded on refusal
- **GIVEN** the Business Service returns a refusal classification or system tags include `policy_violation`
- **WHEN** the flow completes
- **THEN** it records an audit event with intent, chat id, and reason, updates telemetry with latency/error hints, and returns the enriched metadata to the caller.
