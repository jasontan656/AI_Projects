## MODIFIED Requirements

### Requirement: Telegram Conversation Handler Sends Direct Responses
Interface layer MUST send a single Telegram message using the LLM output when `ConversationResult.mode` is not `ignored`, without streaming placeholders or chunk edits.

#### Scenario: Direct reply without placeholder
- **GIVEN** Business Service returns `mode="direct"` and `agent_output.text` for a handled message
- **WHEN** the Telegram handler executes
- **THEN** it sends one `send_message` call with the provided text and updates metrics/logs accordingly
- **AND** no placeholder/edit operations are attempted.

### Requirement: Conversation Service Result Contains Only Active Fields
`ConversationServiceResult` MUST expose only the fields populated by the direct LLM flow: status, mode, intent, agent request, agent response, telemetry, adapter contract/outbound payload/metrics, audit reason, error hint, user text, logging payload, update type, and core/legacy envelopes.

#### Scenario: Legacy fields removed
- **GIVEN** a developer inspects `ConversationServiceResult`
- **WHEN** they access legacy attributes such as `triage_prompt` or `agent_bridge`
- **THEN** an attribute error occurs, signalling the prompt pipeline is deprecated.

### Requirement: Prompt Registry Injection Removed
Application startup MUST NOT inject the legacy prompt registry into FastAPI app state.

#### Scenario: App state lacks prompt registry
- **GIVEN** the FastAPI app is initialised
- **WHEN** a component inspects `app.state`
- **THEN** it does not find `prompt_registry` or `prompt_category_manifest`, reflecting prompt-less design.

### Requirement: OpenAI Bridge Signature Simplified
`behavior_agents_bridge` MUST accept only prompt-related parameters (`prompt`, optional `history`, `tokens_budget`, `model`, `request_id`) and return a mapping with `text`, `usage`, and `response_id`.

#### Scenario: Bridge call ignores repo root
- **GIVEN** Business Service builds an `agent_request`
- **WHEN** it invokes `behavior_agents_bridge`
- **THEN** no repo-root parameter is required, and the bridge returns the minimal LLM result payload.
