import pytest
from app.rag import chunks

def test_chunks_empty():
    assert chunks("  ") == []

def test_chunks_preserve_end_and_limit_size():
    text=" ".join("token"+str(i) for i in range(80))
    result=chunks(text)
    assert len(result)>1
    assert all(len(x)<=900 for x in result)
    assert "token79" in result[-1]

def test_invalid_overlap(monkeypatch):
    import app.rag as rag
    monkeypatch.setattr(rag.settings,"chunk_size",10)
    monkeypatch.setattr(rag.settings,"overlap",10)
    with pytest.raises(ValueError): chunks("some text")
