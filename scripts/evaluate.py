"""Recall@K와 MRR@K로 조문 검색 품질을 평가한다."""
import json
from pathlib import Path
from app.rag.retriever import retrieve

TEST_FILE = Path("data/evaluation/questions.json")

def calculate_metrics(cases, search, top_k=5):
    if not cases:
        raise ValueError("평가 질문이 없습니다.")
    hits, reciprocal_ranks, details = 0, [], []
    for case in cases:
        expected = set(case["expected_articles"])
        results = search(case["question"], top_k)
        ranked = [row.get("metadata", {}).get("article_id") for row in results]
        rank = next((i + 1 for i, value in enumerate(ranked) if value in expected), None)
        hits += int(rank is not None)
        reciprocal_ranks.append(1 / rank if rank else 0)
        details.append({"question": case["question"], "expected": sorted(expected),
                        "retrieved": ranked, "hit": rank is not None, "rank": rank})
    return {"question_count": len(cases), "top_k": top_k, "recall_at_k": hits / len(cases),
            "mrr_at_k": sum(reciprocal_ranks) / len(cases), "details": details}

def main():
    cases = json.loads(TEST_FILE.read_text(encoding="utf-8"))
    report = calculate_metrics(cases, lambda question, k: retrieve(question, top_k=k))
    for item in report["details"]:
        print(f"{item['question']} | 기대={item['expected']} | 검색={item['retrieved']} | 적중={item['hit']}")
    print(f"Recall@{report['top_k']}: {report['recall_at_k']:.3f}")
    print(f"MRR@{report['top_k']}: {report['mrr_at_k']:.3f}")

if __name__ == "__main__":
    main()
