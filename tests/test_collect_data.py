from pathlib import Path
import json

from scripts import collect_data


def test_momo_seed_reviews_are_enriched_from_existing_movie_api(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "data" / "raw" / "momo_reviews.jsonl"
    output = tmp_path / "processed" / "momo_reviews.jsonl"
    monkeypatch.setattr(collect_data, "SOURCE", source)
    monkeypatch.setattr(collect_data, "OUTPUT", output)

    calls = []
    def fake_detail(_session, movie_code):
        calls.append(movie_code)
        rows = {
            "20183782": {"movieCode": "20183782", "title": "기생충", "genre": "드라마", "director": "봉준호", "releaseDate": "20190530", "overview": "계층과 공간을 다룬다.", "actors": ["배우A"]},
            "20149120": {"movieCode": "20149120", "title": "인터스텔라", "genre": "SF", "director": "크리스토퍼 놀란", "releaseDate": "20141106", "overview": "우주 탐사를 다룬다.", "actors": []},
            "20182530": {"movieCode": "20182530", "title": "극한직업", "genre": "코미디", "director": "이병헌", "releaseDate": "20190123", "overview": "수사팀의 위장 창업 이야기.", "actors": []},
            "20161872": {"movieCode": "20161872", "title": "라라랜드", "genre": "뮤지컬", "director": "데이미언 셔젤", "releaseDate": "20161207", "overview": "꿈을 좇는 두 사람의 이야기.", "actors": []},
            "20135428": {"movieCode": "20135428", "title": "겨울왕국", "genre": "애니메이션", "director": "크리스 벅", "releaseDate": "20140116", "overview": "자매의 모험.", "actors": []},
        }
        return rows[movie_code]

    monkeypatch.setattr(collect_data, "fetch_movie_detail", fake_detail)
    collect_data.main()

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 10
    assert len(set(calls)) == 5
    assert {row["movie_title"] for row in rows} == {"기생충", "인터스텔라", "극한직업", "라라랜드", "겨울왕국"}
    assert all(row["director"] for row in rows)
    assert all(row["overview"] for row in rows)
    assert all(row["source_api"].startswith("http://localhost:8111/api/movies/") for row in rows)
