import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from shared_utilities.validator import ensure_timestamp_uuidv4, normalize_auth_username
from shared_utilities.mango_db.db_queue_manager import start_workers, stop_workers
from shared_utilities.response import create_error_response

from .logger import info, error, exception
from langchain_core.runnables import Runnable  # type: ignore


class ChatRequest(BaseModel):
    """Pydantic model enforcing chat contract."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., description="User's natural language message")
    user_id: str = Field(..., description="User ID for context and authorization")
    auth_username: str = Field(default="", description="User auth username accompanying user_id")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    request_id: str = Field(..., description="Request trace ID for debugging")
    authorization: Optional[str] = Field(None, description="Bearer token presented by the client")
    stream: Optional[bool] = Field(False, description="Whether to stream the response")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context (e.g., form state)")

    @field_validator("user_id")
    def _validate_user_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="user_id")

    @field_validator("request_id")
    def _validate_request_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="request_id")

    @field_validator("auth_username", mode="before")
    def _validate_auth_username(cls, value: str | None) -> str:
        return normalize_auth_username(value)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_workers()
    info("db.queue.workers.started")
    try:
        yield
    finally:
        await stop_workers()
        info("db.queue.workers.stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Career Bot Hub",
        version="1.0.0",
        lifespan=lifespan,
    )

    allowed_origins = os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000",
    ).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in allowed_origins if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .services.memory_service import MemoryService
    from .services.audit_service import AuditService
    from .services.form_service import FormService
    from .models.orchestrator import Orchestrator
    from .router import HubRouter

    memory_service = MemoryService()
    audit_service = AuditService()
    form_service = FormService()
    orchestrator = Orchestrator(
        memory_service=memory_service,
        audit_service=audit_service,
        form_service=form_service,
    )

    from tool_modules.auth.tools import AUTH_TOOL_SPEC
    from tool_modules.mbti.tools import MBTI_TOOL_SPEC

    orchestrator.register_tool(
        name=AUTH_TOOL_SPEC["name"],
        handler=AUTH_TOOL_SPEC["handler"],
        description=AUTH_TOOL_SPEC["description"],
        actions=AUTH_TOOL_SPEC["actions"],
    )
    orchestrator.register_tool(
        name=MBTI_TOOL_SPEC["name"],
        handler=MBTI_TOOL_SPEC["handler"],
        description=MBTI_TOOL_SPEC["description"],
        actions=MBTI_TOOL_SPEC["actions"],
    )

    router = HubRouter(orchestrator=orchestrator)
    chat_adapter = LangServeChatAdapter(router=router)
    chat_runnable = LangServeChatRunnable(adapter=chat_adapter)

    from langserve import add_routes  # type: ignore

    add_routes(app, chat_runnable, path="/chat")

    return app



class LangServeChatAdapter:
    """Adapter exposing hub chat orchestrator through LangServe."""

    ROUTE_PATH: tuple[str, ...] = ("chat", "v1", "message")

    def __init__(self, router: Any, *, timeout_seconds: float = 60.0) -> None:
        self.router = router
        self.timeout_seconds = timeout_seconds

    async def ainvoke(
        self, input: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        chat_req, envelope, error_response, context = self._build_envelope(
            input, prefer_stream=False
        )
        if error_response is not None:
            error(
                "chat.request.invalid",
                trace_id=context.get("trace_id") or "unknown",
                request_id=context.get("request_id") or "unknown",
                route_path=context["route_path"],
                details=context.get("details"),
            )
            return error_response

        self._log_request(chat_req, prefer_stream=False)
        try:
            result = await asyncio.wait_for(
                self.router.route(envelope),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            error_response = create_error_response(
                error="Request timed out",
                error_type="INTERNAL_ERROR",
                details={"timeout_seconds": self.timeout_seconds},
            )
            exception(
                "chat.timeout",
                user_id=chat_req.user_id,
                session_id=chat_req.session_id,
                trace_id=chat_req.request_id,
                request_id=chat_req.request_id,
                route_path=context["route_path"],
                timeout_seconds=self.timeout_seconds,
            )
            self._log_response(chat_req, error_response)
            return error_response

        self._log_response(chat_req, result)
        return result

    async def astream(
        self, input: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Any, None]:
        chat_req, envelope, error_response, context = self._build_envelope(
            input, prefer_stream=True
        )
        if error_response is not None:
            error(
                "chat.stream.invalid",
                trace_id=context.get("trace_id") or "unknown",
                request_id=context.get("request_id") or "unknown",
                route_path=context["route_path"],
                details=context.get("details"),
            )
            yield {"type": "error", **error_response}
            return

        self._log_request(chat_req, prefer_stream=True)

        async for event in self.router.stream(envelope):
            event_type = event.get("type") if isinstance(event, dict) else None
            if event_type in {"final", "error"}:
                self._log_response(chat_req, event)
            yield event

    def _build_envelope(
        self, raw_input: Dict[str, Any], *, prefer_stream: bool
    ) -> tuple[Optional[ChatRequest], Optional[Dict[str, Any]], Optional[Dict[str, Any]], Dict[str, Any]]:
        route_path_list = list(self.ROUTE_PATH)
        route_path_str = "/".join(route_path_list)
        request_id_candidate: Optional[str] = None
        if isinstance(raw_input, dict):
            request_id_value = raw_input.get("request_id")
            if isinstance(request_id_value, str):
                request_id_candidate = request_id_value
        try:
            chat_req = ChatRequest(**raw_input)
        except ValidationError as exc:
            details: Dict[str, Any] = {"errors": exc.errors()}
            if request_id_candidate:
                details["request_id"] = request_id_candidate
            return (
                None,
                None,
                create_error_response(
                    error="Invalid chat request",
                    error_type="INVALID_INPUT",
                    details=details,
                ),
                {
                    "trace_id": request_id_candidate,
                    "request_id": request_id_candidate,
                    "route_path": route_path_str,
                    "details": details,
                },
            )

        payload_data = {"message": chat_req.message, **(chat_req.context or {})}
        payload_data["request_id"] = chat_req.request_id
        payload_data.setdefault("auth_username", chat_req.auth_username)

        envelope = {
            "user": {
                "id": chat_req.user_id,
                "auth_username": chat_req.auth_username,
                "authorization": chat_req.authorization,
            },
            "payload": {
                "route": {"path": route_path_list},
                "data": payload_data,
            },
            "meta": {
                "trace_id": chat_req.request_id,
                "request_id": chat_req.request_id,
                "session_id": chat_req.session_id,
                "prefer_stream": prefer_stream,
            },
        }

        return chat_req, envelope, None, {
            "trace_id": chat_req.request_id,
            "request_id": chat_req.request_id,
            "route_path": route_path_str,
        }

    def _log_request(self, chat_req: ChatRequest, *, prefer_stream: bool) -> None:
        info(
            "chat.request",
            trace_id=chat_req.request_id,
            request_id=chat_req.request_id,
            route_path="/".join(self.ROUTE_PATH),
            user_id=chat_req.user_id,
            session_id=chat_req.session_id,
            message_preview=chat_req.message[:50] if chat_req.message else "",
            stream=prefer_stream,
            has_context=bool(chat_req.context),
        )

    def _log_response(self, chat_req: ChatRequest, result: Any) -> None:
        payload = result if isinstance(result, dict) else {}
        info(
            "chat.response",
            trace_id=chat_req.request_id,
            request_id=chat_req.request_id,
            route_path="/".join(self.ROUTE_PATH),
            user_id=chat_req.user_id,
            session_id=chat_req.session_id,
            success=payload.get("success"),
            error=payload.get("error"),
            error_type=payload.get("error_type"),
            event_type=payload.get("type"),
            handled_by_llm=payload.get("handled_by_llm"),
        )


__all__ = ["create_app", "ChatRequest", "LangServeChatAdapter", "LangServeChatRunnable"]


class LangServeChatRunnable(Runnable):
    """Runnable wrapper delegating to LangServeChatAdapter for LangServe."""

    def __init__(self, adapter: "LangServeChatAdapter") -> None:  # noqa: F821
        self.adapter = adapter

    def invoke(
        self, input: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # Synchronous execution is not supported in this adapter; LangServe uses async paths.
        raise RuntimeError("Synchronous invoke is not supported; use ainvoke instead.")

    async def ainvoke(
        self, input: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return await self.adapter.ainvoke(input, config)

    async def astream(
        self, input: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Any, None]:
        async for event in self.adapter.astream(input, config):
            yield event
