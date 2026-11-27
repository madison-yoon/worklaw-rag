# 데이터 수집 및 전처리

## 원천 데이터

- 제공기관: 법제처 국가법령정보센터
- 문서: 근로기준법 본문
- URL: https://law.go.kr/LSW/lsInfoP.do?lsiSeq=285279
- 수집 방식: `scripts/collect_data.py`가 공식 페이지를 HTTP 요청하고 HTML 본문에서 조문 제목 패턴을 찾아 조문별 JSONL로 저장한다.

## 정제 및 저장 구조

각 레코드는 다음 필드를 가진다.

| 필드 | 의미 |
|---|---|
| article_id | 제17조 등 조문 식별자 |
| title | 조문 제목 |
| text | 조문 원문 텍스트 |
| source | 원문 URL |

원문에서 조문 단위로 분리한 다음 RecursiveCharacterTextSplitter로 청킹한다. chunk metadata에는 article_id, title, source를 반복 저장하여 검색 결과의 출처를 복원할 수 있다.

## 청킹 설정

- chunk_size: 500 characters
- chunk_overlap: 80 characters
- separators: 문단, 줄바꿈, 문장 종결, 공백 순서

이는 POC 초기 설정이다. 법령 조문은 조·항·호의 구조가 중요하므로 향후에는 항·호 단위 구조화 청킹과 조문 전체 문맥 병합을 비교할 필요가 있다.

## 벡터 저장

- DB: ChromaDB PersistentClient
- collection: `worklaw_articles`
- distance: cosine
- embedding: `text-embedding-3-small`, 1,536 dimensions
- 저장 경로: `./chroma_db` (Git 제외)
