"""
Telegram message handlers implementing CoreEnvelope pipeline.

generated-from: 02@28a8d3a
"""
from __future__ import annotations

import asyncio
import logging
from time import perf_counter
import json
from typing import Any, Awaitable, Callable, Dict, Literal, Mapping, Optional, TypedDict
from pathlib import Path

from aiogram import Bot, Router
from aiogram.exceptions import TelegramForbiddenError, TelegramNetworkError
from aiogram.types import Message

from SharedUtility.Contracts import toolcalls
from SharedUtility.Contracts.behavior_contract import (
    SchemaValidationError,
    behavior_agents_bridge,
    behavior_telegram_inbound,
    behavior_telegram_outbound,
    get_bootstrap_state,
)
from TelegramAPI.adapters.response import core_to_telegram_response
from TelegramAPI.adapters.telegram import append_streaming_buffer, telegram_update_to_core
from SharedUtility.core.context import ContextBridge
from SharedUtility.core.prompt_registry import PROMPT_REGISTRY
router = Router(name="telegram_message_router")
log = logging.getLogger(__name__)

class ProcessUpdateResult(TypedDict, total=False):
    status: Literal["handled", "ignored"]
    mode: str
    outbound: Dict[str, Any]
    response_text: str
    user_text: str
    output_payload: Dict[str, Any]
    core_envelope: Dict[str, Any]
    envelope: Dict[str, Any]
    logging: Dict[str, Any]
    intent: str
    triage_prompt: str
    error_hint: str
    agent_bridge: Dict[str, Any]
    agent_bridge_telemetry: Dict[str, Any]
    audit_reason: str
    adapter_contract: Dict[str, Any]
    outbound_metrics: Dict[str, Any]
    telemetry: Dict[str, Any]
    update_type: str


def _classify_intent(user_text: str) -> str:
    normalized = user_text.strip()
    if not normalized or len(normalized) <= 1 or normalized.strip("?.!！？，") == "":
        return "clarify"
    lower = normalized.lower()
    if any(keyword in lower for keyword in ("拒绝", "越权", "敏感", "forbidden", "restricted")):
        return "refusal"
    if "help" in lower or "帮助" in normalized:
        return "help"
    return "compose"


