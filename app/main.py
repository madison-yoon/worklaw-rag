from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAIError
from pydantic import BaseModel, Field

from app.config import settings
from app.rag.generator import generate_answer
from app.rag.retriever import retrieve
from app.rag.vector_store import check_connection

app = FastAPI(
    title="MOMO Movie Search & Recommendation RAG",
    description="MOMO 영화 API와 리뷰를 활용한 근거 기반 검색·추천",
)
BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health():
    database = check_connection()
    api_configured = bool(settings.openai_api_key)
    return {
        "status": "ok" if database["connected"] else "degraded",
        "vector_db": "MongoDB Atlas Vector Search",
        "vector_db_connected": database["connected"],
        "database": database.get("database"),
        "collection": database.get("collection"),
        "indexed_chunks": database["document_count"],
        "vector_db_error": database["error"],
        "api_key_configured": api_configured,
        "momo_api_base_url": settings.momo_api_base_url,
        "ready": database["connected"] and database["document_count"] > 0 and api_configured,
    }


@app.get("/api/recommendations")
def recommendations(genre: str | None = Query(default=None, max_length=30)):
    """MOMO가 이미 제공하는 박스오피스 기반 추천 후보 API를 그대로 재사용한다."""
    params = {"genre": genre.strip()} if genre and genre.strip() else {}
    try:
        response = requests.get(
            f"{settings.momo_api_base_url.rstrip('/')}/api/movies/recommendations",
            params=params,
            timeout=(3, 10),
        )
        response.raise_for_status()
        movies = response.json()
        if not isinstance(movies, list):
            raise ValueError("MOMO 추천 API 응답 형식이 올바르지 않습니다.")
        return {"movies": movies[:12], "source": "MOMO /api/movies/recommendations"}
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="MOMO 백엔드 연결에 실패했습니다. MOMO Spring Boot 서버(기본 포트 8111)를 실행하세요.",
        ) from exc


@app.post("/api/ask")
def ask(request: AskRequest):
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY를 프로젝트 루트의 .env에 설정하세요.")
    database = check_connection()
    if not database["connected"]:
        raise HTTPException(
            status_code=503,
            detail=f"MongoDB Atlas 연결 실패: {database['error']}",
        )
    if database["document_count"] == 0:
        raise HTTPException(status_code=503, detail="검색 데이터가 없습니다. 수집과 인덱싱을 먼저 실행하세요.")

    try:
        sources = retrieve(request.question, top_k=settings.retrieval_top_k)
        if not sources:
            return {
                "answer": "관련 MOMO 영화·리뷰에서 근거를 찾지 못했습니다. 영화명이나 감상 조건을 구체적으로 질문해 주세요.",
                "sources": [],
                "retrieval_count": 0,
            }
        answer = generate_answer(request.question, sources)
        return {
            "answer": answer,
            "retrieval_count": len(sources),
            "sources": [
                {
                    "review_id": source["metadata"].get("review_id"),
                    "movie_title": source["metadata"].get("movie_title"),
                    "title": source["metadata"].get("title"),
                    "text": source["text"],
                    "genre": source["metadata"].get("genre"),
                    "director": source["metadata"].get("director"),
                    "release_date": source["metadata"].get("release_date"),
                    "overview": source["metadata"].get("overview"),
                    "score": source.get("score"),
                    "url": source["metadata"].get("source"),
                }
                for source in sources
            ],
        }
    except OpenAIError as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenAI API 요청에 실패했습니다. API 키와 사용 한도를 확인하세요.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"검색 처리 오류: {type(exc).__name__}") from exc
