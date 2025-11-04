"""Verify that project_utility modules do not import higher-layer packages."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

FORBIDDEN_PREFIXES = (
    "shared_utility.",
    "interface_entry",
    "openai_agents",
)


def iter_python_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.py")):
        yield path


def check_file(path: Path) -> List[Tuple[str, int]]:
    violations: List[Tuple[str, int]] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if is_forbidden(alias.name):
                    violations.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level != 0:
                continue
            if is_forbidden(module):
                violations.append((module, node.lineno))
    return violations


def is_forbidden(module: str) -> bool:
    return module.startswith(FORBIDDEN_PREFIXES)


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "src" / "project_utility"
    if not root.exists():
        print("project_utility package not found", file=sys.stderr)
        return 1

    any_failures = False
    for path in iter_python_files(root):
        violations = check_file(path)
        if not violations:
            continue
        any_failures = True
        for module, lineno in violations:
            print(f"{path}: forbidden import '{module}' at line {lineno}", file=sys.stderr)

    return 1 if any_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
