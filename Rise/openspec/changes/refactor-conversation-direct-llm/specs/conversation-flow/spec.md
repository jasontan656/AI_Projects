## MODIFIED Requirements

### Requirement: Telegram Conversation Service Direct LLM Flow
Business Service MUST expose `TelegramConversationService.process_update` that, for handled Telegram messages, constructs an `LLMRequest` and delegates directly to the OpenAI Responses API via `behavior_agents_bridge`, without local prompt rendering or staged pipelines.

#### Scenario: Direct LLM call returns response
- **GIVEN** a Telegram update containing user text and optional history snippets
- **WHEN** `process_update` runs
- **THEN** it calls `behavior_agents_bridge` with the user text and metadata and returns a `ConversationServiceResult` containing the generated reply text, token usage, and Telegram adapter contract.

### Requirement: Minimal Conversation Result Mapping
Business Logic `TelegramConversationFlow.process` MUST act as a pass-through that maps the service result into `ConversationResult` without重新引入已删除的 triage/prompt 字段，确保接口层获得与服务层一致的结构。

#### Scenario: Logic wrapper returns basic result
- **GIVEN** Business Service returns an LLM result with `text="Hello"`
- **WHEN** Business Logic processes the update
- **THEN** `ConversationResult` contains the same text in `agent_output`、`mode="direct"`，并仅填充服务层提供的字段（telemetry、适配器信息等）。

### Requirement: OpenAI Bridge Direct Responses
`behavior_agents_bridge` MUST use `AsyncOpenAI.responses.create` to generate replies, returning a dictionary with keys `text`, `usage`, and `response_id`. On API errors it MUST propagate exceptions for the caller to handle.

#### Scenario: Bridge returns structured payload
- **GIVEN** a valid `LLMRequest.prompt`
- **WHEN** the bridge executes
- **THEN** it returns `{"text": <str>, "usage": {"input_tokens": int, "output_tokens": int}, "response_id": <str>}`.

## REMOVED Requirements

### Requirement: Prompt-based Conversation Flow
All requirements that mandated prompt rendering (`agent_triage_system`, `telegram_history_summarize`, `agent_consult_compose`, etc.) are removed; the system no longer depends on prompt registry YAML files.
