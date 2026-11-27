from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    mongodb_uri: str = ""
    mongodb_database: str = "momo_rag"
    mongodb_collection: str = "review_chunks"
    mongodb_vector_index: str = "review_vector_index"
    mongodb_vector_path: str = "embedding"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


settings = Settings()
