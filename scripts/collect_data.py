"""국가법령정보센터 공개 법령 본문 페이지에서 근로기준법을 수집한다.

공동활용 OPEN API 인증키를 사용하지 않는다.
"""
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = (
    "https://www.law.go.kr/lsLinkProc.do"
    "?ancYnChk=0&chrClsCd=010202&lsNm=%EA%B7%BC%EB%A1%9C%EA%B8%B0%EC%A4%80%EB%B2%95&mode=20"
)
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "labor_standards_act.jsonl"
ARTICLE_HEADING = re.compile(
    r"(?m)^\s*(제\d+조(?:의\d+)?)[ \t]*[（(]([^）)\n]{1,120})[）)]"
)
EFFECTIVE_DATE = re.compile(r"시행\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})")


def fetch_law_page() -> str:
    """공개 법령 본문 페이지를 내려받는다."""
    response = requests.get(
        SOURCE_URL,
        timeout=40,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; WorkLaw-RAG/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"

    if "근로기준법" not in response.text:
        raise RuntimeError(
            "국가법령정보센터 응답에서 근로기준법 본문을 확인하지 못했습니다. "
            f"응답 주소: {response.url}"
        )
    return response.text


def extract_law_text(html: str) -> tuple[str, str]:
    """페이지 HTML에서 시행일자와 본문 텍스트를 추출한다."""
    soup = BeautifulSoup(html, "html.parser")

    for element in soup(["script", "style", "noscript", "header", "footer"]):
        element.decompose()

    page_text = soup.get_text("\n", strip=True)
    page_text = page_text.replace("\xa0", " ")
    page_text = re.sub(r"[ \t]+", " ", page_text)

    date_match = EFFECTIVE_DATE.search(page_text)
    effective_date = ""
    if date_match:
        year, month, day = date_match.groups()
        effective_date = f"{year}-{int(month):02d}-{int(day):02d}"

    # 본문 시작점을 '제1조(목적)'으로 고정해 부칙의 제1조(시행일)와 섞이지 않게 한다.
    start_match = re.search(r"(?m)^\s*제1조\s*[（(]목적[）)]", page_text)
    if not start_match:
        raise RuntimeError(
            "공개 페이지에서 근로기준법 본문 시작점인 '제1조(목적)'을 찾지 못했습니다. "
            "국가법령정보센터 페이지 구조가 변경되었을 수 있습니다."
        )

    body = page_text[start_match.start():]
    appendix_match = re.search(r"(?m)^\s*부칙(?:\s|$)", body)
    if appendix_match:
        body = body[:appendix_match.start()]

    return body, effective_date


def parse_articles(html: str) -> list[dict[str, str]]:
    """법령 본문을 조문별 레코드로 분리한다."""
    body, effective_date = extract_law_text(html)
    matches = list(ARTICLE_HEADING.finditer(body))
    records: list[dict[str, str]] = []

    for index, match in enumerate(matches):
        article_id = match.group(1)
        article_title = re.sub(r"\s+", " ", match.group(2)).strip()
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = re.sub(r"\s+", " ", body[content_start:content_end]).strip()
        content = re.sub(r"^[\s:：]+", "", content)

        if len(content) < 10:
            continue

        title = f"{article_id}({article_title})"
        records.append(
            {
                "article_id": article_id,
                "title": title,
                "text": f"{title}\n{content}",
                "source": SOURCE_URL,
                "law_name": "근로기준법",
                "effective_date": effective_date,
            }
        )

    # 동일 조문이 페이지 내비게이션과 본문에 중복 노출될 경우 본문 레코드 하나만 유지한다.
    unique_records = {item["article_id"]: item for item in records}
    return sorted(
        unique_records.values(),
        key=lambda item: tuple(int(value) for value in re.findall(r"\d+", item["article_id"])),
    )


def main() -> None:
    html = fetch_law_page()
    articles = parse_articles(html)

    if len(articles) < 20:
        raise RuntimeError(
            f"조문 추출 결과가 {len(articles)}개입니다. "
            "페이지 구조가 변경되었거나 본문이 일부만 내려왔습니다. "
            "기존 JSONL 파일은 덮어쓰지 않았습니다."
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = OUTPUT_PATH.with_suffix(".jsonl.tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        for article in articles:
            file.write(json.dumps(article, ensure_ascii=False) + "\n")
    temp_path.replace(OUTPUT_PATH)

    print(f"수집 완료: {len(articles)}개 조문")
    print(f"시행일자: {articles[0]['effective_date'] or '페이지에서 확인되지 않음'}")
    print(f"저장: {OUTPUT_PATH}")
    print("샘플:", ", ".join(item["article_id"] for item in articles[:5]))
    print(f"출처: {SOURCE_URL}")


if __name__ == "__main__":
    main()
