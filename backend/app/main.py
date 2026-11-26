"""Main FastAPI entry point for Chanakya Research Commons."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.auth_users import router as auth_users_router
from backend.app.api.intelligence import router as intelligence_router
from backend.app.api.library import router as library_router
from backend.app.api.posts import router as posts_router
from backend.app.core.config import settings
from backend.app.core.database import init_db
from ingestion.scheduler import start_scheduler, stop_scheduler
from ml.embeddings.embedder import preload_embedder_async

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("chanakya_commons")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.validate_production_security()
    init_db()
    if settings.APP_ENV != "test":
        preload_embedder_async()
        if settings.ENABLE_SCHEDULER:
            start_scheduler()
    logger.info(
        "Chanakya Research Commons API started (env=%s, scheduler=%s)",
        settings.APP_ENV,
        settings.ENABLE_SCHEDULER and settings.APP_ENV != "test",
    )
    yield
    if settings.APP_ENV != "test" and settings.ENABLE_SCHEDULER:
        stop_scheduler()


app = FastAPI(
    title="Chanakya Research Commons API",
    description=(
        "University-wide research collaboration, data warehousing, and intelligent discovery platform "
        "(Subsystems F1-F9) for Chanakya University School of Engineering."
    ),
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    detail = "Internal server error" if settings.is_production else str(exc)
    return JSONResponse(status_code=500, content={"detail": detail})

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

app.include_router(auth_users_router)
app.include_router(posts_router)
app.include_router(library_router)
app.include_router(intelligence_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "database_backend": "postgresql" if settings.is_postgres else "sqlite",
    }
