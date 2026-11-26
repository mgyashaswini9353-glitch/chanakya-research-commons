"""Scheduled incremental batch ingestion using APScheduler (F4) with multi-instance lock safety."""
from __future__ import annotations

import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.models import Paper
from data_warehouse.etl import build_warehouse
from ingestion.pipeline import ingest_arxiv, ingest_curated_rss, ingest_openalex
from ml.embeddings.embedder import get_embedder
from ml.search.search_engine import compute_and_store_pagerank

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None
_local_lock = threading.Lock()
PG_ADVISORY_LOCK_KEY = 7842109


def _try_acquire_db_lock(db) -> bool:
    """Acquire a non-blocking PostgreSQL advisory lock so concurrent replicas cannot overlap jobs."""
    if not settings.is_postgres:
        return True
    try:
        return bool(db.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": PG_ADVISORY_LOCK_KEY}).scalar())
    except Exception as exc:
        logger.warning("Could not acquire PostgreSQL advisory lock: %s", exc)
        return False


def _release_db_lock(db) -> None:
    if not settings.is_postgres:
        return
    try:
        db.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": PG_ADVISORY_LOCK_KEY})
    except Exception:
        pass


def run_scheduled_refresh() -> bool:
    """Execute one incremental ingestion + embedding + PageRank + warehouse cycle safely."""
    if not _local_lock.acquire(blocking=False):
        logger.info("Skipping scheduled refresh: another refresh is already running in this process.")
        return False

    db = SessionLocal()
    acquired_pg = False
    try:
        acquired_pg = _try_acquire_db_lock(db)
        if not acquired_pg:
            logger.info("Skipping scheduled refresh: another backend instance holds the advisory lock.")
            return False

        logger.info("Running scheduled incremental external ingestion refresh...")
        ingest_openalex(db, per_query=10)
        ingest_arxiv(db, per_query=8)
        ingest_curated_rss(db, max_per_feed=8)

        new_papers = db.query(Paper).filter(Paper.embedding.is_(None)).all()
        if new_papers:
            embedder = get_embedder()
            texts = [f"{p.title}. {p.abstract or ''} {' '.join(p.topics or [])}" for p in new_papers]
            vecs = embedder.encode(texts)
            for p, v in zip(new_papers, vecs):
                p.embedding = [round(float(x), 5) for x in v]
            db.commit()

        compute_and_store_pagerank(db)
        build_warehouse(db)
        logger.info("Scheduled incremental refresh completed (newly_embedded=%d).", len(new_papers))
        return True
    except Exception as exc:
        logger.error("Scheduled refresh error: %s", exc)
        return False
    finally:
        if acquired_pg:
            _release_db_lock(db)
        db.close()
        _local_lock.release()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.add_job(
            run_scheduled_refresh,
            "interval",
            hours=12,
            id="incremental_ingestion_job",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        _scheduler.start()
        logger.info("APScheduler started (12h incremental refresh interval, max_instances=1, pg_advisory_lock enabled).")
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
