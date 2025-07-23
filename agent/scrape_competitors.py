# agent/scrape_competitors.py

import requests
from bs4 import BeautifulSoup
import yaml
from agent import embedder, vectorstore
from playwright.sync_api import sync_playwright  # ✅ NEU für Browserless

def load_competitors():
    with open("competitors.yaml", "r") as f:
        return yaml.safe_load(f)

def scrape_with_browserless(url):
    BROWSERLESS_WS_ENDPOINT = "ws://browserless:3000"
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(BROWSERLESS_WS_ENDPOINT)
        page = browser.new_page()
        page.goto(url)
        html = page.content()
        browser.close()
    return html

def scrape_and_update():
    competitors = load_competitors()

    for kunde, urls in competitors.items():
        print(f"✅ Scraping für Kunde: {kunde}")

        for url in urls:
            print(f"🔗 Hole Daten von: {url}")
            try:
                if url.startswith("js-heavy|"):
                    url_clean = url.replace("js-heavy|", "")
                    print(f"⚡ Nutze Browserless/Playwright für: {url_clean}")
                    html = scrape_with_browserless(url_clean)
                    soup = BeautifulSoup(html, "html.parser")
                else:
                    print("🔎 Nutze requests + BS4")
                    response = requests.get(url, timeout=10)
                    soup = BeautifulSoup(response.text, "html.parser")

                paragraphs = soup.find_all("p")
                text = "\n".join([p.text for p in paragraphs])

                chunks = []
                for para in text.split("\n\n"):
                    if para.strip():
                        emb = embedder.create_embedding(para)
                        chunks.append({"text": para, "embedding": emb})

                vectorstore.upsert_chunks(chunks, collection_name=f"{kunde}_competitors")
                print(f"✅ {len(chunks)} Chunks gespeichert für {kunde}!")

            except Exception as e:
                print(f"❌ Fehler beim Scraping {url}: {e}")

if __name__ == "__main__":
    scrape_and_update()
