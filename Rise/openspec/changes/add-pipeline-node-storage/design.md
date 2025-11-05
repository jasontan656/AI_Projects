## Overview
We will layer a dedicated pipeline node service on top of MongoDB so draft/production nodes share a single storage contract. A FastAPI router will expose CRUD-lite APIs aligned with `docs/contracts/pipeline-node-draft.json`, and an orchestrator adaptor will load nodes and enforce `allowLLM` before delegating to the OpenAI bridge.

## Data Model
- Collection: `pipeline_nodes`
- Document shape:
  - `_id`: ObjectId
  - `node_id`: string UUID (returned to clients)
  - `pipeline_id`: nullable string (enables grouping/filtering; optional for standalone drafts)
  - `name`: string (unique per pipeline or globally when `pipeline_id` is null)
  - `status`: enum (`draft`, `published`)
  - `system_prompt`: string (saved verbatim, stored as UTF-8)
  - `allow_llm`: bool
  - `strategy`: nullable object for future expansion (persisted even when empty)
  - `version`: int (monotonic revision counter; incremented on update)
  - `created_at`: datetime (server timestamp)
  - `client_created_at`: datetime (optional; from request `createdAt`)
  - `updated_at`: datetime (server timestamp)
  - `updated_by`: string actor id (from auth context; required for audit)
- Indexes:
  - `{ name: 1, pipeline_id: 1 }` unique (treat null pipeline_id as unique scope)
  - `{ node_id: 1 }` unique

## API Surface
- `POST /api/pipeline-nodes`: Validates payload against the JSON schema (we will add the missing `docs/contracts/pipeline-node-draft.json`), assigns UUID, stores document, returns node record with `latestSnapshot` (mirrors stored document) plus server `createdAt`/`updatedAt`.
- `PUT /api/pipeline-nodes/{node_id}`: Applies partial/full update, increments `version`, writes `updated_at`, preserves `system_prompt` verbatim.
- `GET /api/pipeline-nodes`: Supports `pipelineId`, `status`, `page`, `pageSize` query params. Returns list with pagination metadata and each node’s latest snapshot.
- DTOs live under `src/interface_entry/http/pipeline_nodes/dto.py`; router in `pipeline_nodes/routes.py`.
- 409 conflict on duplicate `name` within the same pipeline scope; response explains conflict so frontend can prompt the user.

## Orchestrator Integration
- Introduce `PipelineNodeResolver` in `business_service.pipeline` that fetches node definitions by `node_id` and surfaces configuration to orchestration flows.
- Add `PipelineNodeExecutor` shim in `business_logic` that wraps `AgentDelegator.dispatch`. When `allow_llm` is `False`, it returns either cached prompts or raises a controlled error; when `True`, it dispatches normally. The executor also passes along the stored `system_prompt` to the conversation service when pipelines assemble composite prompts.
- Extend runtime policy/context wiring so pipeline executions call the resolver before stage dispatch.

## Observability & Audit
- New `audit.pipeline_node` event logged via `toolcalls.call_record_audit` with fields: `node_id`, `actor`, `change_type`, `diff`, `strategy`, `version`.
- HTTP responses include `updatedBy` and `version` so frontend can show change history.
- Mongo write acknowledgements and FastAPI error handlers will surface into existing logs; we will add structured log tests.

## Risks & Open Questions
- `docs/contracts/pipeline-node-draft.json` is missing; we must add it (from product team) or author a first-cut schema aligned with frontend expectations.
- AuthN/AuthZ for identifying the actor is undefined; proposal assumes we can derive `actor` from request headers (fallback to `ContextBridge.request_id()` until SSO arrives).
