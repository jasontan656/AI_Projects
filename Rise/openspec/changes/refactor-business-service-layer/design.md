## Context

- Business Service layer is currently absent; interface handlers directly coordinate prompts, classifications, and agents.
- Knowledge snapshot lifecycle (`behavior_memory_loader`, Redis sync, asset guard) lives in `foundational_service/integrations/memory_loader.py`, mixing business semantics with infrastructure.
- Telegram handler mixes channel plumbing with business rules (triage prompts, refusal logic, audit logging), making reuse by future channels/business flows difficult.
- We attempted to enumerate additional guidance via the `context 7` MCP server but it is unavailable in this environment; proceed using repo instructions only.

## Decisions

- **Service packages**: Introduce `business_service.conversation` and `business_service.knowledge` namespaces that expose explicit service classes and typed models. These modules import foundational services (`foundational_service.integrations.openai_bridge`, toolcalls) but are the highest layer owning domain orchestration.
- **Conversation API**: Implement `TelegramConversationService.process_update(update, policy)` that returns a `ConversationResult` dataclass/TyepdDict with envelopes, outbound contract, prompt info, agent metadata, and audit hints. The interface handler calls this and focuses on Telegram-specific IO (sending placeholders, retries).
- **Knowledge API**: Implement `KnowledgeSnapshotService.load()` and `.refresh(reason)` wrapping existing YAML/Redis flows, returning a `SnapshotResult` containing status, telemetry, and Redis metadata. Asset guard checks become methods in the same service.
- **Helpers relocation**: Move `_classify_intent`, direct prompt table, token budget defaults, and audit logging invocations to the conversation module. Only channel-specific adjustments remain in the interface layer.
- **File structure**: Adopt the layout described in the proposal’s target file tree, ensuring `__all__` exports from `business_service/__init__.py` present stable entry points for other layers.
- **Testing**: Introduce focused unit tests (or extend existing smoke tests) for the new services to protect refusal/prompt/agent paths and snapshot refresh scenarios, enabling future channels to reuse these services confidently.

## Open Questions

- Should knowledge snapshot service expose async APIs to align with future background refresh jobs? (Current plan keeps sync API; revisit if concurrency becomes necessary.)
- Do we need a shared business-level logger or can we continue relying on `project_utility` logging helpers? Decision pending once implementation starts.
- Are there additional domain capabilities (e.g., pricing calculators) that should move in this change, or can they wait for follow-up work after the base services land?
