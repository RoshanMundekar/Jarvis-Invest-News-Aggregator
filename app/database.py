import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Engine  (sync – pymysql)
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,     # test connection health before use
    pool_size=10,
    max_overflow=20,
    echo=False,             # set True to log raw SQL queries
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency – yields a DB session and closes it after the request
# ---------------------------------------------------------------------------
def get_db():
    """Yield a SQLAlchemy Session; roll back on error; always close."""
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Call once on startup to create all tables
# ---------------------------------------------------------------------------
def init_db() -> None:
    """Create all tables defined via SQLAlchemy models (idempotent)."""
    logger.info("Initialising database – creating tables if they do not exist …")
    try:
        # Import models so their metadata is registered with Base
        from app import models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        logger.info("Database initialisation complete.")
    except Exception as exc:
        logger.error("Failed to initialise the database: %s", exc, exc_info=True)
        raise
