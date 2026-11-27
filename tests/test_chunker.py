from app.rag.chunker import split_documents


def test_chunker_keeps_article_citation_metadata():
    documents = [{"article_id": "제17조", "title": "제17조(근로조건의 명시)", "text": "근로조건 " * 120, "source": "https://law.go.kr/example"}]
    chunks = split_documents(documents, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(chunk["article_id"] == "제17조" for chunk in chunks)
    assert all(chunk["source"].startswith("https://law.go.kr") for chunk in chunks)
    assert all(len(chunk["text"]) <= 100 for chunk in chunks)


def test_chunker_rejects_invalid_overlap():
    try:
        split_documents([], chunk_size=100, chunk_overlap=100)
    except ValueError:
        return
    raise AssertionError("invalid overlap must raise ValueError")
