import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional


DEFAULT_KB_ROOT = Path("D:/AI_Projects/.TelegramChatHistory/KB")
DEFAULT_ORGANIZED_ROOT = Path("D:/AI_Projects/.TelegramChatHistory/Organized")


def ensure_dirs(kb_root: Path) -> None:
    (kb_root / "services").mkdir(parents=True, exist_ok=True)
    (kb_root / "logs").mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(name: str) -> str:
    s = name.strip().lower()
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        elif ch in {" ", "-", "_"}:
            out.append("-")
    slug = "".join(out).strip("-")
    return slug or "service"


def cmd_init_kb(kb_root: Path) -> Dict[str, Any]:
    ensure_dirs(kb_root)
    index_path = kb_root / "index.json"
    state_path = kb_root / "state.json"
    if not index_path.exists():
        save_json(index_path, {"services": []})
    if not state_path.exists():
        save_json(state_path, {"lastProcessedFile": None, "lastOffsetLine": 0, "filesDone": []})
    return {"ok": True}


def list_ordered_chat_files(organized_root: Path) -> List[Path]:
    # Deterministic order across common subfolders
    subfolders = ["dialogs", "groups", "channels", "bots", "unknown"]
    files: List[Path] = []
    for sub in subfolders:
        d = organized_root / sub
        if not d.exists():
            continue
        for p in sorted(d.glob("*.jsonl")):
            files.append(p)
    return files


def cmd_state_get(kb_root: Path) -> Dict[str, Any]:
    state = load_json(kb_root / "state.json", {"lastProcessedFile": None, "lastOffsetLine": 0, "filesDone": []})
    return state


def cmd_state_update(kb_root: Path, params: Dict[str, Any]) -> Dict[str, Any]:
    state_path = kb_root / "state.json"
    state = load_json(state_path, {"lastProcessedFile": None, "lastOffsetLine": 0, "filesDone": []})
    if "lastProcessedFile" in params:
        state["lastProcessedFile"] = params["lastProcessedFile"]
    if "lastOffsetLine" in params:
        state["lastOffsetLine"] = int(params["lastOffsetLine"])
    fda = params.get("filesDoneAppend")
    if fda:
        if fda not in state.get("filesDone", []):
            state.setdefault("filesDone", []).append(fda)
        # Reset offset if file completed
        if state.get("lastProcessedFile") == fda:
            state["lastProcessedFile"] = None
            state["lastOffsetLine"] = 0
    save_json(state_path, state)
    return {"ok": True}


def cmd_queue_get_next_file(kb_root: Path, organized_root: Path) -> Dict[str, Any]:
    state = cmd_state_get(kb_root)
    files_done = set(state.get("filesDone", []))
    last_file = state.get("lastProcessedFile")
    chat_files = list_ordered_chat_files(organized_root)
    # If we were in the middle of a file, return it first
    if last_file and last_file not in files_done:
        if Path(last_file).exists():
            return {"path": last_file}
    for p in chat_files:
        sp = str(p)
        if sp in files_done:
            continue
        return {"path": sp}
    return {"path": None}


def cmd_chat_read_lines(params: Dict[str, Any]) -> Dict[str, Any]:
    path = Path(params["path"])  # required
    start_line = int(params.get("start_line", 1))
    max_lines = int(params.get("max_lines", 500))
    if max_lines <= 0:
        max_lines = 1
    lines: List[str] = []
    next_line = start_line
    eof = False
    with path.open("r", encoding="utf-8") as f:
        # Skip to start_line
        for _ in range(start_line - 1):
            if not f.readline():
                eof = True
                break
        if not eof:
            for _ in range(max_lines):
                line = f.readline()
                if not line:
                    eof = True
                    break
                lines.append(line.rstrip("\n"))
                next_line += 1
    return {"lines": lines, "next_line": next_line, "eof": eof}


