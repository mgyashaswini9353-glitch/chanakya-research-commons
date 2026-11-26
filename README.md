# Chanakya Research Commons

**University-Wide Research Collaboration, Data Warehousing, and Intelligent Discovery Platform**  
*Chanakya University, Bangalore — School of Engineering · V Semester, B.Tech. (2026–27)*  
*Summative Assessment: Mini-Project | Data Mining and Warehousing (DMW)*

---

## 1. Overview

**Chanakya Research Commons** unifies research discovery, campus collaboration, a shared university paper library, a medallion lakehouse + Kimball Star Schema data warehouse, and five empirically evaluated data mining and machine learning subsystems (**F1–F9**) into a single full-stack platform.

### Implemented Subsystems (F1–F9)
| ID | Subsystem | Implementation Highlights |
|---|---|---|
| **F1** | **User Accounts & Profiles** | Registration, Login/Logout, `bcrypt` hashing, JWT auth, RBAC (`student`, `faculty`, `researcher`, `admin`), department profiles, research interests & tags, publication links, member & topic following. |
| **F2** | **Posts & Discussions** | Create/edit/delete posts, attach papers from library or URLs, comments, nested replies, toggle upvotes, Personalized / Followed Members / Followed Topics / All feeds. |
| **F3** | **Research Library** | Save from search or add by **DOI / arXiv ID / URL** (live metadata resolution via OpenAlex & arXiv), personal collections, private notes, shared campus-wide Chanakya Library with save counts & duplicate prevention. |
| **F4** | **External Data Ingestion** | Real open scholarly API ingestion from **OpenAlex**, **arXiv**, and **curated RSS feeds** (MIT News AI, arXiv cs.DB, arXiv cs.LG). Bronze untouched raw JSON (`data/raw/`) → Silver Parquet (`data/processed/`) → Gold Star Schema Parquet (`data/parquet/`) + DuckDB. APScheduler 12h incremental refresh + job logging. |
| **F5** | **Unified 4-Panel Search** | Single search box returning **4 panels**: (1) External Research Papers, (2) Chanakya Library, (3) Researchers & Students, (4) Posts & Discussions. Supports **Keyword**, **Semantic (384-dim Vector)**, and **Hybrid (RRF + NetworkX Citation PageRank)** modes, with **MinHash + LSH (`datasketch`) + Author Entity Resolution** merging duplicates into one unified record with all sources listed. |
| **F6** | **Recommendation Engine** | Personalized paper recommendations (**Content-Based + User-Item Collaborative Filtering + Cold-Start**), researcher recommendations (**shared interests + NetworkX greedy modularity communities**), and **"Members who saved this also saved"** via **FP-Growth (`mlxtend`)** association rules. |
| **F7** | **Trends & Monitoring** | Sliding-window Z-score sudden topic spike detection (excluding spam accounts) and **Isolation Forest + behavioral risk** spam account detection with explainable admin alerts & moderation controls. |
| **F8** | **AI Research Assistant (RAG)** | Grounded natural-language Q&A over retrieved corpus passages with verifiable inline `[1]..[K]` citations, inspectable source passages, local **Ollama** integration, deterministic extractive synthesis fallback, and strict out-of-scope insufficient-evidence refusal. |
| **F9** | **Institutional Analytics** | Admin-only dashboard queried directly from **DuckDB over Star Schema Parquet** (5 dimensions, 4 fact tables): department comparisons, 6-month trends, cross-department collaboration, Ward hierarchical topic clustering, and interactive **4-level OLAP drill-down** (`University → Department → Topic → Member`). |

---

## 2. Project Structure

