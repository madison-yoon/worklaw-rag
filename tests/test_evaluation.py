from scripts.evaluate import calculate_metrics


def test_recall_and_mrr_are_calculated_from_ranked_results():
    cases = [
        {"question": "질문1", "expected_articles": ["제17조"]},
        {"question": "질문2", "expected_articles": ["제43조"]},
        {"question": "질문3", "expected_articles": ["제50조", "제54조"]},
    ]
    results = {
        "질문1": [{"metadata": {"article_id": "제17조"}}],
        "질문2": [
            {"metadata": {"article_id": "제10조"}},
            {"metadata": {"article_id": "제43조"}},
        ],
        "질문3": [{"metadata": {"article_id": "제99조"}}],
    }

    report = calculate_metrics(
        cases,
        lambda question, _k: results[question],
        top_k=2,
    )

    assert report["recall_at_k"] == 2 / 3
    assert report["mrr_at_k"] == (1 + 0.5) / 3


def test_empty_evaluation_set_is_rejected():
    try:
        calculate_metrics([], lambda _question, _k: [], top_k=2)
    except ValueError as exc:
        assert "평가 질문" in str(exc)
    else:
        raise AssertionError("빈 평가 데이터는 거부해야 합니다.")
