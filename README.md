# WorkLaw RAG

근로기준법 조문을 검색하고 검색된 근거를 바탕으로 답변하는 한국어 RAG 웹서비스 POC입니다.

## 기술 구성

- API: FastAPI
- LLM: OpenAI `gpt-4.1-mini`
- Embedding: OpenAI `text-embedding-3-small` (1,536 dimensions)
- Vector DB: ChromaDB PersistentClient (로컬 디스크 저장)
- UI: HTML / CSS / Vanilla JavaScript

## 실행 순서

Python 3.11 이상을 권장합니다.

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env`의 `OPENAI_API_KEY`에 본인의 API 키를 입력합니다. 키를 GitHub에 커밋하지 마세요.

```bash
python scripts/collect_data.py
python scripts/build_index.py
uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 열고 질문합니다. 인덱스 구축은 OpenAI 임베딩 API를 호출하므로 API 사용료가 발생할 수 있습니다.

검색 평가:

```bash
python scripts/evaluate.py
```

## 데이터 출처 및 범위

- 국가법령정보센터, 근로기준법: https://law.go.kr/LSW/lsInfoP.do?lsiSeq=285279
- 수집 스크립트가 공식 페이지의 조문 본문을 추출해 `data/processed/labor_standards_act.jsonl`로 저장합니다.
- 법령은 개정될 수 있습니다. 실제 권리·의무 판단 전에는 반드시 국가법령정보센터의 최신 시행 법령과 관련 하위법령을 확인하세요.
- 본 서비스는 학습·정보 탐색용 POC이며 법률 자문이 아닙니다.

## 평가

`data/evaluation/questions.json`의 질문과 기대 조문을 기준으로 Recall@5 및 MRR@5를 계산합니다. 개선 실험에서는 chunk 크기·overlap·top-k를 한 번에 하나씩 바꾸고 동일 질문 세트로 재측정합니다. 실험 결과와 한계는 `docs/evaluation.md`에 기록합니다.

## API

- `GET /api/health`: 서비스 및 인덱스 상태
- `POST /api/ask`: `{ "question": "연차 유급휴가는 어떻게 보장되나요?" }`
