# MOMO 리뷰 데이터 구축 및 전처리

## 데이터 원천과 범위

원천은 기존 MOMO 프로젝트의 RAG 시연 데이터다.

- 원본 저장소: https://github.com/madison-yoon/MOMO
- 원본 코드: `MOMO-RAG/scripts/seed.py`
- 원본 상수: `MOVIES`, `OPINIONS`
- 이관 데이터: `data/raw/momo_reviews.jsonl`
- 정제 결과: `data/processed/momo_reviews.jsonl`
- 수집·정제 코드: `scripts/collect_data.py`

영화는 기생충, 인터스텔라, 극한직업, 라라랜드, 겨울왕국 5편이며 서로 다른 감상 관점의 리뷰 10건으로 구성한다. 해당 리뷰는 MOMO RAG의 로컬 시연을 위해 작성된 가상 감상이다. 실제 회원의 작성 내용이나 개인정보는 포함하지 않는다.

## 정제 절차

1. JSONL을 한 줄씩 읽어 레코드 단위로 파싱한다.
2. 리뷰 ID, 영화 코드, 영화명, 리뷰 제목, 본문, 출처의 필수 필드를 검사한다.
3. 본문 앞뒤와 연속 공백을 정리한다.
4. 리뷰 ID를 기준으로 중복을 제거한다.
5. 영화명과 리뷰 제목을 결합해 검색용 제목을 만든다.
6. 원본 MOMO Seed 코드 링크를 출처 메타데이터로 저장한다.
7. 중복 제거 후 10건이 아니면 색인 입력 파일을 생성하지 않고 중단한다.

## JSONL 스키마

| 필드 | 설명 |
|---|---|
| document_id | RAG 문서의 고유 ID |
| review_id | MOMO 리뷰 식별자(시연 데이터 ID) |
| movie_code | KOBIS 영화 코드 |
| movie_title | 영화 제목 |
| review_title | 리뷰 제목 |
| title | 영화명과 리뷰 제목을 결합한 검색 제목 |
| aspect | 감상 요소 |
| text | 정제된 리뷰 본문 |
| source | 원본 MOMO Seed 코드 URL |

## 청킹 설계

- 크기: 500자
- 오버랩: 80자
- 분할 기준: 문장 부호와 공백 경계를 우선 탐색하고, 목표 크기의 65% 이후에서 가장 가까운 경계를 사용
- 메타데이터: document_id, review_id, movie_code, movie_title, title, source, chunk_index 유지

500자는 리뷰의 여러 감상 요소를 한 검색 단위에서 함께 다룰 수 있도록 MOMO RAG에서 사용한 초기 설정을 재사용한 값이다. 80자 overlap은 경계에서 문맥이 끊기는 것을 줄이기 위한 값이다. 최적값으로 단정하지 않고 평가 실험으로 조정한다.

## 임베딩과 벡터 저장

- 임베딩: OpenAI `text-embedding-3-small`
- 차원: 1536
- 벡터 DB: MongoDB Atlas Vector Search
- Database / Collection: `momo_rag_poc.review_chunks`
- Vector index: `review_vector_index`
- 유사도: cosine

문서 본문과 검색 메타데이터, 임베딩 벡터를 같은 chunk 문서에 저장한다. `_id`는 문서 ID와 chunk 번호를 조합해 재색인 시 upsert한다.
