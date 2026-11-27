"""Recall@K와 MRR@K로 조문 검색 품질을 평가한다."""
import json
import sys
from pathlib import Path

# scripts/ 디렉터리에서 직접 실행해도 프로젝트 루트를 모듈 경로에 포함한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.rag.retriever import retrieve

TEST_FILE = PROJECT_ROOT / "data" / "evaluation" / "questions.json"


def calculate_metrics(cases, search, top_k):
    if not cases:
        raise ValueError("평가 질문이 없습니다.")

    hits = 0
    reciprocal_ranks = []
    details = []

    for case in cases:
        expected = set(case["expected_articles"])
        results = search(case["question"], top_k)
        ranked = [row.get("metadata", {}).get("article_id") for row in results]
        rank = next(
            (index + 1 for index, article in enumerate(ranked) if article in expected),
            None,
        )
        hits += int(rank is not None)
        reciprocal_ranks.append(1 / rank if rank else 0)
        details.append({
            "question": case["question"],
            "expected": sorted(expected),
            "retrieved": ranked,
            "hit": rank is not None,
            "rank": rank,
        })

    return {
        "question_count": len(cases),
        "top_k": top_k,
        "recall_at_k": hits / len(cases),
        "mrr_at_k": sum(reciprocal_ranks) / len(cases),
        "details": details,
    }


def main():
    cases = json.loads(TEST_FILE.read_text(encoding="utf-8"))
    top_k = settings.retrieval_top_k
    report = calculate_metrics(
        cases,
        lambda question, limit: retrieve(question, top_k=limit),
        top_k,
    )
    for item in report["details"]:
        print(
            f'{item["question"]} | 기대={item["expected"]} '
            f'| 검색={item["retrieved"]} | 적중={item["hit"]}'
        )
    print(f'Recall@{top_k}: {report["recall_at_k"]:.3f}')
    print(f'MRR@{top_k}: {report["mrr_at_k"]:.3f}')


if __name__ == "__main__":
    main()
