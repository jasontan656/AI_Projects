"""Chat agent implemented with LangChain 0.3 tool-calling agent."""

from __future__ import annotations

import json
from contextlib import suppress
from typing import Any, AsyncGenerator, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from shared_utilities.validator import ensure_timestamp_uuidv4, normalize_auth_username
try:
    from langchain_openai import ChatOpenAI  # type: ignore
except ImportError:  # pragma: no cover - optional dependency for tests
    ChatOpenAI = None  # type: ignore
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .tool_registry import ToolRegistry
from shared_utilities.retrieval import LocalRetriever
from shared_utilities.response import create_error_response, create_success_response
from hub.logger import error, exception, warning


CHAT_SYSTEM_PROMPT = """
You are a career development assistant that helps users with:
1. Authentication (login, registration, password reset)
2. MBTI personality testing
3. General career-related questions and advice

When users express intent to login, register, or take tests, use the appropriate tool.
If you're uncertain about the user's intent, kindly ask for clarification.
Always be helpful, professional, and concise.
"""


PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", CHAT_SYSTEM_PROMPT),
        MessagesPlaceholder("retrieval_context", optional=True),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(..., description="User's message")
    user_id: str = Field(..., description="User ID if authenticated")
    request_id: str = Field(..., description="Request trace ID for debugging and correlation")
    auth_username: str = Field(default="", description="Auth username (email) accompanying the user")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")
    authorization: Optional[str] = Field(None, description="Authorization token")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")

    @field_validator("user_id")
    def _validate_user_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="user_id")

    @field_validator("request_id")
    def _validate_request_id(cls, value: str) -> str:
        return ensure_timestamp_uuidv4(value, field_name="request_id")

    @field_validator("auth_username", mode="before")
    def _validate_auth_username(cls, value: str | None) -> str:
        return normalize_auth_username(value)


