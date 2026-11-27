# 데이터 수집 및 전처리

## 원천 데이터
- 제공기관: 법제처 국가법령정보센터
- 문서: 현행 근로기준법
- 수집 방식: 국가법령정보센터에서 로그인 없이 공개하는 법령 본문 HTML 페이지 수집
- 공개 원문: https://www.law.go.kr/lsLinkProc.do?ancYnChk=0&chrClsCd=010202&lsNm=%EA%B7%BC%EB%A1%9C%EA%B8%B0%EC%A4%80%EB%B2%95&mode=20
- 수집 코드: `scripts/collect_data.py`
- 정제 결과: `data/processed/labor_standards_act.jsonl`
- 인증: 별도 법령 OPEN API 키 불필요

수집기는 공개 본문 페이지를 HTTP로 요청하고 HTML에서 시행일자와 본문을 추출한다. 본문 시작점은 '제1조(목적)'으로 고정하고, 조문 제목 패턴을 기준으로 조문별 텍스트를 분리한다. 부칙은 본문 조문 데이터와 혼합되지 않도록 별도 범위로 제외한다. 조문 식별자, 제목, 본문, 원문 URL, 법령명, 시행일자를 JSONL 레코드로 저장한다.

페이지 요청 실패, 본문 시작점 미발견, 조문 추출 수가 20개 미만인 경우 수집을 중단하고 기존 결과 파일을 보존한다. 수집 시점의 법령 시행일자를 함께 저장하며, 법령 개정 이후에는 수집 스크립트를 다시 실행해 데이터와 벡터 인덱스를 갱신한다.

## JSONL 필드
| 필드 | 설명 |
|---|---|
| article_id | 제17조, 제17조의2 등 조문 식별자 |
| title | 조문 번호와 조문 제목 |
| text | 조문 제목과 본문 |
| source | 국가법령정보센터 원문 페이지 |
| law_name | 근로기준법 |
| effective_date | 원문 페이지에서 추출한 시행일자 |

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
