import pytest
from app.rag import chunks

def test_chunks_empty():
    assert chunks("  ") == []

def test_chunks_preserve_end_and_limit_size():
    text=" ".join("token"+str(i) for i in range(80))
    result=chunks(text,size=50,overlap=10)
    assert len(result)>1
    assert all(len(x)<=50 for x in result)
    assert "token79" in result[-1]

def test_invalid_overlap():
    with pytest.raises(ValueError):
        chunks("some text",size=10,overlap=10)
