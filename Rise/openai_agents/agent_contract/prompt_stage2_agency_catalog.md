{{input.cached_state}}

command:
Identify which government agency/agencies are relevant to the user inquiry stored in cached_state.
Determine complexity level and decide the next execution step.
Return strict JSON. Do not include natural language or commentary.

output json:
{
  "session_id": "<uuid>",
  "response_id": "<string>",
  "judgements": {
    "agencyDetected": ["agencyId"],
    "agencyInfo": [
      { "agencyId": "string", "name": "string", "path": "string", "description": "string" }
    ],
    "complexity": "low | high",
    "agencyCount": "integer",
    "nextStep": "category_select_v1 | semantic_analysis_v1 | session_end"
  }
}

validation:
- session_id must match cached_state.session_id
- response_id must not be null or empty
- if validation fails → re-output corrected JSON
- output must be valid JSON (double-quoted keys)

[POST EXECUTION]

Offline orchestration will:
1. Parse the JSON result.
2. Extract fields for cached_state update:
   ```json
   {
     "agency_detect_v1": {
       "agencyDetected": ["agencyId"],
       "agencyInfo": [
         { "agencyId": "string", "name": "string", "path": "string", "description": "string" }
       ],
       "agencyCount": <integer>,
       "complexity": "low | high"
     },
     "nextStep": "category_select_v1 | semantic_analysis_v1"
   }
Append this data to cached_state.json.

Validate session consistency (session_id check).

If complexity == "low" → load next Stage Execution Contract category_select_v1.
If complexity == "high" → load next Stage Execution Contract semantic_analysis_v1.

Store full JSON output (for log) and update minimal cached state for runtime injection.


