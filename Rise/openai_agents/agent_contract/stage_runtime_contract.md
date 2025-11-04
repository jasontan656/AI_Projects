# Stage Runtime Contract (v2)

This contract defines how the orchestrator assembles runtime payloads for every stage, and how each
stage must respond. All prompts share the cached **Base System Persona Block** (`store: true`). A
stage-specific directive is appended on top of a user block populated with the inputs listed below.

---

## Shared Runtime Conventions

1. **Strict JSON output.** The model must return a single JSON object using double-quoted keys and
   UTF-8 text. No Markdown or explanatory prose is allowed.
2. **`session_id` / `response_id`.** Stages that read from `cached_state.session_id` must echo the
   same `session_id` in their JSON response and provide a new `response_id`. Stages whose prompts do
   not mention these fields must omit them.
3. **Score precision.** Confidence or relevance scores must keep two decimal places (for example
   `0.87`).
4. **Telemetry on failure.** If any validation check fails, the model immediately re-issues the JSON
   with a `"telemetry": {"notes": "<reason>"}` block describing the fix.
5. **State merge.** The orchestrator persists only the fields defined under “State Merge” for each
   stage into `cached_state`.

---

## Shared Input Slots

| Placeholder                        | Description                                                                 |
|-----------------------------------|-----------------------------------------------------------------------------|
| `{{input.user_prompt}}`           | Latest user utterance.                                                      |
| `{{input.chat_context_summary}}`  | Optional summary of earlier turns (≤20 items).                             |
| `{{input.cached_state}}`          | Aggregated JSON of prior stage outputs, keyed by stage ID.                  |
| `{{input.runtime_directive}}`     | Optional external instruction injected by offline tooling.                  |
| `{{input.KnowledgeBase_Dictionary}}` | Per-agency dictionary used by category/semantic analysis stages.          |
| `{{input.service_index}}`         | Service index for the currently selected agency (key, name, overview, etc). |

---

## Stage Topology

| Order | Stage ID                        | Prompt File                          | Purpose Summary                                               |
|-------|---------------------------------|--------------------------------------|---------------------------------------------------------------|
| 0     | `base_system`                   | `prompt_base_system.md`              | Injects persona & global policy (no model invocation).        |
| 1     | `judgement_v1`                  | `prompt_stage1_judgement.md`         | Classifies valid inquiry vs. small talk.                      |
| 2     | `agency_detect_v1`              | `prompt_stage2_agency_catalog.md`    | Selects agencies and complexity branch.                       |
| 3a    | `category_select_v1` (low)      | `prompt_stage3-1_templatefill.md`    | Picks dictionary categories for low-complexity flow.          |
| 3b    | `semantic_analysis_v1` (high)   | `prompt_stege3-1_semantic_analysis.md` | Scores categories per agency and picks a primary agency.    |
| 4     | `service_select_v1`             | `prompt_stage3-2_templatefill.md`    | Chooses target service and drafts template skeleton.          |
| 5*    | `multi_agency_service_answer_v1`| `prompt_stage3-2_semnatic_analysis.md` | Synthesises final answer when multiple agencies are needed. |
| End   | `session_end`                   | –                                    | Terminates workflow (no prompt file).                         |

\*Invoked when the orchestrator detects high-complexity multi-agency requirements.

---

## Stage Contracts

### Stage: base_system

- **Purpose:** Provides persona, tone, safety rails, and global constraints. Executed once with
  `store: true`; no model call is issued.
- **Inputs:** None (static system prompt).
- **Expected Output:** None. Orchestrator proceeds directly to `judgement_v1`.
- **State Merge:** Not applicable.

---

### Stage: judgement_v1

- **Purpose:** Decide whether the current turn is a government-service inquiry and, if not, respond
  with guidance.
- **Inputs:** `user_prompt`, `chat_context_summary` (optional).
- **Expected Output:**

  ```json
  {
    "stage": "judgement_v1",
    "stageStatus": "ready",
    "judgements": {"inquiry": true | false},
    "assistantReply": "string | null",
    "nextStep": "agency_detect_v1 | session_end",
    "telemetry": {"notes": "string | null"}
  }
  ```

- **Validation:**
  - `judgements.inquiry` must be boolean.
  - If `inquiry = true`, `assistantReply` must be `null` and `nextStep = "agency_detect_v1"`.
  - If `inquiry = false`, `assistantReply` must contain guidance and `nextStep = "session_end"`.
- **State Merge:** Store `{"judgement_v1": {"inquiry": <bool>}}`.

---

### Stage: agency_detect_v1

- **Purpose:** Identify relevant agencies, complexity level, and the next branch.
- **Inputs:** `cached_state`, `runtime_directive` (optional).
- **Expected Output:**

  ```json
  {
    "session_id": "<uuid>",
    "response_id": "<string>",
    "stage": "agency_detect_v1",
    "judgements": {
      "agencyDetected": ["agencyId"],
      "agencyInfo": [
        {"agencyId": "string", "name": "string", "path": "string", "description": "string"}
      ],
      "agencyCount": "integer",
      "complexity": "low | high"
    },
    "nextStep": "category_select_v1 | semantic_analysis_v1 | session_end",
    "telemetry": {"notes": "string | null"}
  }
  ```

- **Validation:**
  - `session_id` must equal `cached_state.session_id`.
  - `agencyDetected` must contain ≥1 entry when `inquiry = true`.
  - `agencyCount` must equal the length of `agencyDetected`.
  - `complexity` must be either `"low"` or `"high"`.
  - `nextStep` logic: `low → category_select_v1`, `high → semantic_analysis_v1`, otherwise `session_end`.
