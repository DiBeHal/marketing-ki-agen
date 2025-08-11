# agent/tools/ads_runner.py

import os
import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)

HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 10


def fetch_linkedin_ads(company_domain: str, limit: int = 3) -> str:
    """
    Scrapt die LinkedIn-Company-Seite nach neuesten Aktivitäten/Ads
    und gibt die Top-`limit` Text-Snippets zurück.
    Hinweis: Für eine zuverlässige Lösung empfiehlt sich Playwright/Selenium.
    """
    url = f"https://www.linkedin.com/company/{company_domain}/posts/?feedView=all"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        posts = soup.select(".feed-shared-text__text-view")[:limit]

        snippets = []
        for post in posts:
            text = post.get_text(strip=True)
            if text:
                snippets.append(f"- {text[:200]}{'...' if len(text) > 200 else ''}")

        return "\n".join(snippets)
    except Exception as e:
        logging.warning(f"Fehler beim Abrufen von LinkedIn-Posts: {e}")
        return ""


def fetch_google_ads(company_name: str, limit: int = 3) -> str:
    """
    Greift auf das Google Ads Transparency Center zu und
    extrahiert per Scraping die Ad-Snippets (Platzhalter-Implementierung).
    Für robuste Lösungen empfiehlt sich ein Headless-Browser.
    """
    url = f"https://transparencyreport.google.com/political-ads/home?searchTerm={company_name}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".ad-card")[:limit]

        snippets = []
        for item in items:
            text = item.get_text(strip=True)
            if text:
                snippets.append(f"- {text[:200]}{'...' if len(text) > 200 else ''}")

        return "\n".join(snippets)
    except Exception as e:
        logging.warning(f"Fehler beim Abrufen von Google Ads: {e}")
        return ""


def fetch_facebook_ads(page_id: str, limit: int = 3) -> str:
    """
    Nutzt die Facebook Ad Library API zum Abruf von Ad-Textelementen.
    Erfordert Umgebungsvariable FACEBOOK_ACCESS_TOKEN.
    """
    token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    if not token:
        logging.warning("Kein Facebook Access Token gefunden.")
        return ""

    endpoint = "https://graph.facebook.com/v12.0/ads_archive"
    params = {
        "access_token": token,
        "search_terms": page_id,
        "ad_reached_countries": "US",
        "limit": limit,
        "fields": "ad_creative_body"
    }

    try:
        r = requests.get(endpoint, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data", [])

        snippets = []
        for ad in data[:limit]:
            body = ad.get("ad_creative_body")
            if body:
                snippets.append(f"- {body}")

        return "\n".join(snippets)
    except Exception as e:
        logging.warning(f"Fehler beim Abrufen von Facebook Ads: {e}")
        return ""
