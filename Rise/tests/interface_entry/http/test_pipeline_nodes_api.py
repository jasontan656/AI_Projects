from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from business_service.pipeline.models import PipelineNode, _now_utc
from business_service.pipeline.repository import (
    AsyncPipelineNodeRepository,
    DuplicateNodeNameError,
)
from business_service.pipeline.service import AsyncPipelineNodeService
from interface_entry.http.dependencies import get_pipeline_service
from interface_entry.http.errors import http_exception_handler, unhandled_exception_handler
from interface_entry.http.pipeline_nodes import get_router
from interface_entry.http.security import ActorContext, get_actor_context


class InMemoryPipelineNodeRepository(AsyncPipelineNodeRepository):
    def __init__(self) -> None:
        self._items: Dict[str, PipelineNode] = {}

    async def create(self, node: PipelineNode) -> PipelineNode:
        self._ensure_unique(node.name, node.pipeline_id)
        self._items[node.node_id] = node
        return node

    async def update(self, node_id: str, updates: Dict[str, Any]) -> PipelineNode:
        node = self._items.get(node_id)
        if node is None:
            raise KeyError(node_id)
        name = str(updates.get("name", node.name))
        pipeline_id = updates.get("pipeline_id", node.pipeline_id)
        if name != node.name or pipeline_id != node.pipeline_id:
            self._ensure_unique(name, pipeline_id, exclude=node_id)
        updated = PipelineNode(
            node_id=node.node_id,
            name=name,
            allow_llm=bool(updates.get("allow_llm", node.allow_llm)),
            system_prompt=str(updates.get("system_prompt", node.system_prompt)),
            status=str(updates.get("status", node.status)),
            pipeline_id=pipeline_id,
            strategy=updates.get("strategy", node.strategy) or {},
            version=node.version + 1,
            created_at=node.created_at,
            updated_at=_now_utc(),
            client_created_at=node.client_created_at,
            updated_by=updates.get("updated_by", node.updated_by),
        )
        self._items[node_id] = updated
        return updated

    async def get(self, node_id: str) -> Optional[PipelineNode]:
        return self._items.get(node_id)

    async def list_nodes(
        self,
        pipeline_id: Optional[str],
        status: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[list[PipelineNode], int]:
        items = list(self._items.values())
        if pipeline_id is not None:
            items = [item for item in items if item.pipeline_id == pipeline_id]
        if status:
            items = [item for item in items if item.status == status]
        items.sort(key=lambda n: n.updated_at, reverse=True)
        skip = max(0, (page - 1) * page_size)
        sliced = items[skip : skip + page_size]
        return sliced, len(items)

    async def delete(self, node_id: str) -> Optional[PipelineNode]:
        return self._items.pop(node_id, None)

    def _ensure_unique(self, name: str, pipeline_id: Optional[str], exclude: Optional[str] = None) -> None:
        for node in self._items.values():
            if exclude and node.node_id == exclude:
                continue
            if node.name == name and node.pipeline_id == pipeline_id:
                raise DuplicateNodeNameError(name, pipeline_id)


@pytest.fixture()
def pipeline_app() -> Tuple[FastAPI, InMemoryPipelineNodeRepository]:
    repo = InMemoryPipelineNodeRepository()
    service = AsyncPipelineNodeService(repository=repo)

    async def override_service() -> AsyncPipelineNodeService:
        return service

    async def override_actor() -> ActorContext:
        return ActorContext(actor_id="tester", roles=(), tenant_id=None, request_id="req-1")

    application = FastAPI()
    application.include_router(get_router())
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)
    application.dependency_overrides[get_pipeline_service] = override_service
    application.dependency_overrides[get_actor_context] = override_actor
    return application, repo


@pytest.fixture()
def client(pipeline_app: Tuple[FastAPI, InMemoryPipelineNodeRepository]) -> TestClient:
    application, _ = pipeline_app
    return TestClient(application)


def _payload(name: str = "Node A", pipeline_id: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "allowLLM": True,
        "systemPrompt": "You are a helpful assistant.",
        "createdAt": _now_utc().isoformat(),
        "status": "draft",
        "strategy": {},
    }
    if pipeline_id is not None:
        payload["pipelineId"] = pipeline_id
    return payload


