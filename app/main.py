from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.rag import ingest, retrieve, answer, store

app = FastAPI(title="Python Docs RAG")
static = Path(__file__).resolve().parent.parent / "static"
app.mount("/static",StaticFiles(directory=static),name="static")

class AskRequest(BaseModel):
    question: str = Field(min_length=2,max_length=1000)
    top_k: int | None = Field(default=None,ge=1,le=20)

@app.get("/",response_class=HTMLResponse)
def home(): return (static/"index.html").read_text(encoding="utf-8")

@app.get("/api/health")
def health():
    try: count=store().count()
    except Exception: count=0
    return {"status":"ok","chunks":count}

@app.post("/api/ingest")
def run_ingest():
    try: return ingest()
    except Exception as exc: raise HTTPException(502,detail=f"수집·색인 실패: {exc}") from exc

@app.post("/api/ask")
def ask(body: AskRequest):
    try:
        hits=retrieve(body.question,body.top_k)
        if not hits: raise HTTPException(404,detail="색인된 문서가 없습니다. 먼저 공식 문서 수집을 실행하세요.")
        return {"answer":answer(body.question,hits),"sources":[{"title":h["title"],"url":h["url"],"score":h["score"],"chunk":h["chunk"]} for h in hits]}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(502,detail=str(exc)) from exc
