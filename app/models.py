# """
# app/models.py
# SQLAlchemy ORM models.
# """

# from datetime import datetime

# from sqlalchemy import DateTime, Integer, String, Text
# from sqlalchemy.orm import Mapped, mapped_column

# from app.database import Base


# class NewsArticle(Base):
#     """Represents a single news article fetched from NewsAPI."""

#     __tablename__ = "news_articles"

#     id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

#     source_name: Mapped[str] = mapped_column(String(255), nullable=False)
#     author: Mapped[str | None] = mapped_column(String(255), nullable=True)
#     title: Mapped[str] = mapped_column(String(3000), nullable=False)
#     description: Mapped[str | None] = mapped_column(Text, nullable=True)
#     url: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
#     url_to_image: Mapped[str | None] = mapped_column(Text, nullable=True)

#     # NewsAPI returns publishedAt as ISO-8601 string; we parse it to a datetime
#     published_at: Mapped[datetime] = mapped_column(
#         DateTime,
#         nullable=False,
#         index=True,
#     )

#     content: Mapped[str | None] = mapped_column(Text, nullable=True)

#     # Timestamp of when we persisted this record
#     fetched_at: Mapped[datetime] = mapped_column(
#         DateTime,
#         nullable=False,
#         default=datetime.utcnow,
#     )

#     def __repr__(self) -> str:  # pragma: no cover
#         return f"<NewsArticle id={self.id} title={self.title[:40]!r}>"



from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 🔥 CHANGE HERE
    title: Mapped[str] = mapped_column(Text, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # URLs can also be long sometimes
    # url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # url: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_to_image: Mapped[str | None] = mapped_column(Text, nullable=True)

    published_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )

    # content can be VERY large → keep Text (or LONGTEXT in DB)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<NewsArticle id={self.id} title={self.title[:40]!r}>"
