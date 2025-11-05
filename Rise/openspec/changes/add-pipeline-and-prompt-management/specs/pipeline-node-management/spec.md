## MODIFIED Requirements

### Requirement: Persist Pipeline Nodes
Pipeline node metadata MUST be stored durably with revision tracking and update/delete workflows.
#### Scenario: Update Node Metadata
- **WHEN** the client issues `PUT /api/pipeline-nodes/{id}` with JSON containing any subset of `name`, `allowLLM`, `systemPrompt`, `status`, `pipelineId`, or `strategy`
- **THEN** the backend MUST persist the provided fields, increment the node `version`, update `updatedAt`, and respond with the full latest snapshot including `id`, `name`, `allowLLM`, `systemPrompt`, `status`, `pipelineId`, `strategy`, `createdAt`, `updatedAt`, and `version`.
- **AND** unchanged fields MUST be returned as stored values; empty strategy payloads MUST be reflected as `{}`.

#### Scenario: Delete Node
- **WHEN** the client issues `DELETE /api/pipeline-nodes/{id}`
- **THEN** the backend MUST remove the node record and respond with HTTP 204 or a body `{ "success": true }`.
- **AND** if the node does not exist, the backend MUST respond with HTTP 404 and body `{ "detail": "<reason>" }`.

### Requirement: Pipeline Node API Contract
Pipeline node REST endpoints MUST expose consistent pagination and snapshot payloads to clients.
#### Scenario: Paginated Node Listing
- **WHEN** the client calls `GET /api/pipeline-nodes?page=<n>&pageSize=<m>`
- **THEN** the backend MUST return HTTP 200 with a JSON envelope containing `items` (array of node snapshots), `page`, `pageSize`, and `total`.
- **AND** each node snapshot MUST contain `id`, `name`, `allowLLM`, `systemPrompt`, `createdAt`, and `updatedAt` (if applicable), plus optional `latestSnapshot` mirroring persisted data.

### Requirement: Pipeline Node Audit Trail
Node mutations MUST emit audit events for traceability.
#### Scenario: Record Audit On Update/Delete
- **WHEN** a node is updated or deleted
- **THEN** the backend MUST emit an `audit.pipeline_node` event capturing `node_id`, actor identifier, `change_type` ("updated" or "deleted"), `version` (for updates), and timestamp, using structured logging.
