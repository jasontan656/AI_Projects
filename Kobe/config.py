from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Project settings loaded from environment and `.env`.

    Mirrors Tech_Decisions.md §5.2 and BackendConstitution mandates.
    """

    mongodb_uri: str = Field(..., env="MONGODB_URI")
    redis_url: str = Field(..., env="REDIS_URL")
    rabbitmq_url: str = Field(..., env="RABBITMQ_URL")

    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")

    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    api_port: int = Field(default=8000, env="API_PORT")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")

    batch_size: int = Field(default=50, env="BATCH_SIZE")
    timeout: int = Field(default=30, env="TIMEOUT")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

