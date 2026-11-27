# WorkLaw RAG

근로기준법 문서를 검색하고 검색된 원문 근거에 기반해 답변하는 한국어 RAG 웹서비스 POC입니다.

## 기술 구성
- API: FastAPI
- LLM 및 Embedding: OpenAI API (모델은 환경 설정)
- Vector DB: MongoDB Atlas Vector Search
- UI: HTML / CSS / Vanilla JavaScript
- 데이터 원천: 국가법령정보센터 현행법령 OPEN API
- Python: 3.12 이상

## 1. 실행 환경 준비

기존 Conda 환경을 활성화하거나 Python 3.12 이상 환경을 준비합니다.

```bash
pip install -r requirements.txt
```

프로젝트 루트의 `.env`에 다음 항목을 설정합니다. 기존 키는 유지하고 국가법령정보센터 OC 키를 추가합니다.

```dotenv
OPENAI_API_KEY=기존에_설정한_키
LAW_API_OC=국가법령정보센터에서_발급받은_OC
MONGODB_URI=mongodb+srv://사용자:비밀번호@클러스터주소/
MONGODB_DATABASE=worklaw_db
MONGODB_COLLECTION=law_chunks
MONGODB_VECTOR_INDEX=vector_index
MONGODB_VECTOR_PATH=embedding
```

실제 인증키와 MongoDB URI가 포함된 `.env`는 절대 Git에 커밋하지 않습니다.

## 2. MongoDB Atlas Vector Search 인덱스

Atlas에서 대상 Database와 Collection을 생성하거나 첫 데이터 저장 시 자동 생성되도록 둡니다. 이후 해당 Collection에서 Vector Search Index를 생성합니다.

인덱스 이름은 `vector_index`로 지정하고 아래 정의를 사용합니다.

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

임베딩 차원을 변경했다면 인덱스의 numDimensions도 동일하게 변경해야 합니다.

## 3. 연결 확인 및 데이터 구축

```bash
python scripts/collect_data.py
python scripts/check_mongodb.py
python scripts/build_index.py
python scripts/check_mongodb.py
```

- 수집기는 국가법령정보센터 OPEN API의 현행법령 목록에서 근로기준법 ID를 조회한 뒤 현행 본문 JSON을 수집합니다.
- 조문 단위로 정제하여 JSONL 파일을 생성합니다.
- 인덱싱 스크립트는 조문을 청킹하고 OpenAI 임베딩 API를 호출한 뒤 MongoDB에 upsert합니다.
- Vector Search 인덱스가 READY 상태가 된 후 검색을 실행합니다.

## 4. 웹서비스 실행

```bash
uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다.

- `GET /api/health`: MongoDB 연결, chunk 수, API 키 설정 상태
- `POST /api/ask`: 자연어 질문에 대한 근거 기반 답변
- `GET /docs`: FastAPI API 문서

## 5. 평가 및 테스트

```bash
pytest -q
python scripts/evaluate.py
```

검색 평가는 기대 조문이 있는 오프라인 평가 질문을 사용하며 Recall@K와 MRR@K를 출력합니다. 평가 라벨은 서비스 실행 경로에서 사용하지 않습니다.

## 데이터 출처 및 한계
- 국가법령정보센터 현행법령 OPEN API를 통해 근로기준법 목록과 본문을 수집합니다.
- 법령은 개정될 수 있으므로 실제 권리·의무 판단 전에는 최신 시행 법령과 관련 하위법령을 확인해야 합니다.
- 본 서비스는 학습·정보 탐색용 POC이며 법률 자문이 아닙니다.
- 검색 품질은 수집 범위, API 응답 정규화, 청킹, 임베딩, Vector Search 인덱스에 영향을 받습니다.
- OpenAI 임베딩 및 답변 생성에는 API 사용료가 발생할 수 있습니다.
