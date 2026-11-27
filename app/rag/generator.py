from openai import OpenAI
from app.config import settings


def generate_answer(question: str, sources: list[dict]) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
    if not sources:
        return "관련 근거를 찾지 못했습니다. 질문을 구체적으로 바꾸거나 공식 기관에 문의해 주세요."
    context = "\n\n".join(
        f'[{s["metadata"].get("article_id", "조문")}] {s["metadata"].get("title", "")}\n{s["text"]}'
        for s in sources
    )
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_chat_model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": "당신은 근로기준법 학습을 돕는 검색형 안내 도우미입니다. 제공된 법령 근거만 사용해 한국어로 답하세요. 근거에 없는 사실은 추측하지 말고 '제공된 자료에서 확인되지 않습니다'라고 밝히세요. 법률 자문이나 개별 사건의 결론을 단정하지 마세요. 핵심 내용을 설명하고 관련 조문 번호를 답변에 표시하세요."},
            {"role": "user", "content": f"질문: {question}\n\n검색된 법령 근거:\n{context}"},
        ],
    )
    return response.choices[0].message.content or "답변을 생성하지 못했습니다."
