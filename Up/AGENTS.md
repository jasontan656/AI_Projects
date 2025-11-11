# Up Admin Panel Context

## Purpose
- `Up` is the Vue 3 operator console for configuring the Rise backend (`D:\AI_Projects\Rise`). It never serves end users; it publishes prompts, nodes, workflows, and Telegram bindings that the backend executes.
- Operators use the panel to: (1) build pipeline nodes and LLM prompts, (2) assemble/publish workflows, (3) bind workflows to Telegram bots, (4) observe health/logs, and (5) test end-to-end channel delivery.
- Keep parity with backend contracts. Frontend forms (nodes/prompts/workflows/channel policy) serialize into the exact JSON payloads that Rise expects; template mismatches break ops.

## Tech Stack & Build Flow
- Vue 3 + Vite 5 (`npm run dev`, `npm run build`, `npm run preview`). Pinia for state, Vue Router for `/pipelines` workspace, Element Plus for UI, Vue Flow for topology previews, CodeMirror 6 for editors.
- Vitest + Testing Library + Vue Test Utils (`npm run test`). Test harness is configured via `vite.config.js` and `tests/setup/vitest.setup.js` (adds `matchMedia`, `localStorage` polyfills).
- Environment: `.env.development` seeds `VITE_API_BASE_URL` plus actor headers. `VITE_ENABLE_OBSERVABILITY=true` toggles realtime logs/variable/tool tabs in `WorkflowBuilder`.
- `httpClient.js` automatically injects `X-Actor-*` headers from `localStorage` (`up.actorId`, `up.actorRoles`, `up.tenantId`). Set these before manual testing; never hardcode secrets in source.

## Admin Surface vs Backend
- Backend-originated truth stays in Rise; Up only orchestrates CRUD + publish flows via `/api/...` endpoints. Any new surface must align to existing FastAPI routes or land a backend spec change first.
- Channel binding tab (`WorkflowChannelForm` + `channelPolicy` store) enforces Telegram-only policy today. Adding Slack/HTTP/etc. requires multi-channel strategy + backend contract updates.
- Observability tabs use SSE + REST (`logService`, `workflowMetaService`). These should degrade gracefully when backend disables endpoints—guard with feature flag blocks already in place.

## Key Directories
- `src/components` – reusable panels/forms (NodeDraftForm, PromptEditor, WorkflowEditor, ChannelHealthCard, WorkflowCanvas, etc.). Many assume Element Plus form semantics and emit `saved`, `dirty-change`, `open-settings` events—preserve emit contracts.
- `src/views` – main shells: `PipelineWorkspace.vue` (nodes/prompts landing) and `WorkflowBuilder.vue` (multi-tab workflow cockpit).
- `src/stores` – Pinia stores for nodes (`pipelineDraft`), prompts (`promptDraft`), workflows (`workflowDraft`), and channel policy (`channelPolicy`). Stores own API calls and loading/error states; components consume via computed properties.
- `src/services` – thin API clients built on `requestJson`. Keep payload sanitation here (e.g., `sanitizeWorkflowPayload`, `sanitizePolicyPayload`) so UI code remains declarative.
- `src/utils/nodeActions.js` – converts Node Action UI drafts into backend-ready System Prompts; any change must keep serialization stable (`composeSystemPromptFromActions`, `serializeActionsForApi`).
- `docs/ProjectDev` – walkthroughs of layout, nodes, prompts, workflow builder, settings, observability, etc. Use them before altering UX flows. `docs/contracts/*.json` capture JSON schemas for node/prompt drafts.
- `tests/` – `unit/` for vitest specs, `e2e/devtools-ai` JSON scripts for DevTools-AI automation, `reports/console-issues.md` for manual QA notes. Add/extend tests when touching matching areas.
- `AI_WorkSpace/` – mirrors backend workspace conventions:
  - `DevDoc/On` – active design notes per session.
  - `DevDoc/Archieved` – fulfilled designs (typo kept intentionally for tooling compatibility).
  - `notes/`, `Reports/` – discovery + alignment logs.
  - `tools/mock-api-server.cjs` – lightweight backend stub for UI testing; keep in sync with real API contracts when mocking.

