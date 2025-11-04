{{input.cached_state}}

command:
For each agency listed 
compute semantic relevance between cached_state.user_prompt and each agency’s dictionary ({{input_KnowledgeBase_Dictionary}}).
Select key-value pairs (dictionary entries) whose score ≥ 0.50.
Scores must be computed separately per agency, as user intent may differ by context.
Return strict JSON only; no prose.

output json:
{
  "session_id": "<uuid>",
  "response_id": "<string>",

  "semanticAnalysis": {
    "agencies": [
      {
        "agencyId": "string",
        "agencyName": "string",
        "categorySelection": {
          "candidates": {
            "key1": { "value": "description1", "score": 0.92 },
            "key2": { "value": "description2", "score": 0.77 }
          }
        }
      },
      {
        "agencyId": "string",
        "agencyName": "string",
        "categorySelection": {
          "candidates": {
            "key1": { "value": "descriptionA", "score": 0.64 }
          }
        }
      }
    ],
    "primaryAgency": {
      "agencyId": "string",
      "reason": "highest cumulative key relevance"
    }
  },

  "nextStep": "service_select_v1"
}

validation:
- session_id must match cached_state.session_id
- cached_state.agency_detect_v1.complexity must equal "high"
- semanticAnalysis.agencies.length >= 2
- each agency must include ≥1 candidate with score ≥ 0.50
- output must be valid JSON (double-quoted keys)
- if validation fails → re-output corrected JSON 
