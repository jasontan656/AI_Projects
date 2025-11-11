# Rise + Up Violation Alignment Tech Stack Summary (session_20251112_0125)

## Background & Scope
- Derived from `AI_WorkSpace/Requirements/session_20251112_0014_violation_alignment.md` and companion notes; focuses on rectifying four violation scenarios (S1–S4) without changing external behavior.
- Scope spans Rise backend (`interface_entry`, `business_logic`, `business_service`, `foundational_service`) and Up admin frontend (`src/stores`, `src/services`, `src/composables`, `src/views`).
- Primary goals: enforce Clean Architecture layering, keep orchestration out of entry points, split Pinia stores into state vs. effects, and preserve telemetry/audit guarantees demanded by Philippine government channels.

## Tech Stack Overview
### Rise Backend
- FastAPI 0.118.x for HTTP/webhook surface; async dependency injection with `Depends`, lifespan hooks for resource sharing, and background startup/shutdown events for aiogram runtime.
- aiogram 3.22.0 for Telegram webhook dispatch; runtime containerized through `interface_entry/telegram/runtime` with orchestrator delegation only.
- OpenAI Python SDK 1.105.0 powering staged reasoning via `foundational_service.integrations.openai_bridge`.
- Redis 7.x via `redis-py 6.4.0` for chat summaries, queue health, and throttle counters; MongoDB 7.x via `pymongo 4.6.x` for durable chat history and audit trails.
- aio-pika / RabbitMQ for async task routing; telemetry wired with Rich 13.x + custom event bus.

### Up Admin (Vue Repository `D:\AI_Projects\Up`)
- Vue 3 + Vite 5 entry, Element Plus UI, Vue Flow for workflow canvas.
- Pinia stores restricted to state/getters; API orchestration moved to `src/services/*.js`, controllers/composables handle side effects (SSE, polling, debounced submissions).
- HTTP client shared through `src/services/httpClient.js`, injecting operator identity headers required by backend audits.

### Shared Infra & Observability
- Environment variables remain in `.env`; new logical keys (`WORKFLOW_SUMMARY_TTL_SECONDS`, `CHANNEL_HEALTH_POLL_INTERVAL_MS`, `TELEGRAM_RUNTIME_MODE`) declared but not yet populated.
- Telemetry bus continues to emit `workflow.stage`, `workflow.summary.persisted`, `channel.health.snapshot`, `workflow.builder.publish`; audit sink in Mongo preserved.

## Module/File Change Matrix
| Scenario | Modules / Paths | Change Type | Notes |
| --- | --- | --- | --- |
| S1 Workflow execution & summary persistence | `src/business_logic/workflow/orchestrator.py`, new `src/business_logic/workflow/models.py`, new `src/foundational_service/persist/workflow_summary_repository.py`, `src/project_utility/db` consumers | Refactor + Add | Move dataclasses to `models.py`; orchestrator now depends on repository interface injected via FastAPI DI; repository fronts Redis/Mongo writes with telemetry hooks.
| S2 Telegram entry decoupling | `src/business_service/conversation/service.py`, new `src/business_service/conversation/config.py`, `runtime_gateway.py`, `health.py`, `interface_entry/bootstrap/application_builder.py`, `interface_entry/runtime/supervisors.py` | Split + Add | Service only orchestrates inbound→orchestrator→outbound; config/runtime/health modules expose typed dataclasses and factories; bootstrap wires them via DI per channel binding.
| S3 Channel policy binding & health polling | `D:\AI_Projects\Up\src\stores\channelPolicy.js`, new `src/services/channelPolicyClient.js`, `src/services/channelHealthScheduler.js`, `src/schemas/channelPolicy.js`; backend `business_service/channel/health_store.py`, `interface_entry/http/channels.py` | Add + Modify | Store trimmed to state/getters; scheduler handles debounced polls + cooling windows; backend exposes REST endpoints for health snapshots consumed by scheduler.
| S4 Workflow Builder controller | `D:\AI_Projects\Up\src\views\WorkflowBuilder.vue`, new `src/composables/useWorkflowBuilderController.js`, updates to `src/stores/workflowDraft.js`, `src/services/workflowService.js`, SSE wiring in `src/services/pipelineService.js` | Add + Modify | Controller/composable manages loading/saving/publishing, ensures SSE/interval cleanup on route leave, store reduced to pure state transitions.

## Function & Interface Summary
### S1 – Workflow persistence
- `WorkflowOrchestrator.execute(context)` (existing) → now consumes `WorkflowSummaryRepository` interface, focuses on stage sequencing and telemetry only.
- `WorkflowSummaryRepository.append_summary(chat_id, summary_entry)` (new) enforces Redis list (max 20, TTL from env) and Mongo `$push` with `$slice`; emits `workflow.summary.persisted`.
- `WorkflowExecutionContext` dataclass relocates to `business_logic/workflow/models.py`; sanitized helpers keep telemetry metadata separate from persistence payloads.

