## MODIFIED Requirements

### Requirement: Telegram Conversation Delegation
Business Logic MUST keep exposing `TelegramConversationFlow.process(update, policy)` but the method now acts as a thin wrapper around `TelegramConversationService.process_update`. It MUST NOT duplicate prompt rendering, agent orchestration, or adapter shaping logic; instead it converts the returned `ConversationServiceResult` into the existing `ConversationResult` dataclass used by downstream layers.

#### Scenario: Delegation preserves handled results
- **GIVEN** the Business Service returns a `ConversationServiceResult` with populated intent, prompts, agent response, telemetry, adapter contracts, and outbound payload
- **WHEN** Business Logic invokes `TelegramConversationFlow.process`
- **THEN** it maps those fields directly onto `ConversationResult`
- **AND** no additional prompt rendering, agent dispatching, or adapter mutation occurs in the Business Logic layer.

#### Scenario: Delegation preserves ignored results
- **GIVEN** the Business Service marks a Telegram update as ignored
- **WHEN** Business Logic processes the update
- **THEN** it returns `ConversationResult(status="ignored", mode="ignored")` that mirrors the service payload (telemetry, logging, user text) without invoking any Business Service primitives itself.

### Requirement: Service Result Integrity
Business Logic MUST surface every field provided by the Business Service on the `ConversationResult`, including `triage_prompt`, `agent_bridge`, `agent_bridge_telemetry`, `adapter_contract`, `outbound_contract`, `outbound_payload`, `output_payload`, and `outbound_metrics`, so interface layers observe the exact data emitted by the Business Service.

#### Scenario: All service fields are present
- **GIVEN** the Business Service includes chunk metrics, validated agent output, and audit information
- **WHEN** the Business Logic wrapper returns the result
- **THEN** those fields appear on `ConversationResult` unchanged, ensuring observability and transport layers remain aligned with the Business Service contract.
