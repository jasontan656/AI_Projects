## Why
- Frontend users need to create, persist, and revisit pipeline node drafts/launch versions with deterministic metadata so the `/pipelines` view can refresh without drift; today the backend has no storage or API for these nodes, so drafts disappear between sessions.
- `allowLLM`, `systemPrompt`, and other pipeline node metadata must be durable and lossless to feed the upcoming pipeline generator, but the current codebase only offers a direct Telegram conversation flow with no notion of node-level persistence.
- The orchestrator must respect node-level LLM guardrails; right now `behavior_agents_bridge` is invoked unconditionally and cannot differentiate nodes that should not call the model.
- The requested schema (`docs/contracts/pipeline-node-draft.json`) is referenced by product docs but is absent from the repo; we need to codify the contract and agree on the data shape during this change.

## What Changes
- Introduce a Mongo-backed pipeline node store with UTF-8 safe prompt persistence, name uniqueness checks, revision counters, and created/updated timestamps sourced from server clock while preserving client-provided `createdAt`.
- Add FastAPI endpoints (create/update/list) that follow `docs/contracts/pipeline-node-draft.json`, emit latest snapshot payloads, and surface conflict errors when `name` already exists for a given pipeline context.
- Expose an audit hook that records operator, timestamp, diff summary, and node id whenever node metadata or prompts change to support DevTools AI reporting.
- Extend the orchestrator pipeline runner to resolve nodes via the store and enforce `allowLLM` (and future `strategy`) flags before invoking `behavior_agents_bridge`, falling back to non-LLM execution where required.
- Provide pagination and optional pipeline-id filtering for `/pipeline-nodes` listings so `/pipelines` can fetch consistent tables.

## Impact
- New Mongo collection (`pipeline_nodes`) with unique index configuration; environments need migration/seed scripts.
- FastAPI surface gains new routes under an `/api/pipeline-nodes` namespace plus shared Pydantic DTOs validated against the JSON schema.
- Orchestrator behavior changes when `allowLLM` is false, requiring regression tests to cover both execution paths.
- Additional structured logging / audit events will land in existing logging sinks; log processing dashboards must allow for the new event keys.
