## Why

- Business-service responsibilities are scattered across `interface_entry/telegram/handlers.py`, `interface_entry/bootstrap/app.py`, and `foundational_service/integrations/memory_loader.py`, leaving the Business Service layer undefined and violating the layering guide in `openspec/PROJECT_STRUCTURE.md`.
- Domain-aware behaviours (intent classification, prompt short-circuiting, knowledge snapshot orchestration) currently live in interface/foundational modules, making reuse by other channels or future business logic impossible.
- Without a converged package, downstream refactors (e.g., adding WhatsApp ingress or batch knowledge refresh) must duplicate logic and risk inconsistent policy handling.

## What Changes

- Introduce a dedicated `src/business_service/` package that depends on foundational/utility layers but is the single entry point for domain-specific orchestration.
- Split the package into two initial domains:
  - `business_service.conversation.telegram_service`: wraps message classification, prompt selection, agent orchestration, and adapter preparation behind a `TelegramConversationService` API that returns a typed `ConversationResult`.
  - `business_service.knowledge.snapshot_service`: owns knowledge snapshot loading, Redis synchronisation, and refresh flows exposed through a `KnowledgeSnapshotService`.
- Move business-specific helpers out of interface/foundational files:
  - Extract `_classify_intent`, `process_update`, and related helpers from `interface_entry/telegram/handlers.py` into the conversation service.
  - Relocate `behavior_memory_loader`, `behavior_asset_guard`, and `behavior_kb_pipeline` from `foundational_service/integrations/memory_loader.py` into the knowledge service while keeping Redis/file IO abstractions intact.
  - Rehome audit/prompt shortcuts currently accessed directly via `foundational_service.contracts.toolcalls` into thin adapters consumed by the new services.
- Update interface bootstrap and handlers to depend on the services instead of raw helper functions, ensuring Business Logic layer (future work) can build on the same APIs.
- Provide doctypes/TypedDicts in the business package so the interface layer consumes strongly typed results without duplicating schema knowledge.

### Target File Layout

```
src/business_service/
├── __init__.py
├── conversation/
│   ├── __init__.py
│   ├── models.py              # ConversationResult, PromptSpec, AgentInvocation
│   └── telegram_service.py    # TelegramConversationService.process_update(...)
└── knowledge/
    ├── __init__.py
    ├── snapshot_service.py    # KnowledgeSnapshotService.load/refresh, asset guard
    └── models.py              # SnapshotResult, SnapshotStatus, AssetGuardReport
```

## Impact

- Interface layer (`src/interface_entry/telegram/handlers.py`, `src/interface_entry/bootstrap/app.py`) must be rewritten to call the new services; expect significant but mechanical updates.
- Foundational layer loses business-specific helpers, tightening its scope to infrastructure; imports will shift to the new package.
- Requires new shim exports/testing patterns so existing FastAPI bootstrap and aiogram runtime keep working while the service code moves.
- Regression risk sits around conversation flow (prompt short-circuits, refusal handling) and knowledge snapshot availability; the tasks call for dedicated smoke tests to cover these behaviours.
