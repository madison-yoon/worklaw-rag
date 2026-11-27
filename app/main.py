from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAIError
from pydantic import BaseModel, Field

from app.config import settings
from app.rag.retriever import retrieve
from app.rag.generator import generate_answer
from app.rag.vector_store import collection_count

app = FastAPI(title="WorkLaw RAG", description="근로기준법 검색 및 근거 기반 답변")
BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/api/health")
def health():
    count = collection_count()
    configured = bool(settings.openai_api_key)
    return {"status": "ok", "indexed_chunks": count, "api_key_configured": configured,
            "ready": configured and count > 0}

@app.post("/api/ask")
def ask(request: AskRequest):
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY를 프로젝트 루트의 .env에 설정하세요.")
    if collection_count() == 0:
        raise HTTPException(status_code=503, detail="검색 데이터가 없습니다. 데이터 수집과 인덱싱을 먼저 실행하세요.")
    try:
        sources = retrieve(request.question, top_k=5)
        if not sources:
            return {"answer": "검색된 법령 근거가 없습니다. 질문을 구체적으로 바꾸거나 공식 원문을 확인해 주세요.",
                    "sources": [], "retrieval_count": 0}
        answer = generate_answer(request.question, sources)
        return {"answer": answer, "retrieval_count": len(sources), "sources": [
            {"article_id": s["metadata"].get("article_id"), "title": s["metadata"].get("title"),
             "text": s["text"], "distance": s["distance"], "url": s["metadata"].get("source")}
            for s in sources
        ]}
    except OpenAIError as exc:
        raise HTTPException(status_code=502, detail="OpenAI API 요청에 실패했습니다. 키와 사용 한도를 확인하세요.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"검색 처리 오류: {type(exc).__name__}") from exc
