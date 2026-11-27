from functools import lru_cache

import chromadb

from app.config import settings


@lru_cache(maxsize=1)
def _get_client():
    return chromadb.PersistentClient(path=settings.chroma_persist_directory)


@lru_cache(maxsize=1)
def _get_collection():
    return _get_client().get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


def check_connection() -> dict:
    try:
        count = _get_collection().count()
        return {"connected": True, "document_count": count, "error": None}
    except Exception as exc:
        return {"connected": False, "document_count": 0, "error": type(exc).__name__}


def upsert_chunks(chunks: list[dict], embeddings: list[list[float]]) -> None:
    if not chunks:
        raise ValueError("저장할 chunk가 없습니다.")
    if len(chunks) != len(embeddings):
        raise ValueError("chunk와 embedding 개수가 다릅니다.")

    ids = []
    documents = []
    metadatas = []
    vectors = []
    metadata_fields = (
        "document_id", "review_id", "movie_code", "movie_title", "genre",
        "director", "release_date", "overview", "title", "source",
        "source_api", "chunk_index",
    )

    for chunk, embedding in zip(chunks, embeddings):
        if len(embedding) != settings.embedding_dimensions:
            raise ValueError(f"임베딩 차원이 올바르지 않습니다: {len(embedding)}")
        ids.append(str(chunk["id"]))
        documents.append(str(chunk["text"]))
        vectors.append(embedding)
        metadata = {key: chunk.get(key) for key in metadata_fields}
        metadatas.append({
            key: value if value is not None else ""
            for key, value in metadata.items()
        })

    _get_collection().upsert(
        ids=ids,
        documents=documents,
        embeddings=vectors,
        metadatas=metadatas,
    )


def query_chunks(embedding: list[float], top_k: int | None = None) -> list[dict]:
    result_limit = top_k if top_k is not None else settings.retrieval_top_k
    if len(embedding) != settings.embedding_dimensions:
        raise ValueError(f"질문 임베딩 차원이 올바르지 않습니다: {len(embedding)}")
    if result_limit < 1:
        raise ValueError("검색 결과 개수는 1 이상이어야 합니다.")

    result = _get_collection().query(
        query_embeddings=[embedding],
        n_results=result_limit,
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    return [
        {
            "text": text,
            "metadata": metadata or {},
            "score": 1.0 - distance if distance is not None else None,
        }
        for text, metadata, distance in zip(documents, metadatas, distances)
    ]


def clear_collection() -> None:
    # ChromaDB는 조건 없는 delete()를 허용하지 않으므로 기존 ID를 조회해 삭제한다.
    collection = _get_collection()
    existing = collection.get(include=[])
    ids = existing.get("ids", [])
    if ids:
        collection.delete(ids=ids)


def collection_count() -> int:
    return _get_collection().count()
