import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import time
import logging

logging.basicConfig(level=logging.INFO)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"}
TIMEOUT = 10


def safe_request(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logging.warning(f"Request failed for {url}: {e}")
        return ""


def scrape_facebook_ads(company_name, keywords):
    search_url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=DE&q={quote(company_name)}"
    html = safe_request(search_url)
    soup = BeautifulSoup(html, "html.parser")

    results = []
    for kw in keywords:
        if kw.lower() in soup.text.lower():
            results.append(kw)

    return {
        "source": "Facebook Ads Library",
        "keywords_found": results,
        "company": company_name,
        "url": search_url
    }


def scrape_google_ads(company_name, keywords):
    search_url = f"https://adstransparency.google.com/ads?advertiser={quote(company_name)}&region=DE"
    html = safe_request(search_url)
    soup = BeautifulSoup(html, "html.parser")

    results = []
    for kw in keywords:
        if kw.lower() in soup.text.lower():
            results.append(kw)

    return {
        "source": "Google Ads Transparency",
        "keywords_found": results,
        "company": company_name,
        "url": search_url
    }


def scrape_linkedin_ads(company_name, keywords):
    # LinkedIn Ad Library is not openly accessible via server-side scraping
    search_url = "https://www.linkedin.com/ad-library/home"
    return {
        "source": "LinkedIn Ads Library",
        "company": company_name,
        "note": "LinkedIn Ads Library ist client-rendered – bitte manuell im Browser durchsuchen.",
        "url": search_url
    }


def collect_ads_insights(company_name, keywords, platforms):
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
