import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def extract_images_from_url(url: str):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return {"error": f"Fehler beim Laden der Seite: {e}"}

    soup = BeautifulSoup(response.text, "html.parser")
    images = []

    for i, img in enumerate(soup.find_all("img")):
        src = img.get("src")
        if not src:
            continue

        # Absoluten Pfad erzeugen
        full_src = urljoin(url, src)
        alt_text = img.get("alt", "").strip()
        title = img.get("title", "").strip()
        img_id = img.get("id", "")
        img_class = img.get("class", "")

        # Versuche kurzen Kontexttext aus Umgebung zu ziehen
        surrounding = img.find_parent()
        context = ""
        if surrounding:
            context = surrounding.get_text(strip=True)[:200]

        images.append({
            "src": full_src,
            "alt": alt_text,
            "title": title,
            "id": img_id,
            "class": img_class,
            "context": context
        })

        # Nur 10 Bilder maximal
        if len(images) >= 10:
            break

    return images
