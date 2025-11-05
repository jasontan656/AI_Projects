## ADDED Requirements

### Requirement: Enforce Node LLM Permissions
Pipeline orchestration MUST respect each node’s `allowLLM` flag before invoking the OpenAI bridge.

#### Scenario: Block LLM Invocation When Disallowed
- **WHEN** the orchestrator resolves a node whose stored configuration has `allowLLM` set to `false`
- **THEN** it MUST skip calling `behavior_agents_bridge`
- **AND** it MUST return a deterministic non-LLM response (e.g., static prompt output or an error state) while recording an audit event explaining the skip.

#### Scenario: Permit LLM Invocation When Allowed
- **WHEN** the orchestrator resolves a node with `allowLLM` set to `true`
- **THEN** it MUST pass the stored `systemPrompt` verbatim into the LLM request flow (respecting the pipeline’s prompt assembly rules)
- **AND** it MUST include the node `version` in the telemetry so downstream logging can link responses to specific revisions.

### Requirement: Surface Strategy Metadata
The orchestrator MUST preserve the stored `strategy` object for future expansion even if currently empty.

#### Scenario: Propagate Strategy Field
- **WHEN** a node is executed
- **THEN** the execution context MUST carry the node’s `strategy` payload through to the stage handler, enabling later strategy-specific branching without changing the API contract.
