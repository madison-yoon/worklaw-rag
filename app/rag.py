import hashlib
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.operations import SearchIndexModel
from sentence_transformers import SentenceTransformer

from app.config import settings

_model: SentenceTransformer | None = None
_mongo_client: MongoClient | None = None
_collection: Collection | None = None


def chunks(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    size = settings.chunk_size if size is None else size
    overlap = settings.overlap if overlap is None else overlap
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("청크 크기는 양수이고 오버랩은 0 이상 청크 크기 미만이어야 합니다.")

    text = " ".join(text.split())
    result: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary
        part = text[start:end].strip()
        if part:
            result.append(part)
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return result


def embed(texts: list[str]) -> list[list[float]]:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    vectors = _model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vectors.tolist()


def store() -> Collection:
    global _mongo_client, _collection
    if not settings.mongodb_uri:
        raise RuntimeError("MONGODB_URI가 .env에 설정되지 않았습니다.")
    if _collection is None:
        _mongo_client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=settings.mongo_timeout_ms,
            appname="WorklawRAG",
        )
        _mongo_client.admin.command("ping")
        _collection = _mongo_client[settings.mongodb_database][settings.mongodb_collection]
    return _collection


def vector_index_definition(dimensions: int) -> dict:
    return {
        "fields": [
            {
                "type": "vector",
                "path": settings.vector_field,
                "numDimensions": dimensions,
                "similarity": "cosine",
            }
        ]
    }


def vector_index_status() -> dict | None:
    collection = store()
    return next(
        (item for item in collection.list_search_indexes() if item.get("name") == settings.vector_index),
        None,
    )


def ensure_vector_index(dimensions: int) -> dict:
    collection = store()
    existing = vector_index_status()
    if existing:
        if existing.get("type") not in (None, "vectorSearch"):
            raise RuntimeError(
                f"'{settings.vector_index}' 이름의 인덱스가 Vector Search 타입이 아닙니다."
            )
        return {
            "name": settings.vector_index,
            "created": False,
            "queryable": bool(existing.get("queryable")),
        }

    model = SearchIndexModel(
        definition=vector_index_definition(dimensions),
        name=settings.vector_index,
        type="vectorSearch",
    )
    collection.create_search_index(model=model)
    return {"name": settings.vector_index, "created": True, "queryable": False}


def wait_for_vector_index(timeout_seconds: int = 90) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status = vector_index_status()
        if status and status.get("queryable"):
            return True
        time.sleep(2)
    return False


def discover_urls() -> list[str]:
    response = requests.get(settings.sitemap, timeout=settings.timeout)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text for node in root.findall(".//s:loc", namespace) if node.text]

    if urls and urlparse(urls[0]).path.endswith(".xml"):
        nested_urls: list[str] = []
        for url in urls:
            nested_response = requests.get(url, timeout=settings.timeout)
            nested_response.raise_for_status()
            nested_root = ET.fromstring(nested_response.content)
            nested_urls.extend(
                node.text for node in nested_root.findall(".//s:loc", namespace) if node.text
            )
        urls = nested_urls

    return [
        url for url in urls
        if urlparse(url).scheme == "https"
        and urlparse(url).netloc == "docs.python.org"
    ][: settings.max_pages]


