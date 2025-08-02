import requests
from bs4 import BeautifulSoup

def scrape_html(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.prettify()

def extract_image_sources(url: str) -> list:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")
    return [img.get("src") for img in soup.find_all("img") if img.get("src")]
