## Why
- Frontend now needs full CRUD management for pipeline nodes and prompt drafts (listing, updating, deleting) sourced from the backend, per `instruction.md`.
- Existing backend only supports pipeline node creation/list without delete; prompt APIs are absent. Response shapes and error handling do not yet align with frontend expectations.
- Consistent UTC timestamps, structured errors, and pagination metadata are required so UI tables refresh accurately and display backend feedback.

## What Changes
- Extend pipeline node API surface with PUT/DELETE handlers, enforce structured errors, and standardize GET responses (pagination envelope, latest snapshot payload).
- Introduce prompt management API (Mongo-backed) with GET/PUT/DELETE endpoints mirroring node behaviour.
- Propagate new API capabilities to the Vue frontend services/stores, replacing local stubs and wiring delete/update flows while normalizing error display.
- Update documentation/specs to record the REST contracts and repository models.

## Impact
- Backend: new Mongo collection for prompts, repository/service modules, router wiring, additional FastAPI tests; pipeline node service gains delete/update logic.
- Frontend: service layer changes (pipeline/prompt), store enhancements, UI adjustments, and error handling updates.
- Ops: new endpoints require deployment awareness; ensure `.env`/config expose base URL for frontend.
