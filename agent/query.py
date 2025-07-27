# agent/query.py

import os
import re
import uuid
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from langchain_openai import ChatOpenAI

from agent.embedder import create_embedding
from agent.activity_log import log_event  # neu

# ===== Qdrant Client =====
qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# ===== LangChain LLM mit erhöhtem Token-Limit =====
llm = ChatOpenAI(model="gpt-4o", max_tokens=3000)

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

    Returns:
        {
            "response": str,
            "questions": List[str],
            "conversation_id": str
        }
    """
    # 1) Conversation-ID
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())

    # 2) Kontext aus Qdrant (limit=8 für mehr Chunks)
    embedding = create_embedding(question)
    results = qdrant.query_points(
        collection_name=collection_name,
        query_vector=embedding,
        limit=8
    )
    context = "\n---\n".join(hit.payload["text"] for hit in results)

    # 3) System-Message
    system_content = FAST_SYSTEM_MESSAGE if mode == "fast" else DEEP_SYSTEM_MESSAGE

    # 4) Chat-Messages bauen
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"Kontext:\n{context}\n\nFrage: {question}"}
    ]
    if mode == "deep" and clarifications:
        clar_text = "\n".join(f"Frage: {q}\nAntwort: {a}" for q, a in clarifications.items())
        messages.append({"role": "user", "content": f"Klarstellungen:\n{clar_text}"})

    # 5) LLM-Aufruf
    resp = llm.invoke(messages)
    resp_content = resp.content

    # 6) Usage-Logging
    log_event({
        "type": "usage",
        "conversation_id": conversation_id,
        "mode": mode,
        "input_tokens": resp.usage.prompt_tokens,
        "output_tokens": resp.usage.completion_tokens
    })

    # 7) Rückfragen extrahieren (nur deep)
    questions = extract_questions_from_response(resp_content) if mode == "deep" else []

    return {
        "response": resp_content,
        "questions": questions,
        "conversation_id": conversation_id
    }
