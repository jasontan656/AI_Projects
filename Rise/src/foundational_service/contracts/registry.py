"""Prompt registry and layout guard helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, TypedDict

from foundational_service.contracts.prompt_registry import PROMPT_REGISTRY as PROMPT_LOADER
from foundational_service.contracts.toolcalls import LayoutMismatch, call_compare_tree, call_scan_tree

__all__ = [
    "PromptCategoryManifest",
    "PROMPT_CATEGORY_MANIFEST",
    "validate_prompt_registry",
    "BehaviorContract",
    "ProjectLayout",
    "TopEntryManifest",
    "behavior_top_entry",
    "call_verify_layout",
    "call_register_channel",
    "behavior_layout_guard",
]


class PromptCategoryManifest(TypedDict):
    categories: list[str]
    mapping: Dict[str, list[str]]


PROMPT_CATEGORY_MANIFEST: PromptCategoryManifest = {
    "categories": [],
    "mapping": {},
}


def validate_prompt_registry(registry: PromptCategoryManifest) -> bool:
    return all(category in registry["mapping"] for category in registry["categories"])


@dataclass(slots=True)
class BehaviorContract:
    """Apply prompt registry and related contracts to the FastAPI app."""

    registry: PromptCategoryManifest = field(default_factory=lambda: PROMPT_CATEGORY_MANIFEST)

    def apply_contract(self, app: Any) -> None:
        if not validate_prompt_registry(self.registry):
            raise ValueError("prompt_registry_incomplete")
        if not hasattr(app, "state"):
            raise AttributeError("FastAPI app 缺少 state 属性")
        app.state.prompt_registry = PROMPT_LOADER  # type: ignore[attr-defined]
        app.state.prompt_category_manifest = self.registry  # type: ignore[attr-defined]


class ProjectLayout(TypedDict):
    app_py: str
    infra: list[str]
    core: list[str]
    telegrambot: list[str]


class TopEntryManifest(TypedDict):
    app_py: str
    directories: list[str]


def behavior_top_entry(layout: ProjectLayout, app: Optional[Any] = None) -> TopEntryManifest:
    directories: list[str] = []
    directories.extend(layout.get("infra", []))
    directories.extend(layout.get("core", []))
    directories.extend(layout.get("telegrambot", []))

    manifest: TopEntryManifest = {
        "app_py": layout["app_py"],
        "directories": directories,
    }
    if app is not None and hasattr(app, "state"):
        app.state.top_entry_manifest = manifest  # type: ignore[attr-defined]
    return manifest


def call_verify_layout(manifest: TopEntryManifest) -> bool:
    required = [manifest["app_py"], *manifest["directories"]]
    return all(Path(item).exists() for item in required)


def call_register_channel(app: Any, module: str) -> None:
    __import__(module)


def behavior_layout_guard(repo_root: Path | str, expected_tree: str, ownership: Mapping[str, Any]) -> Dict[str, Any]:
    """Compare repository layout with expected tree and raise if mismatched."""

    root = Path(repo_root).resolve()
    actual_tree = call_scan_tree(root)
    diff = call_compare_tree(expected_tree, actual_tree)
    report = {
        "tree": actual_tree,
        "expected": expected_tree,
        "ownership": dict(ownership),
        "status": "clean" if not diff else "violation",
        "diff": diff,
    }
    if diff:
        raise LayoutMismatch(
            diff,
            prompt_id="layout_missing_dir",
            prompt_variables={"diff": diff},
            layout_report=report,
        )
    return report
