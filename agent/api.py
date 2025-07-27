# agent/api.py

import os
import uuid
import hashlib
import datetime
from typing import Dict, Optional, Literal, List

from fastapi import FastAPI, UploadFile, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from agent import loader, embedder, vectorstore, query, scrape_competitors
from agent.schemas import Customer, MemoryEntry, ActivityItem, FeedbackItem, ReportStatus

# ✅ LangSmith Import
from langchain.callbacks.tracers import LangChainTracer
from langchain_core.tracers.context import tracing_v2_enabled

# ✅ Tracer einmal erstellen
tracer = LangChainTracer()

app = FastAPI()

# ===== Einfaches HTTP Basic Auth für alle Endpoints =====
security = HTTPBasic()

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
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

# In-Memory Datenbank
CUSTOMERS = {}
MEMORY = {}
ACTIVITY_LOG = []
USAGE_STATS = {}
FEEDBACKS = []
LIGHTHOUSE_HISTORY = {}
REPORTS = {}

# -------------------------------
# 1) PDF-Upload & Vektor speichern
# -------------------------------
@app.post("/upload-pdf/", dependencies=[Depends(get_current_user)])
async def upload_pdf(file: UploadFile):
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
# 2) Frage stellen (Qdrant + GPT)
# -------------------------------
class AskRequest(BaseModel):
    question: str
    mode: Literal["fast", "deep"] = "fast"
    conversation_id: Optional[str] = None
    clarifications: Optional[Dict[str, str]] = None

@app.post("/ask/", dependencies=[Depends(get_current_user)])
async def ask(req: AskRequest, user: str = Depends(get_current_user)):
    with tracing_v2_enabled() as session:
        session.add_tracer(tracer)
        result = query.query_agent(
            question=req.question,
            mode=req.mode,
            clarifications=req.clarifications,
            conversation_id=req.conversation_id
        )
    ACTIVITY_LOG.append(ActivityItem(
        timestamp=str(datetime.datetime.utcnow()), user=user, action="ask",
        metadata={"question": req.question}
    ))
    USAGE_STATS[user] = USAGE_STATS.get(user, 0) + 1
    return {
        "response": result["response"],
        "questions": result["questions"],
        "conversation_id": result["conversation_id"]
    }

# -------------------------------
# 3) Wettbewerber-Scraping starten
# -------------------------------
@app.post("/scrape-now/", dependencies=[Depends(get_current_user)])
async def scrape_now(user: str = Depends(get_current_user)):
    with tracing_v2_enabled() as session:
        session.add_tracer(tracer)
        scrape_competitors.scrape_and_update()
    ACTIVITY_LOG.append(ActivityItem(
        timestamp=str(datetime.datetime.utcnow()), user=user, action="scrape-now"
    ))
    return {"status": "✅ Scraper gestartet!"}

# -------------------------------
# 4) Health-Check
# -------------------------------
@app.get("/health/", dependencies=[Depends(get_current_user)])
async def health():
    return {"status": "ok"}

# -------------------------------
# 5) Kunden-CRUD
# -------------------------------
@app.post("/customers/", dependencies=[Depends(get_current_user)])
async def create_customer(customer: Customer):
    customer.id = str(uuid.uuid4())
    CUSTOMERS[customer.id] = customer
    return customer

@app.get("/customers/", dependencies=[Depends(get_current_user)])
async def list_customers():
    return list(CUSTOMERS.values())

@app.get("/customers/{customer_id}", dependencies=[Depends(get_current_user)])
async def get_customer(customer_id: str):
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CUSTOMERS[customer_id]

@app.put("/customers/{customer_id}", dependencies=[Depends(get_current_user)])
async def update_customer(customer_id: str, customer: Customer):
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.id = customer_id
    CUSTOMERS[customer_id] = customer
    return customer

@app.delete("/customers/{customer_id}", dependencies=[Depends(get_current_user)])
async def delete_customer(customer_id: str):
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found")
    del CUSTOMERS[customer_id]
    return {"status": "deleted"}

# -------------------------------
# 6) Memory Management
# -------------------------------
@app.get("/customers/{customer_id}/memory/", dependencies=[Depends(get_current_user)])
async def get_memory(customer_id: str):
    return MEMORY.get(customer_id, [])

@app.post("/customers/{customer_id}/memory/", dependencies=[Depends(get_current_user)])
async def add_memory(customer_id: str, entry: MemoryEntry):
    entry.id = str(uuid.uuid4())
    MEMORY.setdefault(customer_id, []).append(entry)
    return entry

@app.put("/customers/{customer_id}/memory/{entry_id}", dependencies=[Depends(get_current_user)])
async def update_memory(customer_id: str, entry_id: str, entry: MemoryEntry):
    entries = MEMORY.get(customer_id, [])
    for i, e in enumerate(entries):
        if e.id == entry_id:
            entry.id = entry_id
            entries[i] = entry
            return entry
    raise HTTPException(status_code=404, detail="Entry not found")

@app.delete("/customers/{customer_id}/memory/{entry_id}", dependencies=[Depends(get_current_user)])
async def delete_memory(customer_id: str, entry_id: str):
    entries = MEMORY.get(customer_id, [])
    for i, e in enumerate(entries):
        if e.id == entry_id:
            del entries[i]
            return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Entry not found")

# -------------------------------
# 7) Activity Log
# -------------------------------
@app.get("/activity-log/", dependencies=[Depends(get_current_user)])
async def get_activity_log():
    return ACTIVITY_LOG

# -------------------------------
# 8) Usage Stats
# -------------------------------
@app.get("/usage-stats/", dependencies=[Depends(get_current_user)])
async def usage_stats():
    return USAGE_STATS

# -------------------------------
# 9) Feedback
# -------------------------------
@app.post("/feedback/", dependencies=[Depends(get_current_user)])
async def add_feedback(item: FeedbackItem):
    FEEDBACKS.append(item)
    return {"status": "ok"}

@app.get("/feedback/", dependencies=[Depends(get_current_user)])
async def get_feedback():
    return FEEDBACKS

# -------------------------------
# 10) Lighthouse-History
# -------------------------------
@app.get("/lighthouse/{scan_id}", dependencies=[Depends(get_current_user)])
async def get_lighthouse(scan_id: str):
    return LIGHTHOUSE_HISTORY.get(scan_id, {})

# -------------------------------
# 11) Reports Async (mit BackgroundTasks)
# -------------------------------
def generate_report(report_id: str):
    # Dummy-Ausgabe nach Wartezeit
    import time
    time.sleep(5)  # Simuliere langen Task
    REPORTS[report_id] = ReportStatus(status="done", result="Dies ist der fertige Monatsreport für ID: " + report_id)

@app.post("/monthly-report/", dependencies=[Depends(get_current_user)])
async def create_report(background_tasks: BackgroundTasks):
    report_id = str(uuid.uuid4())
    REPORTS[report_id] = ReportStatus(status="pending")
    background_tasks.add_task(generate_report, report_id)
    return {"report_id": report_id}

@app.get("/monthly-report/{report_id}/status", dependencies=[Depends(get_current_user)])
async def report_status(report_id: str):
    return REPORTS.get(report_id, {"status": "unknown"})

@app.get("/monthly-report/{report_id}/download", dependencies=[Depends(get_current_user)])
async def report_download(report_id: str):
    report = REPORTS.get(report_id)
    if report and report.result:
        return {"content": report.result}
    raise HTTPException(status_code=404, detail="Report not ready")
