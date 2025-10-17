import argparse
import json
import os
import re
import sys
from decimal import Decimal
from pathlib import Path


def safe_filename(name: str, max_length: int = 128) -> str:
    """Generate a Windows-safe filename from a chat name.

    Keeps unicode characters but removes characters illegal on Windows and trims length.
    """
    if not name:
        name = "chat"
    # Remove characters not allowed on Windows file systems
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    # Remove leading/trailing spaces and periods
    name = name.strip(" .")
    if not name:
        name = "chat"
    if len(name) > max_length:
        name = name[:max_length]
    return name


def write_chat_as_json(chat: dict, out_dir: Path) -> Path:
    chat_id = chat.get("id")
    chat_name = chat.get("name") or str(chat_id)
    filename = f"{safe_filename(chat_name)}_{chat_id}.json"
    out_path = out_dir / filename
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(chat, f, ensure_ascii=False, indent=2)
    return out_path


def write_chat_as_ndjson(chat: dict, out_dir: Path) -> Path:
    """Write a chat into NDJSON with a header line and then one message per line.

    Schema:
    - First line: {"_kind": "chat_header", "name": ..., "type": ..., "id": ...}
    - Following lines: {"_kind": "message", ...original message object...}
    """
    chat_id = chat.get("id")
    chat_name = chat.get("name") or str(chat_id)
    chat_type = chat.get("type")
    messages = chat.get("messages", [])
    filename = f"{safe_filename(chat_name)}_{chat_id}.jsonl"
    out_path = out_dir / filename
    with out_path.open("w", encoding="utf-8") as f:
        header = {"_kind": "chat_header", "name": chat_name, "type": chat_type, "id": chat_id}
        f.write(json.dumps(_normalize_decimals(header), ensure_ascii=False) + "\n")
        for message in messages:
            line = {"_kind": "message"}
            # Avoid mutating original message
            line.update(message)
            f.write(json.dumps(_normalize_decimals(line), ensure_ascii=False) + "\n")
    return out_path


def split_export(input_json: Path, output_dir: Path, fmt: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Try to use ijson to avoid loading the entire file into memory
    try:
        import ijson  # type: ignore
        use_ijson = True
    except Exception:
        use_ijson = False

    if use_ijson:
        with input_json.open("r", encoding="utf-8") as f:
            # Iterate chat-by-chat; each item is one chat object
            for chat in ijson.items(f, "chats.list.item"):
                if fmt == "jsonl":
                    write_chat_as_ndjson(_normalize_decimals(chat), output_dir)
                else:
                    write_chat_as_json(_normalize_decimals(chat), output_dir)
    else:
        # Fallback: load entire JSON (may require substantial memory)
        with input_json.open("r", encoding="utf-8") as f:
            data = json.load(f)
        chats = (data or {}).get("chats", {}).get("list", [])
        for chat in chats:
            if fmt == "jsonl":
                write_chat_as_ndjson(chat, output_dir)
            else:
                write_chat_as_json(chat, output_dir)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Split Telegram export result.json into per-chat files."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        required=True,
        help="Path to Telegram export result.json",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Directory to write per-chat files",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "jsonl"],
        default="jsonl",
        help="Output format: json (whole chat JSON) or jsonl (header + one message per line)",
    )

    args = parser.parse_args(argv)
    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 2

    try:
        split_export(args.input, args.output, args.format)
    except KeyboardInterrupt:
        print("Interrupted.")
        return 130
    return 0


def _normalize_decimals(value):
    """Recursively convert Decimal to int/float for JSON serialization.

    - If a Decimal represents an integer (e.g., 123), return int(Decimal)
    - Otherwise, return float(Decimal)
    - Apply recursively to dicts and lists
    """
    if isinstance(value, Decimal):
        # Convert to int when it's an integer value to preserve semantics
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, dict):
        return {k: _normalize_decimals(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_decimals(v) for v in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())


