from app.rag.vector_store import clear_collection, query_chunks, upsert_chunks


def test_query_uses_atlas_vector_search_and_returns_metadata(monkeypatch):
    from app.config import settings
    from app.rag import vector_store

    class Collection:
        pipeline = None

        def aggregate(self, pipeline):
            self.pipeline = pipeline
            return [{
                "text": "주인공의 선택과 성장에 관한 리뷰",
                "metadata": {
                    "document_id": "review-001",
                    "review_id": "review-001",
                    "movie_code": "MOV-001",
                    "movie_title": "테스트 영화",
                    "genre": "드라마",
                    "title": "성장에 관한 감상",
                    "source": "MOMO-RAG/scripts/seed.py",
                },
                "score": 0.91,
            }]

    collection = Collection()
    monkeypatch.setattr(vector_store, "_get_collection", lambda: collection)
    monkeypatch.setattr(settings, "embedding_dimensions", 3)
    monkeypatch.setattr(settings, "retrieval_top_k", 2)
    monkeypatch.setattr(settings, "mongodb_vector_index", "vector_index")
    monkeypatch.setattr(settings, "mongodb_vector_path", "embedding")

    results = query_chunks([0.1, 0.2, 0.3])

    vector_stage = collection.pipeline[0]["$vectorSearch"]
    assert vector_stage["index"] == "vector_index"
    assert vector_stage["path"] == "embedding"
    assert vector_stage["queryVector"] == [0.1, 0.2, 0.3]
    assert vector_stage["limit"] == 2
    assert results[0]["metadata"]["movie_code"] == "MOV-001"
    assert results[0]["metadata"]["movie_title"] == "테스트 영화"
    assert results[0]["metadata"]["genre"] == "드라마"
    assert results[0]["metadata"]["source"] == "MOMO-RAG/scripts/seed.py"
    assert results[0]["score"] == 0.91


def test_query_rejects_wrong_embedding_dimension(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "embedding_dimensions", 3)
    try:
        query_chunks([0.1, 0.2])
    except ValueError as exc:
        assert "임베딩 차원" in str(exc)
    else:
        raise AssertionError("차원이 다른 임베딩은 거부해야 합니다.")


def test_upsert_rejects_chunk_embedding_count_mismatch():
    try:
        upsert_chunks([{"id": "chunk-1"}], [])
    except ValueError as exc:
        assert "개수가 다릅니다" in str(exc)
    else:
        raise AssertionError("chunk와 embedding 개수가 다르면 거부해야 합니다.")


def test_clear_collection_uses_delete_many(monkeypatch):
    from app.rag import vector_store

    class Collection:
        deleted_filter = None

        def delete_many(self, query):
            self.deleted_filter = query

    collection = Collection()
    monkeypatch.setattr(vector_store, "_get_collection", lambda: collection)

    clear_collection()

    assert collection.deleted_filter == {}
