"""Evaluate retrieval with article-level Recall@K and reciprocal rank."""
import json
from pathlib import Path
from app.rag.retriever import retrieve

TEST_FILE = Path("data/evaluation/questions.json")

def main():
    cases = json.loads(TEST_FILE.read_text(encoding="utf-8"))
    recall_hits = 0
    reciprocal_ranks = []
    for case in cases:
        results = retrieve(case["question"], top_k=5)
        ranked = [row["metadata"].get("article_id") for row in results]
        expected = set(case["expected_articles"])
        hit_rank = next((i + 1 for i, article in enumerate(ranked) if article in expected), None)
        recall_hits += int(hit_rank is not None)
        reciprocal_ranks.append(1 / hit_rank if hit_rank else 0)
        print(f"질문: {case['question']} | 기대 조문: {sorted(expected)} | 검색 결과: {ranked} | hit: {bool(hit_rank)}")
    n = len(cases)
    print(f"Recall@5: {recall_hits / n:.3f}")
    print(f"MRR@5: {sum(reciprocal_ranks) / n:.3f}")

if __name__ == "__main__":
    main()
