# agent/services/destatis.py

from typing import List
import requests


def fetch_destatis_stats(codes: List[str]) -> str:
    """
    Ruft DESTATIS-Statistiken per REST-API ab und
    formatiert die Werte als Bullet-Point-Liste.
    """
    stats = []
    for code in codes:
        try:
            url = f"https://api.destatis.de/v1/statistics/{code}"
            res = requests.get(url, timeout=5)
            if res.ok:
                data = res.json()
                # Annahme: 'value' enthält den gewünschten Wert
                value = data.get("value", "n/a")
                stats.append(f"- {code}: {value}")
        except Exception:
            continue
    return "\n".join(stats)
