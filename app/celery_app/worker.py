"""
app/celery_app/worker.py

Creates the Celery application instance and configures:
  - Broker  : Redis
  - Backend : Redis (for task result storage)
  - Beat schedule : run fetch_news_task every 60 seconds
"""

import logging

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Celery application
# ---------------------------------------------------------------------------
celery_app = Celery(
    "jarvis_invest",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.celery_app.tasks"],  # eagerly import tasks module
)

# ---------------------------------------------------------------------------
# Celery configuration
# ---------------------------------------------------------------------------
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Prevent workers from prefetching too many tasks
    worker_prefetch_multiplier=1,
    # Task result expiry (1 hour)
    result_expires=3600,
)

# ---------------------------------------------------------------------------
# Periodic beat schedule – fetch news every 60 seconds
# ---------------------------------------------------------------------------
celery_app.conf.beat_schedule = {
    "fetch-news-every-minute": {
        "task": "app.celery_app.tasks.fetch_news_task",
        "schedule": 60.0,  # seconds
        "options": {"queue": "default"},
    },
}

logger.info(
    "Celery configured with broker=%s, beat_schedule=%s",
    settings.redis_url,
    list(celery_app.conf.beat_schedule.keys()),
)