```text
DMW-project/
├── DMW-CourseProject (1).pdf          # Official specification (preserved unchanged)
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml                 # Local/Dev stack: PostgreSQL, MinIO, FastAPI Backend, React/Nginx Frontend
├── docker-compose.prod.yml            # Hardened Ubuntu Linux VPS production overlay (mandatory secrets, no public DB/MinIO ports)
├── Caddyfile.example                  # Portable Let's Encrypt HTTPS reverse-proxy template
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                    # FastAPI app, CORS, lifespan, APScheduler
│       ├── core/                      # config.py, database.py, security.py (JWT/bcrypt/RBAC)
│       ├── models/models.py           # 15 SQLAlchemy ORM tables
│       ├── schemas/schemas.py         # Pydantic v2 request/response models
│       └── api/                       # auth_users.py, posts.py, library.py, intelligence.py
├── frontend/
│   ├── Dockerfile & nginx.conf
│   ├── package.json & vite.config.ts & tailwind.config.js
│   └── src/
│       ├── context/AuthContext.tsx
│       ├── services/api.ts
│       ├── layouts/AppLayout.tsx
│       ├── components/PaperCard.tsx
│       └── pages/                     # All 19 functional pages (Landing -> Admin/Analytics/Settings)
├── database/
│   ├── schema.sql                     # Production PostgreSQL + pgvector + FTS GIN + HNSW index DDL
│   └── migrations/001_initial_schema.sql
├── data/
│   ├── raw/{openalex,arxiv,rss}/      # Bronze layer: original untouched external API JSON responses
│   ├── processed/                     # Silver layer: papers_silver.parquet & fitted SVD embedder
│   ├── parquet/                       # Gold Star Schema Parquet files (5 dims + 4 facts)
│   ├── synthetic/dataset_summary.json # Verified dataset counts
│   └── ground_truth/                  # duplicate_pairs.json, spam_accounts.json, topic_spikes.json, search_qrels.json, rag_eval_queries.json
├── ingestion/
│   ├── pipeline.py                    # OpenAlex, arXiv, Curated RSS ELT + DOI/arXiv live lookup
│   └── scheduler.py                   # APScheduler incremental batch refresh
├── data_warehouse/
│   ├── schemas/star_schema.sql        # DuckDB Star Schema DDL over Parquet
│   ├── sql/analytical_queries.sql     # 7 OLAP analytical SQL queries
│   ├── etl.py                         # Operational DB -> Parquet Star Schema -> DuckDB materializer
│   └── duckdb/chanakya_dw.duckdb      # Materialized DuckDB OLAP database
├── ml/
│   ├── embeddings/embedder.py         # SentenceTransformers (all-MiniLM-L6-v2) + 384-d TF-IDF+SVD fallback
│   ├── duplicate_detection/deduplicator.py # Exact DOI/arXiv + Author ER + MinHash LSH (datasketch)
│   ├── search/search_engine.py        # 4-panel Keyword/Semantic/Hybrid RRF + NetworkX PageRank
│   ├── recommendations/recommender.py # Content+CF, FP-Growth (mlxtend), Cold-Start, Communities
│   ├── trend_detection/trends.py      # Sliding-window Z-score spike detector
│   └── anomaly_detection/spam_detector.py # Isolation Forest + behavioral risk scorer
├── research_assistant/rag_engine.py   # Grounded RAG + Ollama / extractive fallback + sufficiency guardrail
├── analytics/warehouse_service.py     # DuckDB OLAP analytics, 4-level drill-down, Ward topic clustering
├── evaluation/
│   ├── run_evaluations.py             # Reproducible benchmark suite (JSON + CSV + Matplotlib charts)
│   └── results/                       # evaluation_summary.json, evaluation_tables.csv
├── tests/                             # Automated Pytest suites covering F1-F9, security & F7 trends (20/20 passing)
├── scripts/
│   ├── generate_synthetic_data.py     # Seed=42 university activity + planted ground truth generator
│   ├── bootstrap_all.py               # Single-command full data + embeddings + warehouse setup
│   ├── generate_diagrams.py           # PNG architecture/schema/pipeline diagram generator
│   ├── start_local.ps1                # One-command local Windows launcher
│   └── regenerate_all.ps1             # Re-run bootstrap, diagrams, evaluations, and pytest
└── documentation/
    ├── technical_report.md            # Complete university submission technical report
    ├── viva_preparation.md            # Viva Q&A & live demonstration script
    ├── api_documentation.md           # Full REST API reference
    ├── architecture/diagrams.md       # Mermaid ER, Star Schema, Architecture & ML workflows
    ├── diagrams/                      # Generated PNG charts & architecture diagrams
    └── screenshots/                   # Live running application screenshots
```

