# Design: Foundational Service Layer Restructure

## Overview
This design reshapes Foundational Service responsibilities into a dedicated `src/foundational_service/` package. The current implementation scatters bootstrap, schema enforcement, telemetry, and OpenAI integration across `shared_utility/` and `telegram_api/`, making the layer boundary unclear. We reorganise these concerns into cohesive subpackages with explicit interfaces while retaining short-term shims for compatibility.

## Current State Snapshot
- `shared_utility/contracts/behavior_contract.py` (≈1,100 LOC) mixes:
  - aiogram/FastAPI bootstrap (`behavior_bootstrap`, `get_bootstrap_state`)
  - Telegram adapters (`behavior_core_envelope`, `behavior_telegram_inbound/outbound`)
  - Knowledge-base loaders and layout guards (`behavior_kb_pipeline`, `behavior_layout_guard`)
  - Webhook signature verification (`behavior_webhook_request`, `call_verify_signature`)
  - OpenAI orchestration (`behavior_agents_bridge`)
- `shared_utility/telemetry/{bus.py,config.py}` provide Rich/JSONL sinks and config loaders but depend on `project_utility.config.paths`.
- `shared_utility/infra/fastapi_app.py` exposes a bare FastAPI factory.
- Runtime policy JSON lives in `shared_utility/config/runtime_policy.json`; loaders are embedded inside `behavior_bootstrap`.
- `telegram_api/runtime.py` imports deep contract functions directly, binding interface logic to foundational details.

## Target Architecture
Create a `src/foundational_service/` namespace with the following structure:

```
src/foundational_service/
  __init__.py
  bootstrap/
    __init__.py
    state.py              # BootstrapState dataclass + lifecycle helpers
    aiogram.py            # behavior_bootstrap equivalent, handler wiring, metrics
    fastapi.py            # FastAPI app factory & middleware adapters
    webhook.py            # Request validation, signature checks
  contracts/
    __init__.py
    envelope.py           # CoreEnvelope models + adapter builders
    telegram.py           # Telegram inbound/outbound transformations
    registry.py           # Prompt registry + layout guard utilities
    toolcalls.py          # Markdown escaping, audit hooks, agent output validators
  integrations/
    __init__.py
    openai_bridge.py      # behavior_agents_bridge + cache/prompt helpers
    memory_loader.py      # Redis/GridFS loaders (currently in behavior_contract)
  policy/
    __init__.py
    runtime.py            # Runtime policy loader/validator (Pydantic wrapper)
    paths.py              # Repo/log root discovery (delegates to project_utility)
  telemetry/
    __init__.py
    bus.py                # Rich/JSONL console abstraction
    config.py             # load_telemetry_config with repository-aware paths
  diagnostics/
    __init__.py
    metrics.py            # Metrics snapshot builder + validation helpers
```

Key characteristics:
- `bootstrap.aiogram` consumes services from `contracts.telegram`, `integrations.openai_bridge`, `policy.runtime`, and `telemetry`.
- No module under `foundational_service` may import from `telegram_api`, business logic, or one-off tooling. Allowed dependencies: standard library, vetted third-party libs (FastAPI, aiogram, Pydantic, yaml, redis, rich), and `project_utility`.
- Compatibility shims under `shared_utility/*` keep the old import surface but only re-export with deprecation warnings.

## Module Responsibilities & Interfaces

### `bootstrap.state`
- Owns `BootstrapState` dataclass, global state registry, and context helpers.
- Provides functions `get_state()`, `set_state()`, `reset_state()` used by aiogram/FastAPI entrypoints and tests.

### `bootstrap.aiogram`
- Replaces `behavior_bootstrap` with `bootstrap_aiogram(...)` returning a typed result (`BootstrapResult`).
- Extracts runtime policy loading into `policy.runtime.load_runtime_policy`.
- Delegates telemetry config to `telemetry.config.load_telemetry_config`.
- Accepts dependency-injected handler attachment callbacks for testability; default uses `telegram_api.handlers.message`.

