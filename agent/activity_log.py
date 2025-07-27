# agent/activity_log.py

import os
import json
from datetime import datetime
from typing import Any, Dict, List

# Pfad zur Log-Datei (kann via ENV überschrieben werden)
LOG_FILE = os.getenv("ACTIVITY_LOG_FILE", "activity_log.jsonl")

def log_event(event: Dict[str, Any]) -> None:
    """
    Hängt einen Event-Datensatz mit Timestamp an die Log-Datei an.
    Event kann z.B. sein: task_run, usage, rating, feedback, …
    """
    record = {
        **event,
        "timestamp": datetime.utcnow().isoformat()
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def get_events() -> List[Dict[str, Any]]:
    """
    Liest alle Events aus der Log-Datei als Liste von Dicts ein.
    """
    events: List[Dict[str, Any]] = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events
