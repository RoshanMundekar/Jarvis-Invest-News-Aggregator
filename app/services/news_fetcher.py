import logging
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import NewsArticle

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class NewsAPIError(Exception):
    """Raised when the NewsAPI returns a non-200 status or an error payload."""


class NewsAPIKeyMissing(NewsAPIError):
    """Raised when NEWS_API_KEY is not configured."""


# ---------------------------------------------------------------------------
# Fetch  (async – httpx)
# ---------------------------------------------------------------------------
async def fetch_top_headlines(date_str: str | None = None) -> list[dict[str, Any]]:
    """
    Call the NewsAPI /top-headlines endpoint and return a list of raw
    article dicts. If date_str (YYYY-MM-DD) is provided, fetches historical news for that date.

    Raises
    ------
    NewsAPIKeyMissing
        When the API key is not set in the environment.
    NewsAPIError
        On any HTTP error or unexpected API response.
    """
    if not settings.news_api_key:
        logger.error("NEWS_API_KEY is not configured – cannot fetch news.")
        raise NewsAPIKeyMissing(
            "NEWS_API_KEY is empty. Set it in your .env file."
        )

    url = f"{settings.news_api_base_url}/everything"
    params = {
        "q":        settings.news_api_query,
        "sortBy":   settings.news_api_sort_by,
        "apiKey":   settings.news_api_key,
        "pageSize": 100,
    }
    
    if date_str:
        params["from"] = date_str
        params["to"] = date_str

    logger.info(
        "Fetching everything from NewsAPI (q=%s, sortBy=%s) …",
        settings.news_api_query,
        settings.news_api_sort_by,
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.error("NewsAPI request timed out: %s", exc)
        raise NewsAPIError(f"Request timed out: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        logger.error(
            "NewsAPI returned HTTP %s: %s",
            exc.response.status_code,
            exc.response.text[:300],
        )
        raise NewsAPIError(
            f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Network error while contacting NewsAPI: %s", exc)
        raise NewsAPIError(f"Network error: {exc}") from exc

    payload = response.json()

    if payload.get("status") != "ok":
        msg = payload.get("message", "Unknown error from NewsAPI")
        logger.error("NewsAPI responded with status != ok: %s", msg)
        raise NewsAPIError(msg)

    articles: list[dict[str, Any]] = payload.get("articles", [])
    logger.info("NewsAPI returned %d article(s).", len(articles))
    return articles


# ---------------------------------------------------------------------------
# Persist  (sync – pymysql via SQLAlchemy)
# ---------------------------------------------------------------------------
def save_articles_to_db(
    articles: list[dict[str, Any]],
    db: Session,
) -> int:
    """
    Bulk-insert articles into the news_articles table.
    Articles whose URL already exists in the DB are silently skipped.

    Parameters
    ----------
    articles:
        List of raw article dicts from NewsAPI.
    db:
        An active SQLAlchemy Session (sync).

    Returns
    -------
    int
        Number of new rows actually inserted.
    """
    if not articles:
        logger.warning("save_articles_to_db called with an empty list – nothing to do.")
        return 0

    inserted = 0
    skipped_missing_url = 0

    for raw in articles:
        url: str | None = raw.get("url")
        if not url or url == "https://removed.com":
            skipped_missing_url += 1
            continue

        # Skip if URL already exists
        exists = db.query(NewsArticle).filter_by(url=url).first()
        if exists:
            continue

        # Parse publishedAt
        raw_published = raw.get("publishedAt") or ""
        try:
            published_at = datetime.fromisoformat(
                raw_published.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except ValueError:
            logger.warning(
                "Could not parse publishedAt=%r for url=%s – using now().",
                raw_published,
                url,
            )
            published_at = datetime.utcnow()

        def _safe_mysql_str(text: str | None, max_chars: int = 65000) -> str | None:
            if not text:
                return None
            # Strip 4-byte emojis mapping to PyMySQL's strict 3-byte utf8 limit
            cleaned = "".join(c for c in text if len(c.encode('utf-8')) <= 3)
            return cleaned[:max_chars]

        safe_source  = _safe_mysql_str((raw.get("source") or {}).get("name") or "Unknown", 255)
        safe_author  = _safe_mysql_str(raw.get("author") or "", 65000)
        safe_title   = _safe_mysql_str(raw.get("title") or "", 65000)
        safe_desc    = _safe_mysql_str(raw.get("description") or "", 65000)
        safe_content = _safe_mysql_str(raw.get("content") or "", 65000)
        safe_url     = url[:255]

        article = NewsArticle(
            source_name  = safe_source,
            author       = safe_author,
            title        = safe_title,
            description  = safe_desc,
            url          = safe_url,
            url_to_image = raw.get("urlToImage") or None,
            published_at = published_at,
            content      = safe_content,
        )
        db.add(article)
        inserted += 1

    if skipped_missing_url:
        logger.warning(
            "Skipped %d article(s) with missing / removed URLs.",
            skipped_missing_url,
        )

    try:
        db.commit()
        logger.info(
            "Inserted %d new article(s) out of %d processed.",
            inserted,
            len(articles),
        )
    except Exception as exc:
        db.rollback()
        logger.error("Database error while saving articles: %s", exc, exc_info=True)
        raise

    return inserted
