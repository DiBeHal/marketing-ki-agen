# agent/services/rss.py

from typing import List
import feedparser


def fetch_rss_snippets(feeds: List[str], limit: int = 3) -> str:
    """
    Parst eine Liste von RSS-Feed-URLs und extrahiert die
    Top-`limit` Einträge pro Feed als Bullet-Point-Liste.
    """
    snippets = []
    for feed in feeds:
        try:
            d = feedparser.parse(feed)
            for entry in d.entries[:limit]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                snippets.append(f"- {title} ({link})")
        except Exception:
            # im Fehlerfall überspringen
            continue
    return "\n".join(snippets)
