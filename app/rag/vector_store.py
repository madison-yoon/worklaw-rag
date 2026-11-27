from functools import lru_cache

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from app.config import settings


@lru_cache(maxsize=1)
def _get_client() -> MongoClient:
    if not settings.mongodb_uri:
        raise RuntimeError("MONGODB_URI가 설정되지 않았습니다. 프로젝트 루트의 .env를 확인하세요.")
    return MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        appname="MOMO-Review-RAG",
    )


def _get_collection() -> Collection:
    return _get_client()[settings.mongodb_database][settings.mongodb_collection]


def check_connection() -> dict:
    try:
        client = _get_client()
        client.admin.command("ping")
        count = _get_collection().count_documents({})
        return {"connected": True, "document_count": count, "error": None}
    except (PyMongoError, RuntimeError) as exc:
        return {"connected": False, "document_count": 0,
                "error": str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__}


def upsert_chunks(chunks: list[dict], embeddings: list[list[float]]) -> None:
    if not chunks:
        raise ValueError("저장할 chunk가 없습니다.")
    if len(chunks) != len(embeddings):
        raise ValueError("chunk와 embedding 개수가 다릅니다.")

    operations = []
    for chunk, embedding in zip(chunks, embeddings):
        if len(embedding) != settings.embedding_dimensions:
            raise ValueError(f"임베딩 차원이 올바르지 않습니다: {len(embedding)}")
        document = {
            "_id": chunk["id"], "text": chunk["text"], "embedding": embedding,
            "document_id": chunk["document_id"], "review_id": chunk["review_id"],
            "movie_code": chunk["movie_code"], "movie_title": chunk["movie_title"],
            "genre": chunk.get("genre", ""), "director": chunk.get("director", ""),
            "release_date": chunk.get("release_date", ""), "overview": chunk.get("overview", ""),
            "title": chunk["title"], "source": chunk["source"],
            "source_api": chunk.get("source_api", ""),
            "chunk_index": chunk.get("chunk_index", 0),
        }
        operations.append(UpdateOne({"_id": chunk["id"]}, {"$set": document}, upsert=True))
    _get_collection().bulk_write(operations, ordered=False)


def query_chunks(embedding: list[float], top_k: int | None = None) -> list[dict]:
    result_limit = top_k if top_k is not None else settings.retrieval_top_k
    if len(embedding) != settings.embedding_dimensions:
        raise ValueError(f"질문 임베딩 차원이 올바르지 않습니다: {len(embedding)}")
    if result_limit < 1:
        raise ValueError("검색 결과 개수는 1 이상이어야 합니다.")

    pipeline = [
        {"$vectorSearch": {
            "index": settings.mongodb_vector_index, "path": settings.mongodb_vector_path,
            "queryVector": embedding,
            "numCandidates": max(result_limit * settings.vector_num_candidates_multiplier, result_limit),
            "limit": result_limit,
        }},
        {"$project": {
            "_id": 0, "text": 1, "document_id": 1, "review_id": 1,
            "movie_code": 1, "movie_title": 1, "genre": 1, "director": 1,
            "release_date": 1, "overview": 1, "title": 1, "source": 1,
            "source_api": 1, "chunk_index": 1,
            "relevance_score": {"$meta": "vectorSearchScore"},
        }},
    ]
    documents = list(_get_collection().aggregate(pipeline))
    return [{
        "text": item["text"],
        "metadata": {key: item.get(key) for key in
                     ("document_id", "review_id", "movie_code", "movie_title", "genre",
                      "director", "release_date", "overview", "title", "source", "source_api", "chunk_index")},
        "score": item.get("relevance_score"),
    } for item in documents]


def collection_count() -> int:
    return _get_collection().count_documents({})
