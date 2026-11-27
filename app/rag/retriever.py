from app.rag.embedder import embed_texts
from app.rag.vector_store import query_chunks


def retrieve(question: str, top_k: int = 5) -> list[dict]:
    vector = embed_texts([question])[0]
    return query_chunks(vector, top_k=top_k)
