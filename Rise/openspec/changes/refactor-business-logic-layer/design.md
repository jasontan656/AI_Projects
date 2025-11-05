## Context

- Business Service layer currently contains `TelegramConversationService` (`src/business_service/conversation/telegram_service.py`) which orchestrates intent控制、代理调用与审计日志；这些编排职责按层级指南应迁移到 Business Logic，保留 Business Service 作为纯数据/集成提供者。
- Interface-level handlers (`src/interface_entry/telegram/handlers.py`) still manage retry loops, placeholder updates, and logging payload composition because no dedicated logic layer exists.
- Knowledge snapshot orchestration lives partly in `business_service/knowledge/snapshot_service.py` and partly in `interface_entry/bootstrap/app.py`, leaving policy decisions (e.g., Redis promotion) spread across layers.
- Reusing these flows outside Telegram (e.g., CLI batch jobs) would currently require directly instantiating Business Service classes and reimplementing orchestration code.

## Decisions

- **Create `business_logic` package**: scaffold `src/business_logic/__init__.py` with subpackages `conversation/` and `knowledge/` to host orchestration-centric classes, keeping dependencies limited to Business Service, foundational adapters, and utilities.
- **Conversation flow extraction**: move orchestration responsibilities（intent 路由、pipeline 节点策略、审计触发、流式组装）从 `TelegramConversationService` 挪至新的 `TelegramConversationFlow` 类，后者消费 Business Service 提供的瘦接口。
- **Service primitives refactor**: reshape `business_service.conversation` into composable helpers (`IntentClassifier`, `AgentDelegator`, `AdapterBuilder`) returning typed data that the logic layer sequences.
- **Knowledge orchestrator**: introduce `SnapshotOrchestrator` that coordinates snapshot loads/refreshes, redis sync status, and alert prompts while delegating IO to `KnowledgeSnapshotService`.
- **Interface integration**: adjust the FastAPI bootstrap and Telegram handler to depend on the logic layer, keeping transport code unchanged while ensuring the new abstractions remain async-friendly.
- **Testing strategy**: add logic-layer tests covering full conversation scenarios and knowledge refresh flows, while updating Business Service tests to target the refactored primitives.

## Open Questions

- Should streaming placeholder retries remain in the interface layer or move into the logic flow for consistency?
- Do we need a shared event/telemetry bus between logic and service layers to avoid duplicating logging payload assembly?
- How will future channels (e.g., email, WhatsApp) integrate—through channel-specific logic subclasses or shared strategy objects?
