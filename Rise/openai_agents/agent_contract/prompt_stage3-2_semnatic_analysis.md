{{input.cached_state}}

command:
For each agency listed in semanticAnalysis.agencies,
perform progressive semantic search of the user inquiry across that agency’s service index ({{input_service_index}}).
1. Within each agency:
   - Search "key" field first.
     - If a direct hit found with confidence ≥ 0.80, accept and include.
     - If confidence < 0.80, continue to search "name" to confirm.
     - If still below 0.80, continue searching "overview" → "applicability_summary".
   - Collect all qualified services (score ≥ 0.80) with their key/value fragments.
2. Using all previously selected agencies/services and cached snippets,
   - compose the final user-facing answer in the appropriate length:
     - If the user only asked for a specific detail (e.g., price), keep it short.
     - If the user needs guidance, provide a concise, structured explanation.
Return strict JSON only; no prose outside the JSON.

output json:
{
  "session_id": "<uuid>",
  "response_id": "<string>",
  "userChatContextSummary": [
    {
      "userPromptSummary": "string",
      "assistantReplySummary": "string",
      "timestamp": "YYYY-MM-DDTHH:MM:SSZ"
    }
  ],
  "assistantReply": "string",
  "sourcesUsed": [
    { "agencyId": "string", "serviceKey": "string", "path": "string" }
  ],
  "nextStep": "session_end"
}

validation:
- session_id must match cached_state.session_id
- userChatContextSummary must contain ≤20 items formatted as above (latest entry first)
- assistantReply must be non-empty
- output must be valid JSON (double-quoted keys)
- if validation fails → re-output corrected JSON 
