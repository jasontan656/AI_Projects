## ADDED Requirements

### Requirement: Persist Prompt Drafts
Prompt records MUST be stored in a durable backend with lossless Markdown content and deterministic metadata, supporting list, update, and delete workflows.

#### Scenario: List Prompts
- **WHEN** the client calls `GET /api/prompts?page=<n>&pageSize=<m>`
- **THEN** the backend MUST return HTTP 200 with an envelope `{ "items": [...], "page": n, "pageSize": m, "total": <count> }`.
- **AND** each item MUST include `id`, `name`, `markdown`, `createdAt`, and `updatedAt` (if applicable).

#### Scenario: Update Prompt
- **WHEN** the client issues `PUT /api/prompts/{id}` with JSON containing `name` and/or `markdown`
- **THEN** the backend MUST persist changes, update `updatedAt`, and return the updated prompt payload.
- **AND** invalid payloads MUST yield HTTP 422 with `{ "detail": "<reason>" }`.

#### Scenario: Delete Prompt
- **WHEN** the client issues `DELETE /api/prompts/{id}`
- **THEN** the backend MUST remove the prompt and respond with HTTP 204 or `{ "success": true }`.
- **AND** on missing prompt, the backend MUST respond with HTTP 404 and structured error `{ "detail": "<reason>" }`.

### Requirement: Prompt Audit Trail
Prompt mutation operations MUST emit audit telemetry for traceability.
#### Scenario: Record Prompt Mutation
- **WHEN** a prompt is updated or deleted
- **THEN** the backend MUST record an audit event (e.g., `audit.prompt`) with prompt id, actor identifier, change type, timestamp, and content hash for traceability.
