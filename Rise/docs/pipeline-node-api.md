## Pipeline Node API Overview

The pipeline node service persists draft and published node definitions backing the `/pipelines` frontend. It exposes a REST surface under `/api/pipeline-nodes` and stores data in the `pipeline_nodes` MongoDB collection.

### Data Contract

- Payloads follow `docs/contracts/pipeline-node-draft.json`.
- Required fields: `name`, `allowLLM`, `systemPrompt`, `createdAt`.
- The backend augments records with `id` (UUID), `version` (monotonic), `createdAt`/`updatedAt` timestamps, and echoes the optional `strategy` object.

### Endpoints

| Method | Path                       | Description                                                |
| ------ | -------------------------- | ---------------------------------------------------------- |
| POST   | `/api/pipeline-nodes`      | Create a node. Rejects duplicate names within a pipeline.  |
| PUT    | `/api/pipeline-nodes/{id}` | Update a node. Increments `version` and updates timestamps.|
| DELETE | `/api/pipeline-nodes/{id}` | Delete a node, returning an empty `ApiResponse` body with status 200. |
| GET    | `/api/pipeline-nodes`      | List nodes, supports `pipelineId`, `status`, `page`, `pageSize`. |

Responses are wrapped in the shared `ApiResponse` envelope (`data`, `meta`, `errors`). `data.latestSnapshot` mirrors the stored record to keep frontend refresh deterministic, while `meta` contains pagination details and the current `requestId`.

### Storage Notes

- Collection: `pipeline_nodes`
- Indexes:
  - `{ name: 1, pipeline_id: 1 }` unique
  - `{ node_id: 1 }` unique
- `systemPrompt` is stored verbatim (UTF-8) to avoid prompt corruption.
- `allowLLM` guides orchestrator execution; nodes with `allowLLM=false` skip LLM calls and return fallback messaging.

### Audit & Telemetry

- `audit.pipeline_node` events are emitted on create, update, and execution skips with fields `node_id`, `actor`, `change_type`, `version`, and prompt hashes.
- Orchestrator telemetry includes `pipeline_node_id`, `pipeline_node_version`, and (when applicable) `prompt_id`.

## Prompt API Overview

Prompt definitions live in the `prompts` collection and provide Markdown content for editors in the `/pipelines` workspace. All endpoints return `ApiResponse` envelopes with consistent `data/meta/errors` fields.

### Endpoints

| Method | Path                | Description                                                   |
| ------ | ------------------- | ------------------------------------------------------------- |
| GET    | `/api/prompts`      | List prompts, supports `page` and `pageSize` pagination.      |
| POST   | `/api/prompts`      | Create a prompt; returns `id`, timestamps, and version.       |
| PUT    | `/api/prompts/{id}` | Update prompt name/markdown, incrementing `version`.          |
| DELETE | `/api/prompts/{id}` | Delete prompt, responding with 204 or `{ "success": true }`.  |

Each prompt payload includes `id`, `name`, `markdown`, `createdAt` (UTC ISO8601), `updatedAt`, `version`, and optional `updatedBy`.

### Error Handling

- All mutation and list endpoints surface structured errors via `{"detail": {"code": "...", "message": "..."}}`, enabling UI toast messaging.
- Validation failures (e.g., invalid pagination, empty body) respond with HTTP 422 and descriptive codes (`INVALID_PAGE`, `INVALID_BODY`, etc.).
- Not-found cases respond with 404 and `NODE_NOT_FOUND` / `PROMPT_NOT_FOUND`.

### Audit

- `audit.prompt` events emit `prompt_id`, actor, change type (`created`, `updated`, `deleted`), version, and Markdown hash to support compliance reporting.
