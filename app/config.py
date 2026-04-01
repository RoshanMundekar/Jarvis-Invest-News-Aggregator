"""
app/config.py
Application settings loaded from environment variables / .env file.
"""

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configurable values are read from the .env file (or environment)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # silently skip unknown keys (e.g. MYSQL_HOST, MYSQL_PORT …)
    )

    # ── NewsAPI ──────────────────────────────────────────────────────────────
    news_api_key: str = "2013d7ec84b244a595f660c64d746609"
    news_api_base_url: str = "https://newsapi.org/v2"
    news_api_query: str = "tesla"  # Use /everything?q=tesla
    news_api_sort_by: str = "publishedAt"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "mysql+pymysql://root:root@localhost:3306/jarvis_news?charset=utf8"

    # ── Redis / Celery ────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton)."""
    return Settings()


# ---------------------------------------------------------------------------
# Configure root logger once at import time so all modules share the same fmt
# ---------------------------------------------------------------------------
def configure_logging(level: str = "INFO") -> None:
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# Run immediately when the module is first imported
configure_logging(get_settings().log_level)
