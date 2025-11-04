## Context

- Business Service layer currently contains `TelegramConversationService` (`src/business_service/conversation/telegram_service.py`) which orchestrates prompt short-circuits, agent streaming, and audit logging—behaviour that belongs to the Business Logic layer per `openspec/PROJECT_STRUCTURE.md`.
- Interface-level handlers (`src/interface_entry/telegram/handlers.py`) still manage retry loops, placeholder updates, and logging payload composition because no dedicated logic layer exists.
- Knowledge snapshot orchestration lives partly in `business_service/knowledge/snapshot_service.py` and partly in `interface_entry/bootstrap/app.py`, leaving policy decisions (e.g., Redis promotion) spread across layers.
- Reusing these flows outside Telegram (e.g., CLI batch jobs) would currently require directly instantiating Business Service classes and reimplementing orchestration code.

## Decisions

- **Create `business_logic` package**: scaffold `src/business_logic/__init__.py` with subpackages `conversation/` and `knowledge/` to host orchestration-centric classes, keeping dependencies limited to Business Service, foundational adapters, and utilities.
- **Conversation flow extraction**: move orchestration responsibilities (prompt routing, audit triggers, streaming planning) from `TelegramConversationService` into a new `TelegramConversationFlow` class that consumes slimmer primitives provided by Business Service.
- **Service primitives refactor**: reshape `business_service.conversation` into composable helpers (`IntentClassifier`, `AgentDelegator`, `AdapterBuilder`) returning typed data that the logic layer sequences.
- **Knowledge orchestrator**: introduce `SnapshotOrchestrator` that coordinates snapshot loads/refreshes, redis sync status, and alert prompts while delegating IO to `KnowledgeSnapshotService`.
- **Interface integration**: adjust the FastAPI bootstrap and Telegram handler to depend on the logic layer, keeping transport code unchanged while ensuring the new abstractions remain async-friendly.
- **Testing strategy**: add logic-layer tests covering full conversation scenarios and knowledge refresh flows, while updating Business Service tests to target the refactored primitives.

## Open Questions

- Should streaming placeholder retries remain in the interface layer or move into the logic flow for consistency?
- Do we need a shared event/telemetry bus between logic and service layers to avoid duplicating logging payload assembly?
- How will future channels (e.g., email, WhatsApp) integrate—through channel-specific logic subclasses or shared strategy objects?
