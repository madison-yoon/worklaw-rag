# 데이터 수집 및 전처리

## 원천 데이터
- 제공기관: 법제처 국가법령정보센터
- 문서: 현행 근로기준법
- 수집 방식: 국가법령정보센터 OPEN API
- 목록 API: `https://www.law.go.kr/DRF/lawSearch.do` (`target=eflaw`, `type=JSON`)
- 본문 API: `https://www.law.go.kr/DRF/lawService.do` (`target=eflaw`, `type=JSON`)
- 인증: `LAW_API_OC` 환경변수 (공동활용 신청 후 승인된 인증키)
- 권한 조건: API 신청 항목 선택만으로 즉시 호출 가능한 것은 아니며, 국가법령정보 공동활용의 승인 완료 후 이용 가능
- 수집 코드: `scripts/collect_data.py`
- 정제 결과: `data/processed/labor_standards_act.jsonl`

수집기는 현행법령 목록에서 법령명이 정확히 '근로기준법'인 항목을 찾고, **동일한 항목에 포함된 법령ID**를 본문 조회에 사용한다. 목록 응답 전체를 재귀 탐색해 첫 번째 법령일련번호와 시행일자를 각각 가져오지 않는다. 본문 API는 `ID`를 전달해 해당 법령의 현행 본문을 조회하며, 이 방식에서는 `efYd`를 전달하지 않는다.

본문 응답의 법령명이 근로기준법과 일치하는지 확인한 뒤 조문번호·조문가지번호·조문제목·조문내용을 조문별 레코드로 정규화한다. 서버가 '공동활용 미신청된 목록/본문' 오류 페이지를 반환하면 JSON 파싱 오류가 아니라 인증키의 공동활용 승인 또는 해당 서비스 권한 거부로 처리한다. API 오류, 다른 법령 응답, 조문 추출 실패 또는 최소 수량 미달 시 기존 결과 파일을 덮어쓰지 않는다.

## JSONL 필드
| 필드 | 설명 |
|---|---|
| article_id | 제17조, 제17조의2 등 조문 식별자 |
| title | 조문 제목 |
| text | 조문 제목과 본문 |
| source | 국가법령정보센터 원문 링크 |
| law_name | 근로기준법 |
| effective_date | 본문 API에서 확인한 시행일자 |

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
