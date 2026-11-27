"""Recall@K와 MRR@K로 MOMO 영화 리뷰 검색 품질을 평가한다."""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.rag.retriever import retrieve

TEST_FILE = PROJECT_ROOT / "data" / "evaluation" / "questions.json"


def calculate_metrics(cases, search, top_k):
    if not cases:
        raise ValueError("평가 질문이 없습니다.")
    if top_k < 1:
        raise ValueError("top_k는 1 이상이어야 합니다.")

    recall_scores, reciprocal_ranks, details = [], [], []
    for case in cases:
        expected = set(case["expected_documents"])
        if not expected:
            raise ValueError("각 평가 질문에는 기대 문서가 최소 1개 필요합니다.")

        results = search(case["question"], top_k)
        ranked = [row.get("metadata", {}).get("document_id") for row in results[:top_k]]
        retrieved = set(ranked)
        relevant_found = expected & retrieved
        recall_scores.append(len(relevant_found) / len(expected))

        rank = next((i + 1 for i, doc_id in enumerate(ranked) if doc_id in expected), None)
        reciprocal_ranks.append(1 / rank if rank else 0)
        details.append({
            "question": case["question"],
            "expected": sorted(expected),
            "retrieved": ranked,
            "relevant_found": sorted(relevant_found),
            "recall": len(relevant_found) / len(expected),
            "rank": rank,
        })

    return {
        "question_count": len(cases),
        "top_k": top_k,
        "recall_at_k": sum(recall_scores) / len(recall_scores),
        "mrr_at_k": sum(reciprocal_ranks) / len(reciprocal_ranks),
        "details": details,
    }


def main():
    cases = json.loads(TEST_FILE.read_text(encoding="utf-8"))
    top_k = settings.retrieval_top_k
    report = calculate_metrics(cases, lambda q, k: retrieve(q, top_k=k), top_k)
    for item in report["details"]:
        print(
            f'{item["question"]} | 기대={item["expected"]} | 검색={item["retrieved"]} '
            f'| 관련문서 재현율={item["recall"]:.3f} | 첫 관련순위={item["rank"]}'
        )
    print(f'Recall@{top_k}: {report["recall_at_k"]:.3f}')
    print(f'MRR@{top_k}: {report["mrr_at_k"]:.3f}')


if __name__ == "__main__":
    main()