### S2 – Telegram entry decoupling
- `TelegramConversationService.handle_update(update)` retains orchestrator invocation but delegates:
  - `TelegramEntryConfig` dataclass (new) provides sync/async mode, localization strings, failure fallbacks.
  - `RuntimeGateway.dispatch(update, mode)` (new) chooses sync vs. queue-backed async using `TaskRuntime` dependency only.
  - `ChannelHealthReporter.record(update, status)` (new) writes Redis health keys, publishes telemetry.
- `interface_entry/bootstrap/application_builder.py` limits itself to DI graph assembly; runtime supervisors move to `interface_entry/runtime/supervisors.py` with bounded responsibilities.

### S3 – Channel policy & health
- `channelPolicyClient.save(policyPayload)` (new service) centralizes schema validation + HTTP calls; store actions call this service only.
- `channelHealthScheduler.start(workflowId)` (new) drives polling intervals, enforces `policy.cooldown`, and writes statuses into store via callbacks.
- Backend `ChannelBindingHealthStore.snapshot(channel_id)` exposes policy-aware health documents for UI consumption.

### S4 – Workflow Builder coordination
- `useWorkflowBuilderController(workflowId)` (new composable) orchestrates `workflowDraft` store, policy scheduler hooks, SSE subscription (through `pipelineService.subscribeToLogs`).
- Controller exposes `loadWorkflow`, `saveDraft`, `publishWorkflow`, `teardown` guarantees; views bind to these APIs only, ensuring view remains declarative.

## Best Practices & Guidelines
- FastAPI dependency injection keeps services/repositories isolated from routes; leverage `Depends()` + lifespan cleanup as outlined in FastAPI 0.118.2 docs for consistent resource ownership. [Context7: /fastapi/fastapi/0.118.2]
- Pinia stores should focus on state/getters while complex effects move to services/composables; store composition and cross-store access follow official guidance to avoid reactivity pitfalls. [Context7: /vuejs/pinia]
- Adopt layered architecture + DI on FastAPI per community patterns: routes → services → repositories with contracts, plus repository pattern for persistence boundaries. [Exa: Layered Architecture & Dependency Injection, 2025-05-29]
- Pinia service separation and scheduler orchestration reference community case studies emphasizing modular stores and composition for scalability. [Exa: StudyRaid "Build Scalable Vue.js Apps with Pinia", 2025-01-16]

## File & Repo Actions
- **Rise**
  - Create `src/business_logic/workflow/models.py` (dataclasses, policy metadata helpers).
  - Create `src/foundational_service/persist/workflow_summary_repository.py`; register in DI container; update `project_utility/db` consumers to use repository.
  - Split `src/business_service/conversation/service.py` into `config.py`, `runtime_gateway.py`, `health.py`; update service import graph and aiogram bootstrap wiring.
  - Move runtime/logging bootstrap helpers from `interface_entry/bootstrap/application_builder.py` into `interface_entry/bootstrap/runtime_lifespan.py`, `interface_entry/runtime/supervisors.py`, `project_utility/logging.py` as needed.
- **Up**
  - Add schema modules under `src/schemas` for workflow drafts & channel policy payloads; ensure stores import from schemas only.
  - Add services `channelPolicyClient.js`, `channelHealthScheduler.js`, `workflowDraftService.js`, `pipelineSseClient.js` (if SSE abstraction missing) to isolate network traffic.
  - Add composable `src/composables/useWorkflowBuilderController.js` and update views to rely exclusively on controller APIs.
  - Relocate throttling/telemetry glue from stores to services/composables; stores expose plain actions for state mutation.

## Risks & Constraints
- **Redis/Mongo availability**: persistence repository must degrade gracefully—Redis failures logged but not blocking HTTP path; Mongo outages trigger retry/backoff and operator alert.
- **Telegram mode drift**: misconfigured `mode` could desync runtime; enforce enum validation in `TelegramEntryConfig` + default fallback to sync.
- **Scheduler over-polling**: Channel health polling must respect cooldown + exponential backoff to avoid rate limits; expose interval via env var.
- **SSE resource leaks**: Workflow Builder controller must dispose SSE streams on route leave to prevent orphan listeners; enforce via `teardown` hook and `onBeforeRouteLeave` guard.
- **Audit requirements**: All policy changes must still produce `AUDIT channel_policy_change` Mongo entries; stores/services need to keep operator metadata on each request.

## Implementation Decisions
1. `WorkflowSummaryRepository` is the single persistence surface for chat summaries; orchestration and services receive it through DI with shared lifespan to reuse Redis/Mongo clients.
2. Telegram entry remains aiogram-based but uses `RuntimeGateway` to decide sync vs. async modes; async path returns ack handles with localized strings defined in config dataclasses.
3. Channel policy editing honors schema-first validation (Yup/Zod equivalent) before any network call; cooldown defaults to 180s unless backend signals override.
4. Workflow Builder interactions flow through `useWorkflowBuilderController`; views never manipulate stores directly, ensuring all side effects pass through controller methods for observability.
5. Scheduler/service modules publish telemetry via existing `/interface_entry/http` endpoints only; no direct Redis usage from frontend code.
