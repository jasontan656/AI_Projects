"""Orchestrator coordinating chat requests via LangChain tools."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Callable, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from shared_utilities.response import create_error_response
from shared_utilities.time import Time
from shared_utilities.validator import ensure_timestamp_uuidv4, normalize_auth_username

from ..logger import info, error
from ..chat_agent import ChatAgent
from ..services.audit_service import AuditService
from ..services.form_service import FormService
from ..services.memory_service import MemoryService
from ..tool_registry import ToolRegistry


class OrchestratorDecisionLog(BaseModel):
    """
    Log entry for orchestrator decisions in chat-driven architecture.
    Currently all calls go through ChatAgent with LLM function calling.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="UUID of the decision log entry")
    user_id: str
    session_id: Optional[str] = None
    user_message: str = Field(..., description="User's natural language message")
    chosen_agent: str = Field(..., description="chat|tool|flow")
    router_reason: Optional[str] = None
    created_at: "datetime" = Field(default_factory=Time.now)


class Orchestrator:
    def __init__(
        self,
        *,
        memory_service: Optional[MemoryService] = None,
        audit_service: Optional[AuditService] = None,
        form_service: Optional[FormService] = None,
        chat_agent: Optional[ChatAgent] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        self.memory = memory_service or MemoryService()
        self.audit = audit_service or AuditService()
        self.forms = form_service or FormService()

        self.tool_registry = tool_registry or ToolRegistry()
        self.chat_agent = chat_agent or ChatAgent(tool_registry=self.tool_registry)

        info(
            "orchestrator.initialized",
            registered_tools=self.tool_registry.list_tools(),
        )

    async def run(self, envelope_like: Dict[str, Any]) -> Dict[str, Any]:
        (
            chat_request,
            error_response,
            prefer_stream,
            user_id,
            session_id,
            route_path,
        ) = self._build_chat_request(envelope_like)

        if error_response is not None:
            return error_response

        result = self.chat_agent.chat(chat_request, prefer_stream=prefer_stream)

        info(
            "orchestrator.run.finish",
            user_id=user_id,
            session_id=session_id or None,
            route_path="/".join(route_path),
            success=result.get("success"),
        )

        return result

    async def stream(self, envelope_like: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Yield streaming events for chat-driven orchestration."""

        (
            chat_request,
            error_response,
            _,
            user_id,
            session_id,
            route_path,
        ) = self._build_chat_request(envelope_like)

        if error_response is not None:
            yield {
                "type": "error",
                "success": False,
                "error": error_response.get("error"),
                "error_type": error_response.get("error_type", "INVALID_INPUT"),
            }
            return

        info(
            "orchestrator.stream.start",
            user_id=user_id,
            session_id=session_id or None,
            route_path="/".join(route_path),
        )

        async for event in self.chat_agent.stream_chat(chat_request):
            yield event

        info(
            "orchestrator.stream.finish",
            user_id=user_id,
            session_id=session_id or None,
            route_path="/".join(route_path),
        )

    def _build_chat_request(
        self, envelope_like: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], bool, str, str, Tuple[str, ...]]:
        """Validate envelope and construct ChatAgent request.

        Returns tuple of (chat_request, error_response, prefer_stream, user_id, session_id, route_path).
        """

        def _error(
            message: str,
            *,
            error_type: str = "INVALID_INPUT",
            user_id_val: str = "",
            session_id_val: str = "",
            route_path_val: Tuple[str, ...] | None = None,
            trace_id_val: str | None = None,
        ):
            error(
                "orchestrator.envelope_invalid",
                error=message,
                error_type=error_type,
                user_id=user_id_val or None,
                session_id=session_id_val or None,
                route_path="/".join(route_path_val) if route_path_val else None,
                trace_id=trace_id_val,
            )
            return None, create_error_response(error=message, error_type=error_type), False, user_id_val, session_id_val, route_path_val or tuple()

        user = envelope_like.get("user")
        if user is None or not isinstance(user, dict):
            return _error("Invalid envelope: 'user' must be a dict")

        payload = envelope_like.get("payload")
        if payload is None or not isinstance(payload, dict):
            return _error("Invalid envelope: 'payload' must be a dict", user_id_val=user.get("id", ""))

        meta = envelope_like.get("meta")
        if meta is None or not isinstance(meta, dict):
            return _error("Invalid envelope: 'meta' must be a dict", user_id_val=user.get("id", ""))

        trace_id = meta.get("trace_id")

        try:
            user_id = ensure_timestamp_uuidv4(user.get("id"), field_name="user_id")
        except ValueError as exc:
            return _error(str(exc), user_id_val=user.get("id", ""), trace_id_val=trace_id)

        try:
            auth_username = normalize_auth_username(user.get("auth_username"))
        except ValueError as exc:
            return _error(str(exc), user_id_val=user_id, trace_id_val=trace_id)

        route = payload.get("route") if isinstance(payload.get("route"), dict) else {}
        path = route.get("path")
        if not isinstance(path, list) or not path or not all(isinstance(seg, str) and seg for seg in path):
            return _error(
                "payload.route.path must be a non-empty list of strings",
                user_id_val=user_id,
                trace_id_val=trace_id,
            )
        if path[0] != "chat":
            return _error(
                "payload.route.path must start with 'chat'",
                user_id_val=user_id,
                trace_id_val=trace_id,
                route_path_val=tuple(path),
            )

        data_obj = payload.get("data") if isinstance(payload.get("data"), dict) else None
        if data_obj is None:
            return _error(
                "payload.data must be an object",
                user_id_val=user_id,
                trace_id_val=trace_id,
                route_path_val=tuple(path),
            )

        session_id = meta.get("session_id")
        if session_id is None and isinstance(data_obj, dict):
            session_id = data_obj.get("session_id", "")
        if session_id is None:
            session_id = ""

        request_id_candidate = meta.get("request_id")
        if request_id_candidate is None:
            request_id_candidate = data_obj.get("request_id")
        try:
            request_id = ensure_timestamp_uuidv4(request_id_candidate, field_name="request_id")
        except ValueError as exc:
            return _error(
                str(exc),
                user_id_val=user_id,
                session_id_val=session_id,
                trace_id_val=trace_id,
                route_path_val=tuple(path),
            )

        message = data_obj.get("message")
        if not message or not isinstance(message, str) or not message.strip():
            return _error(
                "Message is required and must be a non-empty string",
                user_id_val=user_id,
                session_id_val=session_id,
                trace_id_val=request_id,
                route_path_val=tuple(path),
            )

        prefer_stream = bool(meta.get("prefer_stream"))

        context: Dict[str, Any] = {
            key: value
            for key, value in data_obj.items()
            if key not in {"message", "request_id", "auth_username", "user_id"}
        }

        chat_request = {
            "message": message,
            "user_id": user_id,
            "auth_username": auth_username,
            "session_id": session_id,
            "request_id": request_id,
            "authorization": user.get("authorization"),
            "context": context,
        }

        return chat_request, None, prefer_stream, user_id, session_id, tuple(path)

    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        actions: list,
    ) -> None:
        self.tool_registry.register_tool(name, handler, description, actions)


__all__ = [
    "OrchestratorDecisionLog",
    "Orchestrator",
]