- **State Merge:** Copy `judgements` block into `cached_state.agency_detect_v1` and set
  `cached_state.nextStep`.

---

### Stage: category_select_v1 (low-complexity path)

- **Purpose:** Match the user inquiry to dictionary categories for the detected agency.
- **Inputs:** `cached_state`, `KnowledgeBase_Dictionary`.
- **Expected Output:**

  ```json
  {
    "session_id": "<uuid>",
    "response_id": "<string>",
    "stage": "category_select_v1",
    "categorySelection": {
      "candidates": {
        "category_key": {"value": "string", "score": 0.00}
      }
    },
    "nextStep": "service_select_v1",
    "telemetry": {"notes": "string | null"}
  }
  ```

- **Validation:**
  - `session_id` must match `cached_state.session_id`.
  - `cached_state.agency_detect_v1.complexity` must equal `"low"`.
  - `candidates` must contain ≥1 item and each `score ≥ 0.50`.
- **State Merge:** Persist flattened candidates into `cached_state.category_select_v1.candidates` and
  update `cached_state.nextStep`.

---

### Stage: semantic_analysis_v1 (high-complexity path)

- **Purpose:** Score dictionary entries per agency and nominate a primary agency for multi-agency
  workflows.
- **Inputs:** `cached_state`, `KnowledgeBase_Dictionary`.
- **Expected Output:**

  ```json
  {
    "session_id": "<uuid>",
    "response_id": "<string>",
    "stage": "semantic_analysis_v1",
    "semanticAnalysis": {
      "agencies": [
        {
          "agencyId": "string",
          "agencyName": "string",
          "categorySelection": {
            "candidates": {
              "category_key": {"value": "string", "score": 0.00}
            }
          }
        }
      ],
      "primaryAgency": {
        "agencyId": "string",
        "reason": "highest cumulative relevance"
      }
    },
    "nextStep": "service_select_v1",
    "telemetry": {"notes": "string | null"}
  }
  ```

- **Validation:**
  - `session_id` must match `cached_state.session_id`.
  - `cached_state.agency_detect_v1.complexity` must equal `"high"`.
  - `semanticAnalysis.agencies` must list ≥2 agencies.
  - Each candidate score must be ≥0.50.
- **State Merge:** Store the full `semanticAnalysis` block under
  `cached_state.semantic_analysis_v1` and advance `cached_state.nextStep`.

---

### Stage: service_select_v1

- **Purpose:** Select the best-fit service and produce a placeholder-driven reply template.
- **Inputs:** `cached_state`, `service_index`, `KnowledgeBase_Dictionary` (if needed for
  placeholder naming).
- **Expected Output:**

  ```json
  {
    "session_id": "<uuid>",
    "response_id": "<string>",
    "stage": "service_select_v1",
    "serviceSelection": {
      "serviceKey": "string",
      "name": "string",
      "path": "string",
      "matchedField": "key | name | overview | applicability_summary",
      "score": 0.00
    },
    "template": {
      "placeholders": {
        "service_name": "{service_name}"
      },
      "rules": "Describe how to assemble the final reply using placeholders."
    },
    "nextStep": "session_end | multi_agency_service_answer_v1",
    "telemetry": {"notes": "string | null"}
  }
  ```

- **Validation:**
  - `session_id` must match `cached_state.session_id`.
  - `serviceSelection.serviceKey` must be present and `score ≥ 0.50` with two decimal places.
  - `template.placeholders` must include ≥1 key derived from cached data.
  - `nextStep` defaults to `"session_end"` for single-agency flows; set to
    `"multi_agency_service_answer_v1"` when additional synthesis is required.
- **State Merge:** Save `serviceSelection` and `template` under `cached_state.service_select_v1` and
  update `cached_state.nextStep`.

---

### Stage: multi_agency_service_answer_v1 (optional high-complexity synthesis)

- **Purpose:** Compose a consolidated response when multiple agencies/services must be referenced.
- **Inputs:** `cached_state`, accumulated agency/service snippets, `service_index` as needed.
- **Expected Output:**

  ```json
  {
    "session_id": "<uuid>",
    "response_id": "<string>",
    "stage": "multi_agency_service_answer_v1",
    "assistantReply": "string",
    "sourcesUsed": [
      {"agencyId": "string", "serviceKey": "string", "path": "string"}
    ],
    "nextStep": "session_end",
    "telemetry": {"notes": "string | null"}
  }
  ```

- **Validation:**
  - `session_id` must match `cached_state.session_id`.
  - `assistantReply` must be non-empty and actionable.
  - `sourcesUsed` must list every agency/service referenced in the reply.
- **State Merge:** Store the full JSON block under
  `cached_state.multi_agency_service_answer_v1` and set `cached_state.nextStep = "session_end"`.

---

## Session Termination

When `nextStep` returned by any stage equals `"session_end"`, the orchestrator stops the workflow
and outputs the most recent `assistantReply` (if present) to the end user. No further prompts are
loaded.

---

## Validation Checklist (Orchestrator Side)

1. Confirm `session_id` continuity whenever a stage emits the field.
2. Ensure scores retain two decimal precision.
3. Reject any response lacking mandatory fields for that stage; request immediate correction.
4. Merge only the documented state slices to avoid polluting `cached_state`.
