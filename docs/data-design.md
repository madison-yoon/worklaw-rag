# MOMO 영화·리뷰 데이터 구축

## 데이터 출처

| 구분 | 출처 | 사용 필드 |
|---|---|---|
| 영화 상세 | MOMO GET /api/movies/{movieCode} | movieCode, title, releaseDate, genre, director, actors, overview |
| 추천 후보 | MOMO GET /api/movies/recommendations | movieCode, title, releaseDate, genre, director, posterUrl, box-office rank |
| 리뷰 시연 데이터 | MOMO MOMO-RAG/scripts/seed.py | review ID, movie code, movie title, review title, review content |

리뷰는 기존 RAG 수업용 Seed에 포함된 가상 감상 10건이다. 실제 회원의 리뷰·닉네임·회원 ID를 복제하지 않는다. 영화 상세정보는 MOMO Spring Boot 서버의 공개 GET API에서 조회한다.

## 수집·정제 과정

1. 원천 JSONL의 필수 리뷰 필드와 중복 ID를 확인한다.
2. 영화 코드 5개를 중복 제거한다.
3. MOMO 영화 상세 API를 영화 코드당 1회 호출한다.
4. 응답의 movieCode가 요청한 코드와 같은지 검사한다.
5. API의 제목과 Seed 영화 제목이 일치하는지 확인한다.
6. 장르·감독·개봉일·줄거리·배우를 리뷰 문서 메타데이터로 결합한다.
7. 정제 결과를 UTF-8 JSONL로 원자적으로 저장한다.

## JSONL 문서 구조

| 필드 | 설명 |
|---|---|
| document_id | RAG 문서 고유 ID |
| review_id | MOMO RAG 시연 리뷰 ID |
| movie_code | MOMO/KOBIS 영화 코드 |
| movie_title | MOMO API에서 확인한 영화 제목 |
| genre, director, release_date | 영화 상세 메타데이터 |
| overview, actors | 영화 줄거리 및 출연진 |
| title, text | 리뷰 제목과 본문 |
| movie_metadata_text | 임베딩에 넣는 영화 정보 텍스트 |
| source | 원본 MOMO 저장소 |
| source_api | 실제 조회한 MOMO 상세 API 경로 |

## 청킹·임베딩

- 청크 크기: 500자
- 오버랩: 80자
- 문장 부호·공백 경계를 우선 분할
- 임베딩 입력: 영화명 + 장르·감독·개봉일·줄거리 + 리뷰 제목 + 청크 본문
- 모델: OpenAI text-embedding-3-small
- 차원: 1536

영화 정보만 따로 분리하지 않고 리뷰 청크에 함께 넣어 “우주를 다룬 SF”, “봉준호 감독 작품” 같은 질문도 영화 리뷰와 연결되도록 했다. 500/80은 초기 기준값이며 평가 실험으로 조정한다.

## 벡터 저장

- MongoDB Atlas
- Database: worklaw_db
- Collection: law_chunks
- Index: vector_index
- Vector path: embedding
- Similarity: cosine

리뷰 ID와 영화 코드를 유지해 검색 결과를 원본 시연 데이터 및 MOMO 영화 API와 연결한다.
