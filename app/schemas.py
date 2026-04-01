
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, HttpUrl


# ---------------------------------------------------------------------------
# Individual article (outbound)
# ---------------------------------------------------------------------------
class NewsArticleSchema(BaseModel):
    """Schema returned to the API consumer."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_name: str
    author: str | None
    title: str
    description: str | None
    url: str
    url_to_image: str | None
    published_at: datetime
    content: str | None
    fetched_at: datetime


# ---------------------------------------------------------------------------
# List response wrapper (includes timing key injected by middleware)
# ---------------------------------------------------------------------------
class NewsListResponse(BaseModel):
    """Wrapper returned by GET /news."""

    date: str
    total_results: int
    articles: list[NewsArticleSchema]
    # NOTE: `total_time_taken` is NOT declared here –
    # it is injected into the raw JSON body by TimingMiddleware after serialisation.

# ---------------------------------------------------------------------------
# Paginated list response wrapper
# ---------------------------------------------------------------------------
class PaginatedNewsResponse(BaseModel):
    """Wrapper returned by GET /news/all for the data table."""
    total_count: int
    skip: int
    limit: int
    articles: list[NewsArticleSchema]
