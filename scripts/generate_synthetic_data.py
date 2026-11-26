"""
Reproducible Synthetic University Dataset & Planted Ground-Truth Generator.
Fixed random seed = 42.

Satisfies and exceeds all mandatory minimums from DMW-CourseProject (1).pdf:
  - >= 500 research paper records with abstracts (real OpenAlex/arXiv/RSS + clearly flagged synthetic fallback if needed)
  - 60 university members across 6 Chanakya departments (student, faculty, researcher, admin)
  - >= 2,200 posts & comments combined across 6 months
  - >= 12,000 save, view, search, and engagement events across 6 months
  - Follow relationships between members & topics
  - Planted ground truth files in data/ground_truth/:
      * duplicate_pairs.json & duplicate_eval_corpus.json (near-duplicates + author-name variants)
      * spam_accounts.json (6 planted spam/bot accounts with bursts, duplicate text, promo signals)
      * topic_spikes.json (3 planted sudden topic spikes in specific weeks)
      * search_qrels.json (curated relevance judgments for search evaluation)
      * rag_eval_queries.json (research QA evaluation set including unanswerable query)
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.models.models import (
    ActivityEvent,
    Collection,
    Comment,
    Department,
    Paper,
    PaperCitation,
    Post,
    PostUpvote,
    SavedPaper,
    TopicFollow,
    User,
    UserFollow,
)
from ingestion.pipeline import upsert_paper_record

SEED = 42

DEPARTMENTS_SPEC = [
    ("CSAI", "Computer Science & Artificial Intelligence", "Dr. Aravind Deshmukh", "Machine learning, NLP, LLMs, computer vision, and trustworthy AI systems.", ["large-language-models", "retrieval-augmented-generation", "graph-neural-networks", "computer-vision", "deep-learning", "natural-language-processing"]),
    ("DSE", "Data Science & Engineering", "Dr. Meenakshi Rao", "Data warehousing, lakehouse architectures, stream mining, and distributed analytics.", ["data-warehousing", "data-mining", "lakehouse-analytics", "federated-learning", "anomaly-detection", "stream-mining"]),
    ("ECE", "Electronics & Robotics", "Dr. Karthik Subramanian", "Embedded AI, neuromorphic hardware, autonomous robotics, and IoT sensing.", ["edge-ai", "autonomous-robotics", "embedded-systems", "neuromorphic-computing", "iot-systems", "signal-processing"]),
    ("BIO", "Biotechnology & Bioinformatics", "Dr. Nandini Kulkarni", "Computational genomics, protein folding, CRISPR analytics, and medical AI.", ["bioinformatics", "genomics", "computational-biology", "medical-imaging", "drug-discovery", "healthcare-ai"]),
    ("MGT", "Management & Computational Economics", "Dr. Siddharth Menon", "Supply chain optimization, algorithmic economics, causal inference, and fintech risk.", ["computational-economics", "supply-chain-analytics", "decision-science", "financial-analytics", "fraud-detection", "causal-inference"]),
    ("REM", "Renewable Energy & Materials", "Dr. Priya Venkatesh", "Solid-state batteries, perovskite solar cells, smart grids, and sustainable materials.", ["solid-state-batteries", "solar-photovoltaics", "energy-materials", "smart-grid", "renewable-energy", "climate-modeling"]),
]

FIRST_NAMES = [
    "Aarav", "Ananya", "Rohan", "Diya", "Vikram", "Ishita", "Arjun", "Kavya", "Aditya", "Sneha",
    "Pranav", "Meera", "Nikhil", "Tanvi", "Rahul", "Pooja", "Siddharth", "Neha", "Varun", "Riya",
    "Harsh", "Shreya", "Karan", "Divya", "Dev", "Anjali", "Manish", "Lakshmi", "Surya", "Bhavna",
    "Akash", "Chitra", "Gaurav", "Deepika", "Yash", "Swati", "Tarun", "Madhuri", "Nitin", "Revathi",
    "Abhishek", "Pallavi", "Kunal", "Vidya", "Sandeep", "Keerthi", "Rakesh", "Aishwarya", "Mohit", "Gayatri",
]

LAST_NAMES = [
    "Sharma", "Nair", "Patel", "Reddy", "Iyer", "Kulkarni", "Joshi", "Verma", "Rao", "Menon",
    "Bhat", "Desai", "Shetty", "Hegde", "Pillai", "Chatterjee", "Banerjee", "Mishra", "Sinha", "Gupta",
    "Krishnamurthy", "Venkataraman", "Subramanian", "Agarwal", "Chauhan", "Das", "Ghosh", "Kapoor", "Malhotra", "Srinivasan",
]

POST_TEMPLATES = [
    ("Reading group notes on {topic}: key takeaways from recent benchmarks", "We reviewed three recent papers in {topic} during our {dept} seminar. The main bottleneck remains scalability under noisy real-world distributions, and hybrid retrieval + structured evaluation consistently outperformed single-method baselines. Has anyone replicated the ablation study on campus GPUs?"),
    ("Open research question: combining {topic} with {topic2}", "I am exploring how methods from {topic} can transfer to {topic2} workflows in {dept}. Particularly interested in reproducible datasets, evaluation metrics, and open-source implementations that run cleanly on modest hardware."),
    ("Dataset & code pointer for {topic} experiments", "Sharing our curated reading notes and benchmark checklist for {topic}. We found that careful preprocessing, deduplication, and controlled train/validation splits dramatically reduce variance in precision and recall."),
    ("Critique of evaluation practices in {topic}", "Several papers in {topic} report single-run accuracy without statistical baselines or latency budgets. In our {dept} lab, comparing against a strong popularity or BM25 baseline revealed where complex models actually add value."),
    ("Seeking collaborators for university research project on {topic}", "Looking for 2 students or researchers interested in collaborating on an end-to-end {topic} study with shared benchmarks and reproducible experiments. Especially welcome colleagues from {dept} and allied schools!"),
]

COMMENT_TEMPLATES = [
    "Great synthesis! We observed a very similar trend when evaluating {topic} on our department benchmark last month.",
    "Thanks for sharing this paper. The baseline comparison section is super helpful for designing fair ablation studies.",
    "Have you tried combining this with lightweight dimensionality reduction or MinHash blocking? That cut our runtime by 4x.",
    "I just saved the referenced paper to our shared Chanakya library collection—happy to collaborate on reproducing Table 2.",
    "Interesting point about cold-start behavior. In our {dept} experiments, combining metadata tags with similarity scores helped a lot.",
    "Following up on the evaluation metric choice: NDCG@10 and F1-score gave much clearer signal than raw accuracy here.",
    "Would love to discuss this at Friday's Chanakya Research Commons reading circle!",
]

SPAM_POSTS = [
    ("URGENT: Guaranteed Acceptance Fast-Track Journal Publish! Click Here", "Buy now! Guaranteed acceptance in Scopus journals within 48 hours! Instant publish promo discount, contact telegram @fastpaper_promo or whatsapp for cheap assignment and instant thesis writing!"),
    ("Free Discount Thesis & Instant Publish Promo — Click Here Now!", "Click here for cheap assignment help and guaranteed acceptance! Buy now with 80% promo discount on instant publish services via telegram and whatsapp!"),
    ("Guaranteed Acceptance Conference Papers — Cheap Assignment Promo", "Buy now! Instant publish for all departments! Click here for discount rates, whatsapp and telegram support 24/7 for guaranteed acceptance!"),
]


PLANTED_TOPIC_SPIKES = [
    {"topic": "retrieval-augmented-generation", "days_ago_start": 3, "days_ago_end": 8, "extra_events": 115, "department": "CSAI", "cause": "University-wide LLM & RAG Hackathon Week"},
    {"topic": "solid-state-batteries", "days_ago_start": 10, "days_ago_end": 14, "extra_events": 95, "department": "REM", "cause": "Chanakya Clean Energy Symposium Keynote"},
    {"topic": "federated-learning", "days_ago_start": 17, "days_ago_end": 21, "extra_events": 90, "department": "DSE", "cause": "National Privacy-Preserving AI Grant Call"},
]


def _has_planted_spike_events(db: Session) -> bool:
    """Check DB state (not filesystem) for planted spike ActivityEvent rows."""
    spike_topics = [sp["topic"] for sp in PLANTED_TOPIC_SPIKES]
    rows = (
        db.query(ActivityEvent.metadata_json)
        .filter(ActivityEvent.topic.in_(spike_topics))
        .all()
    )
    return any(isinstance(meta, dict) and meta.get("planted_spike") is True for (meta,) in rows)


def ensure_planted_topic_spikes(
    db: Session,
    *,
    dept_objs: Dict[str, Department] | None = None,
    all_regular: List[User] | None = None,
    papers_by_topic: Dict[str, List[Paper]] | None = None,
    papers_by_dept: Dict[str, List[Paper]] | None = None,
    all_papers: List[Paper] | None = None,
    rng: random.Random | None = None,
    now: datetime | None = None,
    gt_dir: Path | None = None,
) -> int:
    """
    Idempotently persist the 3 planted research-topic spikes into `activity_events`.
    Checks the database itself (rather than `topic_spikes.json` on disk) so that
    shared-volume environments (e.g. Docker PostgreSQL mounting `./data` after a
    prior SQLite run) never silently skip inserting planted spike rows.
    """
    gt_dir = gt_dir or (Path(settings.DATA_DIR) / "ground_truth")
    gt_dir.mkdir(parents=True, exist_ok=True)
    spike_marker_file = gt_dir / "topic_spikes.json"

    if now is None:
        latest_row = db.query(ActivityEvent.created_at).order_by(ActivityEvent.created_at.desc()).first()
        if latest_row and latest_row[0] is not None:
            latest_ts = latest_row[0]
            now = latest_ts.replace(tzinfo=timezone.utc) if latest_ts.tzinfo is None else latest_ts.astimezone(timezone.utc)
        else:
            now = datetime.now(timezone.utc)

    inserted = 0
    if not _has_planted_spike_events(db):
        rng = rng or random.Random(SEED + 700)
        if dept_objs is None:
            dept_objs = {d.code: d for d in db.query(Department).all()}
        if all_regular is None:
            all_regular = db.query(User).filter(~User.username.like("promo_bot_acct_%")).all()
        if all_papers is None:
            all_papers = db.query(Paper).all()
        if papers_by_dept is None or papers_by_topic is None:
            papers_by_dept = {}
            papers_by_topic = {}
            for p in all_papers:
                papers_by_dept.setdefault(p.department_hint or "CSAI", []).append(p)
                for t in (p.topics or []):
                    papers_by_topic.setdefault(str(t).lower(), []).append(p)

        spike_events = []
        for sp in PLANTED_TOPIC_SPIKES:
            dept_obj = dept_objs.get(sp["department"])
            dept_id = dept_obj.id if dept_obj else None
            cand_papers = papers_by_topic.get(sp["topic"]) or papers_by_dept.get(sp["department"]) or all_papers
            for _ in range(sp["extra_events"]):
                u = rng.choice(all_regular)
                days_ago = rng.randint(sp["days_ago_start"], sp["days_ago_end"])
                ts = now - timedelta(days=days_ago, hours=rng.randint(9, 21), minutes=rng.randint(0, 59))
                ev_t = rng.choice(["view", "search", "view"])
                spike_events.append(
                    ActivityEvent(
                        user_id=u.id,
                        event_type=ev_t,
                        paper_id=rng.choice(cand_papers).id if (ev_t == "view" and cand_papers) else None,
                        query_text=f"{sp['topic'].replace('-', ' ')} latest papers" if ev_t == "search" else None,
                        topic=sp["topic"],
                        department_id=dept_id,
                        metadata_json={"planted_spike": True},
                        is_synthetic=True,
                        created_at=ts,
                    )
                )
        db.bulk_save_objects(spike_events)
        db.commit()
        inserted = len(spike_events)

    if not spike_marker_file.exists():
        with open(spike_marker_file, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "topic": sp["topic"],
                        "department": sp["department"],
                        "window_start": (now - timedelta(days=sp["days_ago_end"])).strftime("%Y-%m-%d"),
                        "window_end": (now - timedelta(days=sp["days_ago_start"])).strftime("%Y-%m-%d"),
                        "injected_events": sp["extra_events"],
                        "cause": sp["cause"],
                    }
                    for sp in PLANTED_TOPIC_SPIKES
                ],
                f,
                indent=2,
            )

    return inserted


def _ensure_min_papers(db: Session, rng: random.Random, min_total: int = 560) -> int:
    """Supplement real ingested papers with clearly flagged synthetic domain papers only if below min_total."""
    current = db.query(Paper).count()
    if current >= min_total:
        return 0

    needed = min_total - current
    methods = [
        "Contrastive Graph Representation Learning",
        "Adaptive Sliding-Window Stream Mining",
        "Hybrid Retrieval-Augmented Indexing",
        "Federated Privacy-Preserving Optimization",
        "Multi-Modal Hierarchical Attention",
        "Zero-Shot Entity Resolution via MinHash LSH",
        "Columnar Star-Schema Query Acceleration",
        "Causal Counterfactual Intervention Modeling",
        "Physics-Informed Neural Surrogate Modeling",
        "Low-Power Neuromorphic Spiking Inference",
    ]
    domains = [
        "Academic Knowledge Graphs",
        "University Research Repositories",
        "Clinical Diagnostic Pipelines",
        "Distributed IoT Telemetry Streams",
        "Next-Generation Solid-State Electrolytes",
        "Multi-Echelon Supply Chain Networks",
        "High-Throughput Genomic Sequencing",
        "Autonomous Edge Robotics Navigation",
        "Real-Time Financial Fraud Monitoring",
        "Grid-Scale Renewable Load Forecasting",
    ]
    venues = [
        "IEEE Transactions on Knowledge and Data Engineering",
        "ACM SIGKDD Conference on Knowledge Discovery and Data Mining",
        "NeurIPS Workshop on Scholarly AI",
        "VLDB Journal",
        "Nature Computational Science",
        "IEEE Transactions on Smart Grid",
        "Bioinformatics (Oxford)",
        "Management Science",
    ]

    added = 0
    for i in range(needed):
        dept_code, dept_name, _head, _desc, dept_topics = DEPARTMENTS_SPEC[i % len(DEPARTMENTS_SPEC)]
        t1 = dept_topics[i % len(dept_topics)]
        t2 = dept_topics[(i + 1) % len(dept_topics)]
        m = methods[i % len(methods)]
        dom = domains[(i // len(methods) + i) % len(domains)]
        yr = rng.choice([2021, 2022, 2023, 2024, 2025, 2026])
        a1 = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        a2 = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        a3 = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        title = f"{m} for {dom} in {t1.replace('-', ' ').title()} (Study {i + 1})"
        abstract = (
            f"This study investigates {m.lower()} applied to {dom.lower()} within {dept_name}. "
            f"Addressing core challenges in {t1.replace('-', ' ')} and {t2.replace('-', ' ')}, "
            f"we design a reproducible benchmark architecture evaluated across multi-source datasets. "
            f"Experimental results demonstrate substantial gains in precision, recall, and computational efficiency "
            f"compared to conventional baselines while preserving interpretability for university-scale deployment."
        )
        rec = {
            "title": title,
            "abstract": abstract,
            "authors": [a1, a2, a3],
            "publication_year": yr,
            "published_date": f"{yr}-{rng.randint(1,12):02d}-15",
            "venue": rng.choice(venues),
            "doi": f"10.48550/chanakya.syn.{yr}.{1000 + i}",
            "arxiv_id": None,
            "url": f"https://doi.org/10.48550/chanakya.syn.{yr}.{1000 + i}",
            "pdf_url": "",
            "topics": [t1, t2],
            "department_hint": dept_code,
            "primary_source": "synthetic",
            "external_id": f"syn-{1000 + i}",
            "citation_count": rng.randint(5, 180),
            "is_synthetic": True,
        }
        upsert_paper_record(db, rec)
        added += 1
    db.commit()
    return added


def _generate_citation_graph(db: Session, rng: random.Random) -> int:
    """Add intra-topic citation edges so citation PageRank operates on a rich directed graph."""
    papers = db.query(Paper).all()
    by_dept: Dict[str, List[Paper]] = {}
    for p in papers:
        by_dept.setdefault(p.department_hint or "CSAI", []).append(p)

    existing = {(e.citing_paper_id, e.cited_paper_id) for e in db.query(PaperCitation).all()}
    added = 0
    for dept_code, plist in by_dept.items():
        if len(plist) < 5:
            continue
        # Sort oldest first so newer papers cite older high-impact papers
        plist_sorted = sorted(plist, key=lambda x: (x.publication_year or 2023, x.id))
        hubs = sorted(plist, key=lambda x: x.citation_count or 0, reverse=True)[: min(10, len(plist))]
        for idx, p in enumerate(plist_sorted):
            n_cites = rng.randint(2, 5)
            candidates = hubs + plist_sorted[: max(1, idx)]
            chosen = rng.sample(candidates, k=min(n_cites, len(candidates)))
            for target in chosen:
                if target.id != p.id and (p.id, target.id) not in existing:
                    db.add(PaperCitation(citing_paper_id=p.id, cited_paper_id=target.id))
                    existing.add((p.id, target.id))
                    added += 1
    db.commit()
    return added


def _create_duplicate_ground_truth(db: Session, rng: random.Random, gt_dir: Path) -> Dict[str, Any]:
    """
    Create a dedicated near-duplicate evaluation corpus + ground-truth pairs file
    containing exact DOI matches, punctuation/subtitle title variants, and author-name variants
    ("Ananya Sharma" -> "A. Sharma", "Sharma, A.").
    """
    papers = db.query(Paper).limit(140).all()
    eval_records = []
    gt_pairs = []

    for p in papers:
        eval_records.append(
            {
                "record_id": f"orig_{p.id}",
                "paper_id": p.id,
                "title": p.title,
                "abstract": p.abstract or "",
                "authors": p.authors or [],
                "doi": p.doi,
                "arxiv_id": p.arxiv_id,
                "source": p.primary_source,
            }
        )

    # Plant 36 controlled near-duplicates across 3 realistic failure modes
    sample_papers = rng.sample(papers, k=min(36, len(papers)))
    for idx, p in enumerate(sample_papers):
        dup_id = f"dup_{p.id}_{idx}"
        variant_type = idx % 3
        orig_authors = list(p.authors or ["Ananya Sharma", "Rohan Patel"])

        def _abbreviate_author(name: str) -> str:
            parts = name.split()
            if len(parts) >= 2:
                return f"{parts[0][0]}. {parts[-1]}" if idx % 2 == 0 else f"{parts[-1]}, {parts[0][0]}."
            return name

        mod_authors = [_abbreviate_author(a) for a in orig_authors]

        if variant_type == 0:
            # Mode A: Missing DOI, altered punctuation/casing, abbreviated author names
            mod_title = p.title.replace(":", " -").replace("-", " ")
            if len(mod_title) > 15:
                mod_title = mod_title.upper() if idx % 2 == 0 else mod_title.lower()
            rec = {
                "record_id": dup_id,
                "paper_id": p.id,
                "title": mod_title,
                "abstract": (p.abstract or "")[:240],
                "authors": mod_authors,
                "doi": None,
                "arxiv_id": None,
                "source": "arxiv_mirror",
            }
            vlabel = "title_case_punctuation_and_author_initial_variant"
        elif variant_type == 1:
            # Mode B: Slight title wording tweak + missing DOI + author variant (tests MinHash LSH!)
            words = p.title.split()
            mod_title = " ".join(words[:-1]) + " Framework" if len(words) > 5 else p.title + " Study"
            rec = {
                "record_id": dup_id,
                "paper_id": p.id,
                "title": mod_title,
                "abstract": p.abstract or "",
                "authors": mod_authors,
                "doi": None,
                "arxiv_id": None,
                "source": "semantic_scholar_mirror",
            }
            vlabel = "minhash_near_duplicate_title_and_author_variant"
        else:
            # Mode C: Different source formatting, same DOI or arXiv ID, reordered/initialed authors
            rec = {
                "record_id": dup_id,
                "paper_id": p.id,
                "title": f"[Preprint] {p.title}",
                "abstract": (p.abstract or "")[:200],
                "authors": list(reversed(mod_authors)),
                "doi": f"https://doi.org/{p.doi}" if p.doi else None,
                "arxiv_id": p.arxiv_id,
                "source": "openalex_crossref_mirror",
            }
            vlabel = "cross_source_doi_prefix_and_author_reorder"

        eval_records.append(rec)
        gt_pairs.append(
            {
                "id_a": f"orig_{p.id}",
                "id_b": dup_id,
                "variant_type": vlabel,
                "original_title": p.title,
                "variant_title": rec["title"],
            }
        )

    with open(gt_dir / "duplicate_eval_corpus.json", "w", encoding="utf-8") as f:
        json.dump(eval_records, f, indent=2, ensure_ascii=False)
    with open(gt_dir / "duplicate_pairs.json", "w", encoding="utf-8") as f:
        json.dump(gt_pairs, f, indent=2, ensure_ascii=False)

    return {"corpus_size": len(eval_records), "planted_duplicate_pairs": len(gt_pairs)}


def _create_search_and_rag_ground_truth(db: Session, gt_dir: Path) -> Dict[str, Any]:
    """Build reproducible relevance judgments (qrels) for Search evaluation and QA set for RAG evaluation."""
    papers = db.query(Paper).all()

    # Curated academic search queries covering all 6 Chanakya departments, including semantic-phrased queries
    query_specs = [
        ("retrieval augmented generation hallucination grounding", ["retrieval-augmented-generation", "large-language-models"], ["retrieval", "rag", "language", "grounding", "hallucination", "generation"]),
        ("graph neural network node representation learning", ["graph-neural-networks", "deep-learning"], ["graph", "neural", "node", "message", "gnn"]),
        ("columnar data warehouse lakehouse query analytics", ["data-warehousing", "lakehouse-analytics", "data-mining"], ["warehouse", "lakehouse", "query", "olap", "columnar", "analytics"]),
        ("distributed federated learning privacy preserving optimization", ["federated-learning", "anomaly-detection"], ["federated", "privacy", "distributed", "client", "learning"]),
        ("tinyml edge inference autonomous robotics control", ["edge-ai", "autonomous-robotics", "embedded-systems"], ["edge", "robot", "robotics", "autonomous", "embedded", "tinyml"]),
        ("protein structure prediction bioinformatics genomic sequencing", ["bioinformatics", "genomics", "computational-biology"], ["protein", "genomic", "crispr", "bioinformatics", "folding", "dna"]),
        ("medical image segmentation clinical drug discovery", ["medical-imaging", "drug-discovery", "healthcare-ai"], ["medical", "clinical", "drug", "imaging", "diagnostic"]),
        ("supply chain optimization algorithmic computational economics", ["supply-chain-analytics", "computational-economics"], ["supply", "chain", "economic", "optimization", "inventory", "pricing"]),
        ("financial transaction fraud detection anomaly scoring", ["fraud-detection", "financial-analytics", "anomaly-detection"], ["fraud", "financial", "anomaly", "transaction", "detection"]),
        ("solid state lithium battery perovskite photovoltaic solar efficiency", ["solid-state-batteries", "solar-photovoltaics", "energy-materials"], ["battery", "batteries", "solid", "perovskite", "solar", "photovoltaic"]),
        ("microgrid smart grid renewable power load forecasting", ["smart-grid", "renewable-energy", "climate-modeling"], ["grid", "microgrid", "renewable", "solar", "wind", "forecasting"]),
        ("semantic conceptual phrasing: reducing factual errors in neural text models with external documents", ["retrieval-augmented-generation", "large-language-models"], ["retrieval", "augmented", "language", "model", "document", "knowledge"]),
    ]

    qrels = []
    for q_text, target_topics, keywords in query_specs:
        rel_ids = []
        for p in papers:
            p_topics = {str(t).lower() for t in (p.topics or [])}
            text = f"{p.title} {p.abstract}".lower()
            topic_hit = len(p_topics & set(target_topics)) > 0
            kw_hits = sum(1 for k in keywords if k in text)
            if (topic_hit and kw_hits >= 1) or kw_hits >= 3:
                rel_ids.append(p.id)
        if rel_ids:
            qrels.append({"query": q_text, "relevant_paper_ids": rel_ids[:40]})

    with open(gt_dir / "search_qrels.json", "w", encoding="utf-8") as f:
        json.dump(qrels, f, indent=2)

    rag_queries = [
        {"question": "How does retrieval-augmented generation improve large language model accuracy?", "expect_answerable": True, "expected_keywords": ["retrieval", "language", "generation", "knowledge", "model"]},
        {"question": "What approaches are used for federated learning and anomaly detection in data systems?", "expect_answerable": True, "expected_keywords": ["federated", "anomaly", "learning", "privacy", "data"]},
        {"question": "What are recent advances in solid-state batteries and perovskite solar cells?", "expect_answerable": True, "expected_keywords": ["battery", "solid", "solar", "perovskite", "energy"]},
        {"question": "How is machine learning applied to bioinformatics, protein folding, and genomics?", "expect_answerable": True, "expected_keywords": ["protein", "genomic", "bioinformatics", "biology", "learning"]},
        {"question": "What techniques optimize autonomous robotics and edge AI systems?", "expect_answerable": True, "expected_keywords": ["edge", "robot", "autonomous", "embedded", "inference"]},
        {"question": "What are the archaeological excavation findings of ancient Martian underwater coral reefs in 1742?", "expect_answerable": False, "expected_keywords": []},
    ]
    with open(gt_dir / "rag_eval_queries.json", "w", encoding="utf-8") as f:
        json.dump(rag_queries, f, indent=2)

    return {"search_queries": len(qrels), "rag_queries": len(rag_queries)}


def generate_all_synthetic_data(db: Session, reset_synthetic: bool = False) -> Dict[str, Any]:
    """Generate the complete Chanakya synthetic dataset & ground truth deterministically (seed=42)."""
    rng = random.Random(SEED)
    gt_dir = Path(settings.DATA_DIR) / "ground_truth"
    syn_dir = Path(settings.DATA_DIR) / "synthetic"
    gt_dir.mkdir(parents=True, exist_ok=True)
    syn_dir.mkdir(parents=True, exist_ok=True)

    # 1. Seed 6 Departments
    dept_objs: Dict[str, Department] = {}
    for code, name, head, desc, _topics in DEPARTMENTS_SPEC:
        d = db.query(Department).filter(Department.code == code).first()
        if not d:
            d = Department(code=code, name=name, faculty_head=head, description=desc)
            db.add(d)
            db.flush()
        dept_objs[code] = d
    db.commit()

    # 2. Ensure >= 560 papers & citation graph
    syn_papers_added = _ensure_min_papers(db, rng, min_total=560)
    citations_added = _generate_citation_graph(db, rng)
    all_papers = db.query(Paper).all()
    papers_by_dept: Dict[str, List[Paper]] = {}
    papers_by_topic: Dict[str, List[Paper]] = {}
    for p in all_papers:
        papers_by_dept.setdefault(p.department_hint or "CSAI", []).append(p)
        for t in (p.topics or []):
            papers_by_topic.setdefault(str(t).lower(), []).append(p)

    # 3. Create 60 University Members (4 demo accounts + 50 regular synthetic + 6 planted spam accounts)
    existing_users = db.query(User).count()
    now = datetime.now(timezone.utc)
    six_months_ago = now - timedelta(days=182)
    default_pw_hash = hash_password("Chanakya@2026")

    demo_accounts = [
        ("admin@chanakya.edu.in", "admin_chanakya", "Dr. Vikramaditya Rao", "admin", "DSE", "Dean of Research & Institutional Analytics at Chanakya University.", "Data warehousing, institutional research analytics, scientometrics, lakehouse engineering.", ["data-warehousing", "lakehouse-analytics", "data-mining", "anomaly-detection"]),
        ("faculty@chanakya.edu.in", "prof_ananya", "Dr. Ananya Deshpande", "faculty", "CSAI", "Associate Professor of AI & NLP at School of Engineering, Chanakya University.", "Retrieval-augmented generation, large language models, trustworthy AI, graph neural networks.", ["large-language-models", "retrieval-augmented-generation", "graph-neural-networks", "natural-language-processing"]),
        ("researcher@chanakya.edu.in", "dr_rohan_bio", "Dr. Rohan Kulkarni", "researcher", "BIO", "Postdoctoral Computational Biologist working on protein structure & clinical ML.", "Bioinformatics, protein folding, genomics, medical imaging, drug discovery.", ["bioinformatics", "genomics", "computational-biology", "medical-imaging"]),
        ("student@chanakya.edu.in", "aarav_btech", "Aarav Nair", "student", "DSE", "V Semester B.Tech Data Science student building research discovery engines.", "Data mining, stream analytics, recommendation systems, federated learning.", ["data-mining", "federated-learning", "stream-mining", "data-warehousing"]),
    ]

    created_users: List[User] = []
    for email, uname, fname, role, dcode, bio, interests, tags in demo_accounts:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email,
                username=uname,
                password_hash=default_pw_hash,
                full_name=fname,
                role=role,
                department_id=dept_objs[dcode].id,
                bio=bio,
                research_interests_text=interests,
                research_tags=tags,
                publication_links=[f"https://scholar.google.com/citations?user={uname}"],
                personal_website=f"https://chanakyauniversity.edu.in/research/{uname}",
                is_synthetic=False,
                created_at=six_months_ago,
            )
            db.add(u)
            db.flush()
        created_users.append(u)

    # 50 Regular realistic Chanakya members across all 6 departments
    regular_users: List[User] = list(created_users)
    if existing_users < 50:
        for i in range(50):
            dept_code, dept_name, _head, _desc, dept_topics = DEPARTMENTS_SPEC[i % len(DEPARTMENTS_SPEC)]
            fn = FIRST_NAMES[i % len(FIRST_NAMES)]
            ln = LAST_NAMES[(i * 7 + 3) % len(LAST_NAMES)]
            uname = f"{fn.lower()}_{ln.lower()}_{i+1}"
            email = f"{uname}@chanakya.edu.in"
            if db.query(User).filter(User.email == email).first():
                continue
            role = "faculty" if i % 6 == 0 else ("researcher" if i % 4 == 0 else "student")
            tags = rng.sample(dept_topics, k=min(3, len(dept_topics)))
            # Add 1 interdisciplinary tag for realistic cross-dept collaboration
            other_dept_topics = DEPARTMENTS_SPEC[(i + 1) % len(DEPARTMENTS_SPEC)][4]
            if i % 3 == 0:
                tags.append(rng.choice(other_dept_topics))
            u = User(
                email=email,
                username=uname,
                password_hash=default_pw_hash,
                full_name=f"{'Dr. ' if role == 'faculty' else ''}{fn} {ln}",
                role=role,
                department_id=dept_objs[dept_code].id,
                bio=f"{role.title()} in {dept_name} focusing on {tags[0].replace('-', ' ')}.",
                research_interests_text=f"Active research in {', '.join(t.replace('-', ' ') for t in tags)} within {dept_name}.",
                research_tags=tags,
                publication_links=[f"https://orcid.org/0000-0002-{1000+i:04d}-{5000+i:04d}"],
                personal_website=f"https://chanakyauniversity.edu.in/people/{uname}",
                is_synthetic=True,
                created_at=six_months_ago + timedelta(days=rng.randint(0, 45)),
            )
            db.add(u)
            db.flush()
            regular_users.append(u)

    # 6 Planted Spam / Bot Accounts
    spam_users: List[User] = []
    spam_gt = []
    for s_idx in range(6):
        dept_code = DEPARTMENTS_SPEC[s_idx % len(DEPARTMENTS_SPEC)][0]
        uname = f"promo_bot_acct_{s_idx + 1}"
        email = f"{uname}@spam-net.example.com"
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email,
                username=uname,
                password_hash=default_pw_hash,
                full_name=f"FastPublish Agent {s_idx + 1}",
                role="student",
                department_id=dept_objs[dept_code].id,
                bio="Instant publication & thesis writing promo.",
                research_interests_text="Fast publish guaranteed acceptance all journals.",
                research_tags=["promo", "fast-publish", "discount"],
                is_synthetic=True,
                created_at=now - timedelta(days=rng.randint(15, 60)),
            )
            db.add(u)
            db.flush()
        spam_users.append(u)
        spam_gt.append(
            {
                "user_id": u.id,
                "username": u.username,
                "email": u.email,
                "spam_pattern": "burst_rate + duplicate_promo_posts + tag_stuffing + off_hours_bot",
            }
        )
    db.commit()

    with open(gt_dir / "spam_accounts.json", "w", encoding="utf-8") as f:
        json.dump(spam_gt, f, indent=2)

    # Refresh full user lists
    all_regular = db.query(User).filter(~User.username.like("promo_bot_acct_%")).all()
    all_spam = db.query(User).filter(User.username.like("promo_bot_acct_%")).all()
    dept_id_to_code = {d.id: d.code for d in dept_objs.values()}

    # 4. Follow Relationships (UserFollow & TopicFollow)
    if db.query(UserFollow).count() < 200:
        existing_fl = {(f.follower_id, f.following_id) for f in db.query(UserFollow).all()}
        for u in all_regular:
            same_dept = [o for o in all_regular if o.id != u.id and o.department_id == u.department_id]
            other_dept = [o for o in all_regular if o.id != u.id and o.department_id != u.department_id]
            targets = rng.sample(same_dept, k=min(rng.randint(4, 7), len(same_dept))) + rng.sample(
                other_dept, k=min(rng.randint(2, 4), len(other_dept))
            )
            for tgt in targets:
                if (u.id, tgt.id) not in existing_fl:
                    db.add(UserFollow(follower_id=u.id, following_id=tgt.id, created_at=six_months_ago + timedelta(days=rng.randint(1, 150))))
                    existing_fl.add((u.id, tgt.id))
            for tag in (u.research_tags or [])[:3]:
                if not db.query(TopicFollow).filter(TopicFollow.user_id == u.id, TopicFollow.topic == tag.lower()).first():
                    db.add(TopicFollow(user_id=u.id, topic=tag.lower()))
        # Spam accounts mass-follow many users
        for su in all_spam:
            for tgt in rng.sample(all_regular, k=min(28, len(all_regular))):
                if (su.id, tgt.id) not in existing_fl:
                    db.add(UserFollow(follower_id=su.id, following_id=tgt.id))
                    existing_fl.add((su.id, tgt.id))
        db.commit()

    # 5. Personal Collections & Saved University Library Items (clustered for FP-Growth!)
    if db.query(SavedPaper).count() < 400:
        existing_saves = {(sp.user_id, sp.paper_id) for sp in db.query(SavedPaper).all()}
        # Pick 12 "core reading list" papers per department so members co-save realistically for FP-Growth
        dept_core_papers: Dict[str, List[Paper]] = {}
        for dcode in dept_objs.keys():
            pool = papers_by_dept.get(dcode, all_papers)
            dept_core_papers[dcode] = pool[: min(20, len(pool))]

        # Cross-departmental bridge papers
        bridge_papers = all_papers[:18]

        for u in all_regular:
            dcode = dept_id_to_code.get(u.department_id, "CSAI")
            col = Collection(
                user_id=u.id,
                name=f"{dcode} Core Reading List",
                description=f"Curated foundational and recent papers for {dcode} research.",
                is_private=False,
            )
            db.add(col)
            db.flush()

            core_pool = dept_core_papers.get(dcode, all_papers[:20])
            # Each user saves 7-11 core papers (creates rich FP-Growth itemsets) + 2-4 broader/bridge papers
            chosen = rng.sample(core_pool, k=min(rng.randint(7, 11), len(core_pool)))
            broader = papers_by_dept.get(dcode, all_papers)[15:60] or all_papers[:40]
            chosen += rng.sample(broader, k=min(rng.randint(2, 4), len(broader)))
            if rng.random() < 0.6:
                chosen += rng.sample(bridge_papers, k=min(2, len(bridge_papers)))

            for p in chosen:
                if (u.id, p.id) in existing_saves:
                    continue
                saved_ts = six_months_ago + timedelta(days=rng.randint(0, 178), hours=rng.randint(8, 22))
                db.add(
                    SavedPaper(
                        user_id=u.id,
                        paper_id=p.id,
                        collection_id=col.id,
                        private_notes=f"Key reference for {(p.topics or ['research'])[0]} literature survey.",
                        saved_at=saved_ts,
                    )
                )
                existing_saves.add((u.id, p.id))
                p.save_count = (p.save_count or 0) + 1
                p.in_university_library = True
                db.add(
                    ActivityEvent(
                        user_id=u.id,
                        event_type="save",
                        paper_id=p.id,
                        topic=(p.topics[0].lower() if p.topics else "general"),
                        department_id=u.department_id,
                        is_synthetic=True,
                        created_at=saved_ts,
                    )
                )
        db.commit()

    # 6. Posts & Comments (>= 2,200 combined across 6 months)
    if db.query(Post).count() < 400:
        lib_papers = db.query(Paper).filter(Paper.in_university_library == True).all() or all_papers
        created_posts: List[Post] = []

        # 430 legitimate posts
        for i in range(430):
            author = rng.choice(all_regular)
            dcode = dept_id_to_code.get(author.department_id, "CSAI")
            dept_topics = next(d[4] for d in DEPARTMENTS_SPEC if d[0] == dcode)
            t1 = rng.choice(author.research_tags or dept_topics)
            t2 = rng.choice(dept_topics)
            tpl_title, tpl_body = rng.choice(POST_TEMPLATES)
            attached = rng.choice(papers_by_dept.get(dcode, lib_papers)) if rng.random() < 0.65 else None
            # Realistic weekly wave across 6 months
            day_offset = rng.randint(0, 180)
            post_ts = six_months_ago + timedelta(days=day_offset, hours=rng.randint(9, 22), minutes=rng.randint(0, 59))
            po = Post(
                author_id=author.id,
                title=tpl_title.format(topic=t1.replace("-", " "), topic2=t2.replace("-", " "), dept=dcode),
                content=tpl_body.format(topic=t1.replace("-", " "), topic2=t2.replace("-", " "), dept=dcode),
                tags=list(dict.fromkeys([t1.lower(), t2.lower()])),
                attached_paper_id=attached.id if attached else None,
                attached_url=attached.url if attached else "",
                upvote_count=0,
                comment_count=0,
                is_synthetic=True,
                created_at=post_ts,
                updated_at=post_ts,
            )
            db.add(po)
            db.flush()
            created_posts.append(po)
            db.add(
                ActivityEvent(
                    user_id=author.id,
                    event_type="post",
                    post_id=po.id,
                    paper_id=attached.id if attached else None,
                    topic=t1.lower(),
                    department_id=author.department_id,
                    is_synthetic=True,
                    created_at=post_ts,
                )
            )

        # Plant spam posts from the 6 spam accounts (bursty, duplicate promo text, tag stuffing, 02:00-03:59 AM)
        for su in all_spam:
            burst_day = now - timedelta(days=rng.randint(3, 25))
            burst_hour = burst_day.replace(hour=rng.choice([2, 3]), minute=5, second=0, microsecond=0)
            for k in range(14):
                stitle, sbody = SPAM_POSTS[k % len(SPAM_POSTS)]
                ts = burst_hour + timedelta(minutes=k * 2)
                po = Post(
                    author_id=su.id,
                    title=stitle,
                    content=sbody,
                    tags=["promo", "fast-publish", "discount", "ai", "ml", "iot", "blockchain", "thesis", "scopus"],
                    upvote_count=0,
                    comment_count=0,
                    is_synthetic=True,
                    created_at=ts,
                    updated_at=ts,
                )
                db.add(po)
                db.flush()
                db.add(
                    ActivityEvent(
                        user_id=su.id,
                        event_type="post",
                        post_id=po.id,
                        topic="promo",
                        department_id=su.department_id,
                        is_synthetic=True,
                        created_at=ts,
                    )
                )

        # Upvotes + ~1,850 Comments & Replies on legitimate posts (total posts+comments > 2,350!)
        for po in created_posts:
            # Upvotes
            n_up = rng.randint(1, 10)
            upvoters = rng.sample(all_regular, k=min(n_up, len(all_regular)))
            for uv in upvoters:
                db.add(PostUpvote(user_id=uv.id, post_id=po.id, created_at=po.created_at + timedelta(hours=rng.randint(1, 48))))
            po.upvote_count = len(upvoters)

            # Comments + nested replies (average ~4.3 comments/post -> ~1,850 comments)
            n_comm = rng.randint(2, 7)
            top_comments = []
            for c_idx in range(n_comm):
                commenter = rng.choice(all_regular)
                dcode = dept_id_to_code.get(commenter.department_id, "CSAI")
                topic_str = (po.tags[0] if po.tags else "research").replace("-", " ")
                c_ts = min(now, po.created_at + timedelta(hours=rng.randint(1, 96)))
                parent_id = rng.choice(top_comments).id if (top_comments and c_idx >= 2 and rng.random() < 0.35) else None
                cm = Comment(
                    post_id=po.id,
                    author_id=commenter.id,
                    parent_comment_id=parent_id,
                    content=rng.choice(COMMENT_TEMPLATES).format(topic=topic_str, dept=dcode),
                    is_synthetic=True,
                    created_at=c_ts,
                )
                db.add(cm)
                db.flush()
                if parent_id is None:
                    top_comments.append(cm)
                db.add(
                    ActivityEvent(
                        user_id=commenter.id,
                        event_type="comment",
                        post_id=po.id,
                        topic=(po.tags[0] if po.tags else "general"),
                        department_id=commenter.department_id,
                        is_synthetic=True,
                        created_at=c_ts,
                    )
                )
            po.comment_count = n_comm

        # Spam accounts post bursty duplicate comments & night events
        for su in all_spam:
            burst_ts = (now - timedelta(days=rng.randint(2, 18))).replace(hour=3, minute=10, second=0, microsecond=0)
            for k in range(18):
                target_po = rng.choice(created_posts)
                ts = burst_ts + timedelta(minutes=k)
                db.add(
                    Comment(
                        post_id=target_po.id,
                        author_id=su.id,
                        content="Click here for guaranteed acceptance fast publish discount promo! Contact telegram now!",
                        is_synthetic=True,
                        created_at=ts,
                    )
                )
                target_po.comment_count = (target_po.comment_count or 0) + 1
                db.add(
                    ActivityEvent(
                        user_id=su.id,
                        event_type="view",
                        paper_id=rng.choice(all_papers).id,
                        topic="promo",
                        department_id=su.department_id,
                        is_synthetic=True,
                        created_at=ts,
                    )
                )
        db.commit()

    # 7. Activity Events (views & searches across 6 months to exceed 12,000 total events!)
    current_events = db.query(ActivityEvent).count()
    target_events = 12200
    if current_events < target_events:
        needed_ev = target_events - current_events
        search_queries_by_topic = {
            t: [
                f"{t.replace('-', ' ')} survey",
                f"{t.replace('-', ' ')} benchmark",
                f"recent advances in {t.replace('-', ' ')}",
                f"{t.replace('-', ' ')} optimization",
            ]
            for _c, _n, _h, _d, tlist in DEPARTMENTS_SPEC
            for t in tlist
        }

        bulk_events = []
        for _ in range(needed_ev):
            u = rng.choice(all_regular)
            dcode = dept_id_to_code.get(u.department_id, "CSAI")
            dept_topics = next(d[4] for d in DEPARTMENTS_SPEC if d[0] == dcode)
            topic = rng.choice(u.research_tags or dept_topics).lower()
            ev_type = "view" if rng.random() < 0.68 else "search"
            # Realistic weekly wave: weekdays busier, slight upward trend
            day_offset = rng.randint(0, 180)
            ts = six_months_ago + timedelta(days=day_offset, hours=rng.randint(8, 23), minutes=rng.randint(0, 59))
            if ev_type == "view":
                cand_papers = papers_by_topic.get(topic) or papers_by_dept.get(dcode) or all_papers
                p = rng.choice(cand_papers)
                bulk_events.append(
                    ActivityEvent(
                        user_id=u.id,
                        event_type="view",
                        paper_id=p.id,
                        topic=topic,
                        department_id=u.department_id,
                        is_synthetic=True,
                        created_at=ts,
                    )
                )
            else:
                q_str = rng.choice(search_queries_by_topic.get(topic, [topic.replace("-", " ")]))
                bulk_events.append(
                    ActivityEvent(
                        user_id=u.id,
                        event_type="search",
                        query_text=q_str,
                        topic=topic,
                        department_id=u.department_id,
                        metadata_json={"mode": rng.choice(["hybrid", "semantic", "keyword"])},
                        is_synthetic=True,
                        created_at=ts,
                    )
                )
        db.bulk_save_objects(bulk_events)
        db.commit()

    # 8. Plant 3 Sudden Research Topic Spikes in specific recent weeks (recorded in ground_truth/topic_spikes.json)
    planted_spikes = PLANTED_TOPIC_SPIKES
    ensure_planted_topic_spikes(
        db,
        dept_objs=dept_objs,
        all_regular=all_regular,
        papers_by_topic=papers_by_topic,
        papers_by_dept=papers_by_dept,
        all_papers=all_papers,
        rng=rng,
        now=now,
        gt_dir=gt_dir,
    )

    # 9. Create Duplicate Ground Truth & Search/RAG Ground Truth
    dup_info = _create_duplicate_ground_truth(db, rng, gt_dir)
    eval_gt_info = _create_search_and_rag_ground_truth(db, gt_dir)

    summary = {
        "departments": db.query(Department).count(),
        "users": db.query(User).count(),
        "planted_spam_accounts": len(all_spam),
        "papers_total": db.query(Paper).count(),
        "papers_external_real": db.query(Paper).filter(Paper.is_synthetic == False).count(),
        "papers_synthetic": db.query(Paper).filter(Paper.is_synthetic == True).count(),
        "papers_in_university_library": db.query(Paper).filter(Paper.in_university_library == True).count(),
        "citation_edges": db.query(PaperCitation).count(),
        "user_follows": db.query(UserFollow).count(),
        "saved_papers": db.query(SavedPaper).count(),
        "posts": db.query(Post).count(),
        "comments": db.query(Comment).count(),
        "posts_and_comments_combined": db.query(Post).count() + db.query(Comment).count(),
        "activity_events": db.query(ActivityEvent).count(),
        "synthetic_papers_added_this_run": syn_papers_added,
        "citations_added_this_run": citations_added,
        "ground_truth": {
            **dup_info,
            "planted_topic_spikes": len(planted_spikes),
            "planted_spam_accounts": len(spam_gt),
            **eval_gt_info,
        },
    }
    with open(syn_dir / "dataset_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary
