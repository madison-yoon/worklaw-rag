import json
from pathlib import Path
from app.config import settings
from app.rag.chunker import split_documents
from app.rag.embedder import embed_texts
from app.rag.vector_store import upsert_chunks

SOURCE = Path("data/processed/labor_standards_act.jsonl")

def main():
    if not SOURCE.exists():
        raise FileNotFoundError("먼저 python scripts/collect_data.py를 실행하세요.")
    documents = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line.strip()]
    chunks = split_documents(documents, settings.chunk_size, settings.chunk_overlap)
    batch_size = 100
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        vectors = embed_texts([item["text"] for item in batch])
        upsert_chunks(batch, vectors)
        print(f"임베딩 및 저장: {min(start + batch_size, len(chunks))}/{len(chunks)}")
    print(f"인덱싱 완료: 조문 {len(documents)}개, chunk {len(chunks)}개")

if __name__ == "__main__":
    main()
