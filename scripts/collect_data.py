"""Download and normalize the official Labor Standards Act page into JSONL."""
import json
import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup

URL = "https://law.go.kr/LSW/lsInfoP.do?lsiSeq=285279"
OUT = Path("data/processed/labor_standards_act.jsonl")


def main():
    response = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0 WorkLawRAG/1.0"})
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")
    root = soup.select_one("#conScroll") or soup.select_one(".lawcon") or soup.body
    if root is None:
        raise RuntimeError("법령 본문 영역을 찾지 못했습니다. 국가법령정보센터 페이지 구조를 확인하세요.")
    text = root.get_text("\n", strip=True)
    text = re.sub(r"\n{2,}", "\n", text)
    # 조문 제목을 기준으로 분리하고, 조문 번호·제목·본문을 함께 보존한다.
    pattern = re.compile(r"(제\d+조(?:의\d+)?\s*\([^\n]+\))")
    matches = list(pattern.finditer(text))
    if not matches:
        raise RuntimeError("조문을 추출하지 못했습니다. 원문 구조가 변경되었을 수 있습니다.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with OUT.open("w", encoding="utf-8") as file:
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            block = text[match.start():end].strip()
            article_id = re.match(r"제\d+조(?:의\d+)?", match.group(1)).group(0)
            title = match.group(1)
            if len(block) < 25:
                continue
            record = {"article_id": article_id, "title": title, "text": block, "source": URL}
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    if count == 0:
        raise RuntimeError("저장된 조문이 없습니다.")
    print(f"수집 완료: {count}개 조문 -> {OUT}")
    print(f"출처: {URL}")

if __name__ == "__main__":
    main()
