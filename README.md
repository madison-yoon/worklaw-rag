# MOMO Movie Review RAG

MOMO 프로젝트의 영화 감상 리뷰를 자연어로 검색하고, 검색된 리뷰를 근거로 답변하는 RAG 웹서비스 POC입니다.

## 프로젝트 범위
- **도메인:** 영화 감상 리뷰 검색 및 비교
- **대상 사용자:** MOMO에서 영화 리뷰를 읽고 감상 관점을 비교하려는 사용자
- **입력:** “라라랜드의 음악과 스토리에 대한 서로 다른 평가는?”과 같은 자연어 질문
- **출력:** 리뷰 근거를 바탕으로 한 한국어 답변, 영화명·리뷰 제목·리뷰 ID·원문 출처
- **원천 데이터:** MOMO 저장소의 `MOMO-RAG/scripts/seed.py`에 정의된 영화 5편의 시연용 가상 리뷰 10건
- **기술:** FastAPI, OpenAI Embeddings/Chat, MongoDB Atlas Vector Search, HTML/CSS/JavaScript

이 POC는 MOMO에 이미 구현된 RAG의 데이터 계약과 설계(리뷰 단위 문서, 500자/80자 청킹, text-embedding-3-small, Atlas Vector Search, GPT-4.1-mini)를 참고해 독립 실행형 데모로 구성했습니다. MOMO의 실제 회원 리뷰 DB를 복제하거나 개인정보를 수집하지 않습니다.

## 1. 실행 환경

Conda 환경 `worklaw-rag` 또는 Python 3.12 이상 환경에서:

```bash
pip install -r requirements.txt
```

프로젝트 루트의 추적되지 않는 `.env`에 설정합니다.

```dotenv
OPENAI_API_KEY=실제_OpenAI_API_키
MONGODB_URI=실제_MongoDB_Atlas_URI
MONGODB_DATABASE=momo_rag
MONGODB_COLLECTION=review_chunks
MONGODB_VECTOR_INDEX=review_vector_index
MONGODB_VECTOR_PATH=embedding
```

실제 API 키와 MongoDB URI는 Git에 커밋하지 않습니다.

## 2. Atlas Vector Search 인덱스

Database `momo_rag`, Collection `review_chunks`를 사용합니다. Atlas에서 Vector Search Index를 `review_vector_index` 이름으로 생성하고 다음 정의를 적용합니다.

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1536,
      "similarity": "cosine"
    }
  ]
}
```

## 3. 데이터 구축 및 색인

```bash
python scripts/collect_data.py
python scripts/build_index.py
```

- `data/raw/momo_reviews.jsonl`: MOMO RAG Seed에서 가져온 가상 영화 리뷰 10건
- `scripts/collect_data.py`: 필수 필드 검증, 공백 정리, 중복 제거 및 출처 메타데이터 정규화
- `data/processed/momo_reviews.jsonl`: 검색 색인의 입력 문서
- `app/rag/chunker.py`: 리뷰 본문을 500자 단위, 80자 overlap으로 청킹
- `app/rag/embedder.py`: OpenAI `text-embedding-3-small` 임베딩
- `app/rag/vector_store.py`: MongoDB Atlas Vector Search 저장·검색

## 4. 웹서비스

```bash
uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다.

- `GET /api/health`: MongoDB 연결, 색인 청크 수, API 설정 상태
- `POST /api/ask`: 자연어 질문 → 관련 리뷰 검색 → 근거 기반 답변
- `GET /docs`: FastAPI API 문서

## 5. 평가와 개선

```bash
pytest -q
python scripts/evaluate.py
```

8개 평가 질문에 기대 리뷰 ID를 라벨링했습니다. Recall@K와 MRR@K로 검색 결과를 평가합니다. 개선 실험은 동일 평가셋에서 청킹 크기·overlap 또는 top-k 중 한 항목만 변경하고 재색인한 뒤 비교합니다. 실제 점수는 실행 결과를 기록하며 미리 만들어 넣지 않습니다.

## 데이터 범위와 한계
- 현재 데이터는 MOMO RAG 시연용으로 작성한 가상 감상 10건이며, 실제 사용자 리뷰 전체를 대표하지 않습니다.
- 5편의 영화와 제한된 관점만 포함하므로 다른 영화 질문에는 답할 근거가 없습니다.
- 리뷰는 주관적 감상이며 영화의 객관적 사실이나 평론가의 합의가 아닙니다.
- 평가 질문 8개는 소규모 내부 평가셋으로 일반화에 한계가 있습니다.
- OpenAI 임베딩·답변 생성에는 API 비용이 발생할 수 있습니다.
- MOMO 원본 서비스의 인증·권한·리뷰 CRUD와 이 독립형 POC는 연결되어 있지 않습니다.

## 원본 프로젝트
- [MOMO](https://github.com/madison-yoon/MOMO)
- [MOMO RAG 구현 문서](https://github.com/madison-yoon/MOMO/blob/main/docs/RAG.md)
- [MOMO RAG Seed 데이터](https://github.com/madison-yoon/MOMO/blob/main/MOMO-RAG/scripts/seed.py)
