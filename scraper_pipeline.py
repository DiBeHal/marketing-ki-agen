# scraper_pipeline.py

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pipeline_upload import store_results_locally_and_upload
from loguru import logger

logger.add("logs/agent.log", rotation="1 MB", retention="7 days")

def scrape_and_upload(url: str):
    logger.info(f"🌐 Starte Scrape: {url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Dummy-Extraktion: alle H1-Texte
    headings = [h1.text.strip() for h1 in soup.find_all("h1")]

    result = {
        "url": url,
        "timestamp": datetime.utcnow().isoformat(),
        "headings": headings
    }

    logger.info(f"🔎 Gefundene Überschriften: {headings}")
    store_results_locally_and_upload(result, prefix="scraper")

# --- Mini-Test ---
if __name__ == "__main__":
    test_url = "https://example.com"
    scrape_and_upload(test_url)
