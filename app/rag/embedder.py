from openai import OpenAI
from app.config import settings


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts,
        dimensions=settings.embedding_dimensions,
    )
    return [item.embedding for item in response.data]