def read_page(url: str) -> dict | None:
    response = requests.get(
        url,
        timeout=settings.timeout,
        headers={"User-Agent": "WorklawRAG/1.0 (educational project)"},
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    main = soup.select_one("main") or soup.select_one("div.body") or soup.body
    if not main:
        return None

    for tag in main.select("script, style, nav, footer, .related, .sphinxsidebar, .breadcrumb"):
        tag.decompose()

    text = " ".join(main.stripped_strings)
    heading = soup.select_one("h1") or soup.title
    title = heading.get_text(" ", strip=True) if heading else url
    if len(text) < 120:
        return None
    return {"url": url, "title": title, "text": text}


def ingest() -> dict:
    urls = discover_urls()
    pending: list[dict] = []
    fetched = 0
    failed = 0

    for url in urls:
        try:
            page = read_page(url)
            if not page:
                continue
            fetched += 1
            for index, part in enumerate(chunks(page["text"])):
                document_id = hashlib.sha256(f"{url}#{index}".encode("utf-8")).hexdigest()
                pending.append({
                    "_id": document_id,
                    "url": url,
                    "title": page["title"],
                    "chunk": index,
                    "text": part,
                    "content_hash": hashlib.sha256(part.encode("utf-8")).hexdigest(),
                })
        except requests.RequestException:
            failed += 1

    if not pending:
        return {
            "pages_discovered": len(urls),
            "pages_fetched": fetched,
            "pages_failed": failed,
            "chunks_indexed": 0,
            "message": "저장할 문서 청크가 없습니다.",
        }

    collection = store()
    dimensions = len(embed([pending[0]["text"]])[0])
    indexed = 0

    # Collection에 실제 문서를 먼저 넣어야 Atlas Search 인덱스를 생성할 수 있다.
    for offset in range(0, len(pending), 64):
        batch = pending[offset: offset + 64]
        vectors = embed([item["text"] for item in batch])
        operations = [
            UpdateOne(
                {"_id": item["_id"]},
                {"$set": {**item, settings.vector_field: vector}},
                upsert=True,
            )
            for item, vector in zip(batch, vectors)
        ]
        result = collection.bulk_write(operations, ordered=False)
        indexed += result.upserted_count + result.modified_count

    index_status = ensure_vector_index(dimensions)
    index_ready = wait_for_vector_index()
    return {
        "pages_discovered": len(urls),
        "pages_fetched": fetched,
        "pages_failed": failed,
        "chunks_indexed": len(pending),
        "documents_inserted_or_updated": indexed,
        "vector_index": {**index_status, "queryable": index_ready},
    }


def vector_search_pipeline(question_vector: list[float], top_k: int) -> list[dict]:
    return [
        {
            "$vectorSearch": {
                "index": settings.vector_index,
                "path": settings.vector_field,
                "queryVector": question_vector,
                "numCandidates": max(top_k * 20, 100),
                "limit": top_k,
            }
        },
        {
            "$project": {
                "_id": 0,
                "url": 1,
                "title": 1,
                "chunk": 1,
                "text": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]


def retrieve(question: str, top_k: int | None = None) -> list[dict]:
    collection = store()
    count = collection.count_documents({})
    if count == 0:
        return []

    index_status = vector_index_status()
    if not index_status or not index_status.get("queryable"):
        raise RuntimeError(
            f"MongoDB Atlas Vector Search 인덱스 '{settings.vector_index}'가 아직 준비되지 않았습니다."
        )

    limit = min(top_k or settings.top_k, count)
    question_vector = embed([question])[0]
    return list(collection.aggregate(vector_search_pipeline(question_vector, limit)))


def answer(question: str, hits: list[dict]) -> str:
    if not settings.api_key:
        raise RuntimeError("OPENAI_API_KEY가 .env에 설정되지 않았습니다.")

    context = "\n\n".join(
        f"[{index + 1}] {hit['title']} | {hit['url']}\n{hit['text']}"
        for index, hit in enumerate(hits)
    )
    client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
    response = client.chat.completions.create(
        model=settings.llm_model,
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 Python 공식 문서에 근거해 답하는 기술 문서 도우미다. "
                    "반드시 제공된 검색 문맥을 근거로 한국어로 답하고, 근거가 된 출처 번호를 표시한다. "
                    "문맥에 근거가 없으면 추측하지 말고 문서에서 확인할 수 없다고 답한다."
                ),
            },
            {"role": "user", "content": f"질문: {question}\n\n검색 문맥:\n{context}"},
        ],
    )
    return response.choices[0].message.content or "답변을 생성하지 못했습니다."
