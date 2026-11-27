# Python Docs RAG

Python 3 공식 문서를 실제 수집해 임베딩·벡터 검색하고 검색 근거로 답변하는 한국어 RAG POC입니다.

## 사용자와 입출력
- 도메인: Python 공식 문서
- 대상: Python 학습자 및 개발자
- 입력: 자연어 질문
- 출력: LLM 답변, 검색된 문서 제목·URL·유사도

## 실행 (Windows CMD)
```cmd
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
.env에 OPENAI_API_KEY를 입력하고 `uvicorn app.main:app --reload` 실행. http://127.0.0.1:8000 에서 공식 문서 수집 후 질문합니다. 최초 실행 시 임베딩 모델 다운로드가 필요합니다.

## 파이프라인
공식 sitemap → HTML 수집 → 본문 정제 → 청킹 → Sentence Transformers 임베딩 → ChromaDB 저장 → 질문 임베딩 → Top-K 검색 → LLM 생성 → 출처 표시.

## 평가
`python -m scripts.evaluate`로 Recall@K와 MRR을 측정합니다. 평가 질문은 검색 품질 측정용이며 답변을 고정하지 않습니다. Chunk 900/Overlap 150 기준과 700/120 개선안을 동일 평가셋으로 비교합니다. 실행하지 않은 점수는 문서에 기입하지 않습니다.

## 문서
- docs/TECHNICAL.md: 아키텍처, 데이터, 설계, 평가, 한계 및 데모

## 한계
Sitemap과 문서 HTML 구조 변경에 영향을 받습니다. 키워드 기반 평가셋은 의미적 정답성을 완전히 측정하지 못합니다. LLM 답변은 검색 문맥에 의존하며 반드시 원문을 확인해야 합니다.
