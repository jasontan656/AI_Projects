# Project Context

## Purpose
Rise is the canonical repository for the multi-channel “Rise” assistant. The service exposes a FastAPI application that terminates Telegram webhooks, validates requests, loads an in-repo knowledge base, and delegates multi-step reasoning to a staged OpenAI-powered orchestrator. The goal is to deliver deterministic, policy-aligned guidance for Philippine government services while maintaining strict observability (structured logs, reproducible seeds, persisted runtime state).

## Tech Stack
- Python 3.11 for the default runtime; keep type-checking strict and exploit the Python guides.
- **FastAPI-law:**0.118.x with Starlette middlewares powering the HTTP/webhook surface; the 0.118 line’s dependency simplifications and `Annotated` helpers reduce endpoint boilerplate. use typed defs + Pydantic as contracts; framework auto-validates/injects/docs/errors.

- aiogram 3.22.0 for the Telegram bot runtime (dispatcher, router, aiohttp-based webhooks) to align with the v3 FSM fixes and webhook improvements.
- OpenAI Python SDK 1.105.0 to access Responses, Assistants, and Streams APIs with structured callbacks and multi-turn storage.
- Redis 7.x with `redis-py` 6.4.0 backing optional memory snapshots, rate counters, and distributed locks.
- MongoDB 7.x deployments via PyMongo 4.2+ for chat summaries, audit trails, and GridFS artefacts.
- Pydantic v2 (stay on the newest minor) for validation, plus jsonschema (latest) for spec enforcement across YAML/JSON assets.
- Rich 13.x alongside the standard logging stack for console dashboards, plus uvicorn (track the latest stable release) as the ASGI server (`python app.py` runs uvicorn under the hood).

## Project Conventions

### Code Style
- Every Python module uses `from __future__ import annotations` and full typing; prefer dataclasses (`ContextBridge`, `BootstrapState`) for structured runtime state.
- Keep functions single-responsibility; IO workloads are async (`behavior_agents_bridge`, Telegram handlers) while filesystem utilities remain sync.
- Logging must use structured fields via `logging.Logger` with `extra` metadata and `ContextBridge.request_id()`; avoid plain `print`.
- Markdown responses target Telegram MarkdownV2—escape user-facing strings with `toolcalls.call_md_escape` whenever content comes from external sources.
- Paths are resolved with `pathlib.Path`; configuration constants live in `project_utility.config`, while runtime policy assets are loaded through `foundational_service.policy` (see `runtime.py`).
- Knowledge base and prompt assets stay in YAML/MD under `KnowledgeBase/` and `openai_agents/agent_contract`; keep filenames snake_case, ids kebab-case.

### Architecture Patterns
- `app.py` is the entrypoint: it loads `.env`, configures logging, enforces HTTPS webhook URLs, and delegates to `interface_entry.bootstrap.app.create_app` which boots aiogram via `interface_entry.telegram.runtime.bootstrap_aiogram_service` and applies the `BehaviorContract` that wires validation, memory loader, and middleware.
- HTTP layer: `interface_entry.http.middleware` provides request-id and logging middleware, while `interface_entry.middleware.signature.SignatureVerifyMiddleware` guards webhooks; routes in `interface_entry.telegram.routes` expose `/telegram`, `/telegram/setup_webhook`, `/metrics`, `/healthz`, and `/internal/memory_health`.
- Telegram pipeline (`interface_entry.telegram.handlers`) converts updates to CoreEnvelope via `foundational_service.contracts.telegram`, classifies intent, and delegates to `business_service.conversation.TelegramConversationService` which now relies on pipeline node metadata and stored prompt records (persisted via `/api/prompts`) rather than any in-repo prompt registry before calling `foundational_service.integrations.openai_bridge.behavior_agents_bridge`.
- Orchestrator: `openai_agents/agent_contract/stage_manifest.yaml` defines a staged workflow (`judgement_v1`, `agency_detect_v1`, `service_select_v1`, etc.). `foundational_service.integrations.openai_bridge` enforces contracts, seeds deterministic execution, and mediates Redis-backed memory snapshots.
- Knowledge base: YAML dictionaries under `KnowledgeBase/` (indexed by `KnowledgeBase/KnowledgeBase_index.yaml`) feed the agents. On startup `behavior_memory_loader` hydrates an in-memory/Redis snapshot and exposes refresh hooks.
- Cross-cutting utilities now live in `src/foundational_service/` and `src/project_utility/`; the former `shared_utility/` package has been removed. Reuse helpers before introducing new ones; add adapters/contracts under `foundational_service.contracts`.

