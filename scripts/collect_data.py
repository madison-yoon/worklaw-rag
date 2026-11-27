"""국가법령정보센터 OPEN API로 현행 근로기준법 조문을 수집한다."""
import json
import re
from pathlib import Path
from typing import Any

import requests

# 스크립트를 직접 실행해도 프로젝트 루트의 app 패키지를 찾도록 경로를 등록한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from app.config import settings

API_BASE_URL = "https://www.law.go.kr/DRF"
LIST_URL = f"{API_BASE_URL}/lawSearch.do"
DETAIL_URL = f"{API_BASE_URL}/lawService.do"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "labor_standards_act.jsonl"
SOURCE_URL = "https://www.law.go.kr/법령/근로기준법"


def request_json(url: str, params: dict[str, str]) -> dict[str, Any]:
    response = requests.get(
        url,
        params=params,
        timeout=40,
        headers={"User-Agent": "WorkLaw-RAG/1.0"},
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError(
            f"국가법령정보센터가 JSON이 아닌 응답을 반환했습니다: {response.text[:500]}"
        ) from error

    if not isinstance(payload, dict):
        raise RuntimeError(f"예상하지 못한 API 응답 형식입니다: {type(payload).__name__}")

    return payload


def find_value(data: Any, candidates: tuple[str, ...]) -> Any:
    """중첩된 API 응답에서 후보 키의 첫 번째 값을 찾는다."""
    if isinstance(data, dict):
        for key in candidates:
            if key in data and data[key] not in (None, ""):
                return data[key]
        for value in data.values():
            found = find_value(value, candidates)
            if found not in (None, ""):
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_value(item, candidates)
            if found not in (None, ""):
                return found
    return None


def find_article_nodes(data: Any) -> list[dict[str, Any]]:
    """응답의 조문 단위를 재귀적으로 찾아 반환한다."""
    found: list[dict[str, Any]] = []

    def walk(node: Any):
        if isinstance(node, dict):
            article_number = node.get("조문번호")
            article_text = node.get("조문내용")
            if article_number not in (None, "") and article_text not in (None, ""):
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return found


def normalize_text(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(filter(None, (normalize_text(item) for item in value)))
    if isinstance(value, dict):
        return "\n".join(filter(None, (normalize_text(item) for item in value.values())))
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def extract_articles(payload: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = find_article_nodes(payload)
    records: dict[str, dict[str, str]] = {}

    for node in nodes:
        raw_number = str(node.get("조문번호", "")).strip()
        if not raw_number.isdigit():
            continue

        article_number = int(raw_number)
        raw_sub_number = node.get("조문가지번호", "0")
        try:
            sub_number = int(raw_sub_number or 0)
        except (TypeError, ValueError):
            sub_number = 0

        article_id = f"제{article_number}조"
        if sub_number:
            article_id += f"의{sub_number}"

        title_text = normalize_text(node.get("조문제목")) or "제목 없음"
        article_text = normalize_text(node.get("조문내용"))
        if len(article_text) < 10:
            continue

        records[article_id] = {
            "article_id": article_id,
            "title": f"{article_id}({title_text})",
            "text": f"{article_id}({title_text})\n{article_text}",
            "source": SOURCE_URL,
            "law_name": "근로기준법",
            "effective_date": normalize_text(
                find_value(payload, ("시행일자", "시행일"))
            ),
        }

    return sorted(
        records.values(),
        key=lambda item: tuple(
            int(part) for part in re.findall(r"\d+", item["article_id"])
        ),
    )


def main():
    if not settings.law_api_oc:
        raise RuntimeError(
            ".env에 LAW_API_OC를 설정하세요. 국가법령정보센터에서 발급받은 OC 인증키가 필요합니다."
        )

    common_params = {
        "OC": settings.law_api_oc,
        "type": "JSON",
        "query": "근로기준법",
        "display": "100",
        "page": "1",
    }

    listing = request_json(
        LIST_URL,
        {"OC": settings.law_api_oc, "target": "eflaw", "type": "JSON",
         "query": "근로기준법", "display": "100", "page": "1"},
    )
    law_id = find_value(listing, ("법령ID", "법령 id", "법령ID값"))
    if law_id is None:
        message = find_value(listing, ("resultMsg", "메시지", "오류메시지"))
        raise RuntimeError(
            "현행법령 목록에서 근로기준법 ID를 찾지 못했습니다. "
            f"API 응답 메시지: {message or str(listing)[:700]}"
        )

    detail = request_json(
        DETAIL_URL,
        {
            "OC": settings.law_api_oc,
            "target": "eflaw",
            "type": "JSON",
            "ID": str(law_id),
        },
    )
    articles = extract_articles(detail)
    if len(articles) < 20:
        message = find_value(detail, ("resultMsg", "메시지", "오류메시지"))
        raise RuntimeError(
            f"조문 추출 결과가 {len(articles)}개입니다. "
            f"API 응답 메시지: {message or str(detail)[:700]}"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = OUTPUT_PATH.with_suffix(".jsonl.tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        for article in articles:
            file.write(json.dumps(article, ensure_ascii=False) + "\n")
    temp_path.replace(OUTPUT_PATH)

    effective_date = articles[0].get("effective_date") or "API 응답 미제공"
    print(f"수집 완료: {len(articles)}개 조문")
    print(f"법령 ID: {law_id}")
    print(f"시행일자: {effective_date}")
    print(f"저장: {OUTPUT_PATH}")
    print("샘플:", ", ".join(item["article_id"] for item in articles[:5]))
    print(f"출처: {SOURCE_URL}")


if __name__ == "__main__":
    main()
