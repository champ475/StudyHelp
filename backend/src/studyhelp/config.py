"""Twelve-factor config: everything comes from environment variables.

No secrets have defaults beyond the local-dev docker-compose values already
documented in `.env.example` (ARCHITECTURE.md — no real secrets committed).
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://studyhelp:studyhelp@localhost:5432/studyhelp"
    redis_url: str = "redis://localhost:6379/0"

    llm_provider: Literal["mock", "groq"] = "mock"
    groq_api_key: str | None = None
    groq_model: str | None = None

    dialogue_turn_budget: int = 4
    readability_max_grade: float = 5.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
