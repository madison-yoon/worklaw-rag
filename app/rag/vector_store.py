from functools import lru_cache

from pymongo import MongoClient, ReplaceOne
from pymongo.errors import PyMongoError

from app.config import settings


@lru_cache(maxsize=1)
def _get_client() -> MongoClient:
    if not settings.mongodb_uri.strip():
        raise RuntimeError("MONGODB_URI가 .env에 설정되지 않았습니다.")
    return MongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
        appname="momo-movie-rag",
    )


@lru_cache(maxsize=1)
def _get_collection():
    client = _get_client()
    return client[settings.mongodb_database][settings.mongodb_collection]


def check_connection() -> dict:
    """Atlas 연결과 대상 컬렉션의 문서 수를 확인한다."""
    try:
        _get_client().admin.command("ping")
        count = _get_collection().count_documents({})
        return {
            "connected": True,
            "document_count": count,
            "database": settings.mongodb_database,
            "collection": settings.mongodb_collection,
            "error": None,
        }
    except Exception as exc:
        return {
            "connected": False,
            "document_count": 0,
            "database": settings.mongodb_database,
            "collection": settings.mongodb_collection,
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
        }


def upsert_chunks(chunks: list[dict], embeddings: list[list[float]]) -> None:
    if not chunks:
        raise ValueError("저장할 chunk가 없습니다.")
    if len(chunks) != len(embeddings):
        raise ValueError("chunk와 embedding 개수가 다릅니다.")

    operations = []
    metadata_fields = (
        "document_id", "review_id", "movie_code", "movie_title", "genre",
        "director", "release_date", "overview", "title", "source",
        "source_api", "chunk_index",
    )

    for chunk, embedding in zip(chunks, embeddings):
        if len(embedding) != settings.embedding_dimensions:
            raise ValueError(f"임베딩 차원이 올바르지 않습니다: {len(embedding)}")
        chunk_id = str(chunk.get("id", "")).strip()
        if not chunk_id:
            raise ValueError("각 chunk에는 고유한 id가 필요합니다.")

        document = {
            "_id": chunk_id,
            "text": str(chunk["text"]),
            "embedding": [float(value) for value in embedding],
            "source_system": "momo-movie-rag",
        }
        for key in metadata_fields:
            value = chunk.get(key)
            if value is not None:
                document[key] = value

        operations.append(ReplaceOne({"_id": chunk_id}, document, upsert=True))

    try:
        _get_collection().bulk_write(operations, ordered=False)
    except PyMongoError as exc:
        raise RuntimeError(f"MongoDB Atlas 벡터 저장 실패: {exc}") from exc


def query_chunks(embedding: list[float], top_k: int | None = None) -> list[dict]:
    result_limit = top_k if top_k is not None else settings.retrieval_top_k
    if len(embedding) != settings.embedding_dimensions:
        raise ValueError(f"질문 임베딩 차원이 올바르지 않습니다: {len(embedding)}")
    if result_limit < 1:
        raise ValueError("검색 결과 개수는 1 이상이어야 합니다.")
    if not settings.mongodb_vector_index or not settings.mongodb_vector_path:
        raise RuntimeError("MongoDB Vector Search index와 vector path 설정을 확인하세요.")

    pipeline = [
        {
            "$vectorSearch": {
                "index": settings.mongodb_vector_index,
                "path": settings.mongodb_vector_path,
                "queryVector": [float(value) for value in embedding],
                "numCandidates": max(result_limit, result_limit * settings.vector_num_candidates_multiplier),
                "limit": result_limit,
            }
        },
        {
            "$project": {
                "_id": 0,
                "text": 1,
                "metadata": {
                    "document_id": "$document_id",
                    "review_id": "$review_id",
                    "movie_code": "$movie_code",
                    "movie_title": "$movie_title",
                    "genre": "$genre",
                    "director": "$director",
                    "release_date": "$release_date",
                    "overview": "$overview",
                    "title": "$title",
                    "source": "$source",
                    "source_api": "$source_api",
                    "chunk_index": "$chunk_index",
                },
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    try:
        rows = list(_get_collection().aggregate(pipeline))
    except PyMongoError as exc:
        raise RuntimeError(
            "MongoDB Atlas Vector Search 실패: Atlas Search 인덱스 이름·필드 경로·차원(1536)을 확인하세요. "
            f"원인: {exc}"
        ) from exc

    return [
        {
            "text": row.get("text", ""),
            "metadata": {key: value for key, value in (row.get("metadata") or {}).items() if value is not None},
            "score": row.get("score"),
        }
        for row in rows
    ]


def clear_collection() -> None:
    """RAG 전용 컬렉션을 비운다. 대상 컬렉션은 .env의 MONGODB_COLLECTION이다."""
    try:
        _get_collection().delete_many({})
    except PyMongoError as exc:
        raise RuntimeError(f"MongoDB Atlas 컬렉션 초기화 실패: {exc}") from exc


def collection_count() -> int:
    return _get_collection().count_documents({})
