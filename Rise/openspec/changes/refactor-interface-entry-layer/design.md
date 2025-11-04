# Design: Interface / Entry Layer Restructure

## Overview
We consolidate all ingress responsibilities into a dedicated `src/interface_entry/` package. The current structure (`app.py`, `telegram_api/`) predates the layered refactor and still mixes foundational concerns with protocol glue. The new package mirrors the layering model: Interface modules convert external traffic into foundational requests, leveraging utilities without owning business logic.

## Current State
- `app.py` hosts FastAPI setup, middleware definitions, telemetry bootstrapping, and direct interactions with foundational packages.
- `telegram_api/runtime.py` orchestrates aiogram bootstrap, but it still resides at the project root and imports foundational helpers directly.
- `telegram_api/routes.py` combines FastAPI routing, metrics management, and webhook validation.
- `telegram_api/handlers/message.py` contains Telegram message processing, referencing foundational adapters and prompt registries.
- `telegram_api/adapters/telegram.py` and `telegram_api/adapters/response.py` translate between aiogram updates and the foundational contracts.
- `telegram_api/contract/adapter_contract.py` retains legacy helper definitions overlapping with foundational services.

## Target Architecture
Introduce `src/interface_entry/` with the following structure:

```
src/interface_entry/
  __init__.py
  bootstrap/
    __init__.py
    app.py              # FastAPI app factory wiring middlewares/routes
    telegram_runtime.py # Orchestrates aiogram + webhook registration
  http/
    __init__.py
    middleware.py       # Request ID, logging, signature verification
    routes.py           # Shared HTTP routes (healthz, metrics)
  telegram/
    __init__.py
    handlers.py         # Telegram message router handlers
    routes.py           # FastAPI webhook endpoints
    adapters.py         # Update ↔ contract conversions
    runtime.py          # aiogram dispatcher lifecycle helpers
  middleware/
    __init__.py
    logging.py
    request_id.py
    signature.py
  config/
    __init__.py
    manifest_loader.py  # Top entry manifest + route config
```

Key traits:
- **Thin coordination**: Interface modules import foundational services only through public APIs (e.g., `foundational_service.bootstrap.aiogram`).
- **Separation by protocol**: Telegram-specific functionality lives under `telegram/`, while generic HTTP/FastAPI middleware resides under `http/` or `middleware/`.
- **Single entrypoint glue**: A new `interface_entry.bootstrap.app.create_app()` builds the FastAPI app; `app.py` becomes a thin launcher importing from this factory.
- **Manifests/config**: Any interface-specific manifest (e.g., top entry layout, webhook settings) moves into `config/` backed by the existing `config/` directory.

## Module Responsibilities
- `bootstrap.app` – builds the FastAPI app, attaches middleware, registers routes, and exposes CLI helpers.
- `bootstrap.telegram_runtime` – coordinates aiogram bootstrap, registers handlers, and exposes telemetry metadata.
- `http.middleware` – centralizes RequestID and logging middleware; uses `project_utility` for logging and context.
- `middleware.signature` – encapsulates webhook signature checks, exposing errors without coupling to Foundational logic.
- `telegram.adapters` – wraps `foundational_service.contracts.telegram` to transform aiogram updates and outbound payloads.
- `telegram.routes` – defines FastAPI routes for incoming webhooks and webhook setup endpoints.
- `telegram.handlers` – contains aiogram message handlers, delegating business orchestration to `foundational_service`.
- `config.manifest_loader` – loads interface manifests (top entry, route ownership) to keep `app.py` free from file system details.

## Migration Strategy
1. Scaffold `src/interface_entry/` with placeholder modules and updated `pyproject.toml`.
2. Move FastAPI middleware and app factory logic from `app.py` into `interface_entry.bootstrap.app`.
3. Relocate aiogram bootstrap and webhook helpers from `telegram_api/runtime.py` & `routes.py` into `interface_entry.telegram` submodules.
4. Port adapters (`telegram_api/adapters/*.py`) and handlers into `interface_entry.telegram`.
5. Update imports across `app.py`, tests, and tooling to reference the new package.
6. Remove the `telegram_api/` package and any obsolete entry assets.
7. Update documentation (`openspec/PROJECT_STRUCTURE.md`, manifests) to reference the new directories.

## Validation
- Unit tests for interface adapters/handlers (`tests/interface_entry/`).
- Runtime smoke tests launching FastAPI + aiogram bootstrap in dry-run mode.
- Existing validation commands (`python -m compileall`, interface-specific CLI) to confirm no regressions.

