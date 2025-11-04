## Why
Business Service modules (`conversation` and `knowledge`) have drifted from the layering guidance in `openspec/PROJECT_STRUCTURE.md`. Conversation helpers mix transport-facing adapter policy, agent dispatch, and prompt glue without a cohesive service contract, while Knowledge snapshot utilities embed asset scanning, Redis publication, and telemetry shaping inside a single class. During repository review we located these responsibilities in:
- `src/business_service/conversation/primitives.py` (intent heuristics, prompt rendering, adapter writes)
- `src/business_service/knowledge/snapshot_service.py` (asset reads, Redis sync, pipeline tooling)
- `src/business_logic/` consumers that now depend on ad hoc dictionaries without typed contracts.
This fragmentation makes it hard to rewrite Business Service code to respect Business Asset boundaries (e.g., `KnowledgeBase/` layouts) and to provide consistent APIs for Business Logic orchestration.

## What Changes
- Define cohesive Business Service capabilities for Conversation and Knowledge domains, including typed request/response models, explicit asset boundaries, and clear ownership of Redis/prompt integration.
- Introduce a new internal file structure under `src/business_service/` that separates adapters, repositories, and service facades so that Business Asset interactions are centralized.
- Capture service responsibilities in updated capability specs to guide the upcoming rewrite, including required telemetry fields, safety gating hooks, and Redis publish semantics.
- Document the refactor plan and sequencing in a design brief covering module layout, dependency flow, and progressive migration checkpoints.

## Impact
- Provides an authoritative specification for rewriting the Business Service layer in manageable increments.
- Aligns Business Service contracts with Business Asset expectations, reducing duplication across Business Logic and future channels.
- De-risks the rewrite by enumerating telemetry, safety, and publication behaviors before implementation work begins.
