import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time


def extract_visible_text(html):
    soup = BeautifulSoup(html, "html.parser")

    # Entferne Skripte, Styles etc.
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    texts = [t.strip() for t in soup.stripped_strings if len(t.strip()) > 40]
    return "\n".join(texts)


def is_valid_link(link, domain):
    parsed = urlparse(link)
    return (
        parsed.netloc == "" or parsed.netloc == domain
    ) and not parsed.path.endswith(('.pdf', '.jpg', '.png', '.svg'))


def crawl_domain(start_url, max_pages=10, delay=1.0):
    visited = set()
    to_visit = [start_url]
    domain = urlparse(start_url).netloc
    results = {}

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200 or 'text/html' not in response.headers.get('Content-Type', ''):
                continue

            html = response.text
            path = urlparse(url).path or "/"
            text = extract_visible_text(html)
            results[path] = text
            visited.add(url)

            soup = BeautifulSoup(html, "html.parser")
            for link in soup.find_all("a", href=True):
                href = urljoin(url, link['href'])
                if is_valid_link(href, domain) and href not in visited and href not in to_visit:
                    to_visit.append(href)

            time.sleep(delay)
        except Exception as e:
            print(f"Fehler bei {url}: {e}")
            continue

    return results


if __name__ == "__main__":
    domain_results = crawl_domain("https://example.com")
    for path, content in domain_results.items():
        print(f"=== {path} ===\n{content[:500]}...\n")
