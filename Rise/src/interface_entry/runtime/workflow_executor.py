"""Adapters that bridge business-layer workflow orchestrators into contracts."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from business_logic.workflow import WorkflowExecutionContext, WorkflowOrchestrator
from business_service.workflow import StageRepository, WorkflowRepository
from foundational_service.contracts.workflow_exec import (
    WorkflowExecutor,
    WorkflowExecutionPayload,
    WorkflowRunResultPayload,
    WorkflowStageResultPayload,
)
from foundational_service.persist.workflow_summary_repository import WorkflowSummaryRepository

__all__ = ["OrchestratorWorkflowExecutor"]


class OrchestratorWorkflowExecutor(WorkflowExecutor):
    """Thin adapter that hides orchestration classes behind the contract interface."""

    def __init__(
        self,
        *,
        workflow_repository: WorkflowRepository,
        stage_repository: StageRepository,
        summary_repository: WorkflowSummaryRepository,
    ) -> None:
        self._orchestrator = WorkflowOrchestrator(
            workflow_repository=workflow_repository,
            stage_repository=stage_repository,
            summary_repository=summary_repository,
        )

    async def execute(self, payload: WorkflowExecutionPayload) -> WorkflowRunResultPayload:
        context = WorkflowExecutionContext(
            workflow_id=str(payload.get("workflow_id", "")),
            request_id=str(payload.get("request_id", "")),
            user_text=str(payload.get("user_text", "")),
            history_chunks=tuple(payload.get("history_chunks") or ()),
            policy=dict(payload.get("policy") or {}),
            core_envelope=dict(payload.get("core_envelope") or {}),
            telemetry=payload.get("telemetry") or {},
            metadata=payload.get("metadata"),
            inbound=payload.get("inbound"),
        )
        run_result = await self._orchestrator.execute(context)
        stages: Sequence[WorkflowStageResultPayload] = [
            {
                "stage_id": stage.stage_id,
                "name": stage.name,
                "prompt_used": stage.prompt_used,
                "output_text": stage.output_text,
                "raw_response": dict(stage.raw_response),
            }
            for stage in run_result.stage_results
        ]
        return {
            "final_text": run_result.final_text,
            "stage_results": stages,
            "telemetry": dict(run_result.telemetry),
        }
