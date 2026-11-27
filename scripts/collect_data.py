"""MOMO 프로젝트의 기존 RAG 시연 리뷰 데이터를 정제해 색인 입력 JSONL을 만든다.

외부 법령 API나 웹페이지를 호출하지 않는다. 원천은 MOMO 저장소의
MOMO-RAG/scripts/seed.py에 정의된 가상 영화 감상 10건이다.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "momo_reviews.jsonl"
OUTPUT = ROOT / "data" / "processed" / "momo_reviews.jsonl"


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"MOMO 원천 리뷰 파일이 없습니다: {SOURCE}")

    records = {}
    for line_number, line in enumerate(SOURCE.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        required = ("review_id", "movie_code", "movie_title", "review_title", "text", "source")
        if any(not str(item.get(key, "")).strip() for key in required):
            raise ValueError(f"{line_number}번째 데이터의 필수 항목이 비어 있습니다.")
        item["text"] = " ".join(item["text"].split())
        item["title"] = f'{item["movie_title"]} — {item["review_title"]}'
        item["document_id"] = item["review_id"]
        item["source"] = "https://github.com/madison-yoon/MOMO/blob/main/MOMO-RAG/scripts/seed.py"
        records[item["review_id"]] = item

    documents = list(records.values())
    if len(documents) != 10:
        raise ValueError(f"시연 리뷰는 중복 제거 후 10건이어야 합니다. 현재 {len(documents)}건입니다.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".jsonl.tmp")
    temp.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in documents), encoding="utf-8")
    temp.replace(OUTPUT)
    print(f"MOMO 리뷰 정제 완료: {len(documents)}건")
    print(f"영화: {', '.join(sorted({row['movie_title'] for row in documents}))}")
    print(f"저장: {OUTPUT}")


if __name__ == "__main__":
    main()