class ChatAgent:
    def __init__(
        self,
        *,
        llm: Optional[Any] = None,
        tool_registry: Optional[ToolRegistry] = None,
        retriever: Optional[LocalRetriever] = None,
    ) -> None:
        if llm is not None:
            self.llm = llm
        else:
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            # Only instantiate OpenAI LLM when API key is configured
            self.llm = ChatOpenAI(streaming=True) if (ChatOpenAI is not None and api_key) else None
        self.tool_registry = tool_registry or ToolRegistry()
        self.retriever = retriever or LocalRetriever()

    def chat(
        self,
        request: Dict[str, Any],
        prefer_stream: bool = False,
        stream_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        try:
            chat_req = ChatRequest(**request)
        except ValidationError as ve:
            warning("chat_agent.invalid_request", error=str(ve))
            return self._err("Invalid request format", "INVALID_INPUT", details=str(ve))

        message = chat_req.message
        user_context = {
            "user_id": chat_req.user_id,
            "auth_username": chat_req.auth_username,
            "session_id": chat_req.session_id,
            "authorization": chat_req.authorization,
            "context": chat_req.context,
        }

        retrieved = self.retriever.retrieve(message, k=3)
        retrieval_messages = [
            SystemMessage(content=f"Context from {source}:\n{snippet}")
            for source, snippet in retrieved
        ]

        if self.llm is None:
            error("chat_agent.llm_not_configured")
            return self._err("Language model dependency is not configured", "DEPENDENCY_ERROR")

        try:
            tools = self.tool_registry.build_langchain_tools(lambda: user_context)
            agent = create_tool_calling_agent(self.llm, tools, PROMPT)
            executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=False,
                return_intermediate_steps=True,
            )
            result = executor.invoke(
                {
                    "input": message,
                    "chat_history": [],
                    "retrieval_context": retrieval_messages,
                }
            )
            output_text = result.get("output", "") if isinstance(result, dict) else str(result)
            stream_chunks: List[str] = []
            if prefer_stream:
                stream_chunks = self._build_stream_chunks(output_text)

            data: Dict[str, Any] = {
                "handled_by_llm": True,
                "raw": result,
                "retrieval": [
                    {"source": source, "text": snippet}
                    for source, snippet in retrieved
                ],
                "result": {
                    "streaming": bool(prefer_stream),
                    "stream_chunks": stream_chunks,
                },
            }
            if stream_callback is not None:
                with suppress(Exception):
                    stream_callback(data)
            return create_success_response(data=data, message=output_text)
        except (AttributeError, TypeError, RuntimeError, ValueError, KeyError) as exc:
            exception("chat_agent.chat_failed", error=str(exc))
            return self._err("Chat processing failed", "DEPENDENCY_ERROR")

    @staticmethod
    def _err(error: str, error_type: str, details: Optional[str] = None) -> Dict[str, Any]:
        detail_payload = {"reason": details} if details else None
        return create_error_response(error=error, error_type=error_type, details=detail_payload)

    @staticmethod
    def _build_stream_chunks(text: str, *, chunk_size: int = 80) -> List[str]:
        """Split text into SSE-friendly chunks without embedded newlines."""
        if not text:
            return []

        chunks: List[str] = []
        for line in text.splitlines():
            if line == "":
                chunks.append("")
                continue
            for idx in range(0, len(line), chunk_size):
                chunks.append(line[idx: idx + chunk_size])
        return chunks

    async def stream_chat(self, request: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Yield streaming events using the model; do not hard-depend on RAG.

        Behavior:
        - Attempt lightweight local retrieval; always emit a 'metrics' event first.
        - Proceed to model streaming; on dependency errors emit an 'error' event.
        """

        try:
            chat_req = ChatRequest(**request)
        except ValidationError as ve:
            warning("chat_agent.invalid_request_stream", error=str(ve))
            yield {
                "type": "error",
                "success": False,
                "error": "Invalid request format",
                "error_type": "INVALID_INPUT",
                "details": {"reason": str(ve)},
            }
            return

        retrieved = self.retriever.retrieve(chat_req.message, k=3)
        retrieval_messages = [
            SystemMessage(content=f"Context from {source}:\n{snippet}")
            for source, snippet in retrieved
        ]
        yield {"type": "metrics", "retrieval_count": len(retrieved)}

        if self.llm is None:
            error("chat_agent.llm_not_configured")
            yield {"type": "error", "error": "Language model dependency is not configured", "error_type": "DEPENDENCY_ERROR"}
            return

        tools = self.tool_registry.build_langchain_tools(
            lambda: {
                "user_id": chat_req.user_id,
                "auth_username": chat_req.auth_username,
                "session_id": chat_req.session_id,
                "authorization": chat_req.authorization,
                "context": chat_req.context,
            }
        )

        try:
            agent = create_tool_calling_agent(self.llm, tools, PROMPT)
            executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=False,
                return_intermediate_steps=True,
            )
            final_text: List[str] = []
            raw_output: Optional[Dict[str, Any]] = None
            async for event in executor.astream_events(
                {
                    "input": chat_req.message,
                    "chat_history": [],
                    "retrieval_context": retrieval_messages,
                },
                version="v1",
            ):
                kind = event.get("event")
                data = event.get("data") or {}

                if kind == "on_tool_end":
                    tool_output = data.get("output")
                    for derived_event in self._tool_output_events(tool_output):
                        yield derived_event
                elif kind == "on_llm_new_token":
                    chunk = data.get("chunk")
                    token = self._safe_chunk_content(chunk)
                    if token:
                        final_text.append(token)
                        yield {"type": "token", "text": token}
                elif kind == "on_chain_end":
                    outputs = data.get("outputs")
                    if isinstance(outputs, dict):
                        raw_output = outputs
            final_message = "".join(final_text)
            yield {
                "type": "final",
                "success": True,
                "message": final_message,
                "raw": raw_output,
                "retrieval": [
                    {"source": source, "text": snippet}
                    for source, snippet in retrieved
                ],
            }
        except (AttributeError, TypeError, RuntimeError, ValueError, KeyError) as exc:  # pragma: no cover - defensive
            exception("chat_agent.stream_failed", error=str(exc))
            yield {"type": "error", "error": "Chat processing failed", "error_type": "DEPENDENCY_ERROR"}

    @staticmethod
    def _safe_chunk_content(chunk: Any) -> str:
        if chunk is None:
            return ""
        if hasattr(chunk, "content"):
            content = chunk.content
            if isinstance(content, list):
                return "".join(str(part) for part in content)
            return str(content)
        if isinstance(chunk, dict):
            value = chunk.get("content")
            if isinstance(value, list):
                return "".join(str(part) for part in value)
            if value is not None:
                return str(value)
        return str(chunk)

    @staticmethod
    def _tool_output_events(tool_output: Any) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        if tool_output is None:
            return events

        payload: Any = tool_output
        if isinstance(tool_output, str):
            try:
                payload = json.loads(tool_output)
            except json.JSONDecodeError:
                return events

        if not isinstance(payload, dict):
            return events

        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}

        ui_spec = data.get("ui")
        if isinstance(ui_spec, dict):
            events.append({"type": "ui", "ui": ui_spec})

        form_data = data.get("form_data")
        if isinstance(form_data, dict):
            ui_event: Dict[str, Any] = {
                "type": "ui",
                "ui": {
                    "type": "form",
                    "schema": form_data.get("form_schema"),
                    "data": form_data.get("initial_data"),
                    "meta": form_data.get("batch_info"),
                },
            }
            events.append(ui_event)

        artifacts = data.get("artifacts") or payload.get("artifacts")
        if isinstance(artifacts, list) and artifacts:
            events.append({"type": "artifact", "artifacts": artifacts})

        return events


__all__ = ["ChatAgent", "ChatRequest"]
