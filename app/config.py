"""Application configuration settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "K-Pop Concert Tracker"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./concerts.db"

    # Twitter API
    twitter_bearer_token: Optional[str] = None
    twitter_search_limit: int = 450  # requests per 15 minutes
    twitter_window_seconds: int = 900  # 15 minutes

    # Auto-refresh
    refresh_interval_minutes: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
