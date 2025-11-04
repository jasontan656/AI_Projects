"""
FastAPI routing for Telegram webhook.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, Dict, List

from aiogram import Dispatcher
from fastapi import APIRouter, FastAPI, HTTPException, Request, Response, status

from foundational_service.bootstrap.webhook import behavior_webhook_request, behavior_webhook_startup
from foundational_service.contracts import toolcalls
from foundational_service.contracts.envelope import SchemaValidationError
from foundational_service.contracts.telegram import (
    UnsupportedUpdateError,
    behavior_core_envelope,
)
from project_utility.context import ContextBridge
from project_utility.tracing import trace_span

log = logging.getLogger(__name__)


# Histogram bucket boundaries in milliseconds for webhook latency.
_WEBHOOK_LATENCY_BUCKETS: List[float] = [100.0, 250.0, 500.0, 1000.0]


def register_routes(
    app: FastAPI,
    dispatcher: Dispatcher,
    webhook_path: str,
    runtime_policy: dict[str, Any],
    webhook_secret: str,
) -> None:
    router = APIRouter()
    versioning = runtime_policy.get("versioning", {})
    metrics_state = dispatcher.workflow_data.get("metrics")
    if metrics_state is None:
        metrics_state = {
            "telegram_updates_total": 0,
            "telegram_inbound_total": 0,
            "telegram_ignored_total": 0,
            "telegram_streaming_failures": 0,
            "telegram_placeholder_latency_sum": 0.0,
            "telegram_placeholder_latency_count": 0,
            "webhook_signature_failures": 0,
            "webhook_rtt_ms_sum": 0.0,
            "webhook_rtt_ms_count": 0,
        }
        dispatcher.workflow_data["metrics"] = metrics_state
    app.state.telegram_metrics = metrics_state

    def _update_latency_histogram(store: Dict[str, Any], latency_ms: float) -> None:
        buckets = store.setdefault(
            "webhook_rtt_ms_buckets",
            {str(boundary): 0 for boundary in _WEBHOOK_LATENCY_BUCKETS} | {"+Inf": 0},
        )
        placed = False
        for boundary in _WEBHOOK_LATENCY_BUCKETS:
            if latency_ms <= boundary:
                key = str(boundary)
                buckets[key] = buckets.get(key, 0) + 1
                placed = True
                break
        if not placed:
            buckets["+Inf"] = buckets.get("+Inf", 0) + 1
        else:
            buckets["+Inf"] = buckets.get("+Inf", 0) + 1

    @router.post(webhook_path)
    async def telegram_webhook(request: Request) -> Response:
        start = perf_counter()
        request_id = ContextBridge.request_id()
        async with trace_span("telegram.webhook", request_id=request_id) as span:
            payload = await request.json()
            log.debug(
                "webhook.update.received",
                extra={
                    "request_id": request_id,
                    "update_type": next(iter(payload.keys()), ""),
                    "has_message": "message" in payload,
                    "has_edited_message": "edited_message" in payload,
                },
            )
            headers = request.headers
            try:
                webhook_contract = behavior_webhook_request(headers, webhook_secret, dispatcher)
            except HTTPException as exc:
                span.set_attribute("status_code", exc.status_code)
                span.set_attribute("error", "invalid_signature")
                raise

        try:
            result = behavior_core_envelope(payload, channel="telegram")
        except UnsupportedUpdateError as exc:
            latency_ms = (perf_counter() - start) * 1000
            metrics_state["telegram_ignored_total"] = metrics_state.get("telegram_ignored_total", 0) + 1
            log.debug(
                "webhook.update.ignored",
                extra={
                    "request_id": request_id,
                    "update_type": exc.update_type,
                    "latency_ms": round(latency_ms, 3),
                },
            )
            return Response(status_code=status.HTTP_200_OK)
        except SchemaValidationError as exc:  # type: ignore[arg-type]
            latency_ms = (perf_counter() - start) * 1000
            span.set_attribute("status_code", status.HTTP_422_UNPROCESSABLE_ENTITY)
            span.set_attribute("latency_ms", round(latency_ms, 3))
            span.set_attribute("error", str(exc))
            log.warning(
                "webhook.core_schema_violation",
                extra={
                    "request_id": request_id,
                    "chat_id": "",
                    "convo_id": "",
                    "prompt_version": versioning.get("prompt_version"),
                    "doc_commit": versioning.get("doc_commit"),
                    "latency_ms": round(latency_ms, 3),
                    "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "error_hint": str(exc),
                },
            )
            toolcalls.call_emit_schema_alert(str(exc), channel="telegram")
            return Response(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

        latency_ms = (perf_counter() - start) * 1000
        signature_status = getattr(request.state, "signature_status", "accepted")
        telemetry = {
            "request_id": request_id,
            "latency_ms": round(latency_ms, 3),
            "status_code": status.HTTP_200_OK,
            "error_hint": "",
            "signature_status": signature_status,
        }
        if isinstance(webhook_contract, dict):
            telemetry.update(webhook_contract.get("telemetry", {}))
        core_bundle = {
            "core_envelope": result["core_envelope"],
            "telemetry": {**result.get("telemetry", {}), **telemetry},
        }
        log_payload = toolcalls.call_prepare_logging(core_bundle, runtime_policy, telemetry)
        result["telemetry"] = core_bundle["telemetry"]
        result["envelope"] = result["core_envelope"]
        log.info("webhook.accepted", extra=log_payload)
        await dispatcher.feed_raw_update(
            dispatcher.bot,
            payload,
            headers=request.headers,
            scope=request.scope,
        )
        metrics_state["telegram_updates_total"] = metrics_state.get("telegram_updates_total", 0) + 1
        metrics_state["webhook_rtt_ms_sum"] = metrics_state.get("webhook_rtt_ms_sum", 0.0) + telemetry["latency_ms"]
        metrics_state["webhook_rtt_ms_count"] = metrics_state.get("webhook_rtt_ms_count", 0) + 1
        metrics_state["last_webhook_latency_ms"] = telemetry["latency_ms"]
        _update_latency_histogram(metrics_state, telemetry["latency_ms"])
        span.set_attribute("status_code", status.HTTP_200_OK)
        span.set_attribute("latency_ms", telemetry["latency_ms"])
        return Response(status_code=status.HTTP_200_OK)

    @router.post("/telegram/setup_webhook")
    async def setup_webhook(request: Request) -> Response:
        body = await request.json()
        public_url = body.get("public_url")
        if not public_url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="public_url required")
        bot = dispatcher.bot
        telemetry = await behavior_webhook_startup(bot, f"{public_url}{webhook_path}", webhook_secret)
        for prompt in telemetry.get("prompt_events", []):
            log.warning(
                "webhook.prompt.retry",
                extra={
                    "prompt_id": prompt.get("prompt_id"),
                    "prompt_text": prompt.get("prompt_text", ""),
                    "request_id": ContextBridge.request_id(),
                    "retry": prompt.get("prompt_variables", {}).get("retry"),
                },
            )
        log.info(
            "webhook.setup.completed",
            extra={
                "request_id": ContextBridge.request_id(),
                "stages": telemetry.get("telemetry", {}).get("stages", []),
            },
        )
        return Response(status_code=status.HTTP_200_OK)

    @router.get("/metrics")
    async def metrics() -> Response:
        webhook_count = metrics_state.get("webhook_rtt_ms_count", 0)
        placeholder_count = metrics_state.get("telegram_placeholder_latency_count", 0)
        placeholder_avg = (
            metrics_state.get("telegram_placeholder_latency_sum", 0.0) / placeholder_count
            if placeholder_count
            else 0.0
        )
        buckets = metrics_state.get("webhook_rtt_ms_buckets", {})
        histogram_lines = []
        cumulative = 0
        for boundary in _WEBHOOK_LATENCY_BUCKETS:
            count = buckets.get(str(boundary), 0)
            cumulative += count
            histogram_lines.append(f"webhook_rtt_ms_bucket{{le=\"{boundary/1000:.3f}\"}} {cumulative}")
        cumulative += buckets.get("+Inf", 0)
        histogram_lines.append(f"webhook_rtt_ms_bucket{{le=\"+Inf\"}} {cumulative}")
        histogram_lines.append(f"webhook_rtt_ms_sum {metrics_state.get('webhook_rtt_ms_sum', 0.0)}")
        histogram_lines.append(f"webhook_rtt_ms_count {webhook_count}")

        payload = (
            f"telegram_updates_total {metrics_state.get('telegram_updates_total', 0)}\n"
            f"telegram_inbound_total {metrics_state.get('telegram_inbound_total', 0)}\n"
            f"telegram_streaming_failures {metrics_state.get('telegram_streaming_failures', 0)}\n"
            f"telegram_placeholder_latency {round(placeholder_avg, 3)}\n"
            + "\n".join(histogram_lines)
            + "\n"
            f"webhook_signature_failures {metrics_state.get('webhook_signature_failures', 0)}\n"
        )
        return Response(payload, media_type="text/plain")

    app.include_router(router)



