from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

from Contracts.toolcalls import call_match_selectors, call_validate_slot


def _load_json_or_yaml(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def _load_slots(path: Path) -> List[Dict[str, Any]]:
    payload = _load_json_or_yaml(path)
    if isinstance(payload, dict):
        if "slots" in payload and isinstance(payload["slots"], list):
            return [slot for slot in payload["slots"] if isinstance(slot, dict)]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _load_selectors(path: Path) -> List[Dict[str, Any]]:
    payload = _load_json_or_yaml(path)
    selectors: List[Dict[str, Any]] = []
    if isinstance(payload, dict):
        if "selectors" in payload and isinstance(payload["selectors"], list):
            selectors.extend([selector for selector in payload["selectors"] if isinstance(selector, dict) and selector.get("slot")])
        elif payload.get("slot"):
            selectors.append(payload)
    elif isinstance(payload, list):
        selectors.extend([item for item in payload if isinstance(item, dict) and item.get("slot")])
    return selectors


def _load_core_envelope(path: Path) -> Dict[str, Any]:
    payload = _load_json_or_yaml(path)
    if isinstance(payload, dict):
        return payload
    raise ValueError("core envelope payload must be a JSON/YAML object")


def _extract_slots_from_index(index_data: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    entries = index_data.get("entries", [])
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        slot_name = entry.get("level4_key") or entry.get("slot")
        content = entry.get("value") or entry.get("l4_label") or ""
        if not slot_name:
            continue
        yield {
            "slot": slot_name,
            "type": "text",
            "content": str(content),
            "metadata": {"source": entry.get("doc_rel_path")},
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate selector and slot definitions.")
    parser.add_argument("--index", type=Path, default=Path("KnowledgeBase/BI/BI_index.yaml"), help="Agency index file.")
    parser.add_argument("--selectors", type=Path, help="Selectors definition file (JSON or YAML).")
    parser.add_argument("--slots", type=Path, help="Slot definition file (JSON or YAML).")
    parser.add_argument("--core-envelope", type=Path, help="CoreEnvelope sample file.")
    parser.add_argument("--stage", default="triage", help="Selector evaluation stage.")
    parser.add_argument("--debug", action="store_true", help="Enable debug trace prompts.")
    args = parser.parse_args()

    selectors: List[Dict[str, Any]] = []
    slot_candidates: List[Dict[str, Any]] = []

    if args.index.exists():
        index_payload = _load_json_or_yaml(args.index)
        if isinstance(index_payload, dict):
            selectors_block = index_payload.get("selectors")
            if isinstance(selectors_block, dict):
                for _, value in selectors_block.items():
                    if isinstance(value, dict) and value.get("slot"):
                        selectors.append(value)
            slot_candidates.extend(list(_extract_slots_from_index(index_payload)))

    if args.selectors:
        selectors.extend(_load_selectors(args.selectors))
    if args.slots:
        slot_candidates.extend(_load_slots(args.slots))

    if not selectors:
        parser.error("No selectors provided; supply --selectors or ensure index contains selectors.")

    validated_slots: List[Dict[str, Any]] = []
    for slot in slot_candidates:
        try:
            call_validate_slot(slot)
        except ValueError as exc:
            print(f"[slot-validation-error] slot={slot.get('slot')} reason={exc}")
            return 1
        validated_slots.append(slot)

    if args.core_envelope:
        core_envelope = _load_core_envelope(args.core_envelope)
    else:
        core_envelope = {"user_message": ""}
    core_envelope.setdefault("stage", args.stage)

    result = call_match_selectors(core_envelope, selectors)
    matched_slots = result.get("matched_slots", [])
    slot_registry = {slot.get("slot") for slot in validated_slots if isinstance(slot, dict)}
    missing_slots = sorted({selector.get("slot") for selector in selectors if selector.get("slot") and selector.get("slot") not in slot_registry})

    output = {
        "matched_slots": matched_slots,
        "scores": result.get("scores", []),
        "missing_slots": missing_slots,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if missing_slots:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
