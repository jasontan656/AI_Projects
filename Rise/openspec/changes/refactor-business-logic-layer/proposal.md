## Why

- The Business Logic layer defined in `openspec/PROJECT_STRUCTURE.md` is absent: end-to-end flows (Telegram conversation handling, knowledge refresh) still live inside interface handlers and Business Service modules such as `src/business_service/conversation/telegram_service.py`.
- Business Service code currently mixes orchestration with service primitives, making it difficult to reuse the same flows for alternative channels or batch jobs without duplicating logic.
- Without a clear Business Logic package, future workflow-focused features (e.g., proactive reminders, multi-channel rollout) have no home and will continue to bloat the interface layer.
- Attempted to load additional guidance from the `context 7` MCP server but it is unavailable in this environment; proceeding with in-repo conventions only.

## What Changes

- Introduce a dedicated `src/business_logic/` package that owns conversation workflows and runtime coordination while delegating heavy lifting to Business Service modules.
- Split the current `TelegramConversationService` so that:
  - `business_logic.conversation.TelegramConversationFlow` orchestrates prompt selection, agent hand-offs, streaming cadence, and audit logging.
  - `business_service.conversation` is slimmed to reusable primitives (intent classification, agent dispatch, adapter shaping) with clear Typeddict outputs.
- Establish a Business Logic module for knowledge maintenance (`business_logic.knowledge.SnapshotOrchestrator`) that coordinates refresh scheduling, Redis promotion, and alerting while relying on the existing `KnowledgeSnapshotService` for IO.
- Update interface entrypoints (`interface_entry/telegram/handlers.py`, `interface_entry/bootstrap/app.py`) to invoke the new logic layer, leaving them responsible only for transport concerns (HTTP/Telegram bindings).
- Provide typed contracts and factories so downstream flows (e.g., future CLI jobs) can share the same logic orchestrators.

## Impact

- Requires new package scaffolding and extensive refactors of recently introduced business_service modules; downstream imports in interface/foundational layers must be updated.
- Business Service unit tests need to be rewritten to target the slimmed primitives, while new Business Logic tests cover orchestration scenarios.
- Potential to uncover coupling assumptions (e.g., direct references to aiogram state) that must be abstracted via the new logic layer.
- Medium coordination risk: work should proceed incrementally (service extraction before logic adoption) to avoid breaking the Telegram handler during the transition.