### Testing Strategy
- No unit test suite ships yet; rely on deterministic seeds plus the One-off CLI (`python -m one_off <command>`) housed under `src/one_off/sources/` for prompt validation, knowledge-base checks, selector conformance, and data-store smoke tests.
- For runtime verification, launch with `python app.py --clean` (flushes Redis/Mongo, resets logs) and exercise `/healthz`, `/metrics`, and Telegram sandbox chats.
- When adding automated tests, place them under `tests/` (e.g., `tests/foundational_service/`) and prefer `pytest` with async fixtures.

### Git Workflow
- Treat this repo as the single source of truth; feature work flows through OpenSpec proposals. For any new feature, architecture change, or behavior shift, scaffold `openspec/changes/<change-id>/` (`openspec spec list --long` to inspect current catalog) before coding.
- Branching: create short-lived feature branches named `<change-id>-brief-topic`, rebase onto the default branch before merge, and squash/merge after proposal approval.
- Commits should reference the change id in the subject (e.g., `add-telegram-fallback: guard webhook payload`) and keep diffs scoped; update specs/tasks before marking work complete.

## Domain Context
The assistant focuses on Philippine government services for expatriates and employers. Agencies in scope (per `KnowledgeBase/KnowledgeBase_index.yaml`) include:
- Bureau of Immigration (BI) – visas, accreditation, special permits.
- Department of Labor and Employment (DOLE) – Alien Employment Permit (AEP) and labor compliance.
- Department of Foreign Affairs (DFA) – Apostille, consular support.

User flows:
- Telegram inbound messages (often Chinese/English bilingual) are normalised into CoreEnvelope structures.
- The staged orchestrator selects agencies, dictionary categories, and target services, then stitches guidance from YAML knowledge snippets plus prompt templates.
- Outputs must remain deterministic, policy-aligned, and audit-friendly; telemetry records seeds, stages, and knowledge base sources for every turn.

## Important Constraints
- Environment variables (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_SECRETS`, `WEB_HOOK`, `OPENAI_API_KEY`, optional `REDIS_URL`, `MONGODB_URI`/`MONGODB_DATABASE`) are mandatory for production bootstrap; `WEB_HOOK` must be HTTPS or startup fails.
- `app.py --clean` wipes Redis (`flushall`) and Mongo collections; use only in isolated/dev contexts.
- All agent stages must emit strict JSON (no Markdown) as defined in `openai_agents/agent_contract/stage_runtime_contract.md`; schema drift raises `SchemaValidationError`.
- Token budgets and deterministic seeds are enforced via `foundational_service.policy.runtime.load_runtime_policy`; update the embedded defaults (or provide an override policy file) alongside related specs when behaviour changes.
- Telegram outbound text must be MarkdownV2 safe; sanitize dynamic strings and keep responses under per-call token budgets (~3k tokens).
- Knowledge base edits require matching index entries, checksum validity, and may replicate to Redis snapshots—run KB checks after every content change.
- Logging is structured; include `request_id`, `chat_id`, and relevant telemetry fields in log extras to keep observability dashboards consistent.

## External Dependencies
- Telegram Bot API (webhook delivery; aiogram handles polling/dispatch).
- OpenAI API (Responses/Chat Completions endpoints for multi-stage reasoning).
- Redis (cache/memory backend, optional but recommended for production snapshots and rate control).
- MongoDB (stores chat summaries and operational state initialised via dedicated One-off CLI utilities).
- Optional: ngrok or equivalent reverse proxy for local HTTPS webhook exposure; uvicorn for local server hosting.
