{{input.cached_state}}

command:
Perform progressive semantic search of the user inquiry.
1. Search "key" field in {{input_service_index}} first.
   - If a direct hit found with confidence ≥ 0.50, pick highest score, accept and stop.
   - If confidence < 0.50, continue to search "name" to confirm.
   - If still below 0.50, continue searching "overview" → "applicability_summary".
   - Always select exactly one best match (highest score with 2-decimal precision).

2. After serviceKey is decided:
   - Read internal service keys from cached_state (previously loaded from agency files).
   - Dynamically generate a reply-template skeleton.
     The template must be built using the service keys as placeholders and arranged
     according to semantic relevance, not a fixed order.
     Example rule: start with service identification, then required_docs, price, cautions, faq, etc.
Return strict JSON only; no prose or reasoning text.

output json:
{
  "session_id": "<uuid>",
  "response_id": "<string>",
  "userChatContextSummary": [
    {
      "userPromptSummary": "string",
      "assistantReplySummary": "string | null",
      "timestamp": "YYYY-MM-DDTHH:MM:SSZ"
    }
  ],
  "serviceSelection": {
    "serviceKey": "string",
    "name": "string",
    "path": "string",
    "matchedField": "key | name | overview | applicability_summary",
    "score": 0.00
  },
  "template": {
    "placeholders": {
      "<dynamic_key_1>": "{<dynamic_key_1>}",
      "<dynamic_key_2>": "{<dynamic_key_2>}"
      // dynamically populated from cached_state service keys
    },
    "rules": "Arrange placeholders contextually. Generate reply sentences dynamically according to available keys."
  },
  "nextStep": "session_end"
}

validation:
- session_id must match cached_state.session_id
- userChatContextSummary must contain ≤20 items formatted as above (latest entry first)
- serviceSelection.serviceKey must exist (exactly one)
- serviceSelection.score must be ≥ 0.50 and reported with 2-decimal precision
- template.placeholders must contain ≥1 key loaded from cached_state
- output must be valid JSON (double-quoted keys)
- if validation fails → re-output corrected JSON with telemetry.notes briefly explaining reason
