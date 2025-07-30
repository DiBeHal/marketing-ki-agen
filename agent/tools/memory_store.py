from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
import os

def save_to_memory(texts: list[str], index_path: str = "memory/index"):
    """
    Speichert eine Liste von Texten als Embeddings in einem lokalen FAISS-Index.
    """
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    embeddings = OpenAIEmbeddings()
    db = FAISS.from_texts(texts, embedding=embeddings)
    db.save_local(index_path)

def search_memory(query: str, index_path: str = "memory/index", k: int = 5):
    """
    Durchsucht den gespeicherten FAISS-Index nach semantisch passenden Texten.
    """
    embeddings = OpenAIEmbeddings()
    db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    return db.similarity_search(query, k=k)
