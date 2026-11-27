# 데이터 수집 및 전처리

## 원천 데이터
- 제공기관: 법제처 국가법령정보센터
- 문서: 근로기준법
- 원문 URL: 수집 스크립트의 SOURCE_URL
- 수집 코드: scripts/collect_data.py
- 정제 결과: data/processed/labor_standards_act.jsonl

수집 스크립트는 공식 페이지에서 본문을 추출하고 조문 제목 패턴을 기준으로 레코드를 만든다. 조문 추출 실패 또는 최소 수량 미달 시 인덱싱에 사용할 수 없도록 중단한다. 실제 수집 수량은 실행 로그로 확인한다.

## JSONL 필드
| 필드 | 설명 |
|---|---|
| article_id | 제17조 등 조문 식별자 |
| title | 조문 제목 |
| text | 조문 원문 |
| source | 공식 원문 URL |

## 청킹 설계
- 구현: app/rag/chunker.py의 split_documents()
- chunk_size: CHUNK_SIZE 환경 설정
- chunk_overlap: CHUNK_OVERLAP 환경 설정
- 조문 식별자, 제목, 출처를 각 chunk에 유지

조문 단위로 먼저 분리한 뒤 길이 기준으로 청킹한다. 초기값은 실험 시작점이며 최적값으로 단정하지 않는다. 개선 실험에서는 청킹 설정을 변경한 뒤 반드시 전체 재색인하고 동일 평가 질문으로 재측정한다.

## 임베딩 및 벡터 DB
- 임베딩 모델: OPENAI_EMBEDDING_MODEL
- 차원: EMBEDDING_DIMENSIONS
- DB: MongoDB
- Database: MONGODB_DATABASE
- Collection: MONGODB_COLLECTION
- Vector Search Index: MONGODB_VECTOR_INDEX
- Vector field: MONGODB_VECTOR_PATH
- Similarity: cosine

평가 질문과 기대 조문은 data/evaluation/questions.json에 별도 보관한다. 정답 라벨은 오프라인 평가에서만 사용하며 서비스의 검색 및 답변 로직에는 주입하지 않는다.
