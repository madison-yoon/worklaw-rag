import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.rag.chunker import split_documents
from app.rag.embedder import embed_texts
from app.rag.vector_store import upsert_chunks

SOURCE = PROJECT_ROOT / "data" / "processed" / "momo_reviews.jsonl"


def main():
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 .env에 설정되지 않았습니다.")
    if not SOURCE.exists():
        raise FileNotFoundError("먼저 python scripts/collect_data.py를 실행하세요.")

    documents = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(documents) != 10:
        raise ValueError(f"MOMO 시연 리뷰 10건이 필요합니다. 현재 {len(documents)}건입니다.")

    chunks = split_documents(documents, settings.chunk_size, settings.chunk_overlap)
    for start in range(0, len(chunks), settings.embedding_batch_size):
        batch = chunks[start:start + settings.embedding_batch_size]
        vectors = embed_texts([item["embedding_text"] for item in batch])
        upsert_chunks(batch, vectors)
        print(f"임베딩 및 로컬 ChromaDB 저장: {min(start + len(batch), len(chunks))}/{len(chunks)}")
    print(f"인덱싱 완료: 리뷰 {len(documents)}건, chunk {len(chunks)}개")
    print(f"저장 위치: {settings.chroma_persist_directory}")


if __name__ == "__main__":
    main()
