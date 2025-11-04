# Proposal: Refactor Interface / Entry Layer

## Context
- `openspec/PROJECT_STRUCTURE.md` defines the Interface / Entry Layer as the thin surface that terminates inbound protocols (HTTP, webhooks, message consumers) and delegates to lower layers without owning business logic. It should focus on protocol translation, authentication, request validation, and routing.
- Current interface code is split between `app.py` and the `telegram_api/` package. These modules still mix bootstrap logic, adapter behaviour, and foundational responsibilities that we recently relocated under `src/foundational_service/`.
- The repository now exposes clean utility and foundational layers (`src/project_utility/`, `src/foundational_service/`); however, `telegram_api/` remains a top-level package with mixed concerns, and `app.py` embeds structural knowledge about directories that no longer exist.
- We consulted the latest FastAPI documentation via context7 (`/fastapi/fastapi/0.118.2`) to confirm modern guidance on modularizing routers and middleware.

## Problem Statement
We need to converge Interface / Entry Layer code into a dedicated package that:
1. Houses HTTP/FastAPI entrypoints, middleware, and webhook registration in a self-contained namespace (e.g., `src/interface_entry/`).
2. Encapsulates Telegram-specific runtime concerns (aiogram bootstrap, webhook routes, adapters) separate from foundational services.
3. Exposes minimal, testable interfaces for orchestrating foundational operations without duplicating business or foundational logic.
4. Retires the legacy `telegram_api/` structure and removes stale references (e.g., to `shared_utility`) from `app.py`.

## Proposed Changes
- Introduce a `src/interface_entry/` package with submodules:
  - `http/` – FastAPI app factory, middleware, request-id propagation, CORS config.
  - `telegram/` – aiogram runtime bootstrap, webhook routes, handlers, adapters, contract validation.
  - `middleware/` – shared middleware such as logging and signature verification.
  - `bootstrap/` – orchestration helpers that coordinate foundational services and interface routing.
- Migrate existing `app.py`, `telegram_api/runtime.py`, `telegram_api/routes.py`, `telegram_api/handlers/message.py`, and adapters into the new package, rewriting where necessary to align with layering constraints.
- Update `app.py` to delegate entirely to `interface_entry` factories (no direct foundational imports beyond the intended public APIs).
- Provide interface-level configuration (paths, manifests) under `config/` as needed, removing hard-coded references to deleted directories.
- Add shims or migration notes (if required) for CLI tooling that referenced `telegram_api`, planning their eventual removal.

## Scope
**In scope**
- Restructuring interface code into `src/interface_entry/` with clear module boundaries.
- Updating imports across the repo (including tests/tooling) to reference the new package.
- Ensuring middleware, routers, and handlers remain protocol-focused and defer to `foundational_service`.
- Adding documentation/spec updates that clarify the Interface / Entry Layer directory map.

**Out of scope**
- Changes to foundational or business logic beyond compatibility with the new interface package.
- Enhancements to aiogram/FastAPI behaviour unrelated to structural refactoring.
- front-end/client integrations or knowledge base content changes.

## Risks & Mitigations
- **Large import churn** – Mitigate by sequencing migration (introduce interface package, update imports, remove old modules) and adding temporary shims if necessary.
- **Regressions in webhook handling** – Add focused tests/mocks for `interface_entry.telegram` and run existing validation commands after migration.
- **Documentation drift** – Update `openspec/PROJECT_STRUCTURE.md`, project README excerpts, and manifests to reflect the new layout.

## Open Questions
- Should we publish interface package entrypoints (e.g., CLI) beyond FastAPI? (Default: keep scope limited to current HTTP/Telegram flows.)
- Do we need to support additional entry channels in the near future (e.g., REST endpoints beyond Telegram)? (Design will allow extension but focus on existing flows.)

