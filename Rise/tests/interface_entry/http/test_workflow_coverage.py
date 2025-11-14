from __future__ import annotations

import sys
import types

if "project_utility.secrets" not in sys.modules:
    secrets_module = types.ModuleType("project_utility.secrets")

    class _DummyBox:
        def encrypt(self, value: bytes) -> bytes:
            return value

        def decrypt(self, value: bytes) -> bytes:
            return value

    def _get_secret_box(*args, **kwargs):
        return _DummyBox()

    def _mask_secret(value):
        return value

    secrets_module.get_secret_box = _get_secret_box
    secrets_module.mask_secret = _mask_secret
    sys.modules["project_utility.secrets"] = secrets_module

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from business_service.channel.coverage_status import WorkflowCoverageStatus
from business_service.workflow.models import WorkflowDefinition
from interface_entry.http import dependencies as deps
from interface_entry.http.security import ActorContext, get_actor_context
from interface_entry.http.workflows.routes import router


class FakeWorkflowService:
    def __init__(self, workflow: WorkflowDefinition) -> None:
        self._workflow = workflow

    async def get(self, workflow_id: str) -> WorkflowDefinition | None:
        return self._workflow if workflow_id == self._workflow.workflow_id else None

    async def list(self):
        return [self._workflow]


class FakeCoverageService:
    def __init__(self, status: WorkflowCoverageStatus) -> None:
        self._status = status
        self.last_args = None

    async def get_status(self, workflow_id: str) -> WorkflowCoverageStatus:
        return self._status

    async def mark_status(self, workflow_id: str, **kwargs):
        self.last_args = {"workflow_id": workflow_id, **kwargs}
        return self._status


class FakeActor(ActorContext):
    def __init__(self, actor_id: str) -> None:
        self.actor_id = actor_id


@pytest.fixture()
def api_client():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    yield app, client


def _build_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="wf-passport",
        name="Passport Status",
        description="",
        stage_ids=("stage-1",),
        metadata={},
        node_sequence=("node-1",),
        prompt_bindings=(),
        strategy={},
    )


def _coverage(status: str = "green") -> WorkflowCoverageStatus:
    from datetime import datetime, timezone

    return WorkflowCoverageStatus(
        workflow_id="wf-passport",
        status=status,
        updated_at=datetime.now(timezone.utc),
        scenarios=["passport_text"],
    )


def test_get_workflow_includes_coverage(api_client, monkeypatch):
    app, client = api_client
    workflow = _build_workflow()
    coverage = _coverage("green")

    app.dependency_overrides[deps.get_workflow_service] = lambda: FakeWorkflowService(workflow)
    app.dependency_overrides[deps.get_coverage_status_service] = lambda: FakeCoverageService(coverage)

    response = client.get("/api/workflows/wf-passport")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["testCoverage"]["status"] == "green"

    app.dependency_overrides = {}


def test_trigger_tests_marks_pending(api_client):
    app, client = api_client
    workflow = _build_workflow()
    coverage = _coverage("pending")
    coverage_service = FakeCoverageService(coverage)

    app.dependency_overrides[deps.get_workflow_service] = lambda: FakeWorkflowService(workflow)
    app.dependency_overrides[deps.get_coverage_status_service] = lambda: coverage_service
    app.dependency_overrides[get_actor_context] = lambda: FakeActor("operator-1")

    response = client.post("/api/workflows/wf-passport/tests/run", json={"scenarios": ["passport_text"]})
    assert response.status_code == 202
    assert response.json()["data"]["status"] == "pending"
    assert coverage_service.last_args["scenarios"] == ["passport_text"]

    app.dependency_overrides = {}
