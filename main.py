import os
from dotenv import load_dotenv

# OpenAI SDK
from openai import OpenAI

# Qdrant SDK
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

# PDF
import fitz  # PyMuPDF

# -------------------------------
# 1) .env laden
# -------------------------------
load_dotenv()

# -------------------------------
# 2) OpenAI & Qdrant Client starten
# -------------------------------
client = OpenAI()

qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# -------------------------------
# 3) PDF einlesen & chunken
# -------------------------------
pdf_path = "test.pdf"
doc = fitz.open(pdf_path)

full_text = ""
for page in doc:
    full_text += page.get_text()

# Text in Absätze teilen (nach 2 Zeilenumbrüchen)
chunks = [chunk.strip() for chunk in full_text.split("\n\n") if chunk.strip()]

print(f"Gefundene Chunks: {len(chunks)}")

# -------------------------------
# 4) Qdrant Collection vorbereiten
# -------------------------------
collection_name = "pdf_chunks"

# Deprecation-safe: Vorher prüfen, ob die Collection existiert
if not qdrant_client.collection_exists(collection_name=collection_name):
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config={"size": 1536, "distance": "Cosine"}
    )

# -------------------------------
# 5) Für jeden Chunk: Embedding + Upsert
# -------------------------------
points = []
for i, chunk in enumerate(chunks):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=chunk
    )
    embedding = response.data[0].embedding

    point = PointStruct(
        id=i,
        vector=embedding,
        payload={"text": chunk}
    )
    points.append(point)
    print(f"✅ Chunk {i} vorbereitet.")

# Punkte auf einmal hochladen (effizienter)
qdrant_client.upsert(
    collection_name=collection_name,
    points=points
)
print("✅ Alle Chunks wurden mit Embeddings in Qdrant gespeichert!")

# -------------------------------
# 6) Query-Flow: Frage an Qdrant + GPT-4o
# -------------------------------
question = "Worum geht es in dem PDF?"

# 1) Frage-Embedding
query_embedding = client.embeddings.create(
    model="text-embedding-3-small",
    input=question
).data[0].embedding

# 2) Ähnlichkeitssuche mit neuer Methode (Deprecation-safe)
search_result = qdrant_client.query_points(
    collection_name=collection_name,
    query_vector=query_embedding,
    limit=3  # Top 3 ähnlichste Chunks
)

# 3) Kontext bauen
context_texts = []
for hit in search_result:
    print(f"Score: {hit.score:.4f}")
    print(f"Text: {hit.payload['text'][:200]} ...")
    context_texts.append(hit.payload['text'])

context = "\n---\n".join(context_texts)

# 4) GPT-4o mit Kontext befragen
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": "Du bist ein hilfreicher Marketing-Analyse-Agent. Nutze den bereitgestellten Kontext, um die Frage zu beantworten."
        },
        {
            "role": "user",
            "content": f"Kontext:\n{context}\n\nFrage: {question}"
        }
    ]
)

print("\n✅ Antwort von GPT-4o:")
print(response.choices[0].message.content)

from fastapi import UploadFile, File
import shutil
from pdf_qa_pipeline import process_pdf_and_ask_question

@app.post("/analyze-pdf")
def analyze_pdf(file: UploadFile = File(...), question: str = "Worum geht es in dem PDF?"):
    temp_path = f"data/{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    answer = process_pdf_and_ask_question(temp_path, question)
    return {"answer": answer}

