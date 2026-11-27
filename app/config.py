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

    # 기존 MOMO Spring Boot API를 영화 메타데이터 원천으로 사용한다.
    momo_api_base_url: str = "http://localhost:8111"

    mongodb_uri: str = ""
    mongodb_database: str = "worklaw_db"
    mongodb_collection: str = "law_chunks"
    mongodb_vector_index: str = "vector_index"
    mongodb_vector_path: str = "embedding"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


settings = Settings()
