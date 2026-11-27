from openai import OpenAI
from app.config import settings


def generate_answer(question: str, sources: list[dict]) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
    if not sources:
        return "관련 영화 리뷰에서 근거를 찾지 못했습니다. 영화명이나 감상 요소를 구체적으로 질문해 주세요."

    context = "\n\n".join(
        f'[리뷰 {s["metadata"].get("review_id", "미상")}] '
        f'영화: {s["metadata"].get("movie_title", "")} / '
        f'장르: {s["metadata"].get("genre", "")} / '
        f'감독: {s["metadata"].get("director", "")} / '
        f'개봉일: {s["metadata"].get("release_date", "")}\n'
        f'영화 소개: {s["metadata"].get("overview", "")}\n'
        f'리뷰 제목: {s["metadata"].get("title", "")}\n{s["text"]}'
        for s in sources
    )
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_chat_model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": (
                "당신은 MOMO 영화 검색·추천 도우미입니다. 반드시 제공된 MOMO 영화 정보와 리뷰만 근거로 한국어 답변을 작성하세요. "
                "사용자가 영화를 추천해 달라고 하면 검색 결과에 포함된 영화만 추천하고, 장르·감독·줄거리와 리뷰 감상을 근거로 추천 이유를 설명하세요. "
                "서로 다른 리뷰가 있으면 긍정·비판 관점을 구분하세요. "
                "리뷰 작성자의 감상과 영화의 객관적 정보를 구분하고, 근거에 없는 출연진·흥행·수상·제작 정보는 추측하지 마세요. "
                "리뷰에서 가져온 주장은 [리뷰 ID]로 인용하세요. 검색 근거가 부족하면 부족하다고 명시하세요."
            )},
            {"role": "user", "content": f"질문: {question}\n\n검색된 MOMO 영화·리뷰 근거:\n{context}"},
        ],
    )
    return response.choices[0].message.content or "답변을 생성하지 못했습니다."
