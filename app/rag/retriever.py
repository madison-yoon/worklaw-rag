from app.config import settings
from app.rag.embedder import embed_texts
from app.rag.vector_store import query_chunks


def retrieve(question: str, top_k: int | None = None) -> list[dict]:
    if not question or not question.strip():
        raise ValueError("검색 질문이 비어 있습니다.")
    vector = embed_texts([question.strip()])[0]
    return query_chunks(vector, top_k=top_k or settings.retrieval_top_k)
