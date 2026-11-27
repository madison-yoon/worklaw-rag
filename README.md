# MOMO Movie Search & Recommendation RAG

기존 MOMO 영화 서비스의 API와 RAG 시연 리뷰를 활용해 자연어 영화 검색·추천을 제공하는 독립형 웹 POC입니다.

## 프로젝트 정의
- 도메인: 영화 정보 검색, 감상 리뷰 검색, 취향 기반 영화 추천
- 대상 사용자: 영화 선택 전 작품 정보와 감상을 비교하려는 사용자
- 입력: “음악이 좋고 여운이 남는 SF 영화를 추천해줘.”
- 출력: 추천·검색 답변, 영화 정보, 리뷰 ID와 검색 근거
- 기존 서비스 재사용: MOMO Spring API의 영화 상세·추천 API
- AI: OpenAI Embeddings + GPT-4.1-mini
- 벡터 DB: MongoDB Atlas Vector Search
- 웹: FastAPI + HTML/CSS/JavaScript

## 1. MOMO에서 재사용하는 기능

| 기존 MOMO API | 사용 목적 |
|---|---|
| GET /api/movies/{movieCode} | 영화 제목, 장르, 감독, 개봉일, 줄거리, 배우 수집 |
| GET /api/movies/recommendations | 박스오피스 이력 기반 추천 후보 |
| GET /api/movies/recommendations?genre=코미디 | 장르별 추천 후보 |
| MOMO-RAG/scripts/seed.py | 리뷰 시연 데이터 10건 |

영화 데이터와 추천 후보를 새로 만들지 않고 기존 MOMO API를 호출합니다. 리뷰는 기존 RAG Seed의 시연용 가상 감상 10건을 사용합니다. 실제 회원 리뷰 본문이나 작성자 정보는 복제하지 않습니다.

## 2. 실행 환경

MOMO Spring Boot 백엔드를 먼저 실행합니다. 기본 주소는 http://localhost:8111 입니다.

    pip install -r requirements.txt

프로젝트 루트의 추적되지 않는 .env를 설정합니다.

    OPENAI_API_KEY=실제_OpenAI_API_키
    MOMO_API_BASE_URL=http://localhost:8111
    MONGODB_URI=본인_MongoDB_Atlas_URI
    MONGODB_DATABASE=worklaw_db
    MONGODB_COLLECTION=law_chunks
    MONGODB_VECTOR_INDEX=vector_index
    MONGODB_VECTOR_PATH=embedding

실제 API 키와 MongoDB URI는 GitHub에 커밋하지 않습니다.

## 3. Atlas Vector Search 인덱스

MongoDB Atlas에서 worklaw_db.law_chunks 컬렉션을 대상으로 vector_index를 생성합니다. 인덱스 정의는 atlas-vector-index.json을 사용합니다.

## 4. 데이터 수집 및 색인

    python scripts/collect_data.py
    python scripts/build_index.py

수집 과정:
1. MOMO RAG Seed의 영화 리뷰 10건을 읽는다.
2. 영화 코드별로 MOMO GET /api/movies/{movieCode}를 호출한다.
3. 영화 상세 응답의 제목·장르·감독·개봉일·줄거리·배우를 리뷰 문서에 결합한다.
4. 필수 필드와 영화 코드·제목 일치 여부를 확인하고 JSONL로 저장한다.
5. 리뷰 본문을 500자 단위, 80자 overlap으로 청킹한다.
6. 영화 메타데이터와 리뷰 제목을 포함해 text-embedding-3-small으로 임베딩한다.
7. MongoDB Atlas에 저장한다.

## 5. 웹서비스 실행

    uvicorn app.main:app --reload

브라우저: http://127.0.0.1:8000

- GET /api/health: MongoDB·색인·OpenAI 설정 상태
- GET /api/recommendations?genre=코미디: MOMO 기존 추천 API 프록시
- POST /api/ask: 자연어 질문 → 벡터 검색 → 근거 기반 답변
- GET /docs: API 문서

추천 후보는 MOMO의 박스오피스 추천 로직을 그대로 사용합니다. AI 검색은 질문과 가까운 영화 리뷰·상세정보를 찾아 추천 이유를 자연어로 설명합니다.

## 6. 평가 및 개선

    pytest -q
    python scripts/evaluate.py

8개 평가 질문에 기대 리뷰 ID를 라벨링하고 Recall@K, MRR@K를 계산합니다. 개선 실험은 동일 평가셋에서 청킹 크기와 overlap을 변경하고 재색인한 뒤 결과를 비교합니다. 실행하지 않은 수치를 미리 기록하지 않습니다.

## 한계
- 리뷰는 MOMO RAG Seed의 시연용 가상 감상 10건이며 실제 회원 리뷰를 대표하지 않습니다.
- 추천 후보의 품질은 MOMO의 박스오피스 이력·장르 필터 정책에 영향을 받습니다.
- 현재 평가셋은 8개 질문으로 작아 일반화에 한계가 있습니다.
- 리뷰 근거는 주관적 감상이며 영화에 관한 객관적 사실의 증거가 아닙니다.
- MOMO 백엔드가 실행 중이어야 영화 상세 수집과 추천 API 프록시를 사용할 수 있습니다.
- OpenAI 및 MongoDB Atlas 호출에는 네트워크와 사용료가 필요합니다.
- 독립 POC이므로 MOMO 로그인·회원별 권한·MySQL 원본 DB를 직접 수정하지 않습니다.

## 원본 프로젝트
- https://github.com/madison-yoon/MOMO
- https://github.com/madison-yoon/MOMO/blob/main/docs/RAG.md
- https://github.com/madison-yoon/MOMO/blob/main/MOMO-RAG/scripts/seed.py
- https://github.com/madison-yoon/MOMO/blob/main/momo-backend/src/main/java/com/momo/backend/controller/MovieController.java
