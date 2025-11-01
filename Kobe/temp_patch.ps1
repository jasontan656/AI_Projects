*** Begin Patch
*** Update File: OpenaiAgents/UnifiedCS/prompt_renderer.py
@@
-@dataclass(frozen=True)
-class StageOneContext:
-    user_prompt_en: str
-    original_language: str
-    language_detected: str
-    language_reported: str
-    conversation_summaries: Sequence[str]
-
-
-@dataclass(frozen=True)
-class StageTwoContext:
-    payload: Mapping[str, Any]
-
-
-@dataclass(frozen=True)
-class StageThreeContext:
-    payload: Mapping[str, Any]
+@dataclass(frozen=True)
+class StageOneContext:
+    user_prompt_en: str
+    original_language: str
+    language_detected: str
+    language_reported: str
+    conversation_summaries: Sequence[str]
+    judgement_cache: Mapping[str, Any] | None
+    runtime_metadata: Mapping[str, Any]
+
+
+@dataclass(frozen=True)
+class StageTwoContext:
+    agency_payload: Sequence[Mapping[str, Any]]
+    dictionary_payload: Mapping[str, Any]
+    service_index_payload: Mapping[str, Any]
+    intent_keywords: Sequence[str]
+
+
+@dataclass(frozen=True)
+class StageThreeContext:
+    agency_payload: Sequence[Mapping[str, Any]]
+    dictionary_payload: Mapping[str, Any]
+    intent_keywords: Sequence[str]
+    additional_info: Mapping[str, Any] | Sequence[Any] | str
@@
-def render_stage_one(context: StageOneContext) -> str:
-    template = _load_template("stage_one_prompt.txt")
-    rendered = template.safe_substitute(
-        user_prompt_en=context.user_prompt_en,
-        original_language=context.original_language,
-        language_detected=context.language_detected,
-        language_reported=context.language_reported,
-        conversation_summaries=_format_summaries(context.conversation_summaries),
-    )
+def render_stage_one(context: StageOneContext) -> str:
+    template = _load_template("stage_one_prompt.txt")
+    rendered = template.safe_substitute(
+        user_prompt_en=context.user_prompt_en,
+        original_language=context.original_language,
+        language_detected=context.language_detected,
+        language_reported=context.language_reported,
+        conversation_summaries=_format_summaries(context.conversation_summaries),
+        judgement_cache=_serialize(context.judgement_cache or {}),
+        runtime_metadata=_serialize(context.runtime_metadata),
+    )
     return rendered.strip()
 
 
-def render_stage_two(context: StageTwoContext) -> str:
-    template = _load_template("stage_two_prompt.txt")
-    rendered = template.safe_substitute(payload_json=_serialize(context.payload))
+def render_stage_two(context: StageTwoContext) -> str:
+    template = _load_template("stage_two_prompt.txt")
+    rendered = template.safe_substitute(
+        agency_payload=_serialize(list(context.agency_payload)),
+        dictionary_payload=_serialize(context.dictionary_payload),
+        service_index_payload=_serialize(context.service_index_payload),
+        intent_keywords=_serialize(list(context.intent_keywords)),
+    )
     return rendered.strip()
 
 
-def render_stage_three(context: StageThreeContext) -> str:
-    template = _load_template("stage_three_prompt.txt")
-    rendered = template.safe_substitute(payload_json=_serialize(context.payload))
+def render_stage_three(context: StageThreeContext) -> str:
+    template = _load_template("stage_three_prompt.txt")
+    rendered = template.safe_substitute(
+        agency_payload=_serialize(list(context.agency_payload)),
+        dictionary_payload=_serialize(context.dictionary_payload),
+        intent_keywords=_serialize(list(context.intent_keywords)),
+        additional_info=_serialize(context.additional_info),
+    )
     return rendered.strip()
*** End Patch
