# pdf_qa_pipeline.py

import os
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
import fitz  # PyMuPDF

load_dotenv()

client = OpenAI()
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

def process_pdf_and_ask_question(pdf_path: str, question: str) -> str:
    doc = fitz.open(pdf_path)
    full_text = "".join(page.get_text() for page in doc)
    chunks = [chunk.strip() for chunk in full_text.split("\n\n") if chunk.strip()]
    collection_name = "pdf_chunks"

    if not qdrant_client.collection_exists(collection_name=collection_name):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config={"size": 1536, "distance": "Cosine"}
        )

    points = []
    for i, chunk in enumerate(chunks):
        embedding = client.embeddings.create(
            model="text-embedding-3-small",
            input=chunk
        ).data[0].embedding

        points.append(PointStruct(id=i, vector=embedding, payload={"text": chunk}))

    qdrant_client.upsert(collection_name=collection_name, points=points)

    query_embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input=question
    ).data[0].embedding

    search_result = qdrant_client.query_points(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=3
    )

    context = "\n---\n".join(hit.payload["text"] for hit in search_result)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Du bist ein hilfreicher Marketing-Analyse-Agent."},
            {"role": "user", "content": f"Kontext:\n{context}\n\nFrage: {question}"}
        ]
    )

    return response.choices[0].message.content
