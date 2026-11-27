# MOMO 영화 검색·추천 RAG 아키텍처

    사용자
      ├─ 추천 목록 요청 → FastAPI 추천 프록시 → MOMO GET /api/movies/recommendations
      └─ 자연어 질문 → FastAPI RAG → OpenAI 질문 임베딩
                                      ↓
                              MongoDB Atlas Vector Search
                                      ↓ 검색된 영화·리뷰 근거
                                  GPT-4.1-mini
                                      ↓
                           답변 + 리뷰 출처 → 사용자

    데이터 구축
      MOMO RAG Seed 리뷰 10건 ─┐
      MOMO 영화 상세 API ──────┴→ 검증·정제·메타데이터 결합
                                  → 500자 / 80자 청킹
                                  → OpenAI 문서 임베딩
                                  → MongoDB Atlas

## 기존 MOMO 기능 재사용

- GET /api/movies/{movieCode}: 영화 상세정보를 수집한다.
- GET /api/movies/recommendations: 박스오피스 이력 기반 추천 후보를 제공한다.
- GET /api/movies/recommendations?genre=...: 기존 장르 필터 정책을 사용한다.
- MOMO-RAG/scripts/seed.py: 검색·평가용 가상 리뷰 10건을 제공한다.

## 데이터 흐름

영화 상세 수집은 MOMO API를 사용하고, 리뷰는 기존 RAG Seed를 사용한다. 두 자료를 영화 코드로 결합하고 청킹·임베딩해 Atlas에 저장한다. 사용자 질문은 같은 임베딩 모델로 벡터화하고 상위 리뷰 청크를 검색한다. LLM은 검색된 영화 메타데이터와 리뷰만 근거로 답변한다. 추천 후보 목록은 별도 프록시가 기존 MOMO 추천 API에서 가져온다.

## 주요 설계 결정

- MOMO에 이미 있는 영화 상세·추천 로직을 새로 구현하지 않는다.
- 실제 회원의 작성자 정보나 회원별 비공개 리뷰는 수집하지 않는다.
- 영화 추천 후보 선정은 MOMO의 박스오피스 이력 및 장르 필터 정책을 유지한다.
- AI 추천 설명은 Atlas에서 검색한 리뷰 근거와 영화 메타데이터에 한정한다.
- MongoDB Atlas는 worklaw_db.law_chunks 네임스페이스를 사용한다.
- API 키·DB URI는 환경변수로만 주입한다.
