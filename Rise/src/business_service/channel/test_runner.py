from __future__ import annotations

"""Shared Telegram channel test runner used by HTTP API and monitors."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Mapping, Optional, Sequence

from business_service.channel.models import WorkflowChannelPolicy
from business_service.channel.service import WorkflowChannelService
from foundational_service.integrations.telegram_client import TelegramClient, TelegramClientError
from foundational_service.persist.observability import WorkflowRunReadRepository


@dataclass(slots=True)
class ChannelTestOutcome:
    status: str
    duration_ms: int
    trace_id: str
    telegram_message_id: Optional[str]
    error_code: Optional[str]
    workflow_result: Optional[Mapping[str, Any]]
    warnings: Sequence[str]


class ChannelBindingTestRunner:
    """Execute channel test flows and fetch workflow results when requested."""

    def __init__(
        self,
        *,
        service: WorkflowChannelService,
        telegram_client: TelegramClient,
        run_repository: WorkflowRunReadRepository,
    ) -> None:
        self._service = service
        self._telegram_client = telegram_client
        self._run_repository = run_repository

    async def run_test(
        self,
        *,
        workflow_id: str,
        policy: WorkflowChannelPolicy,
        chat_id: str,
        payload_text: str,
        wait_for_result: bool,
        trace_id: str,
    ) -> ChannelTestOutcome:
        token = self._service.decrypt_token(policy)
        start = perf_counter()
        start_time = datetime.now(timezone.utc)
        telegram_message_id: Optional[str] = None
        error_code: Optional[str] = None
        warnings: list[str] = []
        status = "success"

        try:
            result = await self._telegram_client.send_message(
                token,
                chat_id=chat_id,
                text=payload_text,
                parse_mode=None,
                trace_id=trace_id,
            )
            telegram_message_id = str(result.get("message_id")) if result else None
        except TelegramClientError as exc:
            status = "failed"
            error_code = exc.code
            warnings.append(exc.code)

        duration_ms = int((perf_counter() - start) * 1000)
        workflow_result: Optional[Mapping[str, Any]] = None
        if wait_for_result and status == "success":
            workflow_result = await self._await_workflow_result(workflow_id, since=start_time)
            if workflow_result is None:
                warnings.append("WORKFLOW_RESULT_TIMEOUT")

        return ChannelTestOutcome(
            status=status,
            duration_ms=duration_ms,
            trace_id=trace_id,
            telegram_message_id=telegram_message_id,
            error_code=error_code,
            workflow_result=workflow_result,
            warnings=tuple(warnings),
        )

    async def _await_workflow_result(
        self,
        workflow_id: str,
        *,
        since: datetime,
        timeout_seconds: float = 20.0,
        poll_interval: float = 2.0,
    ) -> Optional[Mapping[str, Any]]:
        deadline = perf_counter() + timeout_seconds
        while perf_counter() < deadline:
            runs = await self._run_repository.list_runs(workflow_id, since=since)
            for doc in runs:
                result_payload = doc.get("result")
                updated_at = doc.get("updated_at") or doc.get("created_at") or since
                if (
                    result_payload
                    and isinstance(updated_at, datetime)
                    and updated_at >= since
                ):
                    return result_payload
            await asyncio.sleep(poll_interval)
        return None


__all__ = ["ChannelBindingTestRunner", "ChannelTestOutcome"]
