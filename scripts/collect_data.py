"""국가법령정보센터의 근로기준법 조문 목록을 수집한다."""
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# mode=20은 법령 본문 조문 목록을 제공하는 국가법령정보센터 화면이다.
SOURCE_URL = (
    "https://www.law.go.kr/lsLinkProc.do"
    "?ancYnChk=0&chrClsCd=010202&lsNm=%EA%B7%BC%EB%A1%9C%EA%B8%B0%EC%A4%80%EB%B2%95&mode=20"
)
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "labor_standards_act.jsonl"

# 제목 괄호는 일반 괄호와 전각 괄호 모두 허용한다.
ARTICLE_PATTERN = re.compile(
    r"제\s*(\d+)\s*조(?:\s*의\s*(\d+))?\s*[（(]\s*([^）)]{1,120})[）)]"
)


def extract_articles(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    # 법령 본문은 #content 같은 공통 레이아웃 영역 바깥에 있을 수 있어
    # 특정 레이아웃 선택자에 의존하지 않고 문서 전체 텍스트를 사용한다.
    for node in soup.select("script, style, noscript"):
        node.decompose()

    text = soup.get_text("\n", strip=True)
    text = text.replace("\u00a0", " ")
    matches = list(ARTICLE_PATTERN.finditer(text))

    if not matches:
        title = soup.title.get_text(" ", strip=True) if soup.title else "제목 없음"
        preview = re.sub(r"\s+", " ", text)[:500]
        raise RuntimeError(
            "조문 제목을 찾지 못했습니다. "
            f"응답 페이지: {title}. 본문 미리보기: {preview}"
        )

    records = {}
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].strip()

        article_number = match.group(1)
        sub_number = match.group(2)
        article_id = f"제{article_number}조"
        if sub_number:
            article_id += f"의{sub_number}"

        title = f"{article_id}({match.group(3).strip()})"
        if len(block) < 25:
            continue

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
        timeout=40,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            "Referer": "https://www.law.go.kr/",
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
