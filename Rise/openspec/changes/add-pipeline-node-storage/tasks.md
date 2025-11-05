## 1. Storage Foundations
- [x] Define `docs/contracts/pipeline-node-draft.json` schema and align Pydantic models with it.
- [x] Introduce Mongo pipeline node repository with unique indexes, UTF-8 safe prompt handling, and revision counter support.

## 2. HTTP Surface
- [x] Add FastAPI router/endpoints for create, update, and list operations with conflict handling and pagination.
- [x] Wire DTO ↔ repository translations, ensuring responses include `latestSnapshot`, `createdAt`, `updatedAt`, and `version`.
- [x] Cover happy-path and validation cases with FastAPI tests (using test client + temporary mongo fixture).

## 3. Orchestrator Enforcement
- [x] Add pipeline node resolver/executor that respects `allowLLM` and exposes stored prompts to pipeline runs.
- [x] Update orchestrator/agent delegation path to bypass LLM calls when `allowLLM` is false and emit audit events.

## 4. Observability & Docs
- [x] Emit `audit.pipeline_node` logs on create/update, capturing actor + diff summary.
- [x] Document new API and storage behavior in developer docs (README or dedicated markdown).
- [x] Run `openspec validate add-pipeline-node-storage --strict` and ensure tests pass.
