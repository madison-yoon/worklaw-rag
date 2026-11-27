# 데이터 수집 및 전처리

## 원천 데이터
- 제공기관: 법제처 국가법령정보센터
- 문서: 근로기준법
- URL: https://law.go.kr/LSW/lsInfoP.do?lsiSeq=285279
- 수집 코드: scripts/collect_data.py
- 정제 결과: data/processed/labor_standards_act.jsonl

수집 스크립트는 공식 페이지에서 본문을 추출하고 조문 제목 패턴을 기준으로 레코드를 만든다. 조문이 추출되지 않거나 20개 미만이면 실패 처리한다. 실제 추출 수는 실행 로그로 확인한다.

## JSONL 필드
| 필드 | 설명 |
|---|---|
| article_id | 제17조 등 조문 식별자 |
| title | 조문 제목 |
| text | 조문 원문 |
| source | 공식 원문 URL |

## 청킹 설계
- 구현: app/rag/chunker.py의 split_documents()
- 기본 chunk_size: 500자
- 기본 chunk_overlap: 80자
- 경계 우선순위: 문단, 줄바꿈, 문장 종결, 공백
- article_id, title, source를 각 chunk metadata에 유지

조문 단위로 먼저 분리한 뒤 문자 길이 기준으로 청킹한다. 500/80은 초기 실험값이며 최적값으로 단정하지 않는다. 후속 실험에서 항·호 단위 구조화 청킹과 비교한다.

## 임베딩 및 벡터 DB
- OpenAI Embedding: text-embedding-3-small
- 차원: 1,536
- DB: ChromaDB PersistentClient
- Collection: worklaw_articles
- 거리: cosine
- 경로: ./chroma_db (Git 제외)

평가 질문과 기대 조문은 data/evaluation/questions.json에 별도 보관하며 검색 경로에 정답 라벨을 주입하지 않는다.
