"""Generate crisp publication-quality PNG architectural & schema diagrams in documentation/diagrams/."""
from __future__ import annotations

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

DIAG_DIR = Path(__file__).resolve().parents[1] / "documentation" / "diagrams"
DIAG_DIR.mkdir(parents=True, exist_ok=True)


def _box(ax, x, y, w, h, title, body="", fc="#f8fafc", ec="#0f2342", title_color="#0f2342", lw=1.6, fontsize=8.5):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        facecolor=fc, edgecolor=ec, linewidth=lw,
    )
    ax.add_patch(patch)
    if body:
        ax.text(x + w / 2, y + h - 0.035, title, ha="center", va="top", fontsize=fontsize + 0.5, fontweight="bold", color=title_color)
        ax.text(x + w / 2, y + h / 2 - 0.02, body, ha="center", va="center", fontsize=fontsize - 0.8, color="#334155")
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=fontsize, fontweight="bold", color=title_color)


def _arrow(ax, x1, y1, x2, y2, color="#475569"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", color=color, lw=1.6))


def draw_system_architecture():
    fig, ax = plt.subplots(figsize=(12, 7), dpi=160)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.96, "Chanakya Research Commons — End-to-End System Architecture", ha="center", va="top", fontsize=14, fontweight="bold", color="#0f2342")

    # Presentation Layer
    _box(ax, 0.05, 0.78, 0.90, 0.13, "Presentation Layer (React 18 + TypeScript + Vite + Tailwind CSS + Recharts)",
         "Unified 4-Panel Search (F5)  |  University Library & Collections (F3)  |  Discussions & Feeds (F2)  |  Recommendations (F6)\nTrending & Spike Monitor (F7)  |  Grounded RAG Assistant (F8)  |  Admin Institutional Analytics & OLAP Drill-Down (F9)",
         fc="#eff6ff", ec="#1e3a5f")

    # API Layer
    _box(ax, 0.05, 0.56, 0.90, 0.14, "Application & REST API Layer (FastAPI + Pydantic v2 + JWT Auth + RBAC + APScheduler)",
         "/api/auth & /api/users (F1)   |   /api/posts (F2)   |   /api/papers & /api/library (F3)   |   /api/search/unified (F5)\n/api/recommendations (F6)   |   /api/trends & /api/admin (F7)   |   /api/assistant/ask (F8)   |   /api/analytics (F9)",
         fc="#f0fdfa", ec="#0d9488")

    # Intelligent Services Layer
    _box(ax, 0.05, 0.30, 0.28, 0.19, "Search & Deduplication\n(F5 Engine)",
         "BM25/TF-IDF + pgvector Cosine\nReciprocal Rank Fusion (RRF)\nNetworkX Citation PageRank\nMinHash + LSH (datasketch)\nAuthor Entity Resolution",
         fc="#ffffff", ec="#0284c7")
    _box(ax, 0.36, 0.30, 0.28, 0.19, "Recommendations & RAG\n(F6 & F8 Engines)",
         "Content-Based + Collaborative\nFP-Growth (mlxtend)\nCold-Start & Communities\nGrounded Passage Retrieval\nOllama / Extractive Fallback",
         fc="#ffffff", ec="#0d9488")
    _box(ax, 0.67, 0.30, 0.28, 0.19, "Trends, Spam & Ingestion\n(F4 & F7 Engines)",
         "OpenAlex + arXiv + RSS ELT\nSliding-Window Z-Score Spikes\nIsolation Forest Spam Detection\nBehavioral Risk Scoring\nIncremental Job Logging",
         fc="#ffffff", ec="#d97706")

    # Data & Warehouse Layer
    _box(ax, 0.05, 0.06, 0.28, 0.17, "Operational OLTP DB\n(PostgreSQL + pgvector)",
         "Users, Follows, Posts, Comments\nPapers, Citations, Embeddings\nSaved Papers, Collections\nActivity Events, Alerts, Jobs",
         fc="#0f2342", ec="#0f2342", title_color="#ffffff")
    ax.texts[-1].set_color("#cbd5e1")

    _box(ax, 0.36, 0.06, 0.28, 0.17, "Bronze / Silver Data Lake\n(Local FS + MinIO)",
         "data/raw/{openalex,arxiv,rss}\nUnchanged API JSON Payloads\ndata/processed/papers_silver\ndata/ground_truth/*.json",
         fc="#1e3a5f", ec="#1e3a5f", title_color="#ffffff")
    ax.texts[-1].set_color("#cbd5e1")

    _box(ax, 0.67, 0.06, 0.28, 0.17, "Gold Analytical Warehouse\n(DuckDB + Parquet Star Schema)",
         "5 Dims: Date, Dept, Member,\nTopic, Paper  |  4 Fact Tables\nOLAP Drill-Down Queries\nHierarchical Topic Clustering",
         fc="#0f766e", ec="#0f766e", title_color="#ffffff")
    ax.texts[-1].set_color("#ccfbf1")

    # Arrows
    _arrow(ax, 0.50, 0.78, 0.50, 0.70)
    _arrow(ax, 0.50, 0.70, 0.50, 0.78)
    for cx in (0.19, 0.50, 0.81):
        _arrow(ax, cx, 0.56, cx, 0.49)
        _arrow(ax, cx, 0.30, cx, 0.23)

    fig.tight_layout()
    fig.savefig(DIAG_DIR / "system_architecture.png")
    plt.close(fig)


