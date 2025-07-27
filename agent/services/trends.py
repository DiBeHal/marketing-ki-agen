# agent/services/trends.py

from typing import List
from pytrends.request import TrendReq


def fetch_trends_insights(
    keywords: List[str],
    timeframe: str = "now 7-d"
) -> str:
    """
    Holt mit pytrends die Entwicklung des Suchinteresses
    für die gegebenen Keywords im angegebenen Zeitraum
    und gibt Kurz-Insights als Bullet-Points zurück.
    """
    if not keywords:
        return ""
    try:
        pytrends = TrendReq()
        pytrends.build_payload(keywords, timeframe=timeframe)
        df = pytrends.interest_over_time()
        insights = []
        for kw in keywords:
            if kw in df.columns:
                series = df[kw].dropna()
                if not series.empty:
                    change = series.iloc[-1] - series.iloc[0]
                    insights.append(f"- Suchinteresse für '{kw}' im Zeitraum: Änderung um {change} Punkte")
        return "\n".join(insights)
    except Exception:
        return ""
