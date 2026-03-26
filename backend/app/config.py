"""Application settings loaded from environment variables and .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralised configuration — values come from env vars or .env file."""

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/o2c"
    openrouter_api_key: str = ""
    cors_origins: str = "*"
    llm_rate_limit: int = 10  # max LLM calls per minute per session
    pool_min_size: int = 5
    pool_max_size: int = 20
    data_dir: str = "./sap-o2c-data"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()
