# 데이터 수집 및 전처리

## 원천 데이터
- 제공기관: 법제처 국가법령정보센터
- 문서: 현행 근로기준법
- 수집 방식: 국가법령정보센터 OPEN API
- 목록 API: `https://www.law.go.kr/DRF/lawSearch.do` (target=eflaw, type=JSON)
- 본문 API: `https://www.law.go.kr/DRF/lawService.do` (target=eflaw, type=JSON)
- 인증: `LAW_API_OC` 환경변수
- 수집 코드: `scripts/collect_data.py`
- 정제 결과: `data/processed/labor_standards_act.jsonl`

수집기는 현행법령 목록에서 근로기준법의 법령 ID를 확인한 뒤, 해당 ID로 현행 본문을 조회한다. 응답의 조문번호·조문가지번호·조문제목·조문내용을 조문별 레코드로 정규화한다. API 오류, 조문 추출 실패 또는 최소 수량 미달 시 기존 결과 파일을 덮어쓰지 않는다.

## JSONL 필드
| 필드 | 설명 |
|---|---|
| article_id | 제17조, 제17조의2 등 조문 식별자 |
| title | 조문 제목 |
| text | 조문 제목과 본문 |
| source | 국가법령정보센터 원문 링크 |
| law_name | 근로기준법 |
| effective_date | API에서 확인한 시행일자 |

## 청킹 설계
- 구현: `app/rag/chunker.py`의 `split_documents()`
- chunk_size: `CHUNK_SIZE` 환경 설정
- chunk_overlap: `CHUNK_OVERLAP` 환경 설정
- 조문 식별자, 제목, 출처를 각 chunk에 유지

조문 단위로 먼저 분리한 뒤 길이 기준으로 청킹한다. 초기값은 실험 시작점이며 최적값으로 단정하지 않는다. 개선 실험에서는 청킹 설정을 변경한 뒤 반드시 전체 재색인하고 동일 평가 질문으로 재측정한다.

## 임베딩 및 벡터 DB
- 임베딩 모델: `OPENAI_EMBEDDING_MODEL`
- 차원: `EMBEDDING_DIMENSIONS`
- DB: MongoDB Atlas
- Database: `MONGODB_DATABASE`
- Collection: `MONGODB_COLLECTION`
- Vector Search Index: `MONGODB_VECTOR_INDEX`
- Vector field: `MONGODB_VECTOR_PATH`
- Similarity: cosine

평가 질문과 기대 조문은 `data/evaluation/questions.json`에 별도 보관한다. 정답 라벨은 오프라인 평가에서만 사용하며 서비스의 검색 및 답변 로직에는 주입하지 않는다.
