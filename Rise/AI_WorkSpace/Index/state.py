import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parents[1] / "State.json"
ID_WIDTH = 5
ID_MAX = 10**ID_WIDTH - 1
PH_TZ = timezone(timedelta(hours=8), name="Asia/Manila")


def load_state():
    try:
        with STATE_FILE.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        print(f"State file not found: {STATE_FILE}")
        sys.exit(1)
    except json.JSONDecodeError as err:
        print(f"State file is not valid JSON: {err}")
        sys.exit(1)


def save_state(state):
    with STATE_FILE.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def increment_sequence_id(current_id: str) -> str:
    if not current_id.isdigit():
        raise ValueError("sequence id must be numeric")
    value = int(current_id)
    if value >= ID_MAX:
        raise ValueError(f"sequence id exceeded max {ID_MAX:05d}")
    return f"{value + 1:0{ID_WIDTH}d}"


def ph_now_iso():
    return datetime.now(PH_TZ).isoformat()


def main():
    state = load_state()
    if state.get("lock"):
        print("Please keep using the current sequence ID; no new sequence is needed.")
        return

    sequence = state.get("sequence") or {}
    current = sequence.get("current") or {}
    current_id = current.get("id")

    if not current_id:
        sequence["current"] = {"id": "00000", "createdAt": ph_now_iso()}
        state["sequence"] = sequence
        save_state(state)
        print("Current sequence id was empty. Initialized to 00000.")
        return

    try:
        next_id = increment_sequence_id(current_id)
    except ValueError as err:
        print(f"Invalid sequence id '{current_id}': {err}")
        sys.exit(1)

    history = [item for item in sequence.get("history", []) if item.get("id")]
    archived_at = datetime.now(timezone.utc).isoformat()

    history.insert(
        0,
        {
            "id": current_id,
            "createdAt": current.get("createdAt"),
            "archivedAt": archived_at,
        },
    )

    sequence["history"] = history
    sequence["current"] = {"id": next_id, "createdAt": ph_now_iso()}
    state["sequence"] = sequence
    save_state(state)
    print(f"Archived sequence {current_id} at {archived_at}; next id {next_id}")


if __name__ == "__main__":
    main()
