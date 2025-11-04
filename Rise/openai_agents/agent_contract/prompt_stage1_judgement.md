───────────────────────────────────────────────────────────────────────────────
[EXECUTION CONTEXT]

Input Fields:
- user_prompt: {{input.user_prompt}}
- chat_context_summary: {{input.chat_context_summary}}

───────────────────────────────────────────────────────────────────────────────
[OUTPUT SCHEMA]

{
  "stage": "judgement_v1",
  "stageStatus": "ready",
  "judgements": {
    "inquiry": true | false
  },
  "assistantReply": "string | null",
  "nextStep": "agency_detect_v1 | session_end",
  "telemetry": {
    "notes": "string | null"
  }
}

───────────────────────────────────────────────────────────────────────────────
[EXECUTION RULES]

1. Classification:
   - If user_prompt concerns Philippine government services (visa, permits, immigration, etc.), set judgements.inquiry = true.
   - Otherwise set judgements.inquiry = false.

2. Branch Handling:
   - inquiry = true:
       assistantReply = null
       nextStep = "agency_detect_v1"
       telemetry.notes = null
   - inquiry = false:
       assistantReply = generated assistant reply.
       nextStep = "session_end"
       telemetry.notes = "non-inquiry or smalltalk detected"

3. Ambiguous or irrelevant prompts default to inquiry=false with rationale in telemetry.notes.

4. Output Requirements:
   - Output must match the JSON schema exactly.
   - No extra commentary, markdown, or natural language.
   - stageStatus="ready" by default.

