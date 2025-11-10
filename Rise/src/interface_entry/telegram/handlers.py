"""
Telegram message handlers implementing CoreEnvelope pipeline.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

import asyncio
import json
from time import perf_counter
from typing import Any, Dict, Mapping, Optional, Sequence

from aiogram import Bot, Router
from aiogram.exceptions import TelegramForbiddenError, TelegramNetworkError
from aiogram.types import Message

from business_logic.conversation import TelegramConversationFlow
from business_service.conversation.service import AsyncResultHandle
from foundational_service.bootstrap.aiogram import get_bootstrap_state
from foundational_service.contracts import toolcalls
from foundational_service.contracts.envelope import SchemaValidationError
from interface_entry.telegram.response import core_to_telegram_response
from project_utility.context import ContextBridge
from project_utility.telemetry import emit as telemetry_emit

router = Router(name="telegram_message_router")
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

def _prepare_response_payload(result) -> tuple[Dict[str, Any], str, Dict[str, Any]]:
    outbound_contract = dict(result.outbound_contract)
    text_raw = result.agent_output.get("text", "")
    if not text_raw:
        raise RuntimeError("empty assistant response text")
    text_out = toolcalls.call_md_escape(str(text_raw))
    response_payload = core_to_telegram_response(outbound_contract, text=text_out)
    return response_payload, text_out, outbound_contract


def _emit_telegram_event(
    event_type: str,
    *,
    level: str = "info",
    request_id: Optional[str],
    payload: Optional[Mapping[str, Any]] = None,
    sensitive: Optional[Sequence[str]] = None,
    **fields: Any,
) -> None:
    telemetry_emit(
        event_type,
        level=level,
        request_id=request_id,
        payload=dict(payload or {}),
        sensitive=list(sensitive or []),
        **fields,
    )


async def _send_with_retry(
    bot: Bot,
    payload: Mapping[str, Any],
    *,
    request_id: str,
    metrics_state: Dict[str, Any],
    chat_id: Any,
    action: str,
) -> None:
    attempt = 0
    while True:
        try:
            await bot.send_message(**payload)
            return
        except TelegramForbiddenError as exc:
            metrics_state["telegram_forbidden_total"] = metrics_state.get("telegram_forbidden_total", 0) + 1
            _emit_telegram_event(
                "telegram.user_forbidden",
                level="warning",
                request_id=request_id,
                payload={"action": action, "chat_id": chat_id, "error": str(exc)},
            )
            raise
        except TelegramNetworkError as exc:
            attempt += 1
            _emit_telegram_event(
                "telegram.network_retry",
                level="warning",
                request_id=request_id,
                payload={"action": action, "attempt": attempt, "max_attempts": 3, "error": str(exc)},
            )
            if attempt >= 3:
                _emit_telegram_event(
                    "telegram.network_failed",
                    level="error",
                    request_id=request_id,
                    payload={"action": action, "attempt": attempt, "error": str(exc)},
                )
                raise
            await asyncio.sleep(15)


async def _await_async_completion(handle: AsyncResultHandle, bot: Bot, metrics_state: Dict[str, Any]) -> None:
    request_id = handle.context.request_id
    try:
        ContextBridge.set_request_id(request_id)
        service_result = await handle.resolve()
        final_result = conversation_flow._to_result(service_result)
        payload, text_out, outbound_contract = _prepare_response_payload(final_result)
        _emit_telegram_event(
            "telegram.prompt",
            level="debug",
            request_id=request_id,
            payload={
                "prompt_text": final_result.user_text,
                "reply_text": final_result.agent_output.get("text", ""),
                "mode": final_result.mode,
            },
            sensitive=["prompt_text", "reply_text"],
        )
        await _send_with_retry(
            bot,
            payload,
            request_id=request_id,
            metrics_state=metrics_state,
            chat_id=outbound_contract.get("chat_id"),
            action="send_async_message",
        )
        metrics_state["telegram_async_completed_total"] = metrics_state.get("telegram_async_completed_total", 0) + 1
        _emit_telegram_event(
            "telegram.handler.async_message_sent",
            request_id=request_id,
            payload={
                "task_id": final_result.agent_output.get("task_id"),
                "char_count": len(text_out),
            },
        )
    except TelegramForbiddenError as exc:
        metrics_state["telegram_user_blocked"] = metrics_state.get("telegram_user_blocked", 0) + 1
        _emit_telegram_event(
            "telegram.async.forbidden",
            level="warning",
            request_id=request_id,
            payload={"error": str(exc)},
        )
    except Exception as exc:
        metrics_state["telegram_async_failed_total"] = metrics_state.get("telegram_async_failed_total", 0) + 1
        _emit_telegram_event(
            "telegram.async.failed",
            level="error",
            request_id=request_id,
            payload={"error": str(exc)},
        )
        await _notify_async_failure(handle, bot, metrics_state, request_id)
    finally:
        ContextBridge.clear()


async def _notify_async_failure(
    handle: AsyncResultHandle,
    bot: Bot,
    metrics_state: Dict[str, Any],
    request_id: str,
) -> None:
    metadata = handle.context.core_envelope.get("metadata", {})
    chat_id = metadata.get("chat_id")
    if not chat_id:
        return
    fallback_payload = {
        "chat_id": chat_id,
        "text": toolcalls.call_md_escape(handle.format_failure_text()),
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }
    try:
        await _send_with_retry(
            bot,
            fallback_payload,
            request_id=request_id,
            metrics_state=metrics_state,
            chat_id=chat_id,
            action="send_failure_notice",
        )
    except TelegramForbiddenError:
        metrics_state["telegram_user_blocked"] = metrics_state.get("telegram_user_blocked", 0) + 1
    except Exception:
        metrics_state["telegram_send_failures"] = metrics_state.get("telegram_send_failures", 0) + 1
        log.exception(
            "telegram.async.failure_notice_error",
            extra={"request_id": request_id},
        )


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
    metrics_state.setdefault("telegram_send_failures", 0)
    metrics_state.setdefault("telegram_forbidden_total", 0)
    metrics_state.setdefault("telegram_user_blocked", 0)
    metrics_state.setdefault("telegram_queue_enqueue_failed_total", 0)
    metrics_state.setdefault("telegram_async_pending_total", 0)
    metrics_state.setdefault("telegram_async_completed_total", 0)
    metrics_state.setdefault("telegram_async_failed_total", 0)
    metrics_state.setdefault("telegram_workflow_missing_total", 0)
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

    telemetry_snapshot = dict(result.telemetry)
    queue_status = telemetry_snapshot.get("queue_status")
    if queue_status == "enqueue_failed":
        metrics_state["telegram_queue_enqueue_failed_total"] = metrics_state.get("telegram_queue_enqueue_failed_total", 0) + 1

    agent_output = dict(result.agent_output)
    async_handle_obj = agent_output.pop("async_handle", None)
    result.agent_output = agent_output
    async_handle = async_handle_obj if isinstance(async_handle_obj, AsyncResultHandle) else None

    if result.status == "ignored":
        metrics_state["telegram_ignored_total"] = metrics_state.get("telegram_ignored_total", 0) + 1
        if result.error_hint == "workflow_missing" and agent_output.get("text"):
            metrics_state["telegram_workflow_missing_total"] = metrics_state.get("telegram_workflow_missing_total", 0) + 1
            try:
                payload, _, outbound_contract = _prepare_response_payload(result)
                chat_id = outbound_contract.get("chat_id") or getattr(message.chat, "id", "")
                await _send_with_retry(
                    bot,
                    payload,
                    request_id=request_id,
                    metrics_state=metrics_state,
                    chat_id=chat_id,
                    action="send_workflow_missing",
                )
            except TelegramForbiddenError as exc:
                metrics_state["telegram_user_blocked"] = metrics_state.get("telegram_user_blocked", 0) + 1
                _emit_telegram_event(
                    "telegram.handler.forbidden",
                    level="warning",
                    request_id=request_id,
                    payload={
                        "chat_id": getattr(message.chat, "id", ""),
                        "error": str(exc),
                    },
                )
            except Exception as exc:
                metrics_state["telegram_send_failures"] = metrics_state.get("telegram_send_failures", 0) + 1
                _emit_telegram_event(
                    "telegram.handler.send_error",
                    level="error",
                    request_id=request_id,
                    payload={"error": str(exc)},
                )
                raise
        _emit_telegram_event(
            "telegram.handler.ignored",
            request_id=request_id,
            payload={"update_type": result.update_type, "error_hint": result.error_hint},
        )
        return

    if result.status != "handled":
        raise RuntimeError(f"unexpected conversation status: {result.status}")

    payload, text_out, outbound_contract = _prepare_response_payload(result)
    chat_id = outbound_contract.get("chat_id") or getattr(message.chat, "id", "")
    _emit_telegram_event(
        "telegram.prompt",
        level="debug",
        request_id=request_id,
        payload={
            "prompt_text": result.user_text,
            "reply_text": agent_output.get("text", ""),
            "mode": result.mode,
        },
        sensitive=["prompt_text", "reply_text"],
    )

    try:
        bot = getattr(message, "bot", bot)
        await _send_with_retry(
            bot,
            payload,
            request_id=request_id,
            metrics_state=metrics_state,
            chat_id=chat_id,
            action="send_message",
        )
        _emit_telegram_event(
            "telegram.handler.message_sent",
            request_id=request_id,
            payload={"char_count": len(text_out)},
        )
    except TelegramForbiddenError as exc:
        metrics_state["telegram_user_blocked"] = metrics_state.get("telegram_user_blocked", 0) + 1
        _emit_telegram_event(
            "telegram.handler.forbidden",
            level="warning",
            request_id=request_id,
            payload={
                "chat_id": getattr(message.chat, "id", ""),
                "error": str(exc),
            },
        )
        return
    except Exception as exc:
        metrics_state["telegram_send_failures"] = metrics_state.get("telegram_send_failures", 0) + 1
        conversation_snapshot = {
            "user_text": result.user_text,
            "ai_response": agent_output.get("text", ""),
            "update_type": result.update_type,
        }
        error_payload = {
            "request_id": request_id,
            "error": str(exc),
            "conversation": conversation_snapshot,
        }
        _emit_telegram_event(
            "telegram.handler.send_error",
            level="error",
            request_id=request_id,
            payload=error_payload,
            sensitive=["conversation"],
        )
        raise

    if async_handle is not None:
        metrics_state["telegram_async_pending_total"] = metrics_state.get("telegram_async_pending_total", 0) + 1
        asyncio.create_task(_await_async_completion(async_handle, bot, metrics_state))

    latency_ms = (perf_counter() - start) * 1000
    telemetry_snapshot.update(
        {
            "request_id": request_id,
            "latency_ms": round(latency_ms, 3),
            "status_code": int(agent_output.get("status_code", 200)),
            "error_hint": result.error_hint,
        }
    )
    core_bundle = {
        "core_envelope": result.core_envelope,
        "telemetry": telemetry_snapshot,
    }
    log_payload = toolcalls.call_prepare_logging(
        core_bundle,
        policy,
        {
            "latency_ms": telemetry_snapshot["latency_ms"],
            "status_code": telemetry_snapshot["status_code"],
            "error_hint": telemetry_snapshot["error_hint"],
        },
    )
    result.telemetry = telemetry_snapshot
    log_payload.update(result.logging)
    log_payload["conversation"] = {
        "user_text": result.user_text,
        "ai_response": agent_output.get("text", ""),
        "update_type": result.update_type,
    }
    completed_payload = {
        **log_payload,
        "intent": result.intent,
        "response_mode": result.mode,
    }
    _emit_telegram_event(
        "telegram.handler.completed",
        request_id=request_id,
        payload=completed_payload,
        sensitive=["conversation"],
    )

