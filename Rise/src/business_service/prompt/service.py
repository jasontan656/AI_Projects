from __future__ import annotations

"""Service layer for prompt CRUD operations."""

from datetime import datetime
from hashlib import sha256
from typing import Any, Mapping, Optional, Sequence, Tuple

from business_service.prompt.models import Prompt, _now_utc
from business_service.prompt.repository import (
    AsyncMongoPromptRepository,
    AsyncPromptRepository,
)


class PromptService:
    def __init__(self, repository: AsyncPromptRepository) -> None:
        self._repository = repository

    async def create_prompt(
        self,
        payload: Mapping[str, Any],
        actor: Optional[str],
    ) -> Tuple[Prompt, Mapping[str, Any]]:
        prompt = Prompt.new(
            name=str(payload["name"]),
            markdown=str(payload["markdown"]),
            actor=actor,
        )
        stored = await self._repository.create(prompt)
        audit_entry = self._build_audit_entry("created", actor, before=None, after=stored)
        return stored, audit_entry

    async def update_prompt(
        self,
        prompt_id: str,
        payload: Mapping[str, Any],
        actor: Optional[str],
    ) -> Tuple[Prompt, Mapping[str, Any]]:
        existing = await self._repository.get(prompt_id)
        if existing is None:
            raise KeyError(prompt_id)
        updates = self._prepare_updates(payload, actor)
        updated = await self._repository.update(prompt_id, updates)
        audit_entry = self._build_audit_entry("updated", actor, before=existing, after=updated)
        return updated, audit_entry

    async def delete_prompt(self, prompt_id: str, actor: Optional[str]) -> Mapping[str, Any]:
        deleted = await self._repository.delete(prompt_id)
        if deleted is None:
            raise KeyError(prompt_id)
        return self._build_audit_entry("deleted", actor, before=deleted, after=None)

    async def list_prompts(self, page: int, page_size: int) -> Tuple[Sequence[Prompt], int]:
        return await self._repository.list_prompts(page=page, page_size=page_size)

    def _prepare_updates(self, payload: Mapping[str, Any], actor: Optional[str]) -> Mapping[str, Any]:
        updates: dict[str, Any] = {}
        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "markdown" in payload:
            updates["markdown"] = str(payload["markdown"])
        updates["updated_by"] = actor
        return updates

    def _build_audit_entry(
        self,
        change_type: str,
        actor: Optional[str],
        *,
        before: Optional[Prompt],
        after: Optional[Prompt],
    ) -> Mapping[str, Any]:
        subject = after or before
        if subject is None:
            raise ValueError("audit entry requires at least one subject")
        entry = {
            "event": "audit.prompt",
            "change_type": change_type,
            "prompt_id": subject.prompt_id,
            "actor": actor or "unknown",
            "timestamp": _now_utc().isoformat(),
            "version": subject.version,
            "markdown_hash": _hash_markdown(subject.markdown),
        }
        if before is not None:
            entry["previous_version"] = before.version
            entry["previous_markdown_hash"] = _hash_markdown(before.markdown)
        return entry


def _hash_markdown(markdown: str) -> str:
    return sha256(markdown.encode("utf-8")).hexdigest()


__all__ = ["PromptService", "AsyncMongoPromptRepository"]
