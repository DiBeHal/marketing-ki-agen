# agent/vectorstore.py
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

import os

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

def upsert_chunks(chunks, collection_name="agent_chunks"):
    if not client.collection_exists(collection_name=collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config={"size": 1536, "distance": "Cosine"}
        )

    points = []
    for i, chunk in enumerate(chunks):
        embedding = chunk["embedding"]
        payload = {"text": chunk["text"]}
        points.append(PointStruct(id=i, vector=embedding, payload=payload))

    client.upsert(collection_name=collection_name, points=points)