---

## 3. Verified Dataset Counts (Docker PostgreSQL + DuckDB, Seed = 42)

| Metric | Required Minimum | Actual Verified Count |
|---|---|---|
| Research Papers with Abstracts | ≥ 500 | **687** (**546 real external**: 389 OpenAlex + 127 arXiv + 30 RSS; plus 141 synthetic) |
| Chanakya University Library Papers | — | **224** papers saved across **686** member save records (`54` personal collections) |
| Citation Graph Edges | OpenAlex links | **1,950** directed citation edges (NetworkX PageRank) |
| University Members | ≥ 50 | **60** (54 regular across 4 roles + 6 planted spam accounts) |
| University Departments | ≥ 6 | **6** (`CSAI`, `DSE`, `ECE`, `BIO`, `MGT`, `REM`) |
| Posts & Comments Combined | ≥ 2,000 | **2,553** (514 posts + 2,039 comments & nested replies) |
| Activity Events (6 Months) | ≥ 10,000 | **12,500** across **183** distinct days (synchronized in DuckDB `fact_research_activity`) |
| Follow Relationships | Yes | **629** member follow edges (`162` topic follows) |
| Planted Ground-Truth Sets | Yes | 36 duplicate pairs, 6 spam accounts, 3 topic spikes, 12 search qrels, 6 RAG queries |

---

## 4. Empirical Evaluation Results (Docker PostgreSQL + `all-MiniLM-L6-v2`)

All metrics below are reproduced directly by running `docker compose exec backend python evaluation/run_evaluations.py` (saved in `evaluation/results/evaluation_summary.json` and `evaluation/results/evaluation_tables.csv`):

| Subsystem | Method | Key Metrics |
|---|---|---|
| **F5 Search** *(Judged 560-paper pool)* | Keyword Search | P@5 = `0.8000`, P@10 = `0.7167`, R@10 = `0.7167`, NDCG@10 = `0.7390` |
| **F5 Search** *(Judged 560-paper pool)* | Semantic Search (`all-MiniLM-L6-v2`) | P@5 = `0.6833`, P@10 = `0.5583`, R@10 = `0.5583`, NDCG@10 = `0.6051` |
| **F5 Search** *(Judged 560-paper pool)* | **Hybrid (Anisotropy-Adjusted RRF + PageRank)** | P@5 = `0.7167`, P@10 = `0.7000`, R@10 = `0.7000`, NDCG@10 = `0.7222` |
| **F5 Search** *(Full 687-paper conservative)* | Keyword / Semantic / **Hybrid** | NDCG@10: Keyword `0.4518` · Semantic `0.4677` · **Hybrid `0.4752` (Highest)** |
| **F6 Recommendations** | Popularity Baseline | P@5 = `0.0971`, P@10 = `0.0714`, R@10 = `0.1752` |
| **F6 Recommendations** | **Hybrid Content + CF** | **P@5 = `0.1829` (+88%)**, **P@10 = `0.1971` (+176%)**, **R@10 = `0.5057` (+189% / 2.89×)** |
| **F5 Deduplication** | Exact Match Baseline | Precision = `1.0000`, Recall = `0.0278`, F1 = `0.0541` (1/36 TP) |
| **F5 Deduplication** | **MinHash LSH + Author ER** | **Precision = `1.0000`**, **Recall = `1.0000`**, **F1 = `1.0000`** (36/36 TP, 0 FP) |
| **F7 Spam Detection** | Volume Threshold Baseline | Precision = `0.5455`, Recall = `1.0000`, F1 = `0.7059` (5 FP) |
| **F7 Spam Detection** | **Isolation Forest + Rules** | **Precision = `1.0000`**, **Recall = `1.0000`**, **F1 = `1.0000`** (6/6 TP, 0 FP) |
| **F7 Topic Spikes** | **Non-Adjacent Outlier-Guarded Z-Score** | **Detection Rate = `1.0000` (3/3)**, **Precision = `1.0000`**, **False Alarms = `0`** |
| **F8 RAG Assistant** | **Grounded RAG Pipeline** | **Hit@5 = `1.0000`**, **Citation Acc = `1.0000`**, **Coverage = `1.0000`**, **Refusal Acc = `1.0000`** |

