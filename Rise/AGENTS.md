# Project Context

## Purpose
Rise is the canonical repository for the multi-channel “Rise” assistant. The service exposes a FastAPI application that terminates Telegram webhooks, validates requests, loads an in-repo knowledge base, and delegates multi-step reasoning to a staged OpenAI-powered orchestrator. The goal is to deliver deterministic, policy-aligned guidance for Philippine government services while maintaining strict observability (structured logs, reproducible seeds, persisted runtime state).
- The Vue-based Admin Panel lives in `D:\AI_Projects\Up` (served on port 5173) and is strictly for operators to configure workflows/channels and monitor health; production users always enter through bound channels (Telegram, future chat apps, or custom APIs), never via the admin UI.

## Tech Stack & External Dependencies
- Python 3.11 runtime with strict typing.
- FastAPI 0.118.x + Starlette middlewares for HTTPS webhook surface; Pydantic v2 / jsonschema for validation.
- aiogram 3.22.0 handles Telegram dispatcher/webhooks; Telegram Bot API is the upstream webhook source.
- OpenAI Python SDK 1.105.0 (external OpenAI API) powers staged reasoning with structured callbacks.
- Redis 7.x (`redis-py` 6.4.0) for snapshots, rate counters, distributed locks; optional but recommended.
- MongoDB 7.x (PyMongo 4.2+) stores chat summaries, audit trails, GridFS artefacts.
- Rich 13.x + logging stack; uvicorn (latest stable) as ASGI server; ngrok or equivalent for local HTTPS tunnels when needed.

## Domain Context
The assistant ultimately targets Philippine government services across multiple agencies. Initial deployments focus on the Bureau of Immigration (BI)—visas, accreditation, special permits—while additional agencies (DOLE, DFA, etc.) will be onboarded later by extending the knowledge base (`KnowledgeBase/KnowledgeBase_index.yaml`).

### AI_WorkSpace Usage
- `AI_WorkSpace/Requirements/` — canonical demand/requirements docs (`session_<timestamp>_<topic>.md`).
- `AI_WorkSpace/DevDoc/On/` — active design/implementation docs (`session_<timestamp>_<topic>.md`).
- `AI_WorkSpace/DevDoc/Archive/` — archived/fulfilled design docs.
- `AI_WorkSpace/plans/` — task plans / step checklists (`session_<timestamp>_min_steps.md`).
- `AI_WorkSpace/WorkLogs/` — task checklists / execution logs (`session_<timestamp>_taskchecklist.md`).
- `AI_WorkSpace/notes/` — per-session notes named `session_<timestamp>.md`, containing intent, repo context, tech stack, search findings.
- `AI_WorkSpace/Temp*/` — temporary scripts, diagnostics, or scratch files (may be cleaned anytime).
- Treat other subfolders as scratch pads only when explicitly instructed.

### Channel & Admin Separation
- The `Rise` backend is the execution runtime for all workflows/channel integrations. External user inputs always arrive through bound channels (Telegram webhooks, future chat apps, or custom APIs)—**never through the admin UI**.
- Repository `D:\AI_Projects\Up` hosts the Vue-based Admin Panel served on port **5173**. It exists solely for operators to:
  - create/edit prompts, nodes, and workflows;
  - bind external channels (Telegram, future Slack/HTTP/etc.);
  - monitor health/tests.
- Admin actions call the `Rise` backend APIs; once a channel is configured, end users interact with their native client (e.g., Telegram bot). The admin UI is a visualization/control surface, not an end-user product.
- Workflow/channel contracts must therefore be defined with two audiences in mind:
  1. **Operators (Admin Panel / project `Up`)** – need clear forms, validation rules, and health telemetry while configuring workflows.
  2. **External Clients (channel users)** – interact through Telegram or other APIs and expect stable behavior; all errors/fallbacks are surfaced via those channels.

## Important Constraints
- `.env` files may be read to confirm environment variables (e.g., `TELEGRAM_BOT_TOKEN`, `WEB_HOOK`, `OPENAI_API_KEY`, Redis/Mongo URIs), but must never be modified without explicit user permission.

## External Dependencies
- Telegram Bot API (webhook delivery; aiogram handles polling/dispatch).
- OpenAI API (Responses/Chat Completions endpoints for multi-stage reasoning).
- Redis (cache/memory backend, optional but recommended for production snapshots and rate control).
- MongoDB (stores chat summaries and operational state initialised via dedicated One-off CLI utilities).
- Optional: ngrok or equivalent reverse proxy for local HTTPS webhook exposure; uvicorn for local server hosting.

## File Decomposition & Coupling Guardrails
- Map every new module to the layered model in `AI_WorkSpace\PROJECT_STRUCTURE.md`; document the intended layer in DevDoc before adding code.
- Shape files by domain intent, not sheer quantity. Prefer multiple small modules grouped by behavior (serialization, telemetry, validation) instead of “misc util” buckets.
- Payloads/prompts/policies must live under domain-specific asset folders; mixing unrelated assets in a single file is discouraged unless they share the same lifecycle.
- Large orchestrator files (e.g., webhook dispatcher) are acceptable only when they coordinate multiple submodules; annotate the DevDoc with the rationale and list sub-dependencies to keep future refactors tractable.
- Temporary coupling or transitional glue must be recorded in session notes and task plans with a retirement plan so downstream prompts know when to untangle it.
