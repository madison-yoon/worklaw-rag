import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from app.config import settings

_model = None
_client = None
_col = None

def chunks(text: str) -> list[str]:
    size, overlap = settings.chunk_size, settings.overlap
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Invalid chunk size/overlap configuration")
    text = " ".join(text.split())
    result, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + size // 2, end)
            if boundary > start: end = boundary
        part = text[start:end].strip()
        if part: result.append(part)
        if end == len(text): break
        start = max(end - overlap, start + 1)
    return result

def embed(texts: list[str]) -> list[list[float]]:
    global _model
    if _model is None: _model = SentenceTransformer(settings.embedding_model)
    return _model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()

def store():
    global _client, _col
    if _col is None:
        _client = chromadb.PersistentClient(path=settings.db_path)
        _col = _client.get_or_create_collection(settings.collection, metadata={"hnsw:space":"cosine"})
    return _col

def discover_urls() -> list[str]:
    r = requests.get(settings.sitemap, timeout=settings.timeout)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    ns = {"s":"http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [n.text for n in root.findall(".//s:loc", ns) if n.text]
    if urls and urlparse(urls[0]).path.endswith(".xml"):
        nested = []
        for url in urls:
            page = requests.get(url, timeout=settings.timeout); page.raise_for_status()
            nested.extend(n.text for n in ET.fromstring(page.content).findall(".//s:loc", ns) if n.text)
        urls = nested
    return [u for u in urls if urlparse(u).netloc == "docs.python.org"][:settings.max_pages]

def read_page(url: str):
    r = requests.get(url, timeout=settings.timeout, headers={"User-Agent":"EducationalPythonRAG/1.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    main = soup.select_one("main") or soup.select_one("div.body") or soup.body
    if not main: return None
    for tag in main.select("script,style,nav,footer,.related,.sphinxsidebar,.breadcrumb"): tag.decompose()
    text = " ".join(main.stripped_strings)
    h = soup.select_one("h1") or soup.title
    title = h.get_text(" ", strip=True) if h else url
    return {"url":url,"title":title,"text":text} if len(text) >= 120 else None

def ingest() -> dict:
    urls = discover_urls()
    ids, docs, metas = [], [], []
    fetched = 0
    for url in urls:
        try:
            page = read_page(url)
            if not page: continue
            fetched += 1
            for i, part in enumerate(chunks(page["text"])):
                ids.append(f"{url}#{i}"); docs.append(part)
                metas.append({"url":url,"title":page["title"],"chunk":i})
        except requests.RequestException:
            continue
    if docs:
        store().upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embed(docs))
    return {"pages_discovered":len(urls),"pages_fetched":fetched,"chunks_indexed":len(docs)}

def retrieve(question: str, top_k: int | None = None) -> list[dict]:
    col = store()
    if not col.count(): return []
    vector = embed([question])[0]
    result = col.query(query_embeddings=[vector], n_results=min(top_k or settings.top_k,col.count()))
    return [{"text":d,**m,"score":round(1-dist,4)} for d,m,dist in zip(result["documents"][0],result["metadatas"][0],result["distances"][0])]

def answer(question: str, hits: list[dict]) -> str:
    if not settings.api_key: raise RuntimeError("OPENAI_API_KEY를 .env에 설정하세요.")
    context = "\n\n".join(f"[{i+1}] {h['title']} {h['url']}\n{h['text']}" for i,h in enumerate(hits))
    client = OpenAI(api_key=settings.api_key,base_url=settings.base_url)
    out = client.chat.completions.create(model=settings.llm_model,temperature=0.1,messages=[
        {"role":"system","content":"Python 공식 문서 기반 도우미다. 제공된 검색 문맥만 근거로 한국어 답변을 작성하고 관련 출처 번호를 표시하라. 근거가 없으면 모른다고 답하라."},
        {"role":"user","content":f"질문: {question}\n\n검색 문맥:\n{context}"}
    ])
    return out.choices[0].message.content or "답변을 생성하지 못했습니다."