### `bootstrap.fastapi`
- Houses the FastAPI factory (`create_base_app`, `create_app`) plus new middleware registration utilities.
- Wraps request-id middleware for reuse without referencing `telegram_api`.

### `bootstrap.webhook`
- Implements webhook request validation, signature verification (`verify_signature`), and response normalisation, decoupled from FastAPI specifics.

### `contracts.envelope`
- Migrates `CoreEnvelope`, `SchemaValidationError`, and adapter validation helpers.
- Adds explicit return types (dataclasses) for adapter results.

### `contracts.telegram`
- Provides `build_core_schema`, inbound/outbound conversions, and context quote helpers.
- Accepts channel enumerations for future expansion.

### `contracts.registry`
- Hosts prompt registry validation (`validate_prompt_registry`) and layout guard logic, using `policy.paths` to resolve assets.

### `contracts.toolcalls`
- Keeps Markdown escaping, logging payload builder, audit hooks, and agent output validators with minimal changes.
- Introduces a dataclass for `AgentOutput`.

### `integrations.openai_bridge`
- Encapsulates `behavior_agents_bridge` with dependency injection for OpenAI client, telemetry bus, and runtime policy.
- Splits helper functions (prompt assembly, caching) into private modules for clarity.

### `integrations.memory_loader`
- Moves Redis/GridFS bootstrap and KB pipeline helpers from `behavior_contract`.
- Provides async entry points `load_memory_snapshot`, `hydrate_kb_pipeline`.

### `policy.runtime`
- Wraps runtime policy loading into a typed model (Pydantic) to validate seeds, runtime flags, and token budgets.
- Exposes `load_runtime_policy(Path | None, repo_root: Path)` consumed by bootstrap + tests.

### `telemetry`
- Retains Rich/JSONL bus functionality while decoupling path resolution via `policy.paths`.
- Adds interface `TelemetrySink` (protocol) to simplify testing/mocking.

### `diagnostics.metrics`
- Provides `_default_metrics_state` equivalent, typed as `MetricsSnapshot`, and helper to merge telemetry counters.

## Migration Strategy
1. **Scaffold package:** Create modules and docstrings with dependency guards, add `pyproject.toml` entry for `foundational_service`.
2. **Move contracts:** Relocate core envelope + toolcall logic first; update import sites (Telegram handlers, tests). Leave shims in `shared_utility/core` and `shared_utility/contracts`.
3. **Extract bootstrap state:** Move `BootstrapState` and context functions into `bootstrap.state`; update references.
4. **Port aiogram bootstrap:** Rewrite `behavior_bootstrap` as `bootstrap.aiogram.bootstrap_aiogram` consuming new policy/telemetry modules. Provide backward-compatible wrapper in `shared_utility`.
5. **Relocate telemetry + policy:** Move config loaders/runtime policy parsing into dedicated modules; ensure runtime policy path uses `project_utility`.
6. **Integrations:** Migrate OpenAI bridge and memory loader to `integrations`; adjust call sites.
7. **Interface adjustments:** Update `app.py`, `telegram_api/runtime.py`, and any scripts to import from `foundational_service`.
8. **Shims & cleanup:** Implement deprecation shims, update docs, and plan removal timeline.

## Testing & Validation
- Add unit tests for `contracts.envelope` (core envelope validation) and `bootstrap.aiogram` (bootstrap smoke with stub handlers).
- Provide integration test fixture to ensure telemetry config resolves log paths correctly.
- Leverage existing runtime scripts (e.g., `python app.py --clean`) as manual validation steps; document in `tasks.md`.
- Consider lightweight dependency lint (e.g., `python -m tools.lint_dependencies`) to ensure no upward imports.

## Open Points
- Confirm whether runtime policy should remain JSON-only to minimise churn; design assumes we introduce a thin Pydantic wrapper but can degrade to raw dict if time constrained.
- Determine eventual removal timeline for `shared_utility` shims; default to emit warnings on import to encourage migration.
- Clarify whether telemetry bus needs asynchronous flushing hooks; current implementation uses synchronous writes.

