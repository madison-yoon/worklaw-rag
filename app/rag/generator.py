from openai import OpenAI
from app.config import settings


def generate_answer(question: str, sources: list[dict]) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
    if not sources:
        return "관련 영화 리뷰에서 근거를 찾지 못했습니다. 영화명이나 감상 요소를 구체적으로 질문해 주세요."

    context = "\n\n".join(
        f'[리뷰 {s["metadata"].get("review_id", "미상")}] '
        f'{s["metadata"].get("movie_title", "")} / {s["metadata"].get("title", "")}\n{s["text"]}'
        for s in sources
    )
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_chat_model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": (
                "당신은 MOMO 영화 리뷰 검색 도우미입니다. 제공된 리뷰 내용만 근거로 한국어 답변을 작성하세요. "
                "리뷰 작성자의 감상과 객관적 사실을 구분하고, 여러 리뷰의 관점이 다르면 긍정·비판을 나누어 설명하세요. "
                "근거에 없는 줄거리·흥행·제작 정보는 추측하지 말고 자료에서 확인되지 않는다고 답하세요. "
                "답변의 핵심 주장 뒤에 [리뷰 ID]를 표시하세요."
            )},
            {"role": "user", "content": f"질문: {question}\n\n검색된 MOMO 리뷰 근거:\n{context}"},
        ],
    )
    return response.choices[0].message.content or "답변을 생성하지 못했습니다."