def _response_data(response: Any) -> Dict[str, Any]:
    body = response.json()
    assert body["errors"] == []
    return body["data"]


def test_create_pipeline_node(client: TestClient) -> None:
    response = client.post("/api/pipeline-nodes", json=_payload())
    assert response.status_code == 201
    data = _response_data(response)
    assert data["name"] == "Node A"
    assert data["allowLLM"] is True
    assert data["latestSnapshot"]["systemPrompt"] == "You are a helpful assistant."


def test_update_pipeline_node_increments_version(client: TestClient) -> None:
    created = client.post("/api/pipeline-nodes", json=_payload("Node B"))
    node_id = created.json()["data"]["id"]

    response = client.put(
        f"/api/pipeline-nodes/{node_id}",
        json={"systemPrompt": "Updated prompt", "allowLLM": False},
    )
    assert response.status_code == 200
    data = _response_data(response)
    assert data["version"] == 2
    assert data["allowLLM"] is False
    assert data["latestSnapshot"]["systemPrompt"] == "Updated prompt"


def test_duplicate_name_returns_conflict(client: TestClient) -> None:
    payload = _payload("Node C", pipeline_id="pipe-1")
    assert client.post("/api/pipeline-nodes", json=payload).status_code == 201
    conflict = client.post("/api/pipeline-nodes", json=payload)
    assert conflict.status_code == 409
    error = conflict.json()["errors"][0]
    assert error["code"] == "NODE_NAME_CONFLICT"


def test_list_pipeline_nodes_orders_by_updated_at(client: TestClient) -> None:
    first = client.post("/api/pipeline-nodes", json=_payload("First"))
    first_id = first.json()["data"]["id"]
    client.post("/api/pipeline-nodes", json=_payload("Second"))
    client.put(f"/api/pipeline-nodes/{first_id}", json={"systemPrompt": "Changed"})

    listing = client.get("/api/pipeline-nodes", params={"page": 1, "pageSize": 10})
    assert listing.status_code == 200
    body = listing.json()
    assert body["meta"]["pagination"]["total"] == 2
    names = [item["name"] for item in body["data"]["items"]]
    assert names[0] == "First"
    assert names[1] == "Second"


def test_delete_pipeline_node_success(client: TestClient) -> None:
    created = client.post("/api/pipeline-nodes", json=_payload("Removable"))
    node_id = created.json()["data"]["id"]

    response = client.delete(f"/api/pipeline-nodes/{node_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] is None

    listing = client.get("/api/pipeline-nodes")
    assert listing.json()["data"]["total"] == 0


def test_delete_pipeline_node_not_found(client: TestClient) -> None:
    response = client.delete("/api/pipeline-nodes/non-existent")
    assert response.status_code == 404
    error = response.json()["errors"][0]
    assert error["code"] == "NODE_NOT_FOUND"


def test_list_pipeline_nodes_invalid_page_size(client: TestClient) -> None:
    response = client.get("/api/pipeline-nodes", params={"page": 0})
    assert response.status_code == 422
    error = response.json()["errors"][0]
    assert error["code"] == "INVALID_PAGE"

    response = client.get("/api/pipeline-nodes", params={"page": 1, "pageSize": 0})
    assert response.status_code == 422
    error = response.json()["errors"][0]
    assert error["code"] == "INVALID_PAGE_SIZE"



@pytest.mark.asyncio
async def test_async_pipeline_service_emits_audit_entries() -> None:
    repo = InMemoryPipelineNodeRepository()
    service = AsyncPipelineNodeService(repository=repo)
    payload = _payload("Audit Node")
    node, audit_entry = await service.create_node(payload, actor="tester")
    assert audit_entry["change_type"] == "created"

    updated_payload = {"systemPrompt": "Updated", "allowLLM": False}
    node, audit_entry = await service.update_node(node.node_id, updated_payload, actor="tester")
    assert node.version == 2
    assert audit_entry["change_type"] == "updated"

    audit_entry = await service.delete_node(node.node_id, actor="tester")
    assert audit_entry["change_type"] == "deleted" 

