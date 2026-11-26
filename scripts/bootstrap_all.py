"""
One-command full data bootstrap script for Chanakya Research Commons.
Executes:
  1. Database schema initialization
  2. Real external ingestion (OpenAlex + arXiv + Curated RSS)
  3. Reproducible synthetic university activity & ground truth generation (seed=42)
  4. Semantic embedding generation (all-MiniLM-L6-v2 or TF-IDF+SVD 384-dim fallback)
  5. Citation Graph PageRank computation (NetworkX)
  6. Trend spike & Spam account detection (persisting admin MonitoringAlerts)
  7. Data Warehouse ETL (Star Schema Parquet + DuckDB)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.database import SessionLocal, init_db
from backend.app.models.models import Paper
from data_warehouse.etl import build_warehouse
from ingestion.pipeline import export_silver_papers_parquet, ingest_arxiv, ingest_curated_rss, ingest_openalex
from ml.anomaly_detection.spam_detector import detect_spam_accounts
from ml.embeddings.embedder import get_embedder
from ml.search.search_engine import compute_and_store_pagerank
from ml.trend_detection.trends import compute_trending_and_spikes, persist_spike_alerts
from scripts.generate_synthetic_data import generate_all_synthetic_data


def build_paper_embeddings(db) -> dict:
    papers = db.query(Paper).all()
    texts = [f"{p.title}. {p.abstract or ''} {' '.join(p.topics or [])}" for p in papers]
    embedder = get_embedder()
    backend = embedder.fit_corpus(texts)
    vecs = embedder.encode(texts)
    for p, vec in zip(papers, vecs):
        p.embedding = [round(float(x), 5) for x in vec]
    db.commit()
    return {"papers_embedded": len(papers), "embedder_backend": backend}


def main() -> None:
    print("=== [1/7] Initializing database schema ===")
    init_db()
    db = SessionLocal()
    try:
        existing_real = db.query(Paper).filter(Paper.is_synthetic == False).count()
        if existing_real < 200:
            print("=== [2/7] Running real external ingestion (OpenAlex + arXiv + RSS) ===")
            r_oa = ingest_openalex(db, per_query=35)
            print("OpenAlex:", json.dumps(r_oa))
            r_ax = ingest_arxiv(db, per_query=18)
            print("arXiv:", json.dumps(r_ax))
            r_rss = ingest_curated_rss(db, max_per_feed=10)
            print("RSS:", json.dumps(r_rss))
        else:
            print(f"=== [2/7] Skipping external ingestion ({existing_real} real papers already present) ===")

        print("=== [3/7] Generating synthetic university activity & planted ground truth (seed=42) ===")
        syn_summary = generate_all_synthetic_data(db)
        print("Dataset Summary:", json.dumps(syn_summary, indent=2))

        print("=== [4/7] Computing 384-dim semantic embeddings for all papers ===")
        emb_info = build_paper_embeddings(db)
        print("Embeddings:", json.dumps(emb_info))

        print("=== [5/7] Computing Citation Graph PageRank (NetworkX) ===")
        pr_count = compute_and_store_pagerank(db)
        print(f"PageRank updated for {pr_count} papers.")
        export_silver_papers_parquet(db)

        print("=== [6/7] Running Trend Spike & Spam Anomaly Detection (F7) ===")
        trend_res = compute_trending_and_spikes(db)
        new_spike_alerts = persist_spike_alerts(db, trend_res["topic_spikes"])
        spam_res = detect_spam_accounts(db, persist_alerts=True)
        print(f"Detected {len(trend_res['topic_spikes'])} topic spikes ({new_spike_alerts} alerts saved) and {spam_res['flagged_count']} suspicious accounts.")

        print("=== [7/7] Building Star Schema Data Warehouse (Parquet + DuckDB) ===")
        wh_counts = build_warehouse(db)
        print("Warehouse Star Schema Table Counts:", json.dumps(wh_counts, indent=2))
        print("=== BOOTSTRAP COMPLETE ===")
    finally:
        db.close()


if __name__ == "__main__":
    main()
