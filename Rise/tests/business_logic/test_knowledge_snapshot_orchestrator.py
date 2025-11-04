from __future__ import annotations

from pathlib import Path

import yaml

from business_logic.knowledge import KnowledgeSnapshotOrchestrator
from business_service.knowledge import KnowledgeSnapshotService


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")


def test_orchestrator_load_and_refresh(tmp_path: Path) -> None:
    kb_root = tmp_path / "KnowledgeBase"
    org_index_path = kb_root / "KnowledgeBase_index.yaml"

    org_payload = {
        "agencies": [{"agency_id": "test_agency", "name": "Test Agency"}],
        "org_metadata": {"name": "Rise"},
        "routing_table": [],
    }
    _write_yaml(org_index_path, org_payload)

    service = KnowledgeSnapshotService(base_path=kb_root, org_index_path=org_index_path)
    orchestrator = KnowledgeSnapshotOrchestrator(service)

    initial_state = orchestrator.load()
    assert initial_state.status == "memory_only"
    assert initial_state.health["redis_status"] == "skipped"
    assert initial_state.missing_agencies == ["test_agency"]

    agency_index = kb_root / "test_agency" / "test_agency_index.yaml"
    _write_yaml(agency_index, {"services": []})

    refreshed_state = orchestrator.refresh("manual")
    assert refreshed_state.status == "ready"
    assert refreshed_state.missing_agencies == []
    assert refreshed_state.health["redis_status"] in {"skipped", "ready"}