## Application Modules & Flows
- **Nodes:** `PipelineWorkspace` drives `NodeSubMenu`, `NodeDraftForm`, `NodeList`. Node actions are edited locally, then `NodeDraftForm` flattens actions → System Prompt before POST/PUT via `pipelineService`. Validation ensures name + action compatibility (LLM toggle vs prompt actions). Refresh flows call `listPipelineNodes` and hydrate `pipelineDraft` store.
- **Prompts:** `PromptEditor` uses CodeMirror (Markdown/YAML/JSON support) and auto-saves via `promptService`. Keep preview + metadata sidebars bilingual (CN copy already present).
- **Workflows:** `WorkflowBuilder` tabs:
  1. `WorkflowEditor` – ensures node sequence contains at least one node, binds prompts via `nodePromptMap`, enforces `strategy.retryLimit`/`timeoutMs` ranges.
  2. `WorkflowPublishPanel` – surfaces version history, publish notes, rollback actions.
  3. `WorkflowChannelForm` – binds Telegram bot tokens + webhook/metadata, enforces rate limits, allows unbind with confirmation.
  4. `WorkflowCanvas` – visual map via `@vue-flow/core`; expects `nodeSequence` + `promptBindings`.
  5. `WorkflowLogStream` – SSE subscription + manual export when observability enabled.
  6. `ToolCatalog`/`VariableCatalog` – read-only cards fed by `/variables` & `/tools`.
- Permission guard: Workflow editing is blocked until at least one node and one prompt exist (`canEditWorkflow` check). Keep this to avoid publishing empty workflows.

## Services & API Contracts
- `requestJson` centralizes fetch + error handling. All services should sanitize inputs before sending (trim strings, coerce retry/timeout ranges, filter prompt bindings to existing node IDs, etc.).
- `channelService.sendChannelTest` throttles to three requests/minute (see `channelPolicy.frequencyWindow`). UI should surface the backend error string but maintain front-end guard.
- `logService.subscribeWorkflowLogs` opens SSE to `/api/workflows/{id}/logs/stream`; remember to call returned unsubscribe when leaving tabs to avoid leaks.
- `httpClient` uses `fetch` and expects JSON responses with `{ data, meta }`. Backend errors should include `code`/`message`; new endpoints must follow the same shape for consistent toast messaging.

## Observability & Channel Ops
- Channel health polling uses exponential backoff after three failures (`channelPolicy.scheduleNextPoll`). When adding new health metrics, extend the store shape and `ChannelHealthCard` props together.
- Test panel uses `channelStore.canSendTest` frequency window; surface cooldown UI via `ChannelTestPanel` props (`cooldownUntil` derived in `WorkflowBuilder`).
- Logs/variable/tool tabs are gated by `VITE_ENABLE_OBSERVABILITY`. Any backend flag rename must be reflected in `WorkflowBuilder.vue` to avoid orphaned UI.

## Testing & Tooling Expectations
- For UI/state changes, extend the closest spec (e.g., `tests/unit/PipelineWorkspace.spec.js`, `NodeDraftForm.spec.js`, `PromptEditor.spec.js`, `PipelineWorkspace.spec.js`, `WorkflowBuilder` spec once added). Favor Testing Library queries over brittle selectors.
- When adding contracts or API sanitizers, document them under `docs/contracts` and reference from `AI_WorkSpace/DevDoc`.
- Use `mock-api-server.cjs` to simulate backend flows when Rise server is unavailable; keep request/response payloads aligned with FastAPI routers.

## Documentation & Collaboration
- Follow AI_WorkSpace naming (`session_<timestamp>_<topic>.md`) for notes/plans/logs. Store new proposals under `AI_WorkSpace/DevDoc/On` until shipped, then archive.
- Before large UX/backbone shifts (new panes, tabs, or admin capabilities), produce/refresh a spec in `docs/ProjectDev` + AI_WorkSpace and reference `@/openspec/AGENTS.md`.
- Maintain bilingual strings (many sections already mix English + Simplified Chinese). When adding copy, mirror style or wire translations via `@/docs/ProjectDev`.

## Constraints & Tips
- `.env*` files may be read but not modified unless the user explicitly asks. Treat API tokens/bot secrets as operator-provided runtime data—never commit.
- Keep strict typing-by-convention: although the project is in plain JS, stores/services assume specific shapes. Use JSDoc typedefs if structure becomes complex.
- Prefer CSS tokens defined in `src/styles/tokens.css`; new components should reuse spacing/color variables for consistency.
- Ensure any new long-running subscriptions or timers (`setTimeout`, SSE) are cleaned up in `onBeforeUnmount`/`stopPolling` to avoid resource leaks in the SPA.
- When uncertain about backend expectations, inspect the matching FastAPI router in `Rise` and update both repos in lockstep.
