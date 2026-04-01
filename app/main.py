import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.api import news as news_router
from app.config import get_settings
from app.database import init_db

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
TEMPLATES  = Jinja2Templates(directory=str(BASE_DIR / "templates"))

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================================
# Timing Middleware
# ============================================================================
class TimingMiddleware(BaseHTTPMiddleware):
    """
    Measures total wall-clock time for each HTTP request and injects the
    result into the response body as ``total_time_taken`` (milliseconds).

    Behaviour
    ---------
    - Works only on JSON responses (``Content-Type: application/json``).
    - For non-JSON responses the header ``X-Process-Time-Ms`` is added
      instead so clients still have access to the timing data.
    - The timing field is always a ``float`` rounded to 2 decimal places.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()

        try:
            response: Response = await call_next(request)
        except Exception as exc:  # pylint: disable=broad-except
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "Unhandled exception during request %s %s after %.2f ms: %s",
                request.method,
                request.url.path,
                elapsed_ms,
                exc,
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error.",
                    "total_time_taken": elapsed_ms,
                },
            )

        end_time = time.perf_counter()
        elapsed_ms = round((end_time - start_time) * 1000, 2)

        content_type: str = response.headers.get("content-type", "")

        if "application/json" in content_type:
            # Read, modify, and re-encode the response body
            body_bytes = b""
            async for chunk in response.body_iterator:
                body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()

            try:
                payload: dict = json.loads(body_bytes)
                payload["total_time_taken"] = elapsed_ms
                new_body = json.dumps(payload).encode("utf-8")
            except (json.JSONDecodeError, AttributeError):
                # Not a JSON object (e.g. a bare list/string) – fall back
                logger.warning(
                    "TimingMiddleware: could not inject total_time_taken "
                    "into non-object JSON body for %s %s",
                    request.method,
                    request.url.path,
                )
                new_body = body_bytes

            logger.info(
                "%s %s → %d | %.2f ms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )

            headers = dict(response.headers)
            headers.pop("content-length", None)  # let Response recalculate the length

            return Response(
                content=new_body,
                status_code=response.status_code,
                headers=headers,
                media_type="application/json",
            )

        # Non-JSON response – add a timing header
        response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
        logger.info(
            "%s %s → %d | %.2f ms (non-JSON)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


# ============================================================================
# Lifespan – startup / shutdown hooks
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup logic before yielding control to the ASGI server."""
    logger.info("Application starting up …")
    try:
        from app.database import engine
        from app.models import Base
        
        init_db()   # sync – creates tables via pymysql from scratch

        from app.database import engine
        from sqlalchemy import text
        try:
            logger.info("Converting raw table charset from latin1 to utf8 to support native NewsAPI characters...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE news_articles CONVERT TO CHARACTER SET utf8 COLLATE utf8_unicode_ci;"))
            logger.info("Successfully upgraded table to UTF8!")
        except Exception as e:
            logger.error("Failed to upgrade table charset: %s", e)

        logger.info("Startup complete. API is ready to accept requests.")
    except Exception as exc:
        logger.critical(
            "Startup failed – could not initialise database: %s", exc, exc_info=True
        )
        raise

    yield  # Application runs here

    logger.info("Application shutting down …")


# ============================================================================
# FastAPI application
# ============================================================================
app = FastAPI(
    title="Jarvis Invest – News API",
    description=(
        "Fetches top headlines from NewsAPI.org every minute via a Celery beat task "
        "and stores them in MySQL. Provides a REST endpoint to query stored articles."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Static files ─────────────────────────────────────────────────────────────
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

# ── Middleware (order matters: added last → executed first) ──────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TimingMiddleware)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(news_router.router)


# ── Dashboard UI ─────────────────────────────────────────────────────────────
@app.get("/", tags=["UI"], include_in_schema=False)
async def dashboard(request: Request):
    """Serve the Tailwind CSS news dashboard."""
    return TEMPLATES.TemplateResponse("index.html", {"request": request})


# ── Health-check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"], summary="Health check")
async def health_check() -> dict:
    """Returns a simple alive signal."""
    return {"status": "ok", "service": "Jarvis Invest News API"}
