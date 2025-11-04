# Capability: Foundational Service Contracts

## ADDED Requirements

### Requirement: Deliver typed core envelope definitions
The Foundational Service Layer MUST expose Pydantic models and helpers under `foundational_service.contracts.envelope` that validate inbound/outbound payloads and surface telemetry metadata.

#### Scenario: Validate flattened telegram payload
GIVEN a flattened Telegram message containing `chat_id`, `convo_id`, `channel`, and `user_message`
WHEN it is passed to `CoreEnvelope.validate_payload`
THEN the function returns a `CoreEnvelope` instance with nested metadata/payload/ext_flags sections
AND trimmed context quotes are reflected via `trimmed_context_quote_count`.

### Requirement: Normalise Telegram channel data
The layer MUST provide helper functions under `foundational_service.contracts.telegram` that translate raw Telegram updates into validated core envelopes and outbound payloads.

#### Scenario: Build core schema from message update
GIVEN a Telegram update dict with `message`, `chat`, and `text`
WHEN invoking `build_core_schema(update, channel="telegram")`
THEN the result contains a validated `core_envelope` dict and telemetry payload
AND unsupported channels raise `ChannelNotSupportedError`.

#### Scenario: Compose outbound placeholder
GIVEN an agent chunk sequence and runtime policy
WHEN calling `compose_outbound_payload(...)`
THEN the helper returns a mapping with MarkdownV2-safe placeholder text and records total token usage in telemetry.

### Requirement: Standardise contract utilities
Utility helpers (`call_md_escape`, `call_validate_output`, `call_prepare_logging`, etc.) MUST remain available under `foundational_service.contracts.toolcalls` with consistent behaviour.

#### Scenario: Validate agent output payload
GIVEN a mapping missing `chat_id`
WHEN passed to `call_validate_output`
THEN a `ValueError` is raised explaining the missing field
AND a valid payload returns a normalised dict with `parse_mode` defaulting to `MarkdownV2`.

