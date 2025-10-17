import argparse
from pathlib import Path
import json
import shutil


def detect_type_from_jsonl(file_path: Path) -> str | None:
    try:
        with file_path.open("r", encoding="utf-8") as f:
            header_line = f.readline()
        if not header_line:
            return None
        header = json.loads(header_line)
        if header.get("_kind") == "chat_header":
            return header.get("type")
    except Exception:
        return None
    return None


def detect_type_from_json(file_path: Path) -> str | None:
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("type")
    except Exception:
        return None


def organize(input_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    type_to_subdir = {}
    for file in input_dir.iterdir():
        if not file.is_file():
            continue
        chat_type = None
        if file.suffix.lower() == ".jsonl":
            chat_type = detect_type_from_jsonl(file)
        elif file.suffix.lower() == ".json":
            chat_type = detect_type_from_json(file)

        # Normalize a few common types
        normalized = {
            "personal_chat": "dialogs",
            "private_group": "groups",
            "supergroup": "groups",
            "channel": "channels",
            "bot_chat": "bots",
        }.get(chat_type or "unknown", "unknown")

        dest_dir = output_dir / normalized
        if normalized not in type_to_subdir:
            dest_dir.mkdir(parents=True, exist_ok=True)
            type_to_subdir[normalized] = dest_dir

        target = dest_dir / file.name
        if target.exists():
            # Avoid overwrite: append suffix
            stem = target.stem
            suffix = target.suffix
            i = 1
            while True:
                alt = dest_dir / f"{stem}_{i}{suffix}"
                if not alt.exists():
                    target = alt
                    break
                i += 1

        shutil.move(str(file), str(target))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Organize per-chat files by chat type")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Per-chat directory")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Organized output root")
    args = parser.parse_args(argv)

    organize(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


