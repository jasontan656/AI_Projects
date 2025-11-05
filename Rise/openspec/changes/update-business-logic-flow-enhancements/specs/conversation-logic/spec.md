## MODIFIED Requirements

### Requirement: Telegram Conversation Delegation
Business Logic MUST keep exposing `TelegramConversationFlow.process(update, policy)` but the method now acts as a thin wrapper around `TelegramConversationService.process_update`. It MUST NOT duplicate prompt rendering, agent orchestration, or adapter shaping logic; instead it converts the returned `ConversationServiceResult` into the existing `ConversationResult` dataclass used by downstream layers.

#### Scenario: Delegation preserves handled results
- **GIVEN** the Business Service returns a `ConversationServiceResult` with populated intent、agent response、telemetry、适配器合约与 outbound payload
- **WHEN** Business Logic invokes `TelegramConversationFlow.process`
- **THEN** it maps those fields directly onto `ConversationResult`
- **AND** no additional prompt rendering, agent dispatching, or adapter mutation occurs in the Business Logic layer.

#### Scenario: Delegation preserves ignored results
- **GIVEN** the Business Service marks a Telegram update as ignored
- **WHEN** Business Logic processes the update
- **THEN** it returns `ConversationResult(status="ignored", mode="ignored")` that mirrors the service payload (telemetry, logging, user text) without invoking any Business Service primitives itself.

### Requirement: Service Result Integrity
Business Logic MUST surface every field provided by the Business Service on the `ConversationResult`，包括 `adapter_contract`、`outbound_contract`、`outbound_payload`、`outbound_metrics`、`telemetry`、`audit_reason`、`error_hint` 等观测数据，确保接口层与服务层契约保持一致。

#### Scenario: All service fields are present
- **GIVEN** the Business Service includes chunk metrics, validated agent output, and audit information
- **WHEN** the Business Logic wrapper returns the result
- **THEN** those fields appear on `ConversationResult` unchanged, ensuring observability and transport layers remain aligned with the Business Service contract.
