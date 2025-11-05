## ADDED Requirements

### Requirement: Persist Pipeline Nodes
The system MUST persist pipeline node drafts and published records in a durable store with lossless prompt text and deterministic metadata.

#### Scenario: Store Node Snapshot
- **WHEN** the backend receives a node payload matching `docs/contracts/pipeline-node-draft.json` (including `name`, `allowLLM`, `systemPrompt`, `createdAt`)
- **THEN** it MUST write a record containing those fields plus a generated `id`, server-side `createdAt`/`updatedAt`, and a monotonic `version`
- **AND** `systemPrompt` MUST be stored and returned byte-for-byte identical (UTF-8) to the payload supplied by the frontend.

#### Scenario: Enforce Name Uniqueness
- **WHEN** a node is created or renamed
- **THEN** the store MUST reject the operation with a conflict error if another node with the same `name` exists within the same `pipelineId` scope (treat `null` as a scope)
- **AND** the response MUST surface an error code the frontend can map to “duplicated node name”.

### Requirement: Pipeline Node API Contract
The HTTP API MUST expose create/update endpoints aligned with the draft contract and return the latest snapshot for frontend refresh.

#### Scenario: Create Node API Response
- **WHEN** the client calls `POST /api/pipeline-nodes` with a valid payload
- **THEN** the response body MUST include `id`, `name`, `allowLLM`, `systemPrompt`, `createdAt`, `updatedAt`, `version`, `status`, `pipelineId`, and `latestSnapshot` fields identical to the stored record
- **AND** the API MUST echo any optional `strategy` object even when empty.

#### Scenario: Update Node API Response
- **WHEN** the client updates a node via `PUT /api/pipeline-nodes/{id}`
- **THEN** the backend MUST increment `version`, update `updatedAt`, persist the new values, and return an updated snapshot with the same field set as the create response.

### Requirement: Pipeline Node Listing
The system MUST let clients enumerate nodes predictably for UI tables.

#### Scenario: List Nodes With Filters
- **WHEN** the client calls `GET /api/pipeline-nodes` with `pipelineId`, `page`, and `pageSize` query parameters
- **THEN** the response MUST return a deterministic order (newest `updatedAt` first), include pagination metadata (`page`, `pageSize`, `total`), and list node snapshots matching the filter.

#### Scenario: List Nodes Latest Snapshot
- **WHEN** the frontend refreshes the node list
- **THEN** each list item MUST carry the same field names as the single-node response (`latestSnapshot`, timestamps, `version`) so the UI can render updated metadata without extra fetches.

### Requirement: Pipeline Node Audit Trail
Node mutations MUST generate audit telemetry for dev tooling.

#### Scenario: Emit Audit Event On Mutation
- **WHEN** a node is created or updated
- **THEN** the backend MUST emit an `audit.pipeline_node` log (or equivalent structured audit record) capturing `nodeId`, actor identifier, `changeType`, timestamp, and the old/new `allowLLM` + `systemPrompt` hashes
- **AND** failures to record the audit entry MUST surface an internal error rather than silently succeeding.