def draw_star_schema():
    fig, ax = plt.subplots(figsize=(12, 7.2), dpi=160)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.96, "Data Warehouse Kimball Star Schema (DuckDB over Parquet)", ha="center", va="top", fontsize=14, fontweight="bold", color="#0f2342")

    # Center Fact Tables
    _box(ax, 0.35, 0.51, 0.30, 0.20, "FactResearchActivity (Grain: 1 Event)",
         "activity_id (PK)\ndate_key (FK) | member_key (FK)\ndepartment_key (FK) | topic_key (FK)\npaper_key (FK) | post_key (FK)\nevent_type | is_synthetic | timestamp",
         fc="#0f2342", ec="#0f2342", title_color="#ffffff", fontsize=8)
    ax.texts[-1].set_color("#e2e8f0")

    _box(ax, 0.35, 0.26, 0.145, 0.18, "FactPaperSaves",
         "save_id (PK)\ndate_key, member_key\ndept_key, paper_key\ntopic_key, has_notes",
         fc="#1e3a5f", ec="#1e3a5f", title_color="#ffffff", fontsize=7.5)
    ax.texts[-1].set_color("#e2e8f0")

    _box(ax, 0.505, 0.26, 0.145, 0.18, "FactSearchEvents",
         "search_id (PK)\ndate_key, member_key\ndept_key, topic_key\nquery_text, mode",
         fc="#1e3a5f", ec="#1e3a5f", title_color="#ffffff", fontsize=7.5)
    ax.texts[-1].set_color("#e2e8f0")

    _box(ax, 0.38, 0.05, 0.24, 0.15, "FactPostEngagement",
         "post_key (PK) | date_key | member_key\ndept_key | topic_key | paper_key\nupvote_count | comment_count",
         fc="#1e3a5f", ec="#1e3a5f", title_color="#ffffff", fontsize=7.5)
    ax.texts[-1].set_color("#e2e8f0")

    # 5 Surrounding Dimensions
    _box(ax, 0.03, 0.72, 0.25, 0.18, "DimDate",
         "date_key (PK: YYYYMMDD)\nfull_date, year, quarter\nmonth, month_name\nyear_month, iso_week, dow",
         fc="#f0fdfa", ec="#0d9488", fontsize=8)
    _box(ax, 0.72, 0.72, 0.25, 0.18, "DimDepartment",
         "department_key (PK)\ndepartment_code (CSAI..REM)\ndepartment_name\nfaculty_head",
         fc="#f0fdfa", ec="#0d9488", fontsize=8)
    _box(ax, 0.03, 0.42, 0.25, 0.20, "DimMember",
         "member_key (PK)\nusername, full_name, role\ndepartment_key\nis_flagged_spam, is_synthetic\ncreated_date_key",
         fc="#f0fdfa", ec="#0d9488", fontsize=8)
    _box(ax, 0.72, 0.42, 0.25, 0.20, "DimPaper",
         "paper_key (PK)\ntitle, primary_source\npublication_year, doi, arxiv_id\nprimary_topic, citation_count\npagerank_score, save_count",
         fc="#f0fdfa", ec="#0d9488", fontsize=8)
    _box(ax, 0.03, 0.12, 0.25, 0.17, "DimTopic",
         "topic_key (PK)\ntopic_name\n(normalized research tag)",
         fc="#f0fdfa", ec="#0d9488", fontsize=8)

    # Connector lines
    _arrow(ax, 0.28, 0.78, 0.35, 0.66, "#0d9488")
    _arrow(ax, 0.72, 0.78, 0.65, 0.66, "#0d9488")
    _arrow(ax, 0.28, 0.54, 0.35, 0.58, "#0d9488")
    _arrow(ax, 0.72, 0.54, 0.65, 0.58, "#0d9488")
    _arrow(ax, 0.28, 0.22, 0.35, 0.34, "#0d9488")
    _arrow(ax, 0.28, 0.18, 0.38, 0.13, "#0d9488")
    _arrow(ax, 0.72, 0.45, 0.65, 0.36, "#0d9488")

    fig.tight_layout()
    fig.savefig(DIAG_DIR / "warehouse_star_schema.png")
    plt.close(fig)


