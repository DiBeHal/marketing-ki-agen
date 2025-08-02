from bs4 import BeautifulSoup

def extract_text_blocks(html: str, min_length: int = 30) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    blocks = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = tag.get_text(strip=True)
        if text and len(text) >= min_length:
            blocks.append(text)
    return blocks
