from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAIError
from pydantic import BaseModel, Field

from app.config import settings
from app.rag.generator import generate_answer
from app.rag.retriever import retrieve
from app.rag.vector_store import check_connection

app = FastAPI(
    title="WorkLaw RAG",
    description="근로기준법 검색 및 근거 기반 답변",
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
        "mongodb_connected": database["connected"],
        "indexed_chunks": database["document_count"],
        "mongodb_error": database["error"],
        "api_key_configured": api_configured,
        "ready": (
            database["connected"]
            and database["document_count"] > 0
            and api_configured
        ),
    }


@app.post("/api/ask")
def ask(request: AskRequest):
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY를 프로젝트 루트의 .env에 설정하세요.",
        )

    database = check_connection()
    if not database["connected"]:
        raise HTTPException(
            status_code=503,
            detail=(
                "MongoDB에 연결할 수 없습니다. MONGODB_URI와 Atlas Network Access를 "
                "확인하세요."
            ),
        )
    if database["document_count"] == 0:
        raise HTTPException(
            status_code=503,
            detail="검색 데이터가 없습니다. 데이터 수집과 인덱싱을 먼저 실행하세요.",
        )

    try:
        sources = retrieve(request.question, top_k=settings.retrieval_top_k)
        if not sources:
            return {
                "answer": (
                    "검색된 법령 근거가 없습니다. 질문을 구체적으로 바꾸거나 "
                    "공식 원문을 확인해 주세요."
                ),
                "sources": [],
                "retrieval_count": 0,
            }
        answer = generate_answer(request.question, sources)
        return {
            "answer": answer,
            "retrieval_count": len(sources),
            "sources": [
                {
                    "article_id": source["metadata"].get("article_id"),
                    "title": source["metadata"].get("title"),
                    "text": source["text"],
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
        raise HTTPException(
            status_code=500,
            detail=f"검색 처리 오류: {type(exc).__name__}",
        ) from exc