> *Note on F5 Search Qrels:* Adding 127 newly ingested real arXiv preprints (IDs `561–687`) while preserving the original 560-paper `search_qrels.json` untouched means newly retrieved relevant arXiv papers are conservatively scored as unjudged (`0`), lowering raw P@k/NDCG magnitudes across all modes while **Hybrid achieves the highest overall NDCG@10 (`0.4752`)**.*

---

## 5. Exact Setup & Execution Commands (Windows & Docker)

### Option A: Local Execution on Windows (Zero Docker Required)

1. **Configure Environment** (optional — defaults work out-of-the-box with local SQLite + DuckDB + Parquet):
   ```powershell
   Copy-Item .env.example .env
   ```
2. **Install Python Backend Dependencies**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
   ```
3. **Bootstrap Database, External Ingestion (OpenAlex + arXiv + RSS), Synthetic Data, Embeddings, PageRank & DuckDB Warehouse**:
   ```powershell
   .\.venv\Scripts\python.exe scripts\bootstrap_all.py
   ```
4. **Reproduce All ML Evaluations, Charts & Automated Tests**:
   ```powershell
   .\.venv\Scripts\python.exe scripts\generate_diagrams.py
   .\.venv\Scripts\python.exe evaluation\run_evaluations.py
   .\.venv\Scripts\python.exe -m pytest -v tests\test_trend_detection.py tests\test_platform.py
   ```
5. **Install & Build Frontend** (requires Node.js 20+ or uses `.tools\node` if present):
   ```powershell
   cd frontend
   npm install
   npm run build
   cd ..
   ```
6. **Start Both Servers (Single Command)**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1
   ```
   - Frontend UI: `http://localhost:5173`
   - FastAPI Interactive Swagger Docs: `http://localhost:8000/docs`

### Option B: Full Stack via Docker Compose (PostgreSQL + pgvector + MinIO + FastAPI + Nginx)
Ensure Docker Desktop is running, then execute:
```powershell
Copy-Item .env.example .env
docker compose up --build -d
# Run initial data bootstrap inside the backend container:
docker compose exec backend python scripts/bootstrap_all.py
docker compose exec backend python evaluation/run_evaluations.py
```
- Frontend UI: `http://localhost:3000`
- Backend API: `http://localhost:8000/docs`
- MinIO Console: `http://localhost:9001`

---

## 6. Demo Credentials (All 4 Roles)

All demo accounts use password **`Chanakya@2026`** (also available as one-click role buttons on `/login`):

| Role | Email | Capabilities |
|---|---|---|
| **Admin** | `admin@chanakya.edu.in` | Full platform + **F9 Institutional Analytics (DuckDB)** + **Admin Panel** (alerts, spam moderation, ingestion jobs, ML benchmarks) |
| **Faculty** | `faculty@chanakya.edu.in` | CSAI Professor profile, library collections, posts, search, recommendations, RAG |
| **Researcher** | `researcher@chanakya.edu.in` | BIO Postdoc profile, library collections, posts, search, recommendations, RAG |
| **Student** | `student@chanakya.edu.in` | DSE B.Tech student profile, personalized feed, collections, search, recommendations, RAG |

---

## 7. Academic Deliverables

- **Technical Report**: [`documentation/technical_report.md`](documentation/technical_report.md)
- **Viva Preparation & Demo Script**: [`documentation/viva_preparation.md`](documentation/viva_preparation.md)
- **REST API Reference**: [`documentation/api_documentation.md`](documentation/api_documentation.md)
- **Architecture & Schema Diagrams**: [`documentation/architecture/diagrams.md`](documentation/architecture/diagrams.md) and PNGs in [`documentation/diagrams/`](documentation/diagrams/)
- **Evaluation Outputs**: [`evaluation/results/evaluation_summary.json`](evaluation/results/evaluation_summary.json) & [`evaluation/results/evaluation_tables.csv`](evaluation/results/evaluation_tables.csv)
