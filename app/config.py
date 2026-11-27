from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4.1-mini"
    embedding_dimensions: int = 1536
    chunk_size: int = 500
    chunk_overlap: int = 80
    embedding_batch_size: int = 100
    retrieval_top_k: int = 5
    vector_num_candidates_multiplier: int = 10

    momo_api_base_url: str = "http://localhost:8111"

    # MongoDB Atlas Vector Search
    mongodb_uri: str = ""
    mongodb_database: str = "worklaw_db"
    mongodb_collection: str = "law_chunks"
    mongodb_vector_index: str = "vector_index"
    mongodb_vector_path: str = "embedding"
    mongodb_server_selection_timeout_ms: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


settings = Settings()
