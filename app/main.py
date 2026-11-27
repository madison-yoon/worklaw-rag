from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
from app.rag.retriever import retrieve
from app.rag.generator import generate_answer
from app.rag.vector_store import collection_count

app = FastAPI(title="WorkLaw RAG", description="근로기준법 조문 검색 및 근거 기반 답변")
BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/api/health")
def health():
    return {"status": "ok", "indexed_chunks": collection_count()}

@app.post("/api/ask")
def ask(request: AskRequest):
    try:
        sources = retrieve(request.question, top_k=5)
        answer = generate_answer(request.question, sources)
        return {"answer": answer, "sources": [
            {"article_id": s["metadata"].get("article_id"), "title": s["metadata"].get("title"), "text": s["text"], "distance": s["distance"], "url": s["metadata"].get("source")}
            for s in sources
        ]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
