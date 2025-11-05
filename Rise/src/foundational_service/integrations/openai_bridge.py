"""OpenAI Responses API integration for conversation flows."""

from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Optional, TypedDict

from openai import AsyncOpenAI

from project_utility.context import ContextBridge

__all__ = [
    "TokensBudget",
    "AgentRequest",
    "behavior_agents_bridge",
]


class TokensBudget(TypedDict, total=False):
    per_call_max_tokens: int
    per_flow_max_tokens: int


class AgentRequest(TypedDict, total=False):
    prompt: str
    history: list[str]
    tokens_budget: TokensBudget
    request_id: str
    model: str


_DEFAULT_MODEL = os.getenv("OPENAI_RESPONSES_MODEL", "gpt-4.1-mini")
_CLIENT: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = AsyncOpenAI()
    return _CLIENT


def _compose_prompt(request: Mapping[str, Any]) -> str:
    history = request.get("history") or []
    user_prompt = request.get("prompt", "")
    sections: list[str] = []
    if history:
        sections.append("\n".join(str(item) for item in history if item))
    sections.append(str(user_prompt))
    prompt = "\n\n".join(filter(None, sections))
    if not prompt.strip():
        raise ValueError("empty prompt passed to behavior_agents_bridge")
    return prompt


async def behavior_agents_bridge(agent_request: Mapping[str, Any]) -> Dict[str, Any]:
    """Call OpenAI Responses API with a minimal prompt."""

    client = _get_client()
    request_id = str(agent_request.get("request_id") or ContextBridge.request_id())
    prompt = _compose_prompt(agent_request)
    tokens_budget = agent_request.get("tokens_budget", {}) or {}
    max_output_tokens = tokens_budget.get("per_call_max_tokens")
    model = agent_request.get("model") or _DEFAULT_MODEL

    response = await client.responses.create(
        model=model,
        input=prompt,
        max_output_tokens=max_output_tokens,
    )

    usage = getattr(response, "usage", None)
    usage_payload = {}
    if usage is not None:
        usage_payload = {
            "input_tokens": getattr(usage, "input_tokens", 0),
            "output_tokens": getattr(usage, "output_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
        }

    text = getattr(response, "output_text", None)
    if text is None and getattr(response, "output", None):
        # Responses API may expose output list when not using convenience property.
        chunks = [segment.text for segment in response.output if getattr(segment, "text", None)]
        text = "".join(chunks)
    final_text = text or ""

    return {
        "text": final_text,
        "usage": usage_payload,
        "response_id": getattr(response, "id", request_id),
    }
