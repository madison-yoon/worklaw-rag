"""국가법령정보센터의 공개 현행법령 본문 페이지에서 근로기준법을 수집한다.

공동활용 OPEN API 인증키가 필요 없는 공개 법령 페이지를 사용한다.
"""
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# 국가법령정보센터의 근로기준법 고정 법령 식별자(lsId=001872)를 사용한다.
SOURCE_URL = "https://www.law.go.kr/lsInfoP.do?lsId=001872"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "labor_standards_act.jsonl"

# 조문 제목은 '제17조(근로조건의 명시)' 또는 전각 괄호 형태로 표시된다.
ARTICLE_HEADING = re.compile(
    r"(?<![가-힣A-Za-z0-9])(?P<article_id>제\d+조(?:의\d+)?)[ \t]*[（(](?P<title>[^）)\n]{1,120})[）)]"
)
EFFECTIVE_DATE = re.compile(r"시행\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})")


def fetch_law_page() -> str:
    response = requests.get(
        SOURCE_URL,
        timeout=40,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"

    if "근로기준법" not in response.text:
        raise RuntimeError(
            "국가법령정보센터 공개 페이지에서 근로기준법을 확인하지 못했습니다. "
            f"HTTP {response.status_code}, 응답 길이 {len(response.content)} bytes"
        )
    return response.text


def extract_articles(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")

    # 화면 조작용 스크립트·스타일은 제외하고 본문 텍스트를 추출한다.
    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    page_text = soup.get_text("\n", strip=True).replace("\xa0", " ")
    page_text = re.sub(r"[ \t]+", " ", page_text)

    date_match = EFFECTIVE_DATE.search(page_text)
    effective_date = ""
    if date_match:
        year, month, day = date_match.groups()
        effective_date = f"{year}-{int(month):02d}-{int(day):02d}"

    # 제목이 있는 조문 헤더를 기준으로 분리한다. 줄 시작 여부에 의존하지 않는다.
    matches = list(ARTICLE_HEADING.finditer(page_text))
    if not matches:
        raise RuntimeError(
            "공개 페이지에서 조문 제목 패턴을 찾지 못했습니다. "
            "페이지가 차단되었거나 국가법령정보센터의 HTML 구조가 변경되었을 수 있습니다. "
            f"응답 길이: {len(html)} bytes"
        )

    records: dict[str, dict[str, str]] = {}
    for index, match in enumerate(matches):
        article_id = match.group("article_id")
        article_title = re.sub(r"\s+", " ", match.group("title")).strip()
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(page_text)
        content = re.sub(r"\s+", " ", page_text[content_start:content_end]).strip()
        content = re.sub(r"^[\s:：]+", "", content)

        # 본문 시작 전 목차/페이지 안내에서 잡힌 가짜 조문 헤더를 걸러낸다.
        if len(content) < 10 or "본문" not in page_text[:match.start()] and article_id == "제1조":
            continue

        title = f"{article_id}({article_title})"
        records[article_id] = {
            "article_id": article_id,
            "title": title,
            "text": f"{title}\n{content}",
            "source": SOURCE_URL,
            "law_name": "근로기준법",
            "effective_date": effective_date,
        }

    articles = sorted(
        records.values(),
        key=lambda item: tuple(int(value) for value in re.findall(r"\d+", item["article_id"])),
    )
    return articles


def main() -> None:
    html = fetch_law_page()
    articles = extract_articles(html)

    if len(articles) < 80:
        raise RuntimeError(
            f"조문 추출 결과가 {len(articles)}개입니다. "
            "현행 근로기준법 전체 본문을 가져오지 못한 것으로 판단해 저장을 중단했습니다. "
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
