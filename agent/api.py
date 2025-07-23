# agent/api.py

from fastapi import FastAPI, UploadFile
from pydantic import BaseModel
from agent import loader, embedder, vectorstore, query, scrape_competitors

# ✅ LangSmith Import
from langchain.callbacks.tracers import LangChainTracer
from langchain_core.tracers.context import tracing_v2_enabled

# ✅ Tracer einmal erstellen
tracer = LangChainTracer()

app = FastAPI()

# -------------------------------
# 1) PDF-Upload & Vektor speichern
# -------------------------------

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile):
    """
    Nimmt eine PDF entgegen, extrahiert den Text,
    splittet in Chunks, generiert Embeddings,
    speichert alles in Qdrant.
    """
    content = await file.read()
    with open("uploaded.pdf", "wb") as f:
        f.write(content)

    text = loader.load_pdf("uploaded.pdf")
    chunks = []
    for para in text.split("\n\n"):
        if para.strip():
            emb = embedder.create_embedding(para)
            chunks.append({"text": para, "embedding": emb})

    vectorstore.upsert_chunks(chunks, collection_name="pdf_chunks")

    return {"message": f"✅ {len(chunks)} Chunks gespeichert!"}

# -------------------------------
# 2) Frage stellen (Qdrant + GPT)
# -------------------------------

class AskRequest(BaseModel):
    question: str

@app.post("/ask/")
async def ask(req: AskRequest):
    """
    Nimmt eine Frage entgegen, holt relevante Chunks
    aus Qdrant, schickt sie an GPT, gibt die Antwort zurück.
    Mit LangSmith-Tracing!
    """
    with tracing_v2_enabled() as session:
        session.add_tracer(tracer)
        answer = query.query_agent(req.question)
    return {"answer": answer}

# -------------------------------
# 3) Wettbewerber-Scraping starten
# -------------------------------

@app.post("/scrape-now/")
async def scrape_now():
    """
    Führt den Scraper aus: lädt competitor-URLs,
    scraped Seiten, speichert Embeddings in Qdrant.
    Mit LangSmith-Tracing!
    """
    with tracing_v2_enabled() as session:
        session.add_tracer(tracer)
        scrape_competitors.scrape_and_update()
    return {"status": "✅ Scraper gestartet!"}
