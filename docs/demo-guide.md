# 실행 및 데모

## 준비
프로젝트 루트에서 의존성을 설치한다.
```bash
pip install -r requirements.txt
```
.env에 OPENAI_API_KEY를 설정한다. 실제 키는 GitHub에 올리지 않는다.

## 데이터 수집과 인덱싱
```bash
python scripts/collect_data.py
python scripts/build_index.py
```
수집된 조문 수와 인덱싱 chunk 수를 확인한다.

## 서버 실행
```bash
uvicorn app.main:app --reload
```
http://127.0.0.1:8000 에 접속한다. /api/health에서 키 설정 여부와 인덱스 수를 확인한다.

## 시연 질문
- 근로계약서를 작성할 때 명시해야 하는 내용은?
- 임금은 어떤 원칙으로 지급해야 하나요?
- 근로시간과 휴게시간의 기본 기준은 어떻게 되나요?
- 연차 유급휴가는 어떻게 보장되나요?
- 해고할 때 지켜야 할 절차는?

질문은 실제 임베딩과 벡터 검색을 거쳐 답변을 생성한다. 평가용 정답 조문을 검색 결과에 강제로 넣지 않는다.

## 평가
python scripts/evaluate.py
동일 평가 세트로 기준 설정과 개선 설정을 측정하고 실제 수치를 docs/evaluation.md에 기록한다.

## 주의
키가 없는 상태에서는 수집과 단위 테스트만 가능하며 임베딩·검색·답변 생성은 불가능하다. 본 서비스는 법률 자문이 아닌 학습용 POC다.
