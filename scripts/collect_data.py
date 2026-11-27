"""MOMO 영화 검색 API로 리뷰의 영화 코드를 확인하고 상세 메타데이터를 결합한다.

리뷰 본문은 MOMO 프로젝트의 시연용 가상 데이터이며 실제 회원 리뷰가 아니다.
원본 데이터에 포함된 영화 코드는 오래되었거나 잘못 매핑될 수 있으므로 제목으로 재조회한다.
"""
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings

SOURCE = ROOT / "data" / "raw" / "momo_reviews.jsonl"
OUTPUT = ROOT / "data" / "processed" / "momo_reviews.jsonl"


def find_movie_code_by_title(session: requests.Session, movie_title: str) -> str:
    base_url = settings.momo_api_base_url.rstrip("/")
    response = session.get(
        f"{base_url}/api/movies/search",
        params={"keyword": movie_title, "page": 1, "size": 30},
        timeout=(3, 15),
    )
    response.raise_for_status()
    payload = response.json()
    movies = payload.get("content", []) if isinstance(payload, dict) else []
    exact_matches = [
        movie for movie in movies
        if isinstance(movie, dict) and (movie.get("title") or "").strip() == movie_title
    ]
    if not exact_matches:
        raise ValueError(f"MOMO 영화 검색 결과에서 정확히 일치하는 제목을 찾지 못했습니다: {movie_title}")
    if len(exact_matches) > 1:
        codes = [str(movie.get("movieCode", "")) for movie in exact_matches]
        raise ValueError(f"동일한 제목의 영화가 여러 건 검색되었습니다: {movie_title} / {codes}")
    movie_code = str(exact_matches[0].get("movieCode") or "").strip()
    if not movie_code:
        raise ValueError(f"영화 검색 결과에 영화 코드가 없습니다: {movie_title}")
    return movie_code


def fetch_movie_detail(session: requests.Session, movie_code: str) -> dict:
    base_url = settings.momo_api_base_url.rstrip("/")
    response = session.get(f"{base_url}/api/movies/{movie_code}", timeout=(3, 15))
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
        required = ("review_id", "movie_title", "review_title", "text", "source")
        if any(not str(item.get(key, "")).strip() for key in required):
            raise ValueError(f"{line_number}번째 데이터의 필수 항목이 비어 있습니다.")
        item["text"] = " ".join(item["text"].split())
        raw_records[item["review_id"]] = item

    if len(raw_records) != 10:
        raise ValueError(f"MOMO 시연 리뷰는 중복 제거 후 10건이어야 합니다. 현재 {len(raw_records)}건입니다.")

    documents = []
    movie_details = {}
    movie_codes = {}
    with requests.Session() as session:
        for movie_title in sorted({row["movie_title"] for row in raw_records.values()}):
            movie_code = find_movie_code_by_title(session, movie_title)
            detail = fetch_movie_detail(session, movie_code)
            if (detail.get("title") or "").strip() != movie_title:
                raise ValueError(
                    f"영화 검색 결과와 상세 정보의 제목이 일치하지 않습니다: "
                    f"{movie_title} / {detail.get('title')} ({movie_code})"
                )
            movie_codes[movie_title] = movie_code
            movie_details[movie_title] = detail

    for item in raw_records.values():
        movie_title = item["movie_title"]
        detail = movie_details[movie_title]
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
            "movie_code": movie_codes[movie_title],
            "movie_title": movie_title,
            "genre": detail.get("genre") or "",
            "director": detail.get("director") or "",
            "release_date": detail.get("releaseDate") or "",
            "overview": overview,
            "actors": detail.get("actors") or [],
            "movie_metadata_text": metadata_text,
            "source": "https://github.com/madison-yoon/MOMO",
            "source_api": f'{settings.momo_api_base_url.rstrip("/")}/api/movies/{movie_codes[movie_title]}',
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".jsonl.tmp")
    temp.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in documents),
        encoding="utf-8",
    )
    temp.replace(OUTPUT)
    print(f"MOMO 영화 상세 API 연결 및 리뷰 정제 완료: {len(documents)}건")
    for title, code in sorted(movie_codes.items()):
        print(f"- {title}: {code}")
    print(f"영화 상세 조회: {len(movie_details)}회")
    print(f"저장: {OUTPUT}")


if __name__ == "__main__":
    main()
