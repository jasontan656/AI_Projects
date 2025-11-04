# Proposal: Refactor Foundational Service Layer

## Context
- `openspec/PROJECT_STRUCTURE.md` defines the Foundational Service Layer as the home for bootstrap flows, schema/contract enforcement, telemetry plumbing, configuration loading, and external service adapters. Today those responsibilities live across `shared_utility/` modules, `telegram_api/runtime.py`, and ad-hoc helpers bundled with interface code.
- Prior refactors migrated the Project Utility Layer into `src/project_utility/`, but no canonical `foundational_service` package exists. Core services such as `behavior_contract.py`, telemetry loaders, and FastAPI bootstrap still reside in `shared_utility`, mixing layer boundaries and blocking discoverability.
- The monolithic `shared_utility/contracts/behavior_contract.py` (1.0K+ lines) interleaves aiogram bootstrap, layout guards, OpenAI orchestration, and knowledge-base loaders. Downstream callers import deep internals to circumvent missing abstractions, increasing coupling.
- Telemetry helpers (`shared_utility/telemetry`) and runtime policy assets are consumed by both entrypoints and business logic without a stable interface. File paths are hard-coded, hampering reuse and testing.
- Using the `context 7` MCP server we refreshed FastAPI application layout guidance (`/fastapi/fastapi/0.118.2`) to confirm the plan aligns with current packaging best practices for modularizing services.

## Problem Statement
We need a cohesive Foundational Service Layer that:
1. Lives under a dedicated `src/foundational_service/` package with submodules grouped by concern (bootstrap, contracts, telemetry, policy, integrations).
2. Exposes explicit, well-typed entry points so interface/business layers can depend on stable APIs instead of monolithic modules.
3. Retires `shared_utility` as an implementation home for foundational code, leaving only compatibility shims with clear deprecation paths.
4. Documents dependency boundaries to prevent upward references and to enable incremental rewrites without breaking existing flows.

## Proposed Changes
- Scaffold `src/foundational_service/` with top-level packages:
  - `bootstrap/` for aiogram/FastAPI setup, webhook verification, metrics state, and handler attachment.
  - `contracts/` for core envelope schema, adapter factories, and toolcall utilities.
  - `telemetry/` for Rich/JSONL bus management plus config loaders.
  - `policy/` for runtime policy loading, validation, and repository path helpers.
  - `integrations/` for OpenAI agent orchestration (`behavior_agents_bridge`) and Redis/Mongo adapters needed by bootstrap.
- Break up `shared_utility/contracts/behavior_contract.py` into cohesive modules (state bootstrap, inbound/outbound adapters, KB pipeline, layout guards, webhook middleware) with typed dataclasses and async boundaries.
- Relocate telemetry helpers (`shared_utility/telemetry`) and FastAPI factory (`shared_utility/infra/fastapi_app.py`) into the new package, rewriting as necessary to enforce downward-only dependencies.
- Update interface layer entrypoints (`telegram_api/runtime.py`, `app.py`, FastAPI routes) to consume the new `foundational_service` APIs. Introduce narrow shims in `shared_utility` that re-export the new modules while emitting deprecation warnings.
- Establish a layering contract document and adoption checklist inside the change describing import rules, required dependency injections, and migration steps for other teams.

## Scope
**In scope**
- Cataloguing all Foundational Service responsibilities currently in `shared_utility`, `telegram_api/runtime`, and adjacent helpers; relocating or rewriting them under `src/foundational_service/`.
- Creating compatibility modules under `shared_utility` that forward to the new package with warnings, then updating first-party imports to the canonical paths.
- Introducing typed interfaces for bootstrap state, telemetry configuration, and contract validation to replace ad-hoc dictionaries.
- Providing test scaffolding or diagnostics (where feasible) to validate bootstrap behavior and schema enforcement after the move.

**Out of scope**
- Business logic or knowledge-base content updates beyond what is required for layer compliance.
- Interface rewrites outside Telegram/FastAPI entrypoints touched by the bootstrap changes.
- Performance optimisation or new functionality unrelated to the structural refactor.

## Risks & Mitigations
- **Large module churn breaks downstream work** – Mitigate by adding shims with warnings and sequencing consumer updates before removing legacy imports.
- **Hidden upward dependencies** – Add dependency guards (import lint/test) during migration and adjust modules to depend only on `project_utility` or lower layers.
- **Regression in webhook/bootstrap flows** – Create integration tests (e.g., async bootstrap smoke) and leverage telemetry metrics snapshots to validate parity.

## Open Questions
- Should Redis/Mongo adapters stay in Foundational Service or move to a future integrations layer under Business Services? (Proposal assumes they remain foundational for now.)
- What deprecation window is acceptable before removing `shared_utility` shims? (Recommend agreeing on timeline with maintainers once initial rollout lands.)
- Do we promote runtime policy JSON into a typed model or keep raw dict parsing? (Design explores introducing Pydantic models if time permits.)

