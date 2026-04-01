import asyncio
import logging

from celery import Task
from celery.utils.log import get_task_logger

from app.celery_app.worker import celery_app
from app.database import SessionLocal, init_db
from app.services.news_fetcher import (
    NewsAPIError,
    NewsAPIKeyMissing,
    fetch_top_headlines,
    save_articles_to_db,
)

logger = get_task_logger(__name__)


# ---------------------------------------------------------------------------
# Core implementation
# ---------------------------------------------------------------------------
def _fetch_and_store() -> dict:
    """Fetch headlines (async) then persist to MySQL (sync)."""
    # fetch_top_headlines is async – bridge with asyncio.run
    articles = asyncio.run(fetch_top_headlines())

    with SessionLocal() as session:
        inserted = save_articles_to_db(articles, session)

    return {"fetched": len(articles), "inserted": inserted}


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------
@celery_app.task(
    name="app.celery_app.tasks.fetch_news_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def fetch_news_task(self: Task) -> dict:
    """
    Periodic task: fetch top headlines and persist to MySQL.

    Retry policy
    ------------
    - NewsAPIError          → retry up to 3× with 30 s delay
    - NewsAPIKeyMissing     → log ERROR, no retry (config issue)
    - Unexpected exceptions → log ERROR, no retry
    """
    logger.info(
        "fetch_news_task starting (attempt %d/%d) …",
        self.request.retries + 1,
        self.max_retries + 1,
    )

    try:
        result = _fetch_and_store()
        logger.info(
            "fetch_news_task succeeded: fetched=%d, inserted=%d",
            result["fetched"],
            result["inserted"],
        )
        return result

    except NewsAPIKeyMissing as exc:
        logger.error(
            "NewsAPI key missing – task will NOT be retried. "
            "Set NEWS_API_KEY in .env. Error: %s", exc,
        )
        return {"error": str(exc), "retried": False}

    except NewsAPIError as exc:
        logger.warning(
            "Transient NewsAPI error (attempt %d): %s – will retry.",
            self.request.retries + 1, exc,
        )
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(
                "fetch_news_task failed after %d retries: %s",
                self.max_retries, exc,
            )
            return {"error": str(exc), "retried": True}

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(
            "Unexpected error in fetch_news_task: %s", exc, exc_info=True
        )
        return {"error": str(exc), "retried": False}
