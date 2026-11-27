from app.rag.vector_store import query_chunks, upsert_chunks


def test_query_uses_configured_index_and_returns_source_metadata(monkeypatch):
    from app.config import settings
    from app.rag import vector_store

    class Collection:
        pipeline = None

        def aggregate(self, pipeline):
            self.pipeline = pipeline
            return [{
                "text": "근로조건을 명시해야 한다.",
                "article_id": "제17조",
                "title": "근로조건의 명시",
                "source": "https://law.go.kr/example",
                "chunk_index": 0,
                "relevance_score": 0.91,
            }]

    collection = Collection()
    monkeypatch.setattr(vector_store, "_get_collection", lambda: collection)
    monkeypatch.setattr(settings, "embedding_dimensions", 3)
    monkeypatch.setattr(settings, "mongodb_vector_index", "test_vector")
    monkeypatch.setattr(settings, "mongodb_vector_path", "embedding")
    monkeypatch.setattr(settings, "retrieval_top_k", 2)

    results = query_chunks([0.1, 0.2, 0.3])

    assert collection.pipeline[0]["$vectorSearch"]["index"] == "test_vector"
    assert collection.pipeline[0]["$vectorSearch"]["path"] == "embedding"
    assert collection.pipeline[0]["$vectorSearch"]["limit"] == 2
    assert results[0]["metadata"]["article_id"] == "제17조"
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