async def process_update(message: Message, policy: dict[str, Any]) -> ProcessUpdateResult:
    request_id = ContextBridge.request_id()
    message_payload = message.model_dump()
    update: Dict[str, Any] = {"message": message_payload}
    update_id = getattr(message, "message_id", None)
    if update_id is not None:
        try:
            update["update_id"] = int(update_id)
        except (TypeError, ValueError):
            update["update_id"] = update_id

    inbound = behavior_telegram_inbound(update, policy)
    if inbound.get("response_status") == "ignored":
        log.debug(
            "telegram.handler.ignored_update",
            extra={"request_id": request_id, "update_type": inbound.get("telemetry", {}).get("update_type")},
        )
        telemetry = dict(inbound.get("telemetry", {}))
        ignored_user_text = str(message_payload.get("text") or message_payload.get("caption") or "")
        return ProcessUpdateResult(
            status="ignored",
            mode="ignored",
            logging=inbound.get("logging", {}),
            telemetry=telemetry,
            intent="ignored",
            error_hint=inbound.get("error_hint", "ignored"),
            update_type=telemetry.get("update_type", ""),
            user_text=ignored_user_text,
        )
    core_envelope = dict(inbound.get("core_envelope", {}))
    legacy_envelope = inbound.get("envelope", core_envelope)
    payload_section = dict(core_envelope.get("payload", {}))
    agent_request = dict(inbound.get("agent_request", {}))
    tokens_budget = policy.get("tokens_budget") or {
        "per_call_max_tokens": 3000,
        "per_flow_max_tokens": 6000,
        "summary_threshold_tokens": 2200,
    }
    agent_request.setdefault("tokens_budget", tokens_budget)
    logging_payload = inbound.get("logging", {})
    prompt_id = inbound.get("prompt_id")
    prompt_vars = inbound.get("prompt_variables", {})

    user_text = payload_section.get("user_message", "")
    history_quotes = payload_section.get("context_quotes", [])
    history_chunks = [quote.get("excerpt", "") for quote in history_quotes]
    triage_prompt = ""
    if user_text:
        triage_prompt = PROMPT_REGISTRY.render(
            "agent_triage_system",
            user_message=user_text,
            intent_candidates=["consult", "plan", "operation"],
            domain_profiles=["telegram"],
        )
    intent = _classify_intent(user_text)
    error_hint = inbound.get("error_hint", "")
    audit_reason = ""
    bridge_meta: Dict[str, Any] = {}
    bridge_telemetry: Dict[str, Any] = {}
    mode = "stream"

    direct_prompts = {
        "refusal": {
            "prompt_id": "agent_refusal_policy",
            "variables": {"rule": "safety_policy", "contact": "support@example.com"},
            "error_hint": "policy_violation",
            "audit": "policy_violation",
        },
        "help": {
            "prompt_id": "telegram_prompt_missing",
            "variables": {},
            "error_hint": "prompt_help",
            "audit": "",
        },
    }

    if prompt_id:
        base_text = PROMPT_REGISTRY.render(prompt_id, **prompt_vars)
        outbound = behavior_telegram_outbound([base_text], policy)
        response_text = outbound["text"] or toolcalls.call_md_escape(base_text)
        mode = "prompt"
        if not error_hint:
            error_hint = "prompt_required"
    elif intent in direct_prompts:
        prompt_spec = direct_prompts[intent]
        base_text = PROMPT_REGISTRY.render(prompt_spec["prompt_id"], **prompt_spec["variables"])
        outbound = behavior_telegram_outbound([base_text], policy)
        response_text = outbound["text"] or toolcalls.call_md_escape(base_text)
        mode = intent
        error_hint = error_hint or prompt_spec["error_hint"]
        audit_reason = prompt_spec["audit"]
    else:
        summary_instruction = PROMPT_REGISTRY.render(
            "telegram_history_summarize",
            history_chunks=history_chunks,
            limit_tokens=policy.get("tokens_budget", {}).get("summary_threshold_tokens", 500),
        )
        compose_text = PROMPT_REGISTRY.render(
            "agent_consult_compose",
            tone="业务口吻",
            token_budget=policy.get("tokens_budget", {}).get("per_call_max_tokens", 3000),
            context_snippets=[user_text, summary_instruction],
        )
        safety_level = core_envelope.get("ext_flags", {}).get("safety_level")
        system_tags = agent_request.get("system_tags", [])
        if safety_level == "restricted" or "policy_violation" in system_tags:
            base_text = PROMPT_REGISTRY.render(
                "agent_refusal_policy",
                rule="safety_policy",
                contact="support@example.com",
            )
            outbound = behavior_telegram_outbound([base_text], policy)
            response_text = outbound["text"] or toolcalls.call_md_escape(base_text)
            mode = "refusal"
            error_hint = "policy_violation"
            audit_reason = "policy_violation"
            bridge_meta = {"mode": "compose_renderer", "chunks": [], "tokens_usage": 0}
            bridge_telemetry = {"request_id": ContextBridge.request_id(), "policy_refused": True}
        else:
            bridge_output = await behavior_agents_bridge(agent_request)
            bridge_meta = bridge_output["agent_bridge_result"]
            bridge_telemetry = bridge_output.get("telemetry", {})
            bridge_chunks = bridge_meta.get("chunks") or [compose_text]
            outbound = behavior_telegram_outbound(bridge_chunks, policy)
            response_text = outbound["text"] or compose_text
            bridge_mode = bridge_meta.get("mode")
            mode = "direct" if bridge_mode == "template" else "stream"

    output_payload = toolcalls.call_validate_output(
        {
            "agent_output": {
                "chat_id": legacy_envelope.get("metadata", {}).get("chat_id", ""),
                "text": response_text,
                "parse_mode": "MarkdownV2",
                "status_code": 200,
                "error_hint": error_hint,
            }
        }
    )

    if audit_reason:
        toolcalls.call_record_audit(
            {
                "intent": intent,
                "chat_id": legacy_envelope.get("metadata", {}).get("chat_id", ""),
                "reason": audit_reason,
            }
        )

    core_bundle_for_adapter = {
        "core_envelope": core_envelope,
        "telemetry": inbound.get("telemetry", {}),
    }
    adapter_contract = telegram_update_to_core(
        update,
        core_bundle=core_bundle_for_adapter,
        agent_request=agent_request,
    )

    tokens_budget = int(policy.get("tokens_budget", {}).get("per_call_max_tokens", 3000))

    outbound_contract = adapter_contract["outbound"]
    chunk_metrics = outbound.get("metrics", {}).get("chunk_metrics", [])
    reply_to_message_id = adapter_contract["inbound"].get("reply_to_message_id")
    if reply_to_message_id is not None:
        outbound_contract["reply_to_message_id"] = int(reply_to_message_id)
    outbound_contract["disable_web_page_preview"] = True
    append_streaming_buffer(adapter_contract, chunk_metrics)
    if mode != "stream":
        outbound_contract["text"] = response_text
    toolcalls.call_validate_telegram_adapter_contract(adapter_contract)

    return ProcessUpdateResult(
        status="handled",
        mode=mode,
        outbound=outbound,
        response_text=response_text,
        user_text=user_text,
        output_payload=output_payload,
        core_envelope=core_envelope,
        envelope=legacy_envelope,
        logging=logging_payload,
        intent=intent,
        triage_prompt=triage_prompt,
        error_hint=error_hint,
        agent_bridge=bridge_meta,
        agent_bridge_telemetry=bridge_telemetry,
        audit_reason=audit_reason,
        adapter_contract=adapter_contract,
        outbound_metrics=outbound.get("metrics", {}),
        telemetry=inbound.get("telemetry", {}),
        update_type=inbound.get("telemetry", {}).get("update_type", ""),
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
    metrics_state["telegram_inbound_total"] = metrics_state.get("telegram_inbound_total", 0) + 1

    try:
        result = await process_update(message, policy)
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

    status = result.get("status")
    if status == "ignored":
        metrics_state["telegram_ignored_total"] = metrics_state.get("telegram_ignored_total", 0) + 1
        log.info(
            "telegram.handler.ignored",
            extra={
                "request_id": request_id,
                "update_type": result.get("update_type", ""),
                "error_hint": result.get("error_hint", ""),
            },
        )
        return
    if status != "handled":
        raise RuntimeError(f"unexpected process_update status: {status}")

    outbound = result["outbound"]
    outbound_contract = dict(result["adapter_contract"]["outbound"])
    mode = result["mode"]
    placeholder_id: Optional[int] = None
    user_text_for_log = result.get("user_text", "")
    metrics = result.get("outbound_metrics", {})
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
            "ai_response": result.get("response_text", ""),
            "mode": mode,
            "update_type": result.get("update_type", ""),
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
    telemetry = {**result.get("telemetry", {})}
    agent_output_payload = result.get("output_payload", {}).get("agent_output")
    if not isinstance(agent_output_payload, Mapping):
        raise RuntimeError("agent_output missing from output_payload")
    telemetry.update(
        {
            "request_id": request_id,
            "latency_ms": round(latency_ms, 3),
            "status_code": int(agent_output_payload.get("status_code", 200)),
            "error_hint": result.get("error_hint", ""),
        }
    )
    core_bundle = {
        "core_envelope": result["core_envelope"],
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
    result["telemetry"] = telemetry
    log_payload.update(result.get("logging", {}))
    log_payload.update(
        {
            "chunk_plan_count": len(chunk_metrics),
            "chunk_total_chars": total_chars,
        }
    )
    log_payload["conversation"] = {
        "user_text": user_text_for_log,
        "ai_response": result.get("response_text", ""),
        "mode": mode,
        "update_type": result.get("update_type", ""),
    }
    completed_payload = {
        **log_payload,
        "intent": result["intent"],
        "triage_prompt": result.get("triage_prompt", ""),
        "agent_bridge_mode": result["agent_bridge"].get("mode"),
        "agent_bridge_retries": result.get("agent_bridge_telemetry", {}).get("retries"),
        "response_mode": mode,
    }
    log.info(
        "telegram.handler.completed %s",
        json.dumps(completed_payload, ensure_ascii=False),
    )








