from __future__ import annotations

from pydantic_settings import BaseSettings


class TestConfig(BaseSettings):
    # 服务地址
    REDIS_URL: str = "redis://localhost:6379/1"
    MONGODB_URL: str = "mongodb://localhost:27017/test_TelegramCuration"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    CHROMADB_URL: str = "http://localhost:8001"
    FASTAPI_URL: str = "http://localhost:8000"

    # 测试配置
    RANDOM_SEED: int = 42
    TIMEOUT: int = 300
    MAX_WORKERS: int = 100
    RETRY_TIMES: int = 3

    # 大模型配置
    MOCK_LLM: bool = True
    LLM_RESPONSE_DELAY: float = 0.1
    OPENAI_API_KEY: str = "sk-test"  # 仅在 MOCK_LLM=False 时使用

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/test_run.log"

    class Config:
        env_prefix = "TEST_"
        env_file = ".env.test"

