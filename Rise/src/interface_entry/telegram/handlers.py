"""
Telegram message handlers implementing CoreEnvelope pipeline.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

import asyncio
import logging
from time import perf_counter
import json
from typing import Any, Awaitable, Callable, Dict, Mapping, Optional

from aiogram import Bot, Router
from aiogram.exceptions import TelegramForbiddenError, TelegramNetworkError
from aiogram.types import Message

from business_logic.conversation import TelegramConversationFlow
from foundational_service.bootstrap.aiogram import get_bootstrap_state
from foundational_service.contracts import toolcalls
from foundational_service.contracts.envelope import SchemaValidationError
from interface_entry.telegram.response import core_to_telegram_response
from project_utility.context import ContextBridge
router = Router(name="telegram_message_router")
log = logging.getLogger(__name__)
conversation_flow = TelegramConversationFlow()


def _build_update(message: Message) -> Dict[str, Any]:
    payload = message.model_dump()
    update: Dict[str, Any] = {"message": payload}
    update_id = getattr(message, "message_id", None)
    if update_id is not None:
        try:
            update["update_id"] = int(update_id)
        except (TypeError, ValueError):
            update["update_id"] = update_id
    return update

@router.message()
async def handle_message(message: Message, bot: Bot) -> None:
    start = perf_counter()
    request_id = ContextBridge.request_id()
    state = get_bootstrap_state()
    dispatcher = state.dispatcher

    policy = dispatcher.workflow_data.get("runtime_policy", {})
    if not policy:
        raise RuntimeError("runtime_policy missing from dispatcher workflow data")
    versioning = policy.get("versioning", {})
    metrics_state = dispatcher.workflow_data.setdefault("metrics", {})
    metrics_state.setdefault("telegram_ignored_total", 0)
    metrics_state["telegram_inbound_total"] = metrics_state.get("telegram_inbound_total", 0) + 1

    update_payload = _build_update(message)
    try:
        result = await conversation_flow.process(update_payload, policy=policy)
    except SchemaValidationError as exc:
        toolcalls.call_emit_schema_alert(str(exc), channel="telegram")
        await message.answer("抱歉，输入未通过校验，请检查格式。")
        latency_ms = (perf_counter() - start) * 1000
        log.warning(
            "telegram.handler.schema_violation",
            extra={
                "request_id": request_id,
                "chat_id": "",
                "convo_id": "",
                "prompt_version": versioning.get("prompt_version"),
                "doc_commit": versioning.get("doc_commit"),
                "latency_ms": round(latency_ms, 3),
                "status_code": 422,
                "error_hint": str(exc),
            },
        )
        return

    if result.status == "ignored":
        metrics_state["telegram_ignored_total"] = metrics_state.get("telegram_ignored_total", 0) + 1
        log.info(
            "telegram.handler.ignored",
            extra={
                "request_id": request_id,
                "update_type": result.update_type,
                "error_hint": result.error_hint,
            },
        )
        return
    if result.status != "handled":
        raise RuntimeError(f"unexpected conversation status: {result.status}")

    outbound = dict(result.outbound_payload)
    outbound_contract = dict(result.outbound_contract)
    mode = result.mode
    placeholder_id: Optional[int] = None
    user_text_for_log = result.user_text
    metrics = result.outbound_metrics
    chunk_metrics = metrics.get("chunk_metrics", [])
    total_chars = metrics.get("total_chars", 0)

    async def _run_with_retry(action: str, operation: Callable[[], Awaitable[Any]]) -> Any:
        attempt = 0
        while True:
            try:
                return await operation()
            except TelegramForbiddenError as exc:
                metrics_state["telegram_forbidden_total"] = metrics_state.get("telegram_forbidden_total", 0) + 1
                log.warning(
                    "telegram.user_forbidden",
                    extra={
                        "request_id": request_id,
                        "action": action,
                        "chat_id": getattr(message.chat, "id", ""),
                        "error": str(exc),
                    },
                )
                raise
            except TelegramNetworkError as exc:
                attempt += 1
                log.warning(
                    "telegram.network_retry",
                    extra={
                        "request_id": request_id,
                        "action": action,
                        "attempt": attempt,
                        "max_attempts": 3,
                        "error": str(exc),
                    },
                )
                if attempt >= 3:
                    log.error(
                        "telegram.network_failed",
                        extra={
                            "request_id": request_id,
                            "action": action,
                            "attempt": attempt,
                            "error": str(exc),
                        },
                        exc_info=True,
                    )
                    raise
                await asyncio.sleep(15)

    try:
        bot = getattr(message, "bot", bot)
        if mode == "stream":
            for plan in chunk_metrics:
                log.info(
                    "telegram.stream.plan",
                    extra={
                        "request_id": request_id,
                        "chunk_index": plan.get("chunk_index"),
                        "char_count": plan.get("char_count"),
                        "planned_delay_ms": plan.get("planned_delay_ms"),
                    },
                )
            placeholder_start = perf_counter()
            placeholder_text = toolcalls.call_md_escape(outbound.get("placeholder", "Processing..."))
            placeholder_id = await _run_with_retry(
                "send_placeholder",
                lambda: toolcalls.call_send_placeholder(
                    bot,
                    str(message.chat.id),
                    placeholder_text,
                ),
            )
            placeholder_latency = (perf_counter() - placeholder_start) * 1000
            metrics_state["telegram_placeholder_latency_sum"] = metrics_state.get(
                "telegram_placeholder_latency_sum", 0.0
            ) + placeholder_latency
            metrics_state["telegram_placeholder_latency_count"] = metrics_state.get(
                "telegram_placeholder_latency_count", 0
            ) + 1
            log.info(
                "telegram.stream.placeholder_sent",
                extra={"request_id": request_id, "message_id": placeholder_id},
            )
            for edit in outbound.get("edits", []):
                edit_started = perf_counter()
                await asyncio.sleep(edit.get("delay", 1.5))
                edit_text = toolcalls.call_md_escape(edit.get("text", ""))
                await _run_with_retry(
                    "edit_message_text",
                    lambda: bot.edit_message_text(
                        edit_text,
                        chat_id=message.chat.id,
                        message_id=placeholder_id,
                        parse_mode="MarkdownV2",
                    ),
                )
                edit_latency = (perf_counter() - edit_started) * 1000
                log.info(
                    "telegram.stream.edit_sent",
                    extra={
                        "request_id": request_id,
                        "chunk_index": edit.get("chunk_index"),
                        "char_count": edit.get("char_count"),
                        "planned_delay_ms": round(edit.get("delay", 0) * 1000, 3),
                        "edit_latency_ms": round(edit_latency, 3),
                    },
                )
            final_text_raw = outbound.get("text", "")
            final_text = toolcalls.call_md_escape(final_text_raw) if final_text_raw else ""
            if final_text:
                await _run_with_retry(
                    "edit_message_text",
                    lambda: bot.edit_message_text(
                        final_text,
                        chat_id=message.chat.id,
                        message_id=placeholder_id,
                        parse_mode="MarkdownV2",
                    ),
                )
                log.info(
                    "telegram.stream.final_sent",
                    extra={
                        "request_id": request_id,
                        "char_count": len(final_text),
                        "placeholder_id": placeholder_id,
                    },
                )
        else:
            text_out_raw = outbound.get("text", "")
            text_out = toolcalls.call_md_escape(text_out_raw) if text_out_raw else ""
            response_payload = core_to_telegram_response(outbound_contract, text=text_out)
            await _run_with_retry("send_message", lambda: bot.send_message(**response_payload))
            log.info(
                "telegram.stream.direct_send",
                extra={
                    "request_id": request_id,
                    "char_count": len(text_out),
                    "response_mode": mode,
                },
            )
    except TelegramForbiddenError as exc:
        metrics_state["telegram_user_blocked"] = metrics_state.get("telegram_user_blocked", 0) + 1
        log.warning(
            "telegram.handler.forbidden",
            extra={
                "request_id": request_id,
                "chat_id": getattr(message.chat, "id", ""),
                "error": str(exc),
                "mode": mode,
            },
        )
        return
    except Exception as exc:
        if placeholder_id is not None:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=placeholder_id)
            except Exception:
                pass
        metrics_state["telegram_streaming_failures"] = metrics_state.get("telegram_streaming_failures", 0) + 1
        conversation_snapshot = {
            "user_text": user_text_for_log,
            "ai_response": result.agent_output.get("text", ""),
            "mode": mode,
            "update_type": result.update_type,
        }
        error_payload = {
            "request_id": request_id,
            "error": str(exc),
            "conversation": conversation_snapshot,
        }
        log.error(
            "telegram.handler.streaming_error %s",
            json.dumps(error_payload, ensure_ascii=False),
            exc_info=True,
        )
        raise
    latency_ms = (perf_counter() - start) * 1000
    telemetry = dict(result.telemetry)
    agent_output_payload = result.output_payload.get("agent_output")
    if not isinstance(agent_output_payload, Mapping):
        raise RuntimeError("agent_output missing from output_payload")
    telemetry.update(
        {
            "request_id": request_id,
            "latency_ms": round(latency_ms, 3),
            "status_code": int(agent_output_payload.get("status_code", 200)),
            "error_hint": result.error_hint,
        }
    )
    core_bundle = {
        "core_envelope": result.core_envelope,
        "telemetry": telemetry,
    }
    log_payload = toolcalls.call_prepare_logging(
        core_bundle,
        policy,
        {
            "latency_ms": telemetry["latency_ms"],
            "status_code": telemetry["status_code"],
            "error_hint": telemetry["error_hint"],
        },
    )
    result.telemetry = telemetry
    log_payload.update(result.logging)
    log_payload.update(
        {
            "chunk_plan_count": len(chunk_metrics),
            "chunk_total_chars": total_chars,
        }
    )
    log_payload["conversation"] = {
        "user_text": user_text_for_log,
        "ai_response": result.agent_output.get("text", ""),
        "mode": mode,
        "update_type": result.update_type,
    }
    completed_payload = {
        **log_payload,
        "intent": result.intent,
        "triage_prompt": result.triage_prompt,
        "agent_bridge_mode": result.agent_bridge.get("mode"),
        "agent_bridge_retries": result.agent_bridge_telemetry.get("retries"),
        "response_mode": mode,
    }
    log.info(
        "telegram.handler.completed %s",
        json.dumps(completed_payload, ensure_ascii=False),
    )








