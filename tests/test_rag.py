import pytest

from app.rag import chunks, vector_index_definition, vector_search_pipeline


def test_chunks_empty():
    assert chunks("  ") == []


def test_chunks_preserve_end_and_limit_size():
    text = " ".join("token" + str(i) for i in range(80))
    result = chunks(text, size=50, overlap=10)
    assert len(result) > 1
    assert all(len(item) <= 50 for item in result)
    assert "token79" in result[-1]


def test_invalid_overlap():
    with pytest.raises(ValueError):
        chunks("some text", size=10, overlap=10)


def test_vector_index_definition_matches_embedding_model_dimension():
    definition = vector_index_definition(384)
    assert definition["fields"] == [
        {
            "type": "vector",
            "path": "embedding",
            "numDimensions": 384,
            "similarity": "cosine",
        }
    ]


def test_vector_search_pipeline_uses_atlas_vector_search():
    pipeline = vector_search_pipeline([0.1, 0.2, 0.3], 5)
    stage = pipeline[0]["$vectorSearch"]
    assert stage["index"] == "vector_index"
    assert stage["path"] == "embedding"
    assert stage["queryVector"] == [0.1, 0.2, 0.3]
    assert stage["numCandidates"] == 100
    assert stage["limit"] == 5
    assert pipeline[1]["$project"]["score"] == {"$meta": "vectorSearchScore"}
