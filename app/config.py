import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    base_url: str | None = os.getenv("OPENAI_BASE_URL") or None
    llm_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    sitemap: str = os.getenv("DOCS_SITEMAP_URL", "https://docs.python.org/sitemap.xml")
    max_pages: int = int(os.getenv("MAX_PAGES", "100"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "900"))
    overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    top_k: int = int(os.getenv("TOP_K", "5"))
    mongodb_uri: str = os.getenv("MONGODB_URI", "").strip()
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "worklaw_rag")
    mongodb_collection: str = os.getenv("MONGODB_COLLECTION", "documents")
    vector_index: str = os.getenv("MONGODB_VECTOR_INDEX", "vector_index")
    vector_field: str = os.getenv("MONGODB_VECTOR_FIELD", "embedding")
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    timeout: int = int(os.getenv("REQUEST_TIMEOUT", "20"))
    mongo_timeout_ms: int = int(os.getenv("MONGODB_TIMEOUT_MS", "10000"))


settings = Settings()
