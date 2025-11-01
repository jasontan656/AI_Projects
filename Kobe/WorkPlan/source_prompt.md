
  You are coding inside the repo D:\AI_Projects\Kobe.

  Goal:
  - Implement the offline orchestrator modules for UnifiedCS.
  - Follow the workflow documented in WorkPlan/01.md (sections on stage contracts and “Offline
  Orchestrator Responsibilities”).
  - Use the prompt files under OpenaiAgents/CS_AgentContract as the stage definitions.

  Context:
  - Place all new Python modules under D:\AI_Projects\Kobe\OpenaiAgents\CS_AgentModule\modules\.
  - There is already a helper script SharedUtility/scripts/init_data_stores.py for MongoDB/Redis
  setup; reuse its conventions (chat_summaries, 20-entry window, Redis key `chat:{chat_id}:summary`,
  expiry 3600s).
  - The orchestrator must:
    1. Load cached_state.json (or bootstrap one).
    2. Warm up Redis from Mongo when a chat becomes active.
    3. Loop over stage_manifest.yaml and prompt files, calling OpenAI Responses API (store:true
  + previous_response_id).
    4. Validate each stage output with stage_runtime_contract.md.
    5. Merge stage outputs into cached_state, sync userChatContextSummary to Redis/Mongo, and respect
  guard-agent logic.
    6. Stop when nextStep == session_end, return the final assistant reply.
  - Keep the code modular (orchestrator.py, redis_mongo_store.py, kb_loader.py, guard_agent.py).

  Tasks:
  1. Create the modules listed above.
  2. Provide function-level docstrings that map back to the responsibilities described in
  WorkPlan/01.md.
  3. Include TODO comments where external integrations (actual OpenAI call, logging, etc.) should be
  plugged in.

 load these files:
  - WorkPlan/01.md
  - OpenaiAgents/CS_AgentContract/stage_manifest.yaml
  - OpenaiAgents/CS_AgentContract/prompt_*.md
  - stage_runtime_contract.md (same directory)

