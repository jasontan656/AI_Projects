from __future__ import annotations

import copy
from datetime import datetime, timezone

import pytest

from business_service.workflow.models import WorkflowPublishRecord
from business_service.workflow.workflow_history_repository import (
    WorkflowHistoryRepository,
    calculate_history_checksum,
)
from business_service.workflow.workflow_repository import _build_workflow_update_command


class FakeCursor:
    def __init__(self, documents):
        self._docs = list(documents)

    def sort(self, field, direction):
        reverse = direction < 0
        self._docs.sort(key=lambda item: item.get(field, 0), reverse=reverse)
        return self

    def limit(self, amount):
        self._docs = self._docs[:amount]
        return self

    def __iter__(self):
        for doc in self._docs:
            yield copy.deepcopy(doc)


class FakeCollection:
    def __init__(self):
        self._documents: list[dict] = []

    def create_index(self, *_args, **_kwargs):
        return None

    def insert_one(self, document):
        self._documents.append(copy.deepcopy(document))

    def find(self, query):
        matched = []
        for doc in self._documents:
            if all(doc.get(key) == value for key, value in query.items()):
                matched.append(doc)
        return FakeCursor(matched)

    def find_one(self, query):
        for doc in self._documents:
            if all(doc.get(key) == value for key, value in query.items()):
                return copy.deepcopy(doc)
        return None


def _record(version: int, diff: str = "X") -> WorkflowPublishRecord:
    return WorkflowPublishRecord(
        version=version,
        action="publish",
        actor="tester",
        comment=None,
        timestamp=datetime(2025, 1, version, tzinfo=timezone.utc),
        snapshot={"name": f"workflow-v{version}"},
        diff={"changed": diff},
    )


def test_workflow_history_repository_append_and_list() -> None:
    collection = FakeCollection()
    repository = WorkflowHistoryRepository(collection)  # type: ignore[arg-type]
    repository.append("wf-1", _record(1))
    repository.append("wf-1", _record(2))

    history = repository.list_history("wf-1", limit=10)

    assert [record.version for record in history] == [1, 2]
    stored = collection.find_one({"workflow_id": "wf-1", "version": 2})
    assert stored is not None
    assert stored["record_checksum"]


def test_calculate_history_checksum_changes_on_snapshot_delta() -> None:
    history_a = (_record(1, diff="A"), _record(2, diff="B"))
    history_b = (_record(1, diff="A"), _record(2, diff="C"))

    checksum_a = calculate_history_checksum(history_a)
    checksum_b = calculate_history_checksum(history_b)

    assert checksum_a != checksum_b


def test_build_workflow_update_command_includes_history_checksum() -> None:
    command = _build_workflow_update_command(
        {},
        status="published",
        pending_changes=False,
        published_version=3,
        publish_record=_record(3),
        increment_version=True,
        history_checksum="abc123",
    )

    assert command["$set"]["history_checksum"] == "abc123"
    assert "$push" in command and "publish_history" in command["$push"]
