import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass(frozen=True)
class Settings:
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    base_url: str | None = os.getenv("OPENAI_BASE_URL") or None
    llm_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    sitemap: str = os.getenv("DOCS_SITEMAP_URL", "https://docs.python.org/3/sitemap.xml")
    max_pages: int = int(os.getenv("MAX_PAGES", "100"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "900"))
    overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    top_k: int = int(os.getenv("TOP_K", "5"))
    db_path: str = os.getenv("CHROMA_PATH", "./data/chroma")
    collection: str = os.getenv("CHROMA_COLLECTION", "python_docs")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    timeout: int = int(os.getenv("REQUEST_TIMEOUT", "20"))
settings = Settings()
