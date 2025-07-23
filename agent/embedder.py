# agent/embedder.py

from langchain_openai import OpenAIEmbeddings

# Init LangChain-Embeddings + auto-logging in LangSmith
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

def create_embedding(text: str) -> list[float]:
    """Erstellt ein Embedding für einen Text mit LangChain + LangSmith Logging"""
    return embeddings.embed_query(text)
