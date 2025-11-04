## Why
Business Logic conversation orchestration recently gained new guardrails for ignored updates, policy-gated refusals, triage prompt generation, and adapter contract finalization. The existing `conversation-logic` capability spec does not cover these flows, so contributors lack authoritative guidance on expected results and data contracts. We must update the spec to capture the new behavior before further changes land.

## What Changes
- Document how ignored inbound updates must surface as `ConversationResult` instances with the `ignored` status and telemetry copies.
- Capture triage prompt emission, history summarization, and agent dispatch preparation requirements for handled messages.
- Describe policy/safety gating that forces refusal prompts when inbound payloads are already tagged restricted.
- Specify adapter contract finalization and validation responsibilities owned by the logic layer after agent execution.

## Impact
- Clarifies Business Logic ownership boundaries versus Business Service primitives.
- Provides reviewers concrete scenarios to validate ignored-message and refusal paths.
- Reduces ambiguity for telemetry and adapter teams relying on the shape of `ConversationResult`.
