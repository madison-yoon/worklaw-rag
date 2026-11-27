from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from openai import APIConnectionError, APIStatusError, AuthenticationError, RateLimitError
from pydantic import BaseModel, Field
from pymongo.errors import PyMongoError

from app.config import settings
from app.rag import answer, ingest, retrieve, store, vector_index_status

app = FastAPI(
    title="Python Docs RAG",
    description="Python 공식 문서를 MongoDB Atlas Vector Search로 검색하고 근거 기반 답변을 제공합니다.",
    version="2.0.0",
)
static = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=static), name="static")


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=20)


@app.get("/", response_class=HTMLResponse)
def home():
    return (static / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health():
    try:
        collection = store()
        collection.database.client.admin.command("ping")
        count = collection.count_documents({})
        index = vector_index_status()
        index_ready = bool(index and index.get("queryable"))
        return {
            "status": "ok" if index_ready else "degraded",
            "vector_db": "MongoDB Atlas Vector Search",
            "vector_db_connected": True,
            "indexed_chunks": count,
            "vector_index": settings.vector_index,
            "vector_index_ready": index_ready,
            "api_key_configured": bool(settings.api_key),
            "ready": bool(count and index_ready and settings.api_key),
        }
    except Exception as exc:
        return {
            "status": "error",
            "vector_db": "MongoDB Atlas Vector Search",
            "vector_db_connected": False,
            "indexed_chunks": 0,
            "vector_index": settings.vector_index,
            "vector_index_ready": False,
            "api_key_configured": bool(settings.api_key),
            "ready": False,
            "error": str(exc),
        }


@app.post("/api/ingest")
def run_ingest():
    try:
        return ingest()
    except (PyMongoError, requests.RequestException) as exc:
        raise HTTPException(status_code=502, detail=f"수집·MongoDB 색인 실패: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"수집·색인 실패: {exc}") from exc


@app.post("/api/ask")
def ask(body: AskRequest):
    try:
        hits = retrieve(body.question, body.top_k)
        if not hits:
            raise HTTPException(
                status_code=404,
                detail="검색할 문서가 없습니다. MongoDB 연결과 문서 수집 상태를 확인한 뒤 수집을 실행하세요.",
            )
        generated = answer(body.question, hits)
        return {
            "answer": generated,
            "sources": [
                {
                    "title": hit["title"],
                    "url": hit["url"],
                    "score": round(float(hit["score"]), 4),
                    "chunk": hit["chunk"],
                    "excerpt": hit["text"][:240],
                }
                for hit in hits
            ],
        }
    except HTTPException:
        raise
    except AuthenticationError as exc:
        raise HTTPException(status_code=502, detail="OpenAI API 인증에 실패했습니다. OPENAI_API_KEY를 확인하세요.") from exc
    except RateLimitError as exc:
        raise HTTPException(status_code=502, detail="OpenAI API 사용 한도 또는 결제 한도를 확인하세요.") from exc
    except (APIConnectionError, APIStatusError) as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI API 요청 실패: {exc}") from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=502, detail=f"MongoDB Vector Search 실패: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"질의 처리 실패: {exc}") from exc
