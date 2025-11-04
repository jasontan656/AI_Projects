{{input.cached_state}}

command:
Compute semantic relevance between cached_state.user_prompt and {{input_KnowledgeBase_Dictionary}} entries.
Return the top relevant key-value pairs (dictionary entries) with score ≥ 0.5.
No prose. Strict JSON only.

output json:
{
  "session_id": "<uuid>",
  "response_id": "<string>",
  "categorySelection": {
    "candidates": {
      "key1": { "value": "description1", "score": 0.93 },
      "key2": { "value": "description2", "score": 0.82 },
      "key3": { "value": "description3", "score": 0.56 }
    }
  },
  "nextStep": "service_select_v1"
}

validation:
- session_id must match cached_state.session_id
- cached_state.agency_detect_v1.complexity must equal "low"
- categorySelection.candidates must contain ≥1 item
- every score >= 0.5
- output must be valid JSON (double-quoted keys)
- if any check fails → re-output corrected JSON with telemetry.notes briefly explaining why

[POST EXECUTION]

Offline orchestration will:
1. Parse JSON output.
2. Append minimal fields to cached_state.json:
   {
     "category_select_v1": {
       "candidates": {
         "key1": "description1",
         "key2": "description2",
         "key3": "description3"
       }
     },
     "nextStep": "service_select_v1"
   }
3. Persist the full JSON (with scores) into logs.
4. If no candidate above threshold, trigger semantic recheck or manual review.

4) If selected is empty, halt and route to manual fallback or semantic recheck.
