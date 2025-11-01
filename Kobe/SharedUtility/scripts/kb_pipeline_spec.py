"""KnowledgeBase pipeline specification per WorkPlan/08.md."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence, TypedDict, Literal, Protocol, List, Dict, NotRequired

TITLE: str = "Index 构建与发布流程"

PIPELINE_STEPS: tuple[str, ...] = (
    "lint_yaml",
    "schema_validate",
    "selector_slot_validate",
    "diff_snapshot",
    "publish",
    "notify",
)

REQUIRED_TOOLS: tuple[str, ...] = ("yamllint", "ajv", "pydantic", "sha256sum")


class Approvals(TypedDict):
    kb_owner: int
    arch: int


class KbPipelineConfig(TypedDict, total=False):
    pipeline_steps: Sequence[str]
    required_tools: Sequence[str]
    approvals: Approvals
    publish_targets: Mapping[str, str]
    notifications: Sequence[str]
    rollback_plan: Mapping[str, Any]


class KbPipelineReport(TypedDict, total=False):
    status: Literal["success", "failed"]
    snapshot_path: str
    issues: List[str]
    approvals: Approvals
    duration_ms: float


DEFAULT_PUBLISH_TARGETS: dict[str, str] = {
    "snapshot_path": "{REPO_ROOT}/OpenaiAgents/UnifiedCS/memory/snapshots/{timestamp}.json",
}

DEFAULT_NOTIFICATIONS: tuple[str, ...] = ("plan_autodiscovery_status", "memory_snapshot_ready")

DEFAULT_ROLLBACK_PLAN: dict[str, str] = {
    "restore_snapshot": "scripts/generate_snapshot.py --restore {snapshot}",
    "invalidate_cache": "scripts/check_kb_index.py --invalidate-cache",
    "notify": "kb_pipeline_failed",
}


class PipelineTools(Protocol):
    def run_lint(self, paths: Sequence[Path]) -> None: ...
    def schema_validate(self, paths: Sequence[Path]) -> None: ...
    def selector_slot_validate(self) -> None: ...
    def build_snapshot(self, output_path: Path) -> Path: ...
    def diff_snapshot(self, old: Path, new: Path) -> Mapping[str, Any]: ...
    def publish(self, source: Path, destination: Path) -> None: ...
    def notify(self, prompt_id: str, payload: Mapping[str, Any]) -> None: ...


PIPELINE_EVENT_LOG: list[Mapping[str, Any]] = []


def compute_snapshot_path(template: str, now: datetime | None = None) -> Path:
    moment = now or datetime.utcnow()
    return Path(template.format(timestamp=moment.strftime("%Y-%m-%d_%H-%M-%S")))


def compute_sha256(path: Path) -> str:
    digest = sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def call_run_lint(paths: Sequence[Path], runner: Callable[[Sequence[Path]], None]) -> None:
    runner(paths)


def call_diff_snapshot(
    old: Path,
    new: Path,
    diff_runner: Callable[[Path, Path], Mapping[str, Any]],
) -> Mapping[str, Any]:
    diff = diff_runner(old, new)
    checksum = compute_sha256(new)
    return {**diff, "checksum": checksum}


def call_publish_snapshot(source: Path, destination: Path, publisher: Callable[[Path, Path], None]) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    publisher(source, destination)
    return destination


def call_notify(prompt_id: str, payload: Mapping[str, Any], notifier: Callable[[str, Mapping[str, Any]], None]) -> None:
    notifier(prompt_id, payload)


def log_pipeline_event(event: Mapping[str, Any]) -> None:
    PIPELINE_EVENT_LOG.append(dict(event))


def behavior_kb_pipeline(
    kb_root: Path,
    tools: PipelineTools,
    config: KbPipelineConfig | None = None,
    now: datetime | None = None,
) -> KbPipelineReport:
    cfg = config or {
        "pipeline_steps": PIPELINE_STEPS,
        "required_tools": REQUIRED_TOOLS,
        "approvals": {"kb_owner": 1, "arch": 1},
        "publish_targets": DEFAULT_PUBLISH_TARGETS,
        "notifications": list(DEFAULT_NOTIFICATIONS),
        "rollback_plan": DEFAULT_ROLLBACK_PLAN,
    }
    issues: list[str] = []
    start = datetime.utcnow()
    try:
        yaml_files = list(kb_root.glob("**/*.yaml"))
        call_run_lint(yaml_files, tools.run_lint)
        tools.schema_validate(yaml_files)
        tools.selector_slot_validate()
        snapshot_template = cfg.get("publish_targets", DEFAULT_PUBLISH_TARGETS)["snapshot_path"]
        new_snapshot = tools.build_snapshot(compute_snapshot_path(snapshot_template, now))
        previous_snapshot = new_snapshot.with_suffix(".prev.json")
        diff_payload = call_diff_snapshot(previous_snapshot, new_snapshot, tools.diff_snapshot)
        published_path = call_publish_snapshot(new_snapshot, new_snapshot, tools.publish)
        notify_payload = {
            "snapshot_path": str(published_path),
            "checksum": diff_payload.get("checksum"),
        }
        for prompt_id in cfg.get("notifications", DEFAULT_NOTIFICATIONS):
            call_notify(prompt_id, notify_payload, tools.notify)
        status: Literal["success", "failed"] = "success"
    except Exception as exc:  # noqa: BLE001
        issues.append(str(exc))
        status = "failed"
        rollback = cfg.get("rollback_plan", DEFAULT_ROLLBACK_PLAN)
        log_pipeline_event({"event": "rollback", "plan": rollback, "error": str(exc)})
    duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
    log_pipeline_event(
        {
            "stage": "kb_pipeline",
            "status": status,
            "duration_ms": duration_ms,
            "issues": issues,
        }
    )
    report: KbPipelineReport = {
        "status": status,
        "snapshot_path": cfg.get("publish_targets", DEFAULT_PUBLISH_TARGETS)["snapshot_path"],
        "issues": issues,
        "approvals": cfg.get("approvals", {"kb_owner": 0, "arch": 0}),
        "duration_ms": duration_ms,
    }
    return report
