import asyncio
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from business_service.conversation.service import AsyncResultHandle, TelegramConversationService


class StubBroker:
    def __init__(self) -> None:
        self.waiters: Dict[str, asyncio.Future] = {}

    async def register(self, task_id: str) -> asyncio.Future:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self.waiters[task_id] = fut
        return fut

    async def discard(self, task_id: str, waiter: asyncio.Future) -> None:
        self.waiters.pop(task_id, None)


class StubRuntime:
    def __init__(self) -> None:
        self.results = StubBroker()


class StubSubmitter:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.envelopes: list[Any] = []

    async def submit(self, envelope: Any) -> None:
        self.envelopes.append(envelope)
        if self.should_fail:
            raise RuntimeError("queue down")


@pytest.fixture(autouse=True)
def stub_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_inbound(update: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
        message = update.get("message", {})
        chat = message.get("chat", {})
        core_envelope = {
            "metadata": {
                "chat_id": str(chat.get("id", "0")),
                "convo_id": str(chat.get("id", "0")),
                "language": "en",
            },
            "payload": {
                "user_message": message.get("text", ""),
                "context_quotes": [],
            },
        }
        return {
            "response_status": "handled",
            "core_envelope": core_envelope,
            "envelope": core_envelope,
            "logging": {},
            "telemetry": {"update_type": "message"},
        }

    def fake_outbound(chunks: Any, policy: Dict[str, Any]) -> Dict[str, Any]:
        text = "\n".join(chunks)
        return {
            "text": text,
            "metrics": {"chunk_metrics": [], "total_chars": len(text)},
            "placeholder": "",
            "edits": [],
        }

    monkeypatch.setattr(
        "business_service.conversation.service.contracts_telegram_inbound",
        fake_inbound,
    )
    monkeypatch.setattr(
        "business_service.conversation.service.contracts_telegram_outbound",
        fake_outbound,
    )
    monkeypatch.setattr(
        "business_service.conversation.service.toolcalls.call_validate_telegram_adapter_contract",
        lambda contract: None,
    )


@pytest.mark.asyncio
async def test_async_ack_attaches_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = StubRuntime()
    submitter = StubSubmitter()
    service = TelegramConversationService(
        task_submitter_factory=lambda: submitter,
        task_runtime_factory=lambda: SimpleNamespace(results=runtime.results),
    )
    policy = {
        "workflow_id": "wf-1",
        "entrypoints": {"telegram": {"wait_for_result": False}},
    }
    update = {"message": {"text": "hi", "message_id": 5, "chat": {"id": 42}}}

    result = await service.process_update(update, policy=policy)

    handle = result.agent_response.get("async_handle")
    assert result.mode == "queued"
    assert isinstance(handle, AsyncResultHandle)
    assert submitter.envelopes, "task should be enqueued"

    payload = {
        "status": "completed",
        "result": {
            "finalText": "pong",
            "stageResults": [],
            "telemetry": {},
        },
    }
    handle.waiter.set_result(payload)
    follow_up = await handle.resolve()
    assert follow_up.agent_response["text"] == "pong"


@pytest.mark.asyncio
async def test_idempotency_uses_message_id(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = StubRuntime()
    submitter = StubSubmitter()
    service = TelegramConversationService(
        task_submitter_factory=lambda: submitter,
        task_runtime_factory=lambda: SimpleNamespace(results=runtime.results),
    )
    policy = {"workflow_id": "wf-2"}
    update = {"message": {"text": "ping", "message_id": 9, "chat": {"id": 77}}}

    await service.process_update(update, policy=policy)

    envelope = submitter.envelopes[-1]
    assert envelope.context["idempotencyKey"].endswith(":77:9"), envelope.context["idempotencyKey"]


@pytest.mark.asyncio
async def test_enqueue_failure_returns_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = StubRuntime()
    submitter = StubSubmitter(should_fail=True)
    service = TelegramConversationService(
        task_submitter_factory=lambda: submitter,
        task_runtime_factory=lambda: SimpleNamespace(results=runtime.results),
    )
    policy = {"workflow_id": "wf-err"}
    update = {"message": {"text": "hi", "message_id": 11, "chat": {"id": 1}}}

    result = await service.process_update(update, policy=policy)

    assert result.agent_response["text"].startswith("当前对话系统繁忙")
    assert result.telemetry.get("queue_status") == "enqueue_failed"


@pytest.mark.asyncio
async def test_workflow_missing_returns_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = StubRuntime()
    submitter = StubSubmitter()
    service = TelegramConversationService(
        task_submitter_factory=lambda: submitter,
        task_runtime_factory=lambda: SimpleNamespace(results=runtime.results),
    )
    policy = {"entrypoints": {"telegram": {"workflow_missing_text": "流程缺失"}}}
    update = {"message": {"text": "test", "message_id": 2, "chat": {"id": 99}}}

    result = await service.process_update(update, policy=policy)

    assert result.status == "ignored"
    assert result.agent_response["text"] == "流程缺失"

