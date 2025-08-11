# agent/activity_log.py
from __future__ import annotations

import os
import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Iterable, Optional

# Pfad via ENV überschreibbar (kompatibel zu deiner bisherigen Lösung)
LOG_FILE = os.getenv("ACTIVITY_LOG_FILE", "activity_log.jsonl")

# einfacher Prozess-weiter Lock für parallele Writes
_LOCK = threading.Lock()

# Minimal-Schema, das das Admin-Dashboard typischerweise erwartet
_EXPECTED_KEYS: Iterable[str] = (
    "type", "timestamp", "customer_id", "task",
    "rating", "comment", "mode", "input_tokens", "output_tokens"
)

def _now_iso_utc() -> str:
    # ISO 8601 UTC mit 'Z' Suffix (einheitlicher als naive .isoformat())
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

def _normalize_event(e: Dict[str, Any]) -> Dict[str, Any]:
    """Sanfte Normalisierung: Keys ergänzen, Typen glätten, Timestamp fallback."""
    out = dict(e) if isinstance(e, dict) else {"raw": str(e)}
    # Timestamp sicherstellen
    ts = out.get("timestamp")
    if not ts or not isinstance(ts, str):
        out["timestamp"] = _now_iso_utc()

    # Erwartete Keys auffüllen (None wenn nicht vorhanden)
    for k in _EXPECTED_KEYS:
        out.setdefault(k, None)

    # Token-Felder in ints konvertieren, wenn möglich
    for k in ("input_tokens", "output_tokens"):
        if out.get(k) is not None:
            try:
                out[k] = int(out[k])
            except Exception:
                # falls z. B. "", lasse None
                out[k] = None
    return out

def log_event(event: Dict[str, Any]) -> None:
    """
    Hängt ein Event (task_run, usage, rating, feedback, ...) als JSONL-Zeile an.
    - Beibehaltung deiner bisherigen Signatur & ENV-Handling
    - Ergänzt robusten UTC-Timestamp und Schema-Normalisierung
    """
    record = _normalize_event({**event, "timestamp": _now_iso_utc()})
    _ensure_parent_dir(LOG_FILE)
    with _LOCK:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

def get_events() -> List[Dict[str, Any]]:
    """
    Liest alle Events aus der JSONL-Logdatei.
    - Überspringt defekte Zeilen
    - Normalisiert Events (fehlende Keys, Timestamp etc.)
    """
    events: List[Dict[str, Any]] = []
    if not os.path.exists(LOG_FILE):
        return events

    with _LOCK:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    # defekte Zeile ignorieren
                    continue
                events.append(_normalize_event(obj))
    return events

# ---- Legacy-API (optional), falls irgendwo noch verwendet -------------------
def load_events_as_dataframe():
    """
    Abwärtskompatible Helper-Funktion.
    Gibt wie früher ein pandas.DataFrame zurück – falls pandas nicht installiert,
    wird eine verständliche Exception geworfen.
    """
    try:
        import pandas as pd  # lazy import
    except Exception as e:
        raise RuntimeError(
            "pandas wird für load_events_as_dataframe() benötigt. "
            "Installiere es oder nutze get_events() + pd.DataFrame(get_events())."
        ) from e

    df = pd.DataFrame(get_events())
    # leichte Normalisierung der Spaltennamen (siehe neuere streamlit_app)
    if not df.empty:
        df.columns = df.columns.str.strip().str.lower()
    return df

# ---- Optionale Komfort-Helfer (kannst du bei Bedarf nutzen) -----------------
def log_usage(customer_id: Optional[str], input_tokens: int, output_tokens: int, mode: Optional[str] = None) -> None:
    """Bequemer Short-Cut für Usage-Events."""
    log_event({
        "type": "usage",
        "customer_id": customer_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "mode": mode,
    })

def log_rating(customer_id: Optional[str], rating: Optional[float], comment: Optional[str] = None) -> None:
    """Bequemer Short-Cut für Rating/Feedback-Events."""
    log_event({
        "type": "rating",
        "customer_id": customer_id,
        "rating": rating,
        "comment": comment,
    })
