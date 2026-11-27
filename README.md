# Python Docs RAG

Python 3 공식 문서를 수집·정제하고 Sentence Transformers로 임베딩한 뒤 MongoDB Atlas Vector Search로 검색하는 한국어 RAG 웹서비스입니다. 검색된 문맥을 OpenAI API에 전달해 답변과 원문 출처를 반환합니다.

## 기술 구성

- Python 3.12 이상 / 기존 Conda 환경
- FastAPI + HTML/CSS/JavaScript
- Sentence Transformers: `paraphrase-multilingual-MiniLM-L12-v2` (384차원)
- MongoDB Atlas Vector Search
- OpenAI API

## 환경 설정

프로젝트에서 사용 중인 Conda 환경을 활성화한 상태에서 진행합니다. 새 venv는 만들지 않습니다.

```bash
python --version
pip install -r requirements.txt
```

`.env`가 아직 없을 때만 예제 파일을 복사합니다.

```bash
test -f .env || cp .env.example .env
```

기존 `.env`가 있다면 덮어쓰지 말고 아래 MongoDB 항목만 추가하거나 수정합니다. 실제 MongoDB 비밀번호와 OpenAI 키는 GitHub에 올리지 않습니다.

```dotenv
MONGODB_URI=mongodb+srv://<db_username>:<db_password>@worklaw-rag.vcgem0k.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=worklaw_rag
MONGODB_COLLECTION=documents
MONGODB_VECTOR_INDEX=vector_index
MONGODB_VECTOR_FIELD=embedding
OPENAI_API_KEY=<실제 OpenAI API 키>
```

Atlas 데이터베이스 사용자는 해당 데이터베이스에 읽기·쓰기 권한이 있어야 하며, Atlas Network Access에서 현재 접속 환경의 IP가 허용되어야 합니다. 계정 비밀번호에 특수문자가 있다면 URI 인코딩이 필요합니다.

## 실행

```bash
uvicorn app.main:app --reload
```

- 웹 화면: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- 상태 확인: http://127.0.0.1:8000/api/health

웹 화면에서 **공식 문서 수집 및 색인**을 실행합니다. 첫 실행은 임베딩 모델 다운로드와 Atlas Vector Search 인덱스 생성으로 시간이 걸릴 수 있습니다. 인덱스가 준비된 뒤 질문을 입력하면 검색 결과와 출처가 표시됩니다.

## MongoDB Vector Search 인덱스

애플리케이션은 수집 시 아래 정의로 Vector Search 인덱스 `vector_index`를 생성합니다. Atlas 계정 권한이나 클러스터 설정으로 자동 생성이 제한되면 Atlas UI에서 JSON 파일 `atlas-vector-index.json`을 사용해 다음 설정으로 생성합니다.

- Database: `worklaw_rag`
- Collection: `documents`
- Index name: `vector_index`
- Index type: Vector Search
- Vector field: `embedding`
- Dimensions: `384`
- Similarity: `cosine`

## 파이프라인

Python 공식 sitemap → HTML 수집 → 본문 정제 → 900자 청킹 / 150자 오버랩 → Sentence Transformers 임베딩 → MongoDB 문서 저장 → 질문 임베딩 → Atlas `$vectorSearch` Top-K 검색 → OpenAI 답변 생성 → 출처 URL·유사도 표시.

문서 ID는 원문 URL과 청크 순번의 SHA-256 값으로 생성하고 upsert해 동일 문서를 다시 수집해도 중복 삽입을 방지합니다.

## 평가

`python -m scripts.evaluate`로 Recall@K와 MRR을 계산합니다. 평가 질문과 기대 키워드는 `data/evaluation/questions.json`에 별도로 관리합니다. 검색 품질 개선 전후 점수는 실제 MongoDB 색인과 평가 실행 결과를 기록하며, 실행하지 않은 수치는 기입하지 않습니다.

## 주요 API

- `GET /api/health`: MongoDB 연결, 문서 수, Vector Search 인덱스 준비 상태
- `POST /api/ingest`: 공식 문서 수집·청킹·임베딩·MongoDB 저장
- `POST /api/ask`: Atlas 벡터 검색 및 OpenAI 답변 생성

## 한계

공식 문서의 sitemap 및 HTML 구조 변경에 영향을 받습니다. 키워드 기반 Recall@K·MRR은 의미적 정답성과 생성 답변의 사실성을 완전히 측정하지 못합니다. Vector Search 인덱스가 준비되기 전에는 검색할 수 없으며, OpenAI API 사용량과 네트워크 상태에 영향을 받습니다.