def cmd_kb_load_index(kb_root: Path) -> Dict[str, Any]:
    index = load_json(kb_root / "index.json", {"services": []})
    return index


def read_service_frontmatter(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n")
    if end == -1:
        return {}
    fm = text[4:end]
    try:
        return json.loads(fm)
    except Exception:
        return {}


def write_service_file(kb_root: Path, slug: str, name: str, aliases: List[str], categories: List[str]) -> None:
    path = kb_root / "services" / f"{slug}.md"
    now = datetime.utcnow().strftime("%Y-%m-%d")
    front = {
        "name": name,
        "slug": slug,
        "aliases": sorted(list(set(aliases))),
        "categories": sorted(list(set(categories))),
        "updated_at": now,
    }
    body = (
        f"---\n{json.dumps(front, ensure_ascii=False)}\n---\n\n"
        "## 摘要\n\n"
        "## 材料/要求\n\n"
        "## 办理流程\n\n"
        "## 价格与条件\n\n"
        "| 生效日期 | 币种 | 价格 | 条件/范围 | 备注 | 证据 |\n| - | - | - | - | - | - |\n\n"
        "## 证据引用\n\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def append_to_section(kb_root: Path, slug: str, section: str, markdown: str) -> None:
    path = kb_root / "services" / f"{slug}.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    header = f"## {section}\n"
    if header not in text:
        text = text + f"\n{header}\n"
    text = text + (markdown if markdown.endswith("\n") else markdown + "\n")
    path.write_text(text, encoding="utf-8")


def ensure_service(kb_root: Path, index: Dict[str, Any], name: str, aliases: List[str], categories: List[str]) -> str:
    # Try exact match by name or aliases
    for svc in index.get("services", []):
        names = [svc.get("name", "")] + svc.get("aliases", [])
        if name in names:
            # Merge aliases/categories
            svc["aliases"] = sorted(list(set(svc.get("aliases", []) + aliases)))
            svc["categories"] = sorted(list(set(svc.get("categories", []) + categories)))
            return svc["slug"]
    slug = slugify(name)
    index.setdefault("services", []).append({
        "slug": slug,
        "name": name,
        "aliases": sorted(list(set(aliases))),
        "categories": sorted(list(set(categories))),
    })
    # Create file if missing
    write_service_file(kb_root, slug, name, aliases, categories)
    return slug


def cmd_kb_upsert_service(kb_root: Path, params: Dict[str, Any]) -> Dict[str, Any]:
    slug = params.get("slug")
    name = params.get("name")
    aliases = params.get("aliases", [])
    categories = params.get("categories", [])
    if not name:
        return {"ok": False, "error": "name required"}
    index = load_json(kb_root / "index.json", {"services": []})
    if not slug:
        slug = ensure_service(kb_root, index, name, aliases, categories)
    else:
        # Ensure file exists
        if not (kb_root / "services" / f"{slug}.md").exists():
            write_service_file(kb_root, slug, name, aliases, categories)
        # Update/insert index entry
        found = False
        for svc in index.get("services", []):
            if svc.get("slug") == slug:
                svc["name"] = name
                svc["aliases"] = sorted(list(set(svc.get("aliases", []) + aliases)))
                svc["categories"] = sorted(list(set(svc.get("categories", []) + categories)))
                found = True
                break
        if not found:
            index.setdefault("services", []).append({
                "slug": slug,
                "name": name,
                "aliases": sorted(list(set(aliases))),
                "categories": sorted(list(set(categories))),
            })
    save_json(kb_root / "index.json", index)
    return {"ok": True, "slug": slug}


def cmd_kb_append_markdown(kb_root: Path, params: Dict[str, Any]) -> Dict[str, Any]:
    slug = params["slug"]
    section = params.get("section", "摘要")
    markdown = params.get("markdown", "")
    append_to_section(kb_root, slug, section, markdown)
    return {"ok": True}


def cmd_kb_upsert_pricing(kb_root: Path, params: Dict[str, Any]) -> Dict[str, Any]:
    slug = params["slug"]
    entry = params["entry"]
    path = kb_root / "services" / f"{slug}.md"
    if not path.exists():
        return {"ok": False, "error": "service file missing"}
    currency = entry.get("currency", "")
    amount = entry.get("amount", "")
    eff = entry.get("effective_date", "")
    cond = entry.get("conditions", "").replace("\n", " ")
    notes = entry.get("notes", "").replace("\n", " ")
    evidence = entry.get("evidence", {})
    file = evidence.get("file", "")
    msg_ids = evidence.get("message_ids", [])
    dates = evidence.get("dates", [])
    ev_str = f"file: {file}, ids: {msg_ids}"

    text = path.read_text(encoding="utf-8")
    table_header = "| 生效日期 | 币种 | 价格 | 条件/范围 | 备注 | 证据 |\n"
    if table_header not in text:
        # Append a fresh table
        text += ("\n## 价格与条件\n\n" + table_header + "| - | - | - | - | - | - |\n\n")
    row = f"| {eff} | {currency} | {amount} | {cond} | {notes} | {ev_str} |\n"
    if row not in text:
        text += row
        path.write_text(text, encoding="utf-8")
    return {"ok": True}


def cmd_kb_save_index(kb_root: Path, params: Dict[str, Any]) -> Dict[str, Any]:
    services = params.get("services", [])
    save_json(kb_root / "index.json", {"services": services})
    return {"ok": True}


def cmd_kb_load_index_raw(kb_root: Path) -> Dict[str, Any]:
    return load_json(kb_root / "index.json", {"services": []})


def cmd_log_append(kb_root: Path, params: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.utcnow()
    log_file = kb_root / "logs" / f"run-{now.strftime('%Y%m%d')}.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    payload = params.get("jsonl", "")
    with log_file.open("a", encoding="utf-8") as f:
        f.write(payload.rstrip("\n") + "\n")
    return {"ok": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="KB tools for function-call style usage")
    parser.add_argument("command", help="one of: init_kb, state_get, state_update, queue_get_next_file, chat_read_lines, kb_load_index, kb_upsert_service, kb_append_markdown, kb_upsert_pricing, kb_save_index, log_append")
    parser.add_argument("--params", default="{}", help="JSON string of params")
    parser.add_argument("--kb-root", default=str(DEFAULT_KB_ROOT))
    parser.add_argument("--organized-root", default=str(DEFAULT_ORGANIZED_ROOT))
    args = parser.parse_args()

    kb_root = Path(args.kb_root)
    organized_root = Path(args.organized_root)
    try:
        params = json.loads(args.params)
    except Exception:
        params = {}

    try:
        if args.command == "init_kb":
            result = cmd_init_kb(kb_root)
        elif args.command == "state_get":
            result = cmd_state_get(kb_root)
        elif args.command == "state_update":
            result = cmd_state_update(kb_root, params)
        elif args.command == "queue_get_next_file":
            result = cmd_queue_get_next_file(kb_root, organized_root)
        elif args.command == "chat_read_lines":
            result = cmd_chat_read_lines(params)
        elif args.command == "kb_load_index":
            result = cmd_kb_load_index(kb_root)
        elif args.command == "kb_upsert_service":
            result = cmd_kb_upsert_service(kb_root, params)
        elif args.command == "kb_append_markdown":
            result = cmd_kb_append_markdown(kb_root, params)
        elif args.command == "kb_upsert_pricing":
            result = cmd_kb_upsert_pricing(kb_root, params)
        elif args.command == "kb_save_index":
            result = cmd_kb_save_index(kb_root, params)
        elif args.command == "log_append":
            result = cmd_log_append(kb_root, params)
        else:
            result = {"ok": False, "error": f"unknown command {args.command}"}
    except Exception as e:
        result = {"ok": False, "error": str(e)}

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


