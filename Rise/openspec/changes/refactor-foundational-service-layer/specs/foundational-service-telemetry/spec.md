# Capability: Foundational Service Telemetry

## ADDED Requirements

### Requirement: Centralise telemetry configuration
Telemetry configuration MUST be loaded via `foundational_service.telemetry.config.load_telemetry_config`, merging default settings with optional YAML overrides and resolving paths relative to the repository root.

#### Scenario: Resolve relative telemetry paths
GIVEN `TELEMETRY_CONFIG` points to a YAML file with `jsonl.path: logs/telemetry.jsonl`
WHEN `load_telemetry_config()` runs
THEN the returned config resolves `jsonl.path` to an absolute path under the repo log directory
AND missing files raise a descriptive error.

### Requirement: Provide Rich console + JSONL sinks
The telemetry bus MUST expose a `TelemetryBus` (or equivalent) able to stream events to both Rich console output and JSONL files with optional mirroring.

#### Scenario: Emit stage start event
GIVEN a `TelemetryBus` created from `load_telemetry_config`
WHEN `emit({"event_type": "StageStart", ...})` is called
THEN the console handler renders without raising
AND the JSONL file appends a line containing the event payload.

### Requirement: Offer metrics snapshot utilities
The Foundational Service Layer MUST provide a typed metrics snapshot helper that seeds aiogram/FastAPI bootstrap state with default counters.

#### Scenario: Generate default metrics
GIVEN `foundational_service.diagnostics.metrics.default_snapshot()`
WHEN invoked
THEN it returns a mapping that includes `telegram_updates_total`, `telegram_inbound_total`, `webhook_rtt_ms_sum`, and `webhook_rtt_ms_count`
AND repeated calls yield independent copies safe for mutation.

