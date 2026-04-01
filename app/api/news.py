"""
app/api/news.py

API router for news-related endpoints.

Endpoint
--------
GET /news?date=YYYY-MM-DD
    Returns all news articles stored in the database for the given date.
    The `total_time_taken` field is injected into the response body by
    TimingMiddleware (see app/main.py) – it is not computed here.
"""

import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import NewsArticle
from app.schemas import NewsArticleSchema, NewsListResponse, PaginatedNewsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["News"])


@router.get(
    "",
    response_model=NewsListResponse,
    summary="Get news articles by date",
    description=(
        "Returns all news articles stored in the database. If "
        "`date` is provided, filters by that exact date. Otherwise, returns the 100 most recent."
    ),
)
async def get_news_by_date(
    date: str | None = Query(
        None,
        description="Optional date to filter articles (DD-MM-YYYY)",
        example="15-01-2025",
    ),
    db: Session = Depends(get_db),
) -> NewsListResponse:
    """
    Fetch articles from MySQL.

    Parameters
    ----------
    date:
        Optional target date in YYYY-MM-DD format.
    db:
        Injected sync DB session.

    Raises
    ------
    HTTPException 404:
        When no articles are found for the given criteria.
    HTTPException 500:
        On unexpected database errors.
    """
    logger.info("GET /news called with date=%s", date)

    try:
        query = db.query(NewsArticle)
        
        if date:
            try:
                parsed_date = datetime.strptime(date, "%d-%m-%Y")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Please use DD-MM-YYYY."
                )
                
            day_start = datetime(parsed_date.year, parsed_date.month, parsed_date.day, 0, 0, 0)
            day_end   = datetime(parsed_date.year, parsed_date.month, parsed_date.day, 23, 59, 59)
            query = query.filter(
                NewsArticle.published_at >= day_start,
                NewsArticle.published_at <= day_end,
            )
            
        articles = query.order_by(NewsArticle.published_at.desc()).limit(100).all()
    except Exception as exc:
        logger.error(
            "Database error while querying articles for date=%s: %s",
            date,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while fetching news articles.",
        ) from exc

    # ── On-demand Historical Fetch ──
    # If the user requested a specific date but our database has nothing,
    # reach out to NewsAPI on-the-fly to backfill those records.
    if not articles and date:
        logger.info("Local database empty for %s. Attempting on-demand fetch from NewsAPI …", date)
        try:
            # We already have parsed_date from earlier validation
            iso_date = parsed_date.strftime("%Y-%m-%d")
            new_raw_articles = await fetch_top_headlines(date_str=iso_date)
            if new_raw_articles:
                save_articles_to_db(new_raw_articles, db)
                # Re-query the database now that records exist
                articles = query.order_by(NewsArticle.published_at.desc()).limit(100).all()
            else:
                logger.info("NewsAPI returned 0 articles for %s.", iso_date)
        except Exception as exc:
            logger.error("On-demand fetch failed for %s: %s", date, exc)
            # Log but don't crash, let the 404 fall through

    if not articles:
        msg = f"No news articles found for date {date}." if date else "No news articles found in database."
        logger.warning(msg)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )

    logger.info("Returning %d article(s) for date=%s", len(articles), date)

    return NewsListResponse(
        date=str(date) if date else "Latest",
        total_results=len(articles),
        articles=[NewsArticleSchema.model_validate(a) for a in articles],
    )


from app.services.news_fetcher import fetch_top_headlines, save_articles_to_db

@router.post(
    "/fetch",
    summary="Manually trigger news fetch",
    description="Synchronously fetch news from NewsAPI and store it in the database.",
)
async def trigger_fetch(db: Session = Depends(get_db)):
    """Manually fetch news without waiting for Celery."""
    try:
        articles = await fetch_top_headlines()
        inserted = save_articles_to_db(articles, db)
        return {"status": "success", "fetched": len(articles), "inserted": inserted}
    except Exception as exc:
        logger.error("Manual fetch failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

@router.get(
    "/all",
    response_model=PaginatedNewsResponse,
    summary="Get paginated history",
    description="Returns all fetched news articles with pagination structure for tabular views.",
)
async def get_all_news_paginated(
    date: str | None = Query(None, description="Filter by exact date (DD-MM-YYYY)"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    db: Session = Depends(get_db),
) -> PaginatedNewsResponse:
    try:
        query = db.query(NewsArticle)
        
        if date:
            try:
                parsed_date = datetime.strptime(date, "%d-%m-%Y")
                day_start = datetime(parsed_date.year, parsed_date.month, parsed_date.day, 0, 0, 0)
                day_end   = datetime(parsed_date.year, parsed_date.month, parsed_date.day, 23, 59, 59)
                query = query.filter(
                    NewsArticle.published_at >= day_start,
                    NewsArticle.published_at <= day_end,
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Please use DD-MM-YYYY.")
                
        total_count = query.count()
        articles = query.order_by(NewsArticle.published_at.desc()).offset(skip).limit(limit).all()
        
        return PaginatedNewsResponse(
            total_count=total_count,
            skip=skip,
            limit=limit,
            articles=[NewsArticleSchema.model_validate(a) for a in articles]
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching paginated news: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve paginated news.")

