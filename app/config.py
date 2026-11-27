from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4.1-mini"
    embedding_dimensions: int = 1536
    chunk_size: int = 500
    chunk_overlap: int = 80
    chroma_persist_directory: str = "./chroma_db"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
