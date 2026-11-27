import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.rag.chunker import split_documents
from app.rag.embedder import embed_texts
from app.rag.vector_store import check_connection, clear_collection, upsert_chunks

SOURCE = PROJECT_ROOT / "data" / "processed" / "momo_reviews.jsonl"


def main():
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 .env에 설정되지 않았습니다.")
    if not settings.mongodb_uri:
        raise RuntimeError("MONGODB_URI가 .env에 설정되지 않았습니다.")
    if not SOURCE.exists():
        raise FileNotFoundError("먼저 python scripts/collect_data.py를 실행하세요.")

    documents = [
        json.loads(line)
        for line in SOURCE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(documents) != 10:
        raise ValueError(f"MOMO 시연 리뷰 10건이 필요합니다. 현재 {len(documents)}건입니다.")

    connection = check_connection()
    if not connection["connected"]:
        raise RuntimeError(
            "MongoDB Atlas 연결에 실패했습니다. "
            f"{connection['error']} "
            "Atlas Database Access 사용자, 비밀번호, Network Access IP 허용 목록, URI를 확인하세요."
        )

    chunks = split_documents(documents, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise ValueError("청킹 결과가 없습니다. 원본 리뷰 데이터를 확인하세요.")

    print(
        f"MongoDB 연결 확인: {connection['database']}.{connection['collection']} "
        f"(기존 문서 {connection['document_count']}건)"
    )
    clear_collection()

    for start in range(0, len(chunks), settings.embedding_batch_size):
        batch = chunks[start:start + settings.embedding_batch_size]
        vectors = embed_texts([item["embedding_text"] for item in batch])
        upsert_chunks(batch, vectors)
        print(f"임베딩 및 MongoDB Atlas 저장: {min(start + len(batch), len(chunks))}/{len(chunks)}")

    final_state = check_connection()
    if not final_state["connected"] or final_state["document_count"] != len(chunks):
        raise RuntimeError(
            "색인 후 문서 수 검증에 실패했습니다. "
            f"예상 {len(chunks)}건 / 실제 {final_state['document_count']}건 / "
            f"오류 {final_state['error']}"
        )

    print(f"인덱싱 완료: 리뷰 {len(documents)}건, chunk {len(chunks)}개")
    print(
        f"저장 위치: MongoDB Atlas / {settings.mongodb_database}."
        f"{settings.mongodb_collection}"
    )


if __name__ == "__main__":
    main()
