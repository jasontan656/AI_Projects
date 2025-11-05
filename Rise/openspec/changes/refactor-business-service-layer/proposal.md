## Why

- Business-service responsibilities are scattered across `interface_entry/telegram/handlers.py`, `interface_entry/bootstrap/app.py`, and `foundational_service/integrations/memory_loader.py`, leaving the Business Service layer undefined and violating the layering guide in `openspec/PROJECT_STRUCTURE.md`.
- Domain-aware behaviours（intent classification、会话审计、知识快照编排）散落在 interface/foundational 模块，历史 Prompt shortcut 亦埋在 handler 中，阻碍其他渠道或新业务逻辑复用。
- Without a converged package, downstream refactors (e.g., adding WhatsApp ingress or batch knowledge refresh) must duplicate logic and risk inconsistent policy handling.

## What Changes

- Introduce a dedicated `src/business_service/` package that depends on foundational/utility layers but is the single entry point for domain-specific orchestration.
- Split the package into two initial domains:
  - `business_service.conversation.telegram_service`: wraps message classification、pipeline 节点解析、LLM 请求与适配器准备，暴露 `TelegramConversationService` API 返回 typed `ConversationResult`（不再包含 prompt shortcut）。
  - `business_service.knowledge.snapshot_service`: owns knowledge snapshot loading, Redis synchronisation, and refresh flows exposed through a `KnowledgeSnapshotService`.
- Move business-specific helpers out of interface/foundational files:
  - Extract `_classify_intent`, `process_update`, and related helpers from `interface_entry/telegram/handlers.py` into the conversation service.
  - Relocate `behavior_memory_loader`, `behavior_asset_guard`, and `behavior_kb_pipeline` from `foundational_service/integrations/memory_loader.py` into the knowledge service while keeping Redis/file IO abstractions intact.
  - Rehome audit hooks currently accessed directly via `foundational_service.contracts.toolcalls` into thin adapters consumed by the new services，并删除遗留 prompt shortcut 调用。
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
- Regression risk sits around conversation flow（拒绝链路、LLM 响应整形）与知识快照可用性；任务列表要求以 smoke tests 覆盖这些行为。
