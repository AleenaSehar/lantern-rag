from functools import lru_cache

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "groundwork"
    qdrant_url: AnyHttpUrl = AnyHttpUrl("http://localhost:6333")
    qdrant_api_key: str | None = None
    qdrant_collection: str = "groundwork_chunks"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384
    chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 75
    max_upload_bytes: int = 10 * 1024 * 1024
    upload_directory: str = "data/uploads"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
