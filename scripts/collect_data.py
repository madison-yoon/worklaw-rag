"""국가법령정보센터 근로기준법 페이지에서 조문을 수집한다."""
import json
import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://law.go.kr/LSW/lsInfoP.do?lsiSeq=285279"
OUTPUT_PATH = Path("data/processed/labor_standards_act.jsonl")
ARTICLE_PATTERN = re.compile(r"(제\s*\d+조(?:의\s*\d+)?\s*\([^\n)]{1,120}\))")

def extract_articles(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("#conScroll") or soup.select_one(".lawcon") or soup.select_one("#content") or soup.body
    if root is None:
        raise RuntimeError("법령 본문 영역을 찾지 못했습니다.")
    for node in root.select("script, style, noscript"):
        node.decompose()
    lines = [re.sub(r"\s+", " ", x).strip() for x in root.get_text("\n", strip=True).splitlines()]
    text = "\n".join(x for x in lines if x)
    matches = list(ARTICLE_PATTERN.finditer(text))
    if not matches:
        raise RuntimeError("조문 제목 추출 실패: 공식 페이지의 HTML 구조를 확인하세요.")
    records = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[match.start():end].strip()
        number = re.match(r"제\s*\d+조(?:의\s*\d+)?", match.group(1))
        if not number or len(block) < 25:
            continue
        article_id = re.sub(r"\s+", "", number.group(0))
        records[article_id] = {
            "article_id": article_id, "title": match.group(1).strip(),
            "text": block, "source": SOURCE_URL,
        }
    return list(records.values())

def main():
    response = requests.get(SOURCE_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0 WorkLawRAG/1.0"})
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    articles = extract_articles(response.text)
    if len(articles) < 20:
        raise RuntimeError(f"조문 {len(articles)}개만 추출됐습니다. 본문 추출 결과를 확인하세요.")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT_PATH.with_suffix(".jsonl.tmp")
    with temp.open("w", encoding="utf-8") as file:
        for article in articles:
            file.write(json.dumps(article, ensure_ascii=False) + "\n")
    temp.replace(OUTPUT_PATH)
    print(f"수집 완료: {len(articles)}개 조문")
    print(f"저장: {OUTPUT_PATH}")
    print("샘플:", ", ".join(x["article_id"] for x in articles[:5]))
    print("출처:", SOURCE_URL)

if __name__ == "__main__":
    main()
