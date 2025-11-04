from __future__ import annotations

from business_service.knowledge import KnowledgeSnapshotService


def test_asset_guard_reports_missing_components(tmp_path) -> None:
    report = KnowledgeSnapshotService.asset_guard(tmp_path)
    assert report.status == "violation"
    assert "KnowledgeBase" in report.missing_dirs
