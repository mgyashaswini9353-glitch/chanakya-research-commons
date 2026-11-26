# Architecture, Database ER, Star Schema & ML Workflow Diagrams

High-resolution rendered PNG diagrams are also stored in [`documentation/diagrams/`](../diagrams/):
- [`system_architecture.png`](../diagrams/system_architecture.png)
- [`warehouse_star_schema.png`](../diagrams/warehouse_star_schema.png)
- [`ingestion_elt_pipeline.png`](../diagrams/ingestion_elt_pipeline.png)
- [`eval_search_comparison.png`](../diagrams/eval_search_comparison.png)
- [`eval_ml_benchmarks.png`](../diagrams/eval_ml_benchmarks.png)

---

## 1. System Architecture Diagram

```mermaid
flowchart TD
    UI["React 18 + TypeScript + Tailwind + Recharts\n(19 Pages · F1-F9 UI)"]
    API["FastAPI REST API + JWT/RBAC + APScheduler"]

    subgraph ML["Intelligent Services Layer"]
        F5["F5 Unified Search\nKeyword + 384-d Semantic + RRF\nNetworkX PageRank + MinHash LSH"]
        F6["F6 Recommendations\nContent+CF + Cold-Start\nFP-Growth + Communities"]
        F7["F7 Trends & Monitoring\nSliding-Window Z-Score\nIsolation Forest Spam"]
        F8["F8 Grounded RAG\nPassage Retrieval + Guardrail\nOllama / Extractive Fallback"]
    end

    subgraph DATA["Medallion Data & Warehouse Layer"]
        OLTP[("PostgreSQL + pgvector\n(14 OLTP Tables)")]
        LAKE[("Bronze Raw Lake\nLocal FS + MinIO\ndata/raw/")]
        DW[("Gold Star Schema\nParquet + DuckDB\n5 Dims · 4 Facts")]
    end

    EXT["External Open Sources\nOpenAlex · arXiv · RSS"]

    UI <--> API
    API <--> F5 & F6 & F7 & F8
    EXT -->|"F4 ELT Pipeline"| LAKE
    LAKE -->|"Clean & Deduplicate"| OLTP
    OLTP <--> F5 & F6 & F7 & F8
    OLTP -->|"Warehouse ETL"| DW
    DW -->|"F9 OLAP & Drill-Down"| API
```

---

## 2. Operational Database ER Diagram

```mermaid
erDiagram
    DEPARTMENTS ||--o{ USERS : belongs_to
    USERS ||--o{ USER_FOLLOWS : follows
    USERS ||--o{ TOPIC_FOLLOWS : follows_topic
    USERS ||--o{ POSTS : authors
    USERS ||--o{ COMMENTS : writes
    USERS ||--o{ POST_UPVOTES : upvotes
    USERS ||--o{ COLLECTIONS : owns
    USERS ||--o{ SAVED_PAPERS : saves
    USERS ||--o{ ACTIVITY_EVENTS : generates

    POSTS ||--o{ COMMENTS : has
    COMMENTS ||--o{ COMMENTS : replies_to
    POSTS ||--o{ POST_UPVOTES : receives
    PAPERS ||--o{ POSTS : attached_to

    PAPERS ||--o{ SAVED_PAPERS : saved_in
    COLLECTIONS ||--o{ SAVED_PAPERS : groups
    PAPERS ||--o{ PAPER_CITATIONS : cites
    PAPERS ||--o{ ACTIVITY_EVENTS : referenced_by

    DEPARTMENTS {
        int id PK
        string code UK
        string name
        string faculty_head
    }
    USERS {
        int id PK
        string email UK
        string username UK
        string role
        int department_id FK
        json research_tags
        bool is_flagged_spam
        bool is_synthetic
    }
    PAPERS {
        int id PK
        string canonical_key UK
        text title
        text abstract
        string doi
        string arxiv_id
        json sources
        float pagerank_score
        int save_count
        bool in_university_library
        json embedding
    }
    SAVED_PAPERS {
        int id PK
        int user_id FK
        int paper_id FK
        int collection_id FK
        text private_notes
    }
    ACTIVITY_EVENTS {
        int id PK
        int user_id FK
        string event_type
        int paper_id FK
        string topic
        int department_id FK
        datetime created_at
    }
```

---

## 3. Data Warehouse Kimball Star Schema

```mermaid
erDiagram
    DIM_DATE ||--o{ FACT_RESEARCH_ACTIVITY : date_key
    DIM_DEPARTMENT ||--o{ FACT_RESEARCH_ACTIVITY : department_key
    DIM_MEMBER ||--o{ FACT_RESEARCH_ACTIVITY : member_key
    DIM_TOPIC ||--o{ FACT_RESEARCH_ACTIVITY : topic_key
    DIM_PAPER ||--o{ FACT_RESEARCH_ACTIVITY : paper_key

    DIM_DATE ||--o{ FACT_PAPER_SAVES : date_key
    DIM_MEMBER ||--o{ FACT_PAPER_SAVES : member_key
    DIM_DEPARTMENT ||--o{ FACT_PAPER_SAVES : department_key
    DIM_PAPER ||--o{ FACT_PAPER_SAVES : paper_key
    DIM_TOPIC ||--o{ FACT_PAPER_SAVES : topic_key

    DIM_DATE ||--o{ FACT_SEARCH_EVENTS : date_key
    DIM_MEMBER ||--o{ FACT_SEARCH_EVENTS : member_key
    DIM_DEPARTMENT ||--o{ FACT_SEARCH_EVENTS : department_key
    DIM_TOPIC ||--o{ FACT_SEARCH_EVENTS : topic_key

    DIM_DATE ||--o{ FACT_POST_ENGAGEMENT : date_key
    DIM_MEMBER ||--o{ FACT_POST_ENGAGEMENT : member_key
    DIM_DEPARTMENT ||--o{ FACT_POST_ENGAGEMENT : department_key
    DIM_PAPER ||--o{ FACT_POST_ENGAGEMENT : paper_key
```

---

## 4. Machine Learning Workflows (F5, F6, F7, F8)

```mermaid
flowchart LR
    subgraph Search["F5 Unified Search & Entity Resolution"]
        Q["User Query"] --> KW["Multi-Field BM25/TF-IDF"]
        Q --> SEM["384-d Embedding Cosine"]
        KW & SEM --> RRF["Reciprocal Rank Fusion\n+ NetworkX PageRank"]
        RRF --> P4["4 Unified Panels"]
    end

    subgraph Recs["F6 Recommendations"]
        U["User Profile + Saves"] --> CB["Content Embedding Sim"]
        U --> CF["User-Item CF Matrix"]
        CB & CF --> HR["Hybrid Paper Ranking\n(Cold-Start Aware)"]
        B["Member Save Baskets"] --> FPG["FP-Growth (mlxtend)\nConfidence & Lift"]
    end

    subgraph RAG["F8 Grounded Research Assistant"]
        RQ["Natural Language Question"] --> RET["Hybrid Top-K Retrieval"]
        RET --> SEN["Sentence Scoring &\nSufficiency Guardrail"]
        SEN -->|"Sufficient"| GEN["Ollama / Verified Extractive\nSynthesis + Inline [1..K]"]
        SEN -->|"Insufficient"| REF["Honest Refusal\n(0 Citations)"]
    end
```
