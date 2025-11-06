from __future__ import annotations

"""Workflow orchestrator for multi-stage conversations."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Mapping, MutableMapping, Optional, Sequence

from business_service.workflow import StageDefinition, StageRepository, WorkflowDefinition, WorkflowRepository
from foundational_service.integrations.openai_bridge import behavior_agents_bridge
from project_utility.context import ContextBridge
from project_utility.db import append_chat_summary, get_mongo_database

log = logging.getLogger("business_logic.workflow.orchestrator")

__all__ = [
    "WorkflowExecutionContext",
    "WorkflowOrchestrator",
    "WorkflowRunResult",
    "WorkflowStageResult",
]

FALLBACK_MODEL = "gpt-4o-mini"


@dataclass(slots=True)
class WorkflowStageResult:
    stage_id: str
    name: str
    prompt_used: str
    output_text: str
    raw_response: Mapping[str, Any]


@dataclass(slots=True)
class WorkflowRunResult:
    final_text: str
    stage_results: Sequence[WorkflowStageResult]
    telemetry: Mapping[str, Any]


@dataclass(slots=True)
class WorkflowExecutionContext:
    workflow_id: str
    request_id: str
    user_text: str
    history_chunks: Sequence[str]
    policy: Mapping[str, Any]
    core_envelope: Mapping[str, Any]
    telemetry: MutableMapping[str, Any]

    def chat_id(self) -> Optional[str]:
        metadata = self.core_envelope.get("metadata", {})
        chat_id = metadata.get("chat_id") or metadata.get("conversation_id")
        if chat_id is None:
            inbound = self.core_envelope.get("inbound", {})
            chat_id = inbound.get("chat_id")
        if chat_id is None:
            return None
        return str(chat_id)


class WorkflowOrchestrator:
    def __init__(
        self,
        *,
        workflow_repository: WorkflowRepository,
        stage_repository: StageRepository,
    ) -> None:
        self._workflow_repository = workflow_repository
        self._stage_repository = stage_repository

    async def execute(self, context: WorkflowExecutionContext) -> WorkflowRunResult:
        workflow = self._load_workflow(context.workflow_id)
        stage_defs = self._load_stages(workflow.stage_ids)
        stage_results: List[WorkflowStageResult] = []
        accumulated_history = list(context.history_chunks)

        for stage_id in workflow.stage_ids:
            stage = stage_defs.get(stage_id)
            if stage is None:
                raise RuntimeError(f"workflow stage '{stage_id}' not found")
            prompt = self._compose_prompt(stage, context, stage_results)
            agent_request = {
                "prompt": prompt,
                "history": accumulated_history,
                "tokens_budget": context.policy.get("tokens_budget"),
                "request_id": f"{context.request_id}:{stage_id}",
                "model": context.policy.get("model") or FALLBACK_MODEL,
            }
            raw = await behavior_agents_bridge(agent_request)
            output_text = raw.get("text", "").strip()
            if not output_text:
                raise RuntimeError(f"stage '{stage_id}' returned empty response")
            accumulated_history.append(output_text)
            stage_results.append(
                WorkflowStageResult(
                    stage_id=stage.stage_id,
                    name=stage.name,
                    prompt_used=prompt,
                    output_text=output_text,
                    raw_response=raw,
                )
            )

        final_text = stage_results[-1].output_text if stage_results else ""
        telemetry = dict(context.telemetry)
        telemetry.update(
            {
                "workflow_id": context.workflow_id,
                "stage_count": len(stage_results),
                "stage_results": [
                    {
                        "stage_id": r.stage_id,
                        "prompt_length": len(r.prompt_used),
                        "output_length": len(r.output_text),
                    }
                    for r in stage_results
                ],
            }
        )
        await self._persist_summary(context, final_text, stage_results)
        return WorkflowRunResult(final_text=final_text, stage_results=stage_results, telemetry=telemetry)

    def _load_workflow(self, workflow_id: str) -> WorkflowDefinition:
        workflow = self._workflow_repository.get(workflow_id)
        if workflow is None:
            raise RuntimeError(f"workflow '{workflow_id}' not found")
        if not workflow.stage_ids:
            raise RuntimeError(f"workflow '{workflow_id}' has no stages configured")
        return workflow

    def _load_stages(self, stage_ids: Sequence[str]) -> Mapping[str, StageDefinition]:
        if not stage_ids:
            return {}
        stages = self._stage_repository.get_many(stage_ids)
        mapping = {stage.stage_id: stage for stage in stages}
        missing = [stage_id for stage_id in stage_ids if stage_id not in mapping]
        if missing:
            raise RuntimeError(f"missing stage definitions: {', '.join(missing)}")
        return mapping

    async def _persist_summary(
        self,
        context: WorkflowExecutionContext,
        final_text: str,
        stage_results: Sequence[WorkflowStageResult],
    ) -> None:
        chat_id = context.chat_id()
        if not chat_id:
            return
        summary_entry = {
            "user_text": context.user_text,
            "final_text": final_text,
            "stage_outputs": [
                {"stage_id": result.stage_id, "output": result.output_text} for result in stage_results
            ],
            "request_id": context.request_id,
        }
        try:
            await append_chat_summary(chat_id, summary_entry, max_entries=20, ttl_seconds=3600)
        except Exception:  # pragma: no cover - redis 失败仅记录日志
            log.exception("chat_summary.append_failed", extra={"chat_id": chat_id})
        try:
            database = get_mongo_database()
            database["chat_history"].update_one(
                {"chat_id": chat_id},
                {
                    "$push": {
                        "entries": {
                            "$each": [summary_entry],
                            "$position": 0,
                            "$slice": 20,
                        }
                    },
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                },
                upsert=True,
            )
        except Exception:  # pragma: no cover - mongo失败仅记录日志
            log.exception("chat_history.upsert_failed", extra={"chat_id": chat_id})

    def _compose_prompt(
        self,
        stage: StageDefinition,
        context: WorkflowExecutionContext,
        previous_results: Sequence[WorkflowStageResult],
    ) -> str:
        prompt_context = {
            "user_text": context.user_text,
            "chat_summary": "\n".join(context.history_chunks),
            "previous_stage_outputs": "\n\n".join(r.output_text for r in previous_results),
            "request_id": context.request_id,
            "workflow_id": context.workflow_id,
        }
        try:
            prompt = stage.prompt_template.format_map(_SafeDict(prompt_context))
        except KeyError as exc:
            missing = str(exc)
            log.warning("workflow.prompt.placeholder_missing", extra={"placeholder": missing, "stage_id": stage.stage_id})
            prompt = stage.prompt_template
        return prompt


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
