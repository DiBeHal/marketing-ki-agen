# agent/query.py

import os
import re
import uuid
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from langchain_openai import ChatOpenAI

from agent.embedder import create_embedding

# ===== Qdrant Client =====
qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# ===== LangChain LLM =====
llm = ChatOpenAI(model="gpt-4o")

# ===== System-Prompts für Fast vs. Deep =====
FAST_SYSTEM_MESSAGE = (
    "Du bist ein Marketing-Analyse-Agent. "
    "Nutze den bereitgestellten Kontext, um die Frage präzise zu beantworten."
)
DEEP_SYSTEM_MESSAGE = (
    "Du bist ein Marketing-Analyse-Agent. 🧠 Tiefenanalyse: "
    "Denke Schritt für Schritt, erkläre deine Zwischenschritte und stelle Rückfragen, "
    "wenn etwas unklar ist, bevor du die finale Antwort gibst."
)

def extract_questions_from_response(response: str) -> List[str]:
    """
    Naive Extraktion von Fragen aus der Model-Antwort:
    Sucht nach Sätzen, die mit '?' enden.
    """
    parts = re.split(r'(?<=[\?])\s+', response)
    return [p.strip() for p in parts if p.strip().endswith('?')]

def query_agent(
    question: str,
    mode: str = "fast",
    clarifications: Optional[Dict[str, str]] = None,
    conversation_id: Optional[str] = None,
    collection_name: str = "agent_chunks"
) -> Dict:
    """
    Fragt den Marketing-Analyse-Agenten an und unterstützt optional Deep Reasoning mit Rückfragen.

    Args:
        question: Nutzereingabe/Frage.
        mode: 'fast' oder 'deep'.
        clarifications: Antworten auf vorherige Rückfragen (falls vorhanden).
        conversation_id: ID für die Gesprächssession (wird neu erzeugt, wenn None).
        collection_name: Name der Qdrant-Collection.

    Returns:
        Dict mit:
        - response: die Agenten-Antwort (inkl. CoT, ohne Klarfragen)
        - questions: Liste neuer Rückfragen (leere Liste, wenn keine oder fast-Modus)
        - conversation_id: ID dieser Session
    """
    # 1) Conversation-ID erzeugen oder verwenden
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())

    # 2) Embedding & Kontext aus Qdrant
    embedding = create_embedding(question)
    results = qdrant.query_points(
        collection_name=collection_name,
        query_vector=embedding,
        limit=3
    )
    context = "\n---\n".join(hit.payload["text"] for hit in results)

    # 3) System-Message auswählen
    system_content = FAST_SYSTEM_MESSAGE if mode == "fast" else DEEP_SYSTEM_MESSAGE

    # 4) Initiale Nachrichten
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"Kontext:\n{context}\n\nFrage: {question}"}
    ]

    # 5) Vorherige Klarstellungen hinzufügen (nur im Deep-Modus)
    if mode == "deep" and clarifications:
        clar_text = "\n".join(f"Frage: {q}\nAntwort: {a}" for q, a in clarifications.items())
        messages.append({"role": "user", "content": f"Klarstellungen:\n{clar_text}"})

    # 6) LLM-Aufruf
    resp = llm.invoke(messages)
    resp_content = resp.content

    # 7) Falls Deep-Modus: Rückfragen extrahieren
    questions = extract_questions_from_response(resp_content) if mode == "deep" else []

    # 8) Rückgabe
    return {
        "response": resp_content,
        "questions": questions,
        "conversation_id": conversation_id
    }
