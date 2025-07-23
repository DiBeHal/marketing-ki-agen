# agent/query.py

import os
from qdrant_client import QdrantClient

from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # ✅ LangChain + OpenAI Wrapper

from agent.embedder import create_embedding

# Qdrant Client bleibt
qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

# LangChain LLM
llm = ChatOpenAI(model="gpt-4o")

def query_agent(question, collection_name="agent_chunks"):
    # 1) Frage-Embedding erstellen (deine eigene Funktion)
    embedding = create_embedding(question)

    # 2) Ähnlichkeits-Suche in Qdrant
    results = qdrant.query_points(
        collection_name=collection_name,
        query_vector=embedding,
        limit=3
    )

    # 3) Kontext bauen
    context = "\n---\n".join([hit.payload["text"] for hit in results])

    # 4) GPT-4o über LangChain aufrufen ➜ automatisch getrackt!
    response = llm.invoke([
        {
            "role": "system",
            "content": "Du bist ein Marketing-Analyse-Agent. Nutze den bereitgestellten Kontext, um die Frage zu beantworten."
        },
        {
            "role": "user",
            "content": f"Kontext:\n{context}\n\nFrage: {question}"
        }
    ])

    return response.content
