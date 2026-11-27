from pathlib import Path
import json

from scripts import collect_data


def test_momo_seed_reviews_are_cleaned_and_deduplicated(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "data" / "raw" / "momo_reviews.jsonl"
    output = tmp_path / "processed" / "momo_reviews.jsonl"
    monkeypatch.setattr(collect_data, "SOURCE", source)
    monkeypatch.setattr(collect_data, "OUTPUT", output)

    collect_data.main()

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 10
    assert len({row["document_id"] for row in rows}) == 10
    assert {row["movie_title"] for row in rows} == {"기생충", "인터스텔라", "극한직업", "라라랜드", "겨울왕국"}
    assert all(row["title"].startswith(row["movie_title"]) for row in rows)
    assert all(row["source"].startswith("https://github.com/madison-yoon/MOMO/") for row in rows)
