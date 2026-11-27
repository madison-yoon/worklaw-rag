"""MOMO의 기존 영화 상세 API와 RAG 데모 리뷰를 결합해 검색 문서를 만든다.

실제 회원 리뷰 본문·작성자 정보는 수집하지 않는다. 영화 메타데이터는 로컬 MOMO
Spring API에서 가져오고, 리뷰 문장은 MOMO-RAG/scripts/seed.py의 공개 시연 데이터다.
"""
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "momo_reviews.jsonl"
OUTPUT = ROOT / "data" / "processed" / "momo_reviews.jsonl"


def fetch_movie_detail(session: requests.Session, movie_code: str) -> dict:
    base_url = settings.momo_api_base_url.rstrip("/")
    response = session.get(f"{base_url}/api/movies/{movie_code}", timeout=(3, 10))
    response.raise_for_status()
    detail = response.json()
    if not isinstance(detail, dict) or detail.get("movieCode") != movie_code:
        raise ValueError(f"MOMO 영화 상세 응답이 올바르지 않습니다: {movie_code}")
    return detail


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"MOMO 리뷰 원천 파일이 없습니다: {SOURCE}")

    raw_records = {}
    for line_number, line in enumerate(SOURCE.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        required = ("review_id", "movie_code", "movie_title", "review_title", "text", "source")
        if any(not str(item.get(key, "")).strip() for key in required):
            raise ValueError(f"{line_number}번째 데이터의 필수 항목이 비어 있습니다.")
        item["text"] = " ".join(item["text"].split())
        raw_records[item["review_id"]] = item

    if len(raw_records) != 10:
        raise ValueError(f"MOMO 시연 리뷰는 중복 제거 후 10건이어야 합니다. 현재 {len(raw_records)}건입니다.")

    # 영화별 상세 API는 한 번만 호출해 동일 영화의 메타데이터를 공유한다.
    movie_details = {}
    with requests.Session() as session:
        for movie_code in sorted({row["movie_code"] for row in raw_records.values()}):
            movie_details[movie_code] = fetch_movie_detail(session, movie_code)

    documents = []
    for item in raw_records.values():
        detail = movie_details[item["movie_code"]]
        movie_title = detail.get("title") or item["movie_title"]
        if movie_title != item["movie_title"]:
            raise ValueError(
                f'영화 코드와 제목이 일치하지 않습니다: {item["movie_code"]} ({movie_title})'
            )
        overview = (detail.get("overview") or "").strip()
        metadata_text = " ".join(filter(None, [
            f'장르 {detail.get("genre", "")}',
            f'감독 {detail.get("director", "")}',
            f'개봉일 {detail.get("releaseDate", "")}',
            f'줄거리 {overview}',
        ]))
        documents.append({
            **item,
            "document_id": item["review_id"],
            "movie_title": movie_title,
            "genre": detail.get("genre") or "",
            "director": detail.get("director") or "",
            "release_date": detail.get("releaseDate") or "",
            "overview": overview,
            "actors": detail.get("actors") or [],
            "movie_metadata_text": metadata_text,
            "source": "https://github.com/madison-yoon/MOMO",
            "source_api": f'{settings.momo_api_base_url.rstrip("/")}/api/movies/{item["movie_code"]}',
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".jsonl.tmp")
    temp.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in documents),
        encoding="utf-8",
    )
    temp.replace(OUTPUT)
    print(f"MOMO 영화 상세 API 연결 및 리뷰 정제 완료: {len(documents)}건")
    print(f'영화: {", ".join(sorted({row["movie_title"] for row in documents}))}')
    print(f"영화 상세 조회: {len(movie_details)}회")
    print(f"저장: {OUTPUT}")


if __name__ == "__main__":
    main()
