from __future__ import annotations

"""Service layer bridging HTTP DTOs and the pipeline node repository."""

from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from business_service.pipeline.models import PipelineNode, _now_utc
from business_service.pipeline.repository import (
    AsyncPipelineNodeRepository,
    DuplicateNodeNameError,
    MongoPipelineNodeRepository,
    PipelineNodeRepository,
)
from foundational_service.contracts.toolcalls import call_record_audit


class PipelineNodeService:
    """High level API for managing pipeline nodes."""

    def __init__(self, repository: PipelineNodeRepository) -> None:
        self._repository = repository

    def create_node(self, payload: Mapping[str, Any], actor: Optional[str]) -> PipelineNode:
        node = PipelineNode.new(
            name=str(payload["name"]),
            allow_llm=bool(payload["allowLLM"]),
            system_prompt=str(payload["systemPrompt"]),
            status=str(payload.get("status") or "draft"),
            pipeline_id=_normalize_pipeline_id(payload.get("pipelineId")),
            strategy=payload.get("strategy") or {},
            client_created_at=_parse_datetime(payload.get("createdAt")),
            actor=actor,
        )
        stored = self._repository.create(node)
        self._record_audit("created", actor, before=None, after=stored)
        return stored

    def update_node(
        self,
        node_id: str,
        payload: Mapping[str, Any],
        actor: Optional[str],
    ) -> PipelineNode:
        existing = self._repository.get(node_id)
        if existing is None:
            raise KeyError(node_id)

        updates = self._prepare_updates(payload, actor=actor)
        updated = self._repository.update(node_id, updates)
        self._record_audit("updated", actor, before=existing, after=updated)
        return updated

    def get_node(self, node_id: str) -> Optional[PipelineNode]:
        return self._repository.get(node_id)

    def list_nodes(
        self,
        pipeline_id: Optional[str],
        status: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[Sequence[PipelineNode], int]:
        return self._repository.list_nodes(
            pipeline_id=pipeline_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    def delete_node(self, node_id: str, actor: Optional[str]) -> None:
        existing = self._repository.get(node_id)
        if existing is None:
            raise KeyError(node_id)
        deleted = self._repository.delete(node_id)
        if deleted is None:
            raise KeyError(node_id)
        self._record_audit("deleted", actor, before=existing, after=None)

    def _prepare_updates(self, payload: Mapping[str, Any], *, actor: Optional[str]) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "allowLLM" in payload:
            updates["allow_llm"] = bool(payload["allowLLM"])
        if "systemPrompt" in payload:
            updates["system_prompt"] = str(payload["systemPrompt"])
        if "status" in payload:
            updates["status"] = str(payload["status"] or "draft")
        if "pipelineId" in payload:
            updates["pipeline_id"] = _normalize_pipeline_id(payload.get("pipelineId"))
        if "strategy" in payload:
            updates["strategy"] = payload.get("strategy") or {}
        updates["updated_by"] = actor
        return updates

    def _record_audit(
        self,
        change_type: str,
        actor: Optional[str],
        before: Optional[PipelineNode],
        after: Optional[PipelineNode],
    ) -> None:
        subject = after or before
        if subject is None:
            return
        entry = {
            "event": "audit.pipeline_node",
            "change_type": change_type,
            "node_id": subject.node_id,
            "actor": actor or "unknown",
            "timestamp": _now_utc().isoformat(),
            "version": subject.version,
            "allow_llm": subject.allow_llm,
            "strategy": subject.strategy,
            "system_prompt_hash": _hash_prompt(subject.system_prompt),
        }
        if before is not None:
            entry["previous_version"] = before.version
            entry["previous_allow_llm"] = before.allow_llm
            entry["previous_system_prompt_hash"] = _hash_prompt(before.system_prompt)
        call_record_audit(entry)


class AsyncPipelineNodeService:
    """Async variant of pipeline node service using Motor repositories."""

    def __init__(self, repository: AsyncPipelineNodeRepository) -> None:
        self._repository = repository

    async def create_node(
        self,
        payload: Mapping[str, Any],
        actor: Optional[str],
    ) -> Tuple[PipelineNode, Mapping[str, Any]]:
        node = PipelineNode.new(
            name=str(payload["name"]),
            allow_llm=bool(payload["allowLLM"]),
            system_prompt=str(payload["systemPrompt"]),
            status=str(payload.get("status") or "draft"),
            pipeline_id=_normalize_pipeline_id(payload.get("pipelineId")),
            strategy=payload.get("strategy") or {},
            client_created_at=_parse_datetime(payload.get("createdAt")),
            actor=actor,
        )
        stored = await self._repository.create(node)
        audit_entry = self._build_audit_entry("created", actor, before=None, after=stored)
        return stored, audit_entry

    async def update_node(
        self,
        node_id: str,
        payload: Mapping[str, Any],
        actor: Optional[str],
    ) -> Tuple[PipelineNode, Mapping[str, Any]]:
        existing = await self._repository.get(node_id)
        if existing is None:
            raise KeyError(node_id)
        updates = self._prepare_updates(payload, actor=actor)
        updated = await self._repository.update(node_id, updates)
        audit_entry = self._build_audit_entry("updated", actor, before=existing, after=updated)
        return updated, audit_entry

    async def get_node(self, node_id: str) -> Optional[PipelineNode]:
        return await self._repository.get(node_id)

    async def list_nodes(
        self,
        pipeline_id: Optional[str],
        status: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[Sequence[PipelineNode], int]:
        return await self._repository.list_nodes(
            pipeline_id=pipeline_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    async def delete_node(self, node_id: str, actor: Optional[str]) -> Mapping[str, Any]:
        existing = await self._repository.get(node_id)
        if existing is None:
            raise KeyError(node_id)
        deleted = await self._repository.delete(node_id)
        if deleted is None:
            raise KeyError(node_id)
        return self._build_audit_entry("deleted", actor, before=existing, after=None)

    def _prepare_updates(self, payload: Mapping[str, Any], *, actor: Optional[str]) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "allowLLM" in payload:
            updates["allow_llm"] = bool(payload["allowLLM"])
        if "systemPrompt" in payload:
            updates["system_prompt"] = str(payload["systemPrompt"])
        if "status" in payload:
            updates["status"] = str(payload["status"] or "draft")
        if "pipelineId" in payload:
            updates["pipeline_id"] = _normalize_pipeline_id(payload.get("pipelineId"))
        if "strategy" in payload:
            updates["strategy"] = payload.get("strategy") or {}
        updates["updated_by"] = actor
        return updates

    def _build_audit_entry(
        self,
        change_type: str,
        actor: Optional[str],
        *,
        before: Optional[PipelineNode],
        after: Optional[PipelineNode],
    ) -> Mapping[str, Any]:
        subject = after or before
        if subject is None:
            raise ValueError("audit entry requires at least one subject")
        entry = {
            "event": "audit.pipeline_node",
            "change_type": change_type,
            "node_id": subject.node_id,
            "actor": actor or "unknown",
            "timestamp": _now_utc().isoformat(),
            "version": subject.version,
            "allow_llm": subject.allow_llm,
            "strategy": subject.strategy,
            "system_prompt_hash": _hash_prompt(subject.system_prompt),
        }
        if before is not None:
            entry["previous_version"] = before.version
            entry["previous_allow_llm"] = before.allow_llm
            entry["previous_system_prompt_hash"] = _hash_prompt(before.system_prompt)
        return entry

def _hash_prompt(prompt: str) -> str:
    return sha256(prompt.encode("utf-8")).hexdigest()


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _normalize_pipeline_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)
