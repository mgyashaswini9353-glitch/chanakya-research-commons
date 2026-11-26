# Viva Preparation Guide & Live Demo Script
**Chanakya Research Commons — Data Mining and Warehousing (DMW) Mini-Project**

---

## Part 1: 7-Minute Live Viva Demonstration Script

1. **Landing Page (`http://localhost:3000/` in Docker or `http://localhost:5173/` locally) — 30 sec**
   - Point out the live platform counters pulled directly from the backend database (687 papers, 6 departments, 12,500 activity events).
   - Emphasize that 546 papers were ingested live from **OpenAlex**, **arXiv**, and **curated RSS feeds** with untouched raw JSON preserved in `data/raw/` and MinIO (`chanakya-raw-lake`).

2. **Unified 4-Panel Research Search (`F5`, `/search`) — 90 sec**
   - Search `"retrieval augmented generation"`.
   - Highlight all **4 simultaneous panels**: External Research Papers (with deduplicated source badges), Chanakya University Library (with campus save counts), University Researchers, and Discussions.
   - Toggle between **Keyword**, **Semantic**, and **Hybrid (RRF + PageRank)** modes and explain Reciprocal Rank Fusion + NetworkX Citation PageRank.

3. **Paper Detail, Library Collections & FP-Growth (`F3` & `F6`, `/papers/:id` & `/library`) — 60 sec**
   - Click a library paper to show merged source provenance, citation PageRank, personal collection & private notes editor, and **"Members Who Saved This Also Saved"** showing real **FP-Growth Confidence & Lift** values!
   - Show the **Add by DOI / arXiv ID / URL** drawer on `/library` (live OpenAlex/arXiv metadata lookup + duplicate prevention).

4. **Personalized Recommendations & Cold-Start (`F6`, `/recommendations`) — 45 sec**
   - Sign in using one-click **Student** or **Faculty** demo button on `/login`.
   - Open `/recommendations`: point out explainable recommendation reasons (Content + Collaborative Filtering) and NetworkX collaboration communities.

5. **Grounded AI Research Assistant (`F8`, `/assistant`) — 60 sec**
   - Click the first sample research question → show inline `[1]..[5]` citations, clickable verified sources, and inspectable Retrieved Source Passages with semantic & lexical scores.
   - Click the out-of-scope Martian coral reef test question → show the **Insufficient Evidence** guardrail refusing to hallucinate!

6. **Trends & Sudden Spike Detection (`F7`, `/trends`) — 45 sec**
   - Show the **3 detected sudden topic spikes** (`retrieval-augmented-generation`, `solid-state-batteries`, `federated-learning`) with exact Z-scores and weekly sliding-window Recharts trend lines.

7. **Admin Institutional Analytics (`F9`, `/analytics`) & Admin Monitoring (`F7`, `/admin`) — 90 sec**
   - Sign in as **Admin** (`admin@chanakya.edu.in` / `Chanakya@2026`).
   - Show DuckDB Star Schema KPIs, 6-month activity AreaChart, Department Comparison BarChart, Cross-Department Collaboration pairs, and Ward Hierarchical Topic Clusters.
   - Perform the live **4-Level OLAP Drill-Down**: click `CSAI` → click a topic → click a member!
   - Open `/admin` → show Isolation Forest Spam Report (6/6 bots flagged with behavioral reasons), Ingestion Jobs log (OpenAlex/arXiv/RSS), and the live **ML Evaluation Benchmarks** tab!

---

## Part 2: Anticipated Viva Questions & Model Answers

### Q1. Why did you use both PostgreSQL and DuckDB + Parquet instead of only PostgreSQL?
**Answer:** Operational applications (OLTP) like logging in, posting comments, and saving papers require row-oriented ACID writes and fast indexed point lookups — which PostgreSQL excels at. Institutional analytics (OLAP) like 6-month multi-dimensional roll-ups, cross-department co-save joins, and 4-level drill-downs scan thousands of records across a few columns. Storing a **Kimball Star Schema** (5 dimensions, 4 fact tables) in columnar **Parquet** files and querying them with **DuckDB** achieves vectorized columnar scans without putting heavy analytical load on the OLTP database, cleanly demonstrating a real Data Warehousing / Medallion Lakehouse architecture.

### Q2. Explain your Star Schema design. What is the grain of your fact tables?
**Answer:** We modeled 5 shared conformed dimensions (`dim_date`, `dim_department`, `dim_member`, `dim_topic`, `dim_paper`) and 4 fact tables:
- `fact_research_activity` (grain: one atomic user event — view, save, search, post, comment, upvote, follow; 12,500 rows)
- `fact_paper_saves` (grain: one member saving one paper; 686 rows)
- `fact_search_events` (grain: one search query with mode; 2,952 rows)
- `fact_post_engagement` (grain: one discussion post with upvote & comment metrics; 514 rows)

