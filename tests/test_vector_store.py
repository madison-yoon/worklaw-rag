from app.rag.vector_store import query_chunks, upsert_chunks


def test_query_returns_movie_source_metadata(monkeypatch):
    from app.config import settings
    from app.rag import vector_store

    class Collection:
        query_args = None

        def query(self, **kwargs):
            self.query_args = kwargs
            return {
                "documents": [["주인공의 선택과 성장에 관한 리뷰"]],
                "metadatas": [[{
                    "document_id": "review-001", "review_id": "review-001",
                    "movie_code": "MOV-001", "movie_title": "테스트 영화",
                    "genre": "드라마", "title": "성장에 관한 감상",
                    "source": "MOMO-RAG/scripts/seed.py",
                }]],
                "distances": [[0.09]],
            }

    collection = Collection()
    monkeypatch.setattr(vector_store, "_get_collection", lambda: collection)
    monkeypatch.setattr(settings, "embedding_dimensions", 3)
    monkeypatch.setattr(settings, "retrieval_top_k", 2)

    results = query_chunks([0.1, 0.2, 0.3])

    assert collection.query_args["n_results"] == 2
    assert collection.query_args["include"] == ["documents", "metadatas", "distances"]
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
