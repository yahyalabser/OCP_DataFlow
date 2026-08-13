import json
from pathlib import Path
from datetime import datetime, timezone

STATE_FILE = Path(__file__).parent / "etl_state.json"

def get_last_success(source: str) -> datetime | None:
   if not STATE_FILE.exists():
      return None
   state = json.loads(STATE_FILE.read_text())
   ts = state.get(source)
   return datetime.fromisoformat(ts) if ts else None

def set_last_success(source: str, when: datetime | None = None) -> None:
   state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
   state[source] = (when or datetime.now(timezone.utc)).isoformat()
   STATE_FILE.write_text(json.dumps(state, indent=2))