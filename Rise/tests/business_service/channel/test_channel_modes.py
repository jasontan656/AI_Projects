from __future__ import annotations

import importlib
import sys
import types
from typing import Any, Dict, Optional


if "project_utility.secrets" not in sys.modules:
    fake_secrets = types.ModuleType("project_utility.secrets")

    class _FakeSecretBox:
        def encrypt(self, value: str) -> str:
            return value

        def decrypt(self, token: str) -> str:
            return token

    def _get_secret_box(_: str) -> _FakeSecretBox:
        return _FakeSecretBox()

    def _mask_secret(value: Optional[str], *, head: int = 6, tail: int = 4) -> str:
        return value or ""

    fake_secrets.SecretBox = _FakeSecretBox
    fake_secrets.get_secret_box = _get_secret_box
    fake_secrets.mask_secret = _mask_secret
    sys.modules["project_utility.secrets"] = fake_secrets
    try:
        pkg = importlib.import_module("project_utility")
        setattr(pkg, "secrets", fake_secrets)
    except ModuleNotFoundError:
        pass

import pytest

from business_service.channel.models import ChannelMode, WorkflowChannelPolicy
from business_service.channel.service import ChannelValidationError, WorkflowChannelService
from project_utility import secrets


class FakeChannelRepository:
    def __init__(self) -> None:
        self.saved: Optional[WorkflowChannelPolicy] = None

    async def get(self, workflow_id: str, channel: str) -> Optional[WorkflowChannelPolicy]:
        return self.saved

    async def upsert(self, policy: WorkflowChannelPolicy) -> WorkflowChannelPolicy:
        self.saved = policy
        return policy

    async def delete(self, workflow_id: str, channel: str) -> bool:
        if self.saved and self.saved.workflow_id == workflow_id:
            self.saved = None
            return True
        return False

    async def list_by_channel(self, channel: str) -> list[WorkflowChannelPolicy]:
        return [self.saved] if self.saved else []


class FakeWorkflowRepository:
    def __init__(self, workflow: Optional[Any] = None) -> None:
        self.workflow = workflow

    async def list_workflows(self) -> list[Any]:
        return [self.workflow] if self.workflow else []

    async def get(self, workflow_id: str) -> Optional[Any]:
        if self.workflow and getattr(self.workflow, "workflow_id", None) == workflow_id:
            return self.workflow
        return None

    async def update(self, workflow_id: str, updates: Dict[str, Any], *, increment_version: bool = True) -> Any:
        if self.workflow and getattr(self.workflow, "workflow_id", None) == workflow_id:
            for key, value in updates.items():
                if hasattr(self.workflow, key):
                    setattr(self.workflow, key, value)
            return self.workflow
        return {"workflow_id": workflow_id, **updates}


def _service(workflow: Optional[Any] = None) -> WorkflowChannelService:
    repo = FakeChannelRepository()
    workflow_repo = FakeWorkflowRepository(workflow=workflow)
    return WorkflowChannelService(repository=repo, workflow_repository=workflow_repo)


def _payload(**overrides: Any) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "botToken": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef",
        "webhookUrl": "https://rise.test/webhook",
        "waitForResult": True,
        "workflowMissingMessage": "Workflow unavailable, please contact the operator.",
        "timeoutMessage": "Workflow timeout, please try again.",
        "metadata": {"allowedChatIds": ["1234567890"]},
        "usePolling": False,
    }
    data.update(overrides)
    return data


class _FakeWorkflow:
    def __init__(self, workflow_id: str, *, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.workflow_id = workflow_id
        self.name = workflow_id
        self.metadata = metadata or {}
        self.published_version = 1


@pytest.fixture(autouse=True)
def _tele_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_TOKEN_SECRET", "test-telegram-secret")
    if hasattr(secrets.get_secret_box, "cache_clear"):
        secrets.get_secret_box.cache_clear()


@pytest.mark.asyncio
async def test_save_policy_blocks_polling_with_webhook() -> None:
    service = _service()
    payload = _payload(usePolling=True)
    with pytest.raises(ChannelValidationError) as exc:
        await service.save_policy("wf-01", payload, actor="alice")
    assert exc.value.code == "CHANNEL_MODE_CONFLICT"
    assert "webhookUrl" in str(exc.value)


@pytest.mark.asyncio
async def test_save_policy_accepts_polling_without_webhook() -> None:
    service = _service()
    payload = _payload(usePolling=True)
    payload.pop("webhookUrl", None)
    policy = await service.save_policy("wf-02", payload, actor="ops")
    assert policy.mode is ChannelMode.POLLING
    assert policy.webhook_url == ""


@pytest.mark.asyncio
async def test_save_policy_requires_webhook_for_webhook_mode() -> None:
    service = _service()
    payload = _payload()
    payload.pop("webhookUrl", None)
    with pytest.raises(ChannelValidationError) as exc:
        await service.save_policy("wf-03", payload, actor="ops")
    assert exc.value.code == "WEBHOOK_REQUIRED"


@pytest.mark.asyncio
async def test_get_binding_view_populates_binding_option() -> None:
    workflow = _FakeWorkflow(
        "wf-99",
        metadata={"channels": {"telegram": {"enabled": True, "killSwitch": False}}},
    )
    service = _service(workflow=workflow)
    await service.save_policy("wf-99", _payload(), actor="ops")

    option = await service.get_binding_view("wf-99", channel="telegram")

    assert option.workflow_id == "wf-99"
    assert option.is_bound is True
    assert option.kill_switch is False
