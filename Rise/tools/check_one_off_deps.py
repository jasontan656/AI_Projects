"""Ensure production packages do not import one_off utilities."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

SKIP_DIRS = {
    ".git",
    ".venv",
    ".venvwsl",
    ".venv_cli",
    "AI_WorkSpace",
    "doc",
    "openspec",
    "openai_agents",
    "src/one_off",
    "tools",
}


def iter_python_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.py")):
        parts = set(path.parts)
        if any(part in SKIP_DIRS for part in parts):
            continue
        if "one_off" in parts:
            continue
        yield path


def has_forbidden_import(path: Path) -> List[Tuple[str, int]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    violations: List[Tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "one_off" or alias.name.startswith("one_off."):
                    violations.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "one_off" or module.startswith("one_off."):
                violations.append((module, node.lineno))
    return violations


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    any_failures = False
    for path in iter_python_files(repo):
        violations = has_forbidden_import(path)
        if not violations:
            continue
        any_failures = True
        for module, lineno in violations:
            print(f"{path}: forbidden import '{module}' at line {lineno}", file=sys.stderr)
    return 1 if any_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
