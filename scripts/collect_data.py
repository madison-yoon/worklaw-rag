"""국가법령정보센터 OPEN API로 현행 근로기준법 조문을 수집한다."""
import json
import re
import sys
from pathlib import Path
from typing import Any

import requests

# 스크립트를 직접 실행해도 프로젝트 루트의 app 패키지를 찾도록 경로를 등록한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings

API_BASE_URL = "https://www.law.go.kr/DRF"
LIST_URL = f"{API_BASE_URL}/lawSearch.do"
DETAIL_URL = f"{API_BASE_URL}/lawService.do"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "labor_standards_act.jsonl"
SOURCE_URL = "https://www.law.go.kr/법령/근로기준법"

LAW_NAME_KEYS = ("법령명_한글", "법령명한글", "법령명")
LAW_ID_KEYS = ("법령ID", "법령아이디", "법령 ID")


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
        # 일부 오류 페이지는 응답 헤더의 문자셋이 잘못 지정되어 있으므로 실제 인코딩을 사용한다.
        from bs4 import BeautifulSoup

        # law.go.kr 오류 페이지는 EUC-KR/CP949로 내려오는 경우가 있어 후보 인코딩을 비교한다.
        candidates = []
        for encoding in ("utf-8", "euc-kr", "cp949"):
            try:
                decoded = response.content.decode(encoding)
            except UnicodeDecodeError:
                continue
            plain = BeautifulSoup(decoded, "html.parser").get_text(" ", strip=True)
            hangul_count = sum("\uac00" <= char <= "\ud7a3" for char in plain)
            candidates.append((hangul_count, plain))
        message = max(candidates, key=lambda item: item[0])[1] if candidates else response.content.decode("utf-8", errors="replace")
        # OC 인증키가 포함된 요청 URL은 로그에 출력하지 않는다.
        if "미신청된 목록/본문" in message or "공동활용" in message and "신청" in message:
            raise RuntimeError(
                "국가법령정보센터가 본문 API 접근을 거부했습니다. "
                "요청 형식은 JSON이 아니라 서버의 권한 안내 HTML입니다. "
                "코드에서 우회할 수 없는 공동활용 승인/서비스 권한 문제입니다. "
                f"서버 안내: {message[:900]}"
            ) from error
        raise RuntimeError(
            "국가법령정보센터가 JSON 대신 오류 페이지를 반환했습니다. "
            f"HTTP {response.status_code}, 응답 내용: {message[:900]}"
        ) from error

    if not isinstance(payload, dict):
        raise RuntimeError(f"예상하지 못한 API 응답 형식입니다: {type(payload).__name__}")
    return payload


def normalize_text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(filter(None, (normalize_text(item) for item in value)))
    if isinstance(value, dict):
        return " ".join(filter(None, (normalize_text(item) for item in value.values())))
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def find_law_record(data: Any, law_name: str) -> dict[str, Any] | None:
    """목록 응답에서 이름과 법령 ID가 같은 레코드에 있는 법령만 선택한다."""
    expected_name = re.sub(r"\s+", "", law_name)

    def walk(node: Any) -> dict[str, Any] | None:
        if isinstance(node, dict):
            name = next(
                (node[key] for key in LAW_NAME_KEYS if node.get(key) not in (None, "")),
                None,
            )
            law_id = next(
                (node[key] for key in LAW_ID_KEYS if node.get(key) not in (None, "")),
                None,
            )
            if name is not None and law_id is not None:
                normalized_name = re.sub(r"\s+", "", normalize_text(name))
                if normalized_name == expected_name:
                    return node

            for value in node.values():
                found = walk(value)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = walk(item)
                if found is not None:
                    return found
        return None

    return walk(data)


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


def extract_articles(payload: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = find_article_nodes(payload)
    effective_date = normalize_text(find_value(payload, ("시행일자", "시행일")))
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
            "effective_date": effective_date,
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

    listing = request_json(
        LIST_URL,
        {
            "OC": settings.law_api_oc,
            "target": "eflaw",
            "type": "JSON",
            "query": "근로기준법",
            "display": "100",
            "page": "1",
        },
    )

    # 목록 전체에서 첫 번째 ID를 가져오지 않고, 근로기준법 이름과 ID가 함께 있는 항목을 찾는다.
    law_record = find_law_record(listing, "근로기준법")
    if law_record is None:
        raise RuntimeError(
            "현행법령 목록에서 법령명 '근로기준법'과 법령ID가 함께 있는 항목을 찾지 못했습니다. "
            f"목록 응답 구조: {str(listing)[:900]}"
        )

    law_id = find_value(law_record, LAW_ID_KEYS)
    if law_id is None:
        raise RuntimeError("근로기준법 목록 항목에 법령ID가 없습니다.")

    # 공식 본문 API: ID를 사용하면 현행 본문을 조회하며 efYd는 전달하지 않는다.
    detail = request_json(
        DETAIL_URL,
        {
            "OC": settings.law_api_oc,
            "target": "eflaw",
            "type": "JSON",
            "ID": str(law_id),
        },
    )

    returned_law_name = normalize_text(
        find_value(detail, ("법령명_한글", "법령명한글", "법령명"))
    )
    if returned_law_name and re.sub(r"\s+", "", returned_law_name) != "근로기준법":
        raise RuntimeError(
            f"요청한 법령과 다른 본문이 반환되었습니다: {returned_law_name}"
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
