import chromadb
from app.config import settings

_client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
_collection = _client.get_or_create_collection(name="worklaw_articles", metadata={"hnsw:space": "cosine"})

def upsert_chunks(chunks: list[dict], embeddings: list[list[float]]) -> None:
    if not chunks:
        raise ValueError("저장할 chunk가 없습니다.")
    if len(chunks) != len(embeddings):
        raise ValueError("chunk와 embedding 개수가 다릅니다.")
    _collection.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embeddings,
        metadatas=[{k: c[k] for k in ("article_id", "title", "source")} for c in chunks],
    )

def query_chunks(embedding: list[float], top_k: int = 5) -> list[dict]:
    count = _collection.count()
    if count == 0:
        return []
    result = _collection.query(
        query_embeddings=[embedding], n_results=min(max(1, top_k), count),
        include=["documents", "metadatas", "distances"],
    )
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    return [{"text": doc, "metadata": metas[i] or {},
             "distance": distances[i] if i < len(distances) else None}
            for i, doc in enumerate(docs)]

def collection_count() -> int:
    return _collection.count()
