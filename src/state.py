"""Local persisted state: cached Qobuz OAuth credentials and the
Qobuz playlist id we always sync into (so we never create a duplicate)."""
import json
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text())


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))
