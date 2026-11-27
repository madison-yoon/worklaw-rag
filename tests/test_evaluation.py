from scripts.evaluate import calculate_metrics


def test_recall_and_mrr_use_expected_momo_review_ids():
    cases = [
        {"question": "질문1", "expected_documents": ["momo-demo-001"]},
        {"question": "질문2", "expected_documents": ["momo-demo-002"]},
        {"question": "질문3", "expected_documents": ["momo-demo-003", "momo-demo-004"]},
    ]
    results = {
        "질문1": [{"metadata": {"document_id": "momo-demo-001"}}],
        "질문2": [
            {"metadata": {"document_id": "momo-demo-009"}},
            {"metadata": {"document_id": "momo-demo-002"}},
        ],
        "질문3": [
            {"metadata": {"document_id": "momo-demo-003"}},
            {"metadata": {"document_id": "momo-demo-010"}},
        ],
    }
    report = calculate_metrics(cases, lambda question, _k: results[question], top_k=2)
    assert report["recall_at_k"] == (1 + 1 + 0.5) / 3
    assert report["mrr_at_k"] == (1 + 0.5 + 1) / 3
    assert report["details"][2]["relevant_found"] == ["momo-demo-003"]


def test_empty_evaluation_set_is_rejected():
    try:
        calculate_metrics([], lambda _question, _k: [], top_k=2)
    except ValueError as exc:
        assert "평가 질문" in str(exc)
    else:
        raise AssertionError("빈 평가 데이터는 거부해야 합니다.")


def test_evaluation_rejects_empty_expected_documents():
    try:
        calculate_metrics(
            [{"question": "질문", "expected_documents": []}],
            lambda _question, _k: [],
            top_k=2,
        )
    except ValueError as exc:
        assert "기대 문서" in str(exc)
    else:
        raise AssertionError("기대 문서가 없는 평가는 거부해야 합니다.")
