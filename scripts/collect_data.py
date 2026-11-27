"""국가법령정보센터 근로기준법 페이지에서 조문을 수집한다."""
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# 2026-10-08 시행 근로기준법 본문 페이지
SOURCE_URL = (
    "https://www.law.go.kr/LSW/lsInfoP.do"
    "?ancYnChk=0&chrClsCd=010202&efYd=20261008"
    "&lsiSeq=285279&urlMode=lsInfoP"
)
OUTPUT_PATH = Path("data/processed/labor_standards_act.jsonl")
ARTICLE_PATTERN = re.compile(
    r"(제\s*\d+\s*조(?:\s*의\s*\d+)?\s*\([^)]{1,120}\))"
)
ARTICLE_NUMBER_PATTERN = re.compile(r"제\s*\d+\s*조(?:\s*의\s*\d+)?")


def extract_articles(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    root = (
        soup.select_one("#conScroll")
        or soup.select_one(".lawcon")
        or soup.select_one("#content")
        or soup.body
        or soup
    )
    for node in root.select("script, style, noscript"):
        node.decompose()

    # 조문 제목이 태그로 분리되거나 줄바꿈된 경우도 찾을 수 있도록
    # 공백을 유지한 전체 텍스트에서 조문 경계를 추출한다.
    text = re.sub(r"[ \t\u00a0]+", " ", root.get_text("\n", strip=True))
    matches = list(ARTICLE_PATTERN.finditer(text))

    # 본문 영역 선택자가 변경된 경우 문서 전체에서 한 번 더 탐색한다.
    if not matches:
        full_text = re.sub(r"[ \t\u00a0]+", " ", soup.get_text("\n", strip=True))
        matches = list(ARTICLE_PATTERN.finditer(full_text))
        text = full_text

    if not matches:
        page_title = soup.title.get_text(" ", strip=True) if soup.title else "제목 없음"
        preview = re.sub(r"\s+", " ", text)[:240]
        raise RuntimeError(
            "조문 제목을 찾지 못했습니다. "
            f"응답 페이지: {page_title}. 본문 미리보기: {preview}"
        )

    records = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start():end].strip()
        number = ARTICLE_NUMBER_PATTERN.match(match.group(1))
        if not number or len(block) < 25:
            continue

        article_id = re.sub(r"\s+", "", number.group(0))
        title = re.sub(r"\s+", "", match.group(1))
        records[article_id] = {
            "article_id": article_id,
            "title": title,
            "text": block,
            "source": SOURCE_URL,
        }

    return list(records.values())


def main():
    response = requests.get(
        SOURCE_URL,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
        },
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding

    articles = extract_articles(response.text)
    if len(articles) < 20:
        raise RuntimeError(
            f"조문 {len(articles)}개만 추출됐습니다. "
            "수집 결과를 저장하지 않았습니다."
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT_PATH.with_suffix(".jsonl.tmp")
    with temp.open("w", encoding="utf-8") as file:
        for article in articles:
            file.write(json.dumps(article, ensure_ascii=False) + "\n")
    temp.replace(OUTPUT_PATH)

    print(f"수집 완료: {len(articles)}개 조문")
    print(f"저장: {OUTPUT_PATH}")
    print("샘플:", ", ".join(item["article_id"] for item in articles[:5]))
    print("출처:", SOURCE_URL)


if __name__ == "__main__":
    main()