### Q3. How does your duplicate detection work when DOIs are missing and author names vary (e.g., "A. Sharma" vs "Ananya Sharma")?
**Answer:** Exact DOI/title matching achieved only **2.78% recall (F1 = 0.0541)** in Docker on our 36 planted near-duplicate variants. Our `PaperDeduplicator` uses a 4-stage pipeline: normalized DOI/arXiv ID lookup, normalized punctuation-free title matching, author canonicalization mapping `"Ananya Sharma"`, `"A. Sharma"`, and `"Sharma, A."` to `(first_initial, last_name)` tokens, and **MinHash + LSH (`datasketch`, 128 permutations)** over word 2-shingles and character 3-shingles for fast near-duplicate candidate blocking. This boosted F1 from **0.0541 to 1.0000** (36/36 TP, 0 FP).

### Q4. How does Hybrid Search combine Keyword, Semantic, and Citation PageRank?
**Answer:** Keyword search captures exact technical acronyms (like `MinHash`, `CRISPR`, `arXiv`), while 384-d dense semantic embeddings (`all-MiniLM-L6-v2` in Docker, preloaded asynchronously at startup; `tfidf-svd-384` fallback locally) capture conceptual synonyms. We subtract the corpus median cosine similarity floor to counter transformer anisotropy, fuse lexical and semantic ranks via **Reciprocal Rank Fusion (`k=60`)**, and add a gentle normalized **NetworkX Citation PageRank** boost (`alpha=0.85` over 1,950 citation edges). Across our 687-paper Docker corpus benchmark, Hybrid Search achieved the highest overall **NDCG@10 (`0.4752`)** compared to Keyword (`0.4518`) and Semantic (`0.4677`).

### Q5. Why FP-Growth instead of Apriori for "Members who saved this also saved"?
**Answer:** Apriori repeatedly scans the transaction database and generates an exponential number of candidate itemsets. **FP-Growth** (`mlxtend`) compresses member paper-save baskets into an FP-Tree in two passes and mines frequent itemsets directly without candidate generation, producing interpretable **Confidence** and **Lift** association rules on every paper page.

### Q6. How do you handle Cold-Start users in F6 Recommendations?
**Answer:** When a newly registered user has zero saved papers (`is_cold_start = True`), collaborative filtering has no interaction vector. Our engine detects this state automatically and switches to a cold-start blending strategy combining profile text/tag semantic similarity (`0.45`), explicit research tag Jaccard (`0.25`), department alignment (`0.15`), and Citation PageRank/campus save popularity (`0.15`). We verified this explicitly in `test_f6_recommendations_and_cold_start`.

### Q7. Why did Isolation Forest outperform a simple post-volume threshold for Spam Detection?
**Answer:** A simple threshold (`posts >= 12`) flagged 5 genuinely active faculty/students as false positives (`Precision = 0.5455`, `F1 = 0.7059`). By extracting 7 behavioral features — including hourly burst velocity, pairwise TF-IDF duplicate text ratio, promotional keyword density, tag stuffing, and off-hours 01:00–04:59 cadence — our **Isolation Forest + behavioral risk** model achieved **Precision = 1.0000, Recall = 1.0000, F1 = 1.0000** (6/6 spam accounts caught, 0 legitimate members falsely flagged) and gives admins human-readable reasons for every alert.

### Q8. How does your RAG Research Assistant prevent hallucinations?
**Answer:** First, it enforces a domain-grounding sufficiency threshold: if retrieved passages have zero domain-term overlap or insufficient semantic/lexical relevance, the assistant refuses to answer and reports `Insufficient evidence` with zero citations (`Unanswerable Refusal Accuracy = 1.0000`). Second, every citation `[k]` is bound programmatically to an actual `papers.id` in the database, and the UI displays the exact retrieved source passages alongside the answer so any researcher can inspect and verify every claim.

### Q9. How do you keep real external data separate from synthetic data?
**Answer:** Every `papers`, `users`, `posts`, `comments`, and `activity_events` record carries an explicit boolean `is_synthetic` column plus provenance in `sources`. Real external API payloads from OpenAlex, arXiv, and RSS are preserved unchanged in `data/raw/{source}/` with `is_synthetic=False` (546 papers), while synthetic activity can be purged cleanly at production university deployment without altering any database schema.

### Q10. How can someone reproduce every evaluation number in the report?
**Answer:** Run `.\.venv\Scripts\python.exe evaluation\run_evaluations.py` (or `scripts\regenerate_all.ps1`). Because synthetic generation uses a fixed seed (`SEED = 42`) and all planted ground-truth files are persisted in `data/ground_truth/`, the script deterministically reproduces `evaluation/results/evaluation_summary.json`, `evaluation/results/evaluation_tables.csv`, and both PNG benchmark charts.
