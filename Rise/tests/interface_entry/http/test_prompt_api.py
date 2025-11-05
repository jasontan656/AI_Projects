from __future__ import annotations

from typing import Any, Dict, Tuple

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from business_service.prompt.models import Prompt, _now_utc
from business_service.prompt.repository import AsyncPromptRepository
from business_service.prompt.service import PromptService
from interface_entry.http.dependencies import get_prompt_service
from interface_entry.http.errors import http_exception_handler, unhandled_exception_handler
from interface_entry.http.prompts import get_router
from interface_entry.http.security import ActorContext, get_actor_context


class InMemoryPromptRepository(AsyncPromptRepository):
    def __init__(self) -> None:
        self._items: Dict[str, Prompt] = {}

    async def create(self, prompt: Prompt) -> Prompt:
        self._items[prompt.prompt_id] = prompt
        return prompt

    async def update(self, prompt_id: str, payload: Dict[str, Any]) -> Prompt:
        prompt = self._items.get(prompt_id)
        if prompt is None:
            raise KeyError(prompt_id)
        updated = Prompt(
            prompt_id=prompt.prompt_id,
            name=str(payload.get("name", prompt.name)),
            markdown=str(payload.get("markdown", prompt.markdown)),
            version=prompt.version + 1,
            created_at=prompt.created_at,
            updated_at=_now_utc(),
            updated_by=payload.get("updated_by", prompt.updated_by),
        )
        self._items[prompt_id] = updated
        return updated

    async def delete(self, prompt_id: str) -> Prompt:
        prompt = self._items.pop(prompt_id, None)
        if prompt is None:
            raise KeyError(prompt_id)
        return prompt

    async def get(self, prompt_id: str) -> Prompt | None:
        return self._items.get(prompt_id)

    async def list_prompts(
        self,
        *,
        page: int,
        page_size: int,
    ) -> Tuple[list[Prompt], int]:
        items = sorted(self._items.values(), key=lambda p: p.updated_at, reverse=True)
        skip = max(0, (page - 1) * page_size)
        sliced = items[skip : skip + page_size]
        return sliced, len(items)


@pytest.fixture()
def app() -> Tuple[FastAPI, InMemoryPromptRepository]:
    repo = InMemoryPromptRepository()
    service = PromptService(repository=repo)

    async def override_prompt_service() -> PromptService:
        return service

    async def override_actor_context() -> ActorContext:
        return ActorContext(actor_id="tester", roles=(), tenant_id=None, request_id="req-1")

    application = FastAPI()
    application.include_router(get_router())
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)
    application.dependency_overrides[get_prompt_service] = override_prompt_service
    application.dependency_overrides[get_actor_context] = override_actor_context
    return application, repo


@pytest.fixture()
def client(app: Tuple[FastAPI, InMemoryPromptRepository]) -> TestClient:
    application, _ = app
    return TestClient(application)


def _extract_data(response_json: Dict[str, Any]) -> Dict[str, Any]:
    assert "data" in response_json
    assert "meta" in response_json
    assert response_json["errors"] == []
    return response_json["data"]


def test_create_prompt_returns_envelope(client: TestClient) -> None:
    response = client.post(
        "/api/prompts",
        json={"name": "Welcome Prompt", "markdown": "# Hello\nThis is prompt."},
    )
    assert response.status_code == 201
    data = _extract_data(response.json())
    assert data["name"] == "Welcome Prompt"
    assert data["version"] == 1


def test_list_prompts_returns_paginated_envelope(client: TestClient) -> None:
    client.post("/api/prompts", json={"name": "A", "markdown": "alpha"})
    client.post("/api/prompts", json={"name": "B", "markdown": "beta"})

    response = client.get("/api/prompts", params={"page": 1, "pageSize": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["pagination"]["total"] == 2
    assert payload["meta"]["pagination"]["page"] == 1
    assert payload["meta"]["pagination"]["pageSize"] == 1
    assert len(payload["data"]["items"]) == 1


def test_update_prompt_increments_version(client: TestClient) -> None:
    created = client.post("/api/prompts", json={"name": "Policy", "markdown": "v1"})
    prompt_id = created.json()["data"]["id"]

    response = client.put(f"/api/prompts/{prompt_id}", json={"markdown": "v2"})
    assert response.status_code == 200
    data = _extract_data(response.json())
    assert data["version"] == 2
    assert data["markdown"] == "v2"


def test_delete_prompt_returns_envelope(client: TestClient) -> None:
    created = client.post("/api/prompts", json={"name": "Temp", "markdown": "tmp"})
    prompt_id = created.json()["data"]["id"]

    response = client.delete(f"/api/prompts/{prompt_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] is None

    response = client.delete(f"/api/prompts/{prompt_id}")
    assert response.status_code == 404
    error = response.json()["errors"][0]
    assert error["code"] == "PROMPT_NOT_FOUND"


@pytest.mark.asyncio
async def test_prompt_service_returns_audit_entry() -> None:
    repo = InMemoryPromptRepository()
    service = PromptService(repository=repo)
    prompt, audit_entry = await service.create_prompt({"name": "Doc", "markdown": "v1"}, actor="tester")
    assert prompt.version == 1
    assert audit_entry["change_type"] == "created"

    updated, audit_entry = await service.update_prompt(prompt.prompt_id, {"markdown": "v2"}, actor="tester")
    assert updated.version == 2
    assert audit_entry["change_type"] == "updated"

    audit_entry = await service.delete_prompt(prompt.prompt_id, actor="tester")
    assert audit_entry["change_type"] == "deleted"
