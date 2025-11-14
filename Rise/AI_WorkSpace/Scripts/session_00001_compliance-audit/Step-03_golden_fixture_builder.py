from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = ROOT / "tests" / "business_service" / "conversation" / "fixtures"
SANITIZED_STRING = "REDACTED"
ID_MASK = 999999
TEXT_ALLOWLIST = {"/passport_status"}

SENSITIVE_FIELDS = {"first_name", "last_name", "username", "title"}
PATTERN_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+")
PATTERN_PHONE = re.compile(r"\\+?\\d{8,}")


def _clean_values(node: Any) -> Any:
    if isinstance(node, dict):
        cleaned: Dict[str, Any] = {}
        for key, value in node.items():
            if key in {"id", "chat_id"} and isinstance(value, int):
                cleaned[key] = ID_MASK
            elif key in SENSITIVE_FIELDS:
                cleaned[key] = SANITIZED_STRING
            elif isinstance(value, (dict, list)):
                cleaned[key] = _clean_values(value)
            else:
                cleaned[key] = value
        return cleaned
    if isinstance(node, list):
        return [_clean_values(item) for item in node]
    return node


def _verify_payload(node: Any, *, path: str) -> Iterable[str]:
    issues: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            sub_path = f"{path}.{key}" if path else key
            if isinstance(value, str):
                if key not in SENSITIVE_FIELDS and value not in TEXT_ALLOWLIST:
                    if PATTERN_EMAIL.search(value) or PATTERN_PHONE.search(value):
                        issues.append(f"{sub_path} 包含潜在敏感数据: {value}")
            issues.extend(_verify_payload(value, path=sub_path))
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            issues.extend(_verify_payload(value, path=f"{path}[{idx}]"))
    return issues


def sanitize_fixture(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sanitized = _clean_values(payload)
    path.write_text(json.dumps(sanitized, ensure_ascii=False, indent=2), encoding="utf-8")


def verify_fixture(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    issues = list(_verify_payload(payload, path=""))
    if issues:
        joined = "\\n".join(issues)
        raise SystemExit(f"{path.name} 验证失败:\\n{joined}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sanitize/verify Telegram Golden fixtures.")
    parser.add_argument("--verify", action="store_true", help="仅执行脱敏验证")
    args = parser.parse_args()
    fixture_paths = sorted(FIXTURE_ROOT.rglob("*.json"))
    if not fixture_paths:
        raise SystemExit("未找到任何 JSON 夹具")
    for path in fixture_paths:
        if args.verify:
            verify_fixture(path)
        else:
            sanitize_fixture(path)
            verify_fixture(path)


if __name__ == "__main__":
    main()
