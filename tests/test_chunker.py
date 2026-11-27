from app.rag.chunker import split_documents


def test_chunker_keeps_momo_review_metadata():
    documents = [{
        "document_id": "momo-demo-001", "review_id": "momo-demo-001",
        "movie_code": "20183782", "movie_title": "기생충",
        "title": "기생충 — 공간과 표정", "text": "배우 연기와 촬영 " * 120,
        "source": "https://github.com/madison-yoon/MOMO",
    }]
    chunks = split_documents(documents, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(chunk["review_id"] == "momo-demo-001" for chunk in chunks)
    assert all(chunk["movie_title"] == "기생충" for chunk in chunks)
    assert all(chunk["source"].startswith("https://github.com/") for chunk in chunks)
    assert all(len(chunk["text"]) <= 100 for chunk in chunks)


def test_chunker_rejects_invalid_overlap():
    try:
        split_documents([], chunk_size=100, chunk_overlap=100)
    except ValueError:
        return
    raise AssertionError("invalid overlap must raise ValueError")
