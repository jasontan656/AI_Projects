#!/usr/bin/env python3
"""
Step-01 import guard:
Scans src/ for cross-layer Python imports and reports any upward dependency
violations defined by PROJECT_STRUCTURE.md. Existing (known) violations can be
recorded in Step-01_import_guard_allowlist.json so CI can fail only on new ones.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[3]
SRC_ROOT = REPO_ROOT / "src"
DEFAULT_REPORT = SCRIPT_DIR / "Step-01_import_guard_report.json"
DEFAULT_ALLOWLIST = SCRIPT_DIR / "Step-01_import_guard_allowlist.json"

# Lower numbers mean deeper/lower layers; higher numbers are closer to interfaces.
LAYER_ORDER: Dict[str, int] = {
    "project_utility": 0,
    "foundational_service": 1,
    "business_service": 2,
    "business_logic": 3,
    "interface_entry": 4,
    "one_off": 5,  # treated separately when imported by core
}


@dataclass(frozen=True)
class ImportViolation:
    source: str
    lineno: int
    imported: str
    module_root: str
    layer_from: str
    layer_to: str

    def serialize(self) -> Dict[str, object]:
        return {
            "source": self.source,
            "lineno": self.lineno,
            "imported": self.imported,
            "module_root": self.module_root,
            "layer_from": self.layer_from,
            "layer_to": self.layer_to,
        }


class ImportCollector(ast.NodeVisitor):
    """Collects import statements while skipping TYPE_CHECKING guards."""

    def __init__(self) -> None:
        super().__init__()
        self.records: List[Tuple[str, int]] = []
        self._tc_depth = 0

    # pylint: disable=invalid-name
    def visit_Import(self, node: ast.Import) -> None:  # type: ignore[override]
        if self._tc_depth > 0:
            return
        for alias in node.names:
            self.records.append((alias.name, node.lineno))

    # pylint: disable=invalid-name
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # type: ignore[override]
        if self._tc_depth > 0:
            return
        if node.module:
            self.records.append((node.module, node.lineno))

    # pylint: disable=invalid-name
    def visit_If(self, node: ast.If) -> None:  # type: ignore[override]
        guard = self._is_type_checking_guard(node.test)
        if guard:
            self._tc_depth += 1
            for child in node.body:
                self.visit(child)
            self._tc_depth -= 1
            for child in node.orelse:
                self.visit(child)
        else:
            for child in node.body:
                self.visit(child)
            for child in node.orelse:
                self.visit(child)

    def _is_type_checking_guard(self, expr: ast.expr) -> bool:
        if isinstance(expr, ast.Name) and expr.id == "TYPE_CHECKING":
            return True
        if isinstance(expr, ast.Attribute):
            value = expr.value
            if (
                isinstance(value, ast.Name)
                and value.id == "typing"
                and expr.attr == "TYPE_CHECKING"
            ):
                return True
        return False


def iter_python_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def layer_for(path: Path) -> Optional[str]:
    try:
        rel = path.relative_to(SRC_ROOT)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 2:
        return None
    return parts[0]


def module_root(module_name: str) -> str:
    return module_name.split(".", 1)[0]


def load_allowlist(path: Path) -> set[Tuple[str, str]]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    allowed: set[Tuple[str, str]] = set()
    if isinstance(data, list):
        for entry in data:
            if not isinstance(entry, dict):
                continue
            source = entry.get("source")
            target = entry.get("imported") or entry.get("module_root") or entry.get("module")
            if isinstance(source, str) and isinstance(target, str):
                allowed.add((source, target))
    return allowed


def save_report(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def analyze(args: argparse.Namespace) -> Dict[str, object]:
    scanned = 0
    errors: List[Dict[str, object]] = []
    potential: List[ImportViolation] = []

    for file_path in iter_python_files(SRC_ROOT):
        src_layer = layer_for(file_path)
        if src_layer is None or src_layer not in LAYER_ORDER:
            continue
        scanned += 1
        try:
            source = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            errors.append(
                {
                    "file": str(file_path.relative_to(REPO_ROOT)),
                    "error": f"SyntaxError: {exc}",
                }
            )
            continue
        collector = ImportCollector()
        collector.visit(tree)
        for module_name, lineno in collector.records:
            root = module_root(module_name)
            if root not in LAYER_ORDER:
                continue
            target_layer = root
            if src_layer == target_layer:
                continue
            src_level = LAYER_ORDER[src_layer]
            target_level = LAYER_ORDER[target_layer]
            if target_level <= src_level:
                continue
            rel_path = file_path.relative_to(REPO_ROOT).as_posix()
            violation = ImportViolation(
                source=rel_path,
                lineno=lineno,
                imported=module_name,
                module_root=root,
                layer_from=src_layer,
                layer_to=target_layer,
            )
            potential.append(violation)
    allowlist = load_allowlist(args.allowlist)
    ignored: List[Dict[str, object]] = []
    new: List[Dict[str, object]] = []
    for violation in potential:
        key = (violation.source, violation.imported)
        if key in allowlist:
            ignored.append(violation.serialize())
        else:
            new.append(violation.serialize())
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "scanned_files": scanned,
        "ci_mode": args.ci,
        "layer_order": LAYER_ORDER,
        "allowlist_path": str(args.allowlist),
        "violations": {
            "new": new,
            "allowlisted": ignored,
        },
        "errors": errors,
    }
    save_report(args.report, report)
    return report


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect upward cross-layer imports.")
    parser.add_argument("--ci", action="store_true", help="Fail when new violations exist.")
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Report output path (default: {DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=DEFAULT_ALLOWLIST,
        help=f"Allowlist JSON path (default: {DEFAULT_ALLOWLIST})",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    report = analyze(args)
    new = report["violations"]["new"]  # type: ignore[index]
    ignored = report["violations"]["allowlisted"]  # type: ignore[index]
    errors = report["errors"]  # type: ignore[index]

    print(f"Scanned files: {report['scanned_files']}")
    print(f"New violations: {len(new)}")
    print(f"Allowlisted violations: {len(ignored)}")
    if errors:
        print(f"Files with parse errors: {len(errors)}", file=sys.stderr)
    if new:
        for item in new:  # type: ignore[assignment]
            src = item['source']
            imported = item['imported']
            print(f"[NEW] {src} imports {imported} (layers {item['layer_from']} -> {item['layer_to']})")
        if args.ci:
            print("New violations detected. Failing because --ci is set.", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
