## Overview
Simplify Telegram message handling to match the new direct-LLM flow and delete prompt/streaming leftovers.

## Key Decisions
1. **Conversation Result Model** — Reduce to fields actually produced by `TelegramConversationService`. Clients expecting triage/bridge metadata intentionally receive nothing.
2. **Handler Rewrite** — Replace streaming/placeholder logic with a single send path; metrics/log payloads drop chunk fields.
3. **Prompt Registry Removal** — `BehaviorContract` no longer injects `PROMPT_REGISTRY`; specs should reflect prompt-less architecture.
4. **Bridge Signature** — `behavior_agents_bridge` takes `prompt`, optional `history`, `tokens_budget`, `model`; no repo root.

## Risks / Mitigations
- Downstream code referencing removed fields will fail fast (desired). Run tests/startup to ensure no lingering references.
- If future streaming is required, reintroduce via explicit feature flag rather than hidden branch.
