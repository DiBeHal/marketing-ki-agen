# agent/api.py

import os
import uuid
import hashlib
from typing import Dict, Optional, Literal

from fastapi import FastAPI, UploadFile, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from agent import loader, embedder, vectorstore, query, scrape_competitors

# ✅ LangSmith Import
from langchain.callbacks.tracers import LangChainTracer
from langchain_core.tracers.context import tracing_v2_enabled

# ✅ Tracer einmal erstellen
tracer = LangChainTracer()

app = FastAPI()

# ===== Einfaches HTTP Basic Auth für alle Endpoints =====
security = HTTPBasic()

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """
    Prüft Username und Passwort-Hash gegen ENV-Variablen APP_USER und APP_PASS_HASH.
    """
    expected_user = os.getenv("APP_USER")
    expected_hash = os.getenv("APP_PASS_HASH")
    provided_hash = hashlib.sha256(credentials.password.encode()).hexdigest()
    if not (credentials.username == expected_user and provided_hash == expected_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# -------------------------------
# 1) PDF-Upload & Vektor speichern
# -------------------------------
@app.post(
    "/upload-pdf/",
    dependencies=[Depends(get_current_user)]
)
async def upload_pdf(file: UploadFile):
    """
    Nimmt eine PDF entgegen, extrahiert den Text,
    splittet in Chunks, generiert Embeddings,
    speichert alles in Qdrant.
    """
    content = await file.read()
    path = "uploaded.pdf"
    with open(path, "wb") as f:
        f.write(content)

    text = loader.load_pdf(path)
    chunks = []
    for para in text.split("\n\n"):
        if para.strip():
            emb = embedder.create_embedding(para)
            chunks.append({"text": para, "embedding": emb})

    vectorstore.upsert_chunks(chunks, collection_name="pdf_chunks")
    return {"message": f"✅ {len(chunks)} Chunks gespeichert!"}


# -------------------------------
# 2) Frage stellen (Qdrant + GPT) mit Deep Reasoning
# -------------------------------
class AskRequest(BaseModel):
    question: str
    mode: Literal["fast", "deep"] = "fast"
    conversation_id: Optional[str] = None
    clarifications: Optional[Dict[str, str]] = None


@app.post(
    "/ask/",
    dependencies=[Depends(get_current_user)]
)
async def ask(req: AskRequest):
    """
    Nimmt eine Frage entgegen, holt relevante Chunks
    aus Qdrant, führt Fast- oder Deep-Reasoning durch,
    stellt ggf. Rückfragen und gibt Antwort & neue Fragen zurück.
    """
    with tracing_v2_enabled() as session:
        session.add_tracer(tracer)
        result = query.query_agent(
            question=req.question,
            mode=req.mode,
            clarifications=req.clarifications,
            conversation_id=req.conversation_id
        )

    return {
        "response": result["response"],
        "questions": result["questions"],
        "conversation_id": result["conversation_id"]
    }


# -------------------------------
# 3) Wettbewerber-Scraping starten
# -------------------------------
@app.post(
    "/scrape-now/",
    dependencies=[Depends(get_current_user)]
)
async def scrape_now():
    """
    Führt den Scraper aus: lädt competitor-URLs,
    scraped Seiten, speichert Embeddings in Qdrant.
    """
    with tracing_v2_enabled() as session:
        session.add_tracer(tracer)
        scrape_competitors.scrape_and_update()
    return {"status": "✅ Scraper gestartet!"}
