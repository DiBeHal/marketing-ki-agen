import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import logging

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)

# Konstanten
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
}
TIMEOUT = 10


def safe_request(url: str) -> str:
    """Führt einen sicheren GET-Request aus, mit Fehlerbehandlung."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logging.warning(f"Request fehlgeschlagen für {url}: {e}")
        return ""


def scrape_facebook_ads(company_name: str, keywords: list) -> dict:
    """Scraped die Facebook Ads Library nach Vorkommen bestimmter Keywords."""
    search_url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=DE&q={quote(company_name)}"
    html = safe_request(search_url)
    soup = BeautifulSoup(html, "html.parser")

    found_keywords = [kw for kw in keywords if kw.lower() in soup.text.lower()]

    return {
        "platform": "Facebook Ads Library",
        "company": company_name,
        "url": search_url,
        "keywords_found": found_keywords,
        "status": "success" if found_keywords else "no_match"
    }


def scrape_google_ads(company_name: str, keywords: list) -> dict:
    """Scraped das Google Ads Transparency Center nach Keywords."""
    search_url = f"https://adstransparency.google.com/ads?advertiser={quote(company_name)}&region=DE"
    html = safe_request(search_url)
    soup = BeautifulSoup(html, "html.parser")

    found_keywords = [kw for kw in keywords if kw.lower() in soup.text.lower()]

    return {
        "platform": "Google Ads Transparency",
        "company": company_name,
        "url": search_url,
        "keywords_found": found_keywords,
        "status": "success" if found_keywords else "no_match"
    }


def scrape_linkedin_ads(company_name: str, keywords: list) -> dict:
    """LinkedIn Ads können nicht serverseitig gescraped werden – Hinweis zurückgeben."""
    search_url = "https://www.linkedin.com/ad-library/home"
    return {
        "platform": "LinkedIn Ads Library",
        "company": company_name,
        "url": search_url,
        "note": "LinkedIn Ads Library ist client-rendered – manuelle Suche empfohlen.",
        "keywords_found": [],
        "status": "manual_only"
    }


def collect_ads_insights(company_name: str, keywords: list, platforms: list) -> list:
    """Sammelt Ads-Daten von allen gewünschten Plattformen."""
    results = []
    if "facebook" in platforms:
        results.append(scrape_facebook_ads(company_name, keywords))
    if "google" in platforms:
        results.append(scrape_google_ads(company_name, keywords))
    if "linkedin" in platforms:
        results.append(scrape_linkedin_ads(company_name, keywords))
    return results


if __name__ == "__main__":
    test_result = collect_ads_insights("Zalando", ["Schuhe", "Sommer"], ["facebook", "google", "linkedin"])
    from pprint import pprint
    pprint(test_result)
