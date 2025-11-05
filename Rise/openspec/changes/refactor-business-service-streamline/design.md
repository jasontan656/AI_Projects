## Overview
The Business Service layer must mediate between Business Logic orchestrators and Business Asset content (knowledge base, prompts) using reusable, typed APIs. Repository review shows two major domains:
- `src/business_service/conversation/primitives.py` combines intent heuristics, legacy prompt rendering logic, agent bridge dispatch, and Telegram adapter shaping.
- `src/business_service/knowledge/snapshot_service.py` embeds asset scanning (`KnowledgeBase/`), Redis synchronization, telemetry, and CI tooling in a single class.
The refactor rewrites these modules into cohesive services that expose explicit contracts to Business Logic while delegating asset IO and external integrations to dedicated collaborators.

## Current Findings
- Conversation helpers return loose dictionaries consumed directly by `TelegramConversationFlow`; missing typed aliases for bridge telemetry, chunk metrics, and outbound payloads.
- Adapter helpers mutate inbound/outbound contracts in place, crossing layering guidance by assuming Telegram-specific transport fields.
- Knowledge snapshot service performs filesystem and Redis duties without abstractions, complicating testing and reuse.
- Business Asset interactions (loading `KnowledgeBase/*_index.yaml`) occur directly inside Business Service without validation hooks.

## Target Architecture
1. **Conversation Service Facade** (`ConversationService`): exposes
   - `classify_intent(message: str) -> IntentClassification`
   - `resolve_pipeline_node(update, policy) -> PipelineNode | None`
   - `build_llm_request(context, pipeline_node=None) -> AgentRequest`
   - `dispatch_agent(payload: AgentRequest) -> AgentDispatchResult`
   - `build_adapter_contract(context: AdapterContext, outbound: AgentDispatchResult) -> TelegramAdapterContract`
   Each方法输出 typed dataclass，明确 telemetry、安全标记及流式元数据；若收到 legacy prompt 信号则应直接拒绝。
2. **Knowledge Snapshot Facade** (`KnowledgeSnapshotFacade`): orchestrates
   - Asset repository access via `KnowledgeAssetRepository` (reads Business Asset layer paths, performs checksum/metadata extraction).
   - Cache publication via `SnapshotPublisher` (Redis optional; pluggable backend).
   - Health reporting via structured dataclasses aligned with Business Logic expectations.
3. **Shared Utilities**
   - `business_service/common/telemetry.py` for stage tracking.
   - `business_service/common/types.py` for reusable protocols.

## Proposed File Structure
```
src/business_service/
  __init__.py
  common/
    __init__.py
    telemetry.py
    types.py
  conversation/
    __init__.py
    models.py
    intent_classifier.py
    prompt_service.py
    agent_gateway.py
    adapter_service.py
    service.py
  knowledge/
    __init__.py
    models.py
    asset_repository.py
    checksum.py
    snapshot_publisher.py
    snapshot_service.py
```
- `service.py` modules export the high-level facades consumed by Business Logic.
- Lower-level modules hide integrations, providing small units for testing.

## Migration Plan
1. **Phase 1 – Parallel Implementations**
   - Implement new dataclasses and facades alongside existing primitives.
   - Add adapter compatibility wrappers to keep Business Logic untouched during transition.
2. **Phase 2 – Business Logic Cutover**
   - Update `TelegramConversationFlow` and `KnowledgeSnapshotOrchestrator` to consume the new facades.
   - Remove deprecated primitive exports once Business Logic is migrated.
3. **Phase 3 – Cleanup & Validation**
   - Delete legacy modules and re-export only the new service facades from `business_service/__init__.py`.
   - Add targeted integration checks（如 Redis sync smoke、pipeline 节点与 prompt 持久化互操作测试）放在 `tests/business_service/`。

## Business Asset Integration
- `KnowledgeAssetRepository` encapsulates filesystem layout defined by the Business Asset layer (`KnowledgeBase/` directories, index files) and exposes safe accessors without leaking path logic to Business Logic.
- `prompt_service.py` centralizes prompt persistence and validation against Mongo-backed records authored by the front-end workflow builder, keeping any Markdown/prompt composition concerns within Business Service rather than hard-coded registries.
- Snapshot publisher metadata structure aligns with Business Asset governance by recording checksum, missing agencies, and publish reason for audit trails.

## Open Questions
- Should Redis publication support multiple namespaces for staging/production? (Default to single prefix; extendable via configuration.)
- Do we need additional spec coverage for CI-only helpers (`pipeline_check`)? Potentially move to one-off utilities if out of scope for Business Service contracts.
