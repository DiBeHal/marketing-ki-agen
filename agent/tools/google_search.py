import requests
from bs4 import BeautifulSoup

def find_competitor_sites(query: str, max_results: int = 2) -> list:
    """
    Führt eine einfache Google-Suche durch (Scraping) und extrahiert URLs von echten Wettbewerbern.
    Achtung: Kein offizielles API, kann durch Google-Rate-Limits eingeschränkt sein.
    """
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    search_url = f"https://www.google.com/search?q={query}&num={max_results}"
    response = requests.get(search_url, headers=headers)

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    links = []

    for a in soup.select("a"):
        href = a.get("href")
        if href and "/url?q=" in href:
            clean_url = href.split("/url?q=")[-1].split("&")[0]
            if "google" not in clean_url and "webcache" not in clean_url:
                links.append(clean_url)
        if len(links) >= max_results:
            break

    return links
