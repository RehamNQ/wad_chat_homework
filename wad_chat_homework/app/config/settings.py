from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "wad_chat_homework"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    secret_key: str = Field(..., alias="SECRET_KEY")
    session_secret_key: str = Field(..., alias="SESSION_SECRET_KEY")
    cookie_secure: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/wad_chat_homework"
    redis_url: str = "redis://127.0.0.1:6379/0"

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    github_client_id: str = ""
    github_client_secret: str = ""

    model_path: str = "/home/tharaa/Desktop/Riham/qwer.gguf"
    llm_ctx_size: int = 1024
    llm_threads: int = 4
    llm_max_tokens: int = 256
    llm_temperature: float = 0.2
    llm_preload_on_startup: bool = True
    allow_dev_llm_fallback: bool = False

    @property
    def github_enabled(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
