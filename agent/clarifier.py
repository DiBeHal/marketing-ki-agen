# agent/clarifier.py

import re
from typing import Dict, List

def extract_questions_from_response(response: str) -> List[str]:
    """
    Extrahiert alle Sätze, die mit '?' enden, als mögliche Rückfragen.
    """
    parts = re.split(r'(?<=[\?])\s+', response)
    return [p.strip() for p in parts if p.strip().endswith('?')]

def merge_clarifications(prompt: str, clarifications: Dict[str, str]) -> str:
    """
    Hängt dem ursprünglichen Prompt eine Sektion 'Klarstellungen' mit den
    gelieferten Antworten an.
    """
    clar_lines = []
    for q, a in clarifications.items():
        clar_lines.append(f"Frage: {q}\nAntwort: {a}")
    clar_text = "\n\n".join(clar_lines)
    return f"{prompt}\n\n---\nKlarstellungen:\n{clar_text}"