def draw_ingestion_pipeline():
    fig, ax = plt.subplots(figsize=(12, 4.8), dpi=160)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.94, "F4 External Data Ingestion & Medallion Lakehouse ELT Pipeline", ha="center", va="top", fontsize=13.5, fontweight="bold", color="#0f2342")

    _box(ax, 0.02, 0.22, 0.18, 0.60, "Open Sources",
         "OpenAlex API\n(works + citations)\n\narXiv Atom API\n(preprints)\n\nCurated RSS\n(MIT AI, arXiv)",
         fc="#eff6ff", ec="#1e3a5f", fontsize=8.5)
    _box(ax, 0.24, 0.22, 0.18, 0.60, "Bronze (Raw Lake)",
         "data/raw/<source>/\nTimestamped JSON\nUnchanged Payloads\n\nOptional MinIO\nRaw Bucket Mirror",
         fc="#fef3c7", ec="#d97706", fontsize=8.5)
    _box(ax, 0.46, 0.22, 0.22, 0.60, "Silver (Transform & ER)",
         "Abstract Reconstruction\nDOI/arXiv Normalization\nMinHash LSH + Author ER\nSource List Merging\n384-d Embeddings + PageRank\npapers_silver.parquet",
         fc="#f0fdfa", ec="#0d9488", fontsize=8.5)
    _box(ax, 0.72, 0.22, 0.25, 0.60, "Gold (OLTP + OLAP)",
         "PostgreSQL + pgvector\n(Operational Serving)\n\nParquet Star Schema\n(5 Dims + 4 Facts)\n\nDuckDB OLAP Engine\n(F9 Dashboard & Drill-Down)",
         fc="#0f2342", ec="#0f2342", title_color="#ffffff", fontsize=8.5)
    ax.texts[-1].set_color("#e2e8f0")

    _arrow(ax, 0.20, 0.52, 0.24, 0.52)
    _arrow(ax, 0.42, 0.52, 0.46, 0.52)
    _arrow(ax, 0.68, 0.52, 0.72, 0.52)

    fig.tight_layout()
    fig.savefig(DIAG_DIR / "ingestion_elt_pipeline.png")
    plt.close(fig)


if __name__ == "__main__":
    draw_system_architecture()
    draw_star_schema()
    draw_ingestion_pipeline()
    print("Generated 3 PNG architecture/schema diagrams in", DIAG_DIR)
