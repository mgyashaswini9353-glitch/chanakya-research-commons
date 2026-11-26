"""
F4 External Scholarly Data Ingestion Pipeline (Bronze -> Silver ELT).
Integrates:
  1. OpenAlex API (open scholarly works + abstracts + citation references)
  2. arXiv Atom API (preprints + abstracts + categories)
  3. Semantic Scholar Graph API (optional/polite rate-limited fetch)
  4. Curated Open RSS Research Feeds (technical & academic research news)

Preserves untouched raw payloads in data/raw/<source>/ (and optional MinIO bucket),
transforms and deduplicates via PaperDeduplicator, loads into PostgreSQL/SQLAlchemy,
generates Silver Parquet dataset, and logs every run in ingestion_jobs.
"""
from __future__ import annotations

import json
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import feedparser
import httpx
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.models import IngestionJob, Paper, PaperCitation
from ml.duplicate_detection.deduplicator import (
    PaperDeduplicator,
    make_canonical_key,
    merge_source_lists,
    normalize_arxiv_id,
    normalize_authors_list,
    normalize_doi,
    normalize_title,
)

logger = logging.getLogger(__name__)

# Research areas mapped to the 6 Chanakya University departments
DEPARTMENT_TOPICS = [
    ("CSAI", "retrieval augmented generation large language models", ["large-language-models", "retrieval-augmented-generation", "natural-language-processing"]),
    ("CSAI", "graph neural networks computer vision", ["graph-neural-networks", "computer-vision", "deep-learning"]),
    ("DSE", "data warehousing lakehouse query optimization", ["data-warehousing", "data-mining", "lakehouse-analytics"]),
    ("DSE", "federated learning anomaly detection streaming", ["federated-learning", "anomaly-detection", "stream-mining"]),
    ("ECE", "edge ai tinyml autonomous robotics", ["edge-ai", "autonomous-robotics", "embedded-systems"]),
    ("ECE", "vlsi neuromorphic computing iot sensors", ["neuromorphic-computing", "iot-systems", "signal-processing"]),
    ("BIO", "protein folding bioinformatics crispr genomics", ["bioinformatics", "genomics", "computational-biology"]),
    ("BIO", "medical imaging drug discovery machine learning", ["medical-imaging", "drug-discovery", "healthcare-ai"]),
    ("MGT", "algorithmic economics supply chain optimization", ["computational-economics", "supply-chain-analytics", "decision-science"]),
    ("MGT", "fintech fraud detection behavioral analytics", ["financial-analytics", "fraud-detection", "causal-inference"]),
    ("REM", "solid state batteries perovskite solar cells", ["solid-state-batteries", "solar-photovoltaics", "energy-materials"]),
    ("REM", "smart grid microgrid renewable energy forecasting", ["smart-grid", "renewable-energy", "climate-modeling"]),
]

CURATED_RSS_FEEDS = [
    ("MIT News AI", "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml", "CSAI", ["artificial-intelligence", "research-news"]),
    ("arXiv cs.DB", "https://rss.arxiv.org/rss/cs.DB", "DSE", ["databases", "data-warehousing"]),
    ("arXiv cs.LG", "https://rss.arxiv.org/rss/cs.LG", "CSAI", ["machine-learning", "deep-learning"]),
]


def _reconstruct_openalex_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    pos_word: List[Tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            pos_word.append((pos, word))
    if not pos_word:
        return ""
    pos_word.sort(key=lambda x: x[0])
    return " ".join(w for _, w in pos_word)


def _save_raw_payload(source: str, tag: str, payload: Any) -> str:
    raw_dir = Path(settings.RAW_DATA_DIR) / source
    raw_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_tag = "".join(c if c.isalnum() or c in "-_" else "_" for c in tag)[:40]
    file_path = raw_dir / f"{ts}_{safe_tag}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Optional MinIO Bronze Lake upload when enabled
    if settings.MINIO_ENABLED:
        try:
            from minio import Minio

            endpoint = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
            client = Minio(
                endpoint,
                access_key=settings.MINIO_ROOT_USER,
                secret_key=settings.MINIO_ROOT_PASSWORD,
                secure=settings.MINIO_ENDPOINT.startswith("https://"),
            )
            if not client.bucket_exists(settings.MINIO_BUCKET_RAW):
                client.make_bucket(settings.MINIO_BUCKET_RAW)
            client.fput_object(settings.MINIO_BUCKET_RAW, f"{source}/{file_path.name}", str(file_path))
        except Exception as exc:
            logger.debug("MinIO upload skipped: %s", exc)

    return str(file_path)


def upsert_paper_record(
    db: Session,
    record: Dict[str, Any],
    deduper: Optional[PaperDeduplicator] = None,
    existing_cache: Optional[List[Paper]] = None,
) -> Tuple[Paper, str]:
    """
    Insert or deduplicate-merge a paper into PostgreSQL/SQLAlchemy.
    Returns (paper_obj, action) where action in {'inserted', 'merged', 'skipped'}.
    """
    deduper = deduper or PaperDeduplicator()
    title = (record.get("title") or "").strip()
    if not title:
        raise ValueError("Paper title is required")

    doi = normalize_doi(record.get("doi"))
    arxiv_id = normalize_arxiv_id(record.get("arxiv_id"))
    norm_title = normalize_title(title)
    authors = [str(a).strip() for a in (record.get("authors") or []) if str(a).strip()]
    norm_authors = normalize_authors_list(authors)
    canonical_key = make_canonical_key(title, doi=doi, arxiv_id=arxiv_id)

    source_entry = {
        "source": record.get("primary_source", "openalex"),
        "external_id": record.get("external_id") or doi or arxiv_id or canonical_key,
        "url": record.get("url") or "",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Exact lookups first (fast indexed path)
    match: Optional[Paper] = None
    if doi:
        match = db.query(Paper).filter(Paper.doi == doi).first()
    if not match and arxiv_id:
        match = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
    if not match:
        match = db.query(Paper).filter(Paper.canonical_key == canonical_key).first()
    if not match:
        match = db.query(Paper).filter(Paper.normalized_title == norm_title).first()

    # 2. Near-duplicate check against cached candidates with same year or title prefix
    if not match and existing_cache:
        prefix = norm_title[:18]
        for cand in existing_cache:
            if cand.normalized_title[:18] == prefix or (
                record.get("publication_year") and cand.publication_year == record.get("publication_year")
            ):
                is_dup, _method, _score = deduper.is_duplicate_pair(
                    {"title": cand.title, "abstract": cand.abstract, "authors": cand.authors, "doi": cand.doi, "arxiv_id": cand.arxiv_id},
                    {"title": title, "abstract": record.get("abstract", ""), "authors": authors, "doi": doi, "arxiv_id": arxiv_id},
                )
                if is_dup:
                    match = cand
                    break

    if match:
        # Incremental skip check: already has this exact source+external_id
        existing_pairs = {(s.get("source"), s.get("external_id")) for s in (match.sources or [])}
        is_same_source = (source_entry["source"], source_entry["external_id"]) in existing_pairs

        match.sources = merge_source_lists(match.sources or [], [source_entry])
        if doi and not match.doi:
            match.doi = doi
        if arxiv_id and not match.arxiv_id:
            match.arxiv_id = arxiv_id
        if record.get("abstract") and len(record["abstract"]) > len(match.abstract or ""):
            match.abstract = record["abstract"]
        if record.get("citation_count", 0) > (match.citation_count or 0):
            match.citation_count = int(record["citation_count"])
        if record.get("pdf_url") and not match.pdf_url:
            match.pdf_url = record["pdf_url"]
        merged_topics = sorted(set([str(t).lower() for t in (match.topics or [])] + [str(t).lower() for t in (record.get("topics") or [])]))
        match.topics = merged_topics[:8]
        db.flush()
        return match, ("skipped" if is_same_source else "merged")

    paper = Paper(
        canonical_key=canonical_key,
        title=title,
        normalized_title=norm_title,
        abstract=(record.get("abstract") or "").strip(),
        authors=authors,
        normalized_authors=norm_authors,
        publication_year=record.get("publication_year"),
        published_date=record.get("published_date") or "",
        venue=(record.get("venue") or "").strip()[:250],
        doi=doi,
        arxiv_id=arxiv_id,
        url=(record.get("url") or "").strip()[:990],
        pdf_url=(record.get("pdf_url") or "").strip()[:990],
        topics=sorted(set(str(t).lower().strip() for t in (record.get("topics") or []) if str(t).strip()))[:8],
        department_hint=record.get("department_hint"),
        sources=[source_entry],
        primary_source=record.get("primary_source", "openalex"),
        citation_count=int(record.get("citation_count") or 0),
        pagerank_score=0.0,
        save_count=0,
        in_university_library=bool(record.get("in_university_library", False)),
        is_synthetic=bool(record.get("is_synthetic", False)),
    )
    db.add(paper)
    db.flush()
    if existing_cache is not None:
        existing_cache.append(paper)
    return paper, "inserted"


def ingest_openalex(
    db: Session,
    queries: Optional[List[Tuple[str, str, List[str]]]] = None,
    per_query: int = 35,
) -> Dict[str, Any]:
    """Fetch real scholarly papers, abstracts, and citation links from OpenAlex API."""
    queries = queries or DEPARTMENT_TOPICS
    job = IngestionJob(
        source="openalex",
        query_params={"queries": [q[1] for q in queries], "per_query": per_query},
        status="running",
    )
    db.add(job)
    db.commit()

    deduper = PaperDeduplicator()
    existing_cache = db.query(Paper).all()
    raw_batches = []
    fetched = inserted = merged = 0
    openalex_id_to_paper_id: Dict[str, int] = {}
    pending_refs: List[Tuple[int, List[str]]] = []

    try:
        headers = {"User-Agent": f"ChanakyaResearchCommons/1.0 (mailto:{settings.OPENALEX_MAILTO})"}
        with httpx.Client(timeout=20.0, headers=headers) as client:
            for dept_code, query_str, default_topics in queries:
                url = "https://api.openalex.org/works"
                params = {
                    "search": query_str,
                    "filter": "has_abstract:true,from_publication_date:2020-01-01",
                    "per-page": min(per_query, 50),
                    "sort": "cited_by_count:desc",
                    "mailto": settings.OPENALEX_MAILTO,
                }
                resp = client.get(url, params=params)
                if resp.status_code != 200:
                    logger.warning("OpenAlex query '%s' returned %s", query_str, resp.status_code)
                    continue
                payload = resp.json()
                results = payload.get("results", [])
                raw_batches.append({"department": dept_code, "query": query_str, "count": len(results), "results": results})

                for w in results:
                    fetched += 1
                    abstract = _reconstruct_openalex_abstract(w.get("abstract_inverted_index"))
                    if len(abstract) < 60:
                        continue
                    title = w.get("display_name") or w.get("title") or ""
                    if not title:
                        continue
                    authors = [
                        a.get("author", {}).get("display_name", "")
                        for a in (w.get("authorships") or [])[:8]
                        if a.get("author", {}).get("display_name")
                    ]
                    concepts = [
                        c.get("display_name", "").lower().replace(" ", "-")
                        for c in (w.get("concepts") or [])[:4]
                        if c.get("display_name") and (c.get("score") or 0) >= 0.35
                    ]
                    topics = list(dict.fromkeys(default_topics + concepts))[:6]
                    primary_loc = w.get("primary_location") or {}
                    source_obj = primary_loc.get("source") or {}
                    venue = source_obj.get("display_name") or ""
                    oa_info = w.get("open_access") or {}
                    oa_id = w.get("id") or ""
                    doi = normalize_doi(w.get("doi"))
                    landing = primary_loc.get("landing_page_url") or (f"https://doi.org/{doi}" if doi else oa_id)

                    rec = {
                        "title": title,
                        "abstract": abstract,
                        "authors": authors,
                        "publication_year": w.get("publication_year"),
                        "published_date": w.get("publication_date") or "",
                        "venue": venue,
                        "doi": doi,
                        "arxiv_id": None,
                        "url": landing,
                        "pdf_url": oa_info.get("oa_url") or "",
                        "topics": topics,
                        "department_hint": dept_code,
                        "primary_source": "openalex",
                        "external_id": oa_id,
                        "citation_count": w.get("cited_by_count") or 0,
                        "is_synthetic": False,
                    }
                    paper, action = upsert_paper_record(db, rec, deduper=deduper, existing_cache=existing_cache)
                    if action == "inserted":
                        inserted += 1
                    elif action == "merged":
                        merged += 1
                    if oa_id:
                        openalex_id_to_paper_id[oa_id] = paper.id
                    refs = w.get("referenced_works") or []
                    if refs:
                        pending_refs.append((paper.id, refs[:25]))
                time.sleep(0.15)

        # Link real OpenAlex citation edges between ingested papers
        edges_added = 0
        existing_edges = {(e.citing_paper_id, e.cited_paper_id) for e in db.query(PaperCitation).all()}
        for citing_id, ref_oa_ids in pending_refs:
            for ref_oa in ref_oa_ids:
                cited_id = openalex_id_to_paper_id.get(ref_oa)
                if cited_id and cited_id != citing_id and (citing_id, cited_id) not in existing_edges:
                    db.add(PaperCitation(citing_paper_id=citing_id, cited_paper_id=cited_id))
                    existing_edges.add((citing_id, cited_id))
                    edges_added += 1

        raw_path = _save_raw_payload("openalex", "batch_works", raw_batches)
        job.status = "completed"
        job.records_fetched = fetched
        job.records_inserted = inserted
        job.records_merged = merged
        job.raw_file_path = raw_path
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        export_silver_papers_parquet(db)
        return {
            "job_id": job.id,
            "source": "openalex",
            "status": "completed",
            "records_fetched": fetched,
            "records_inserted": inserted,
            "records_merged": merged,
            "citation_edges_added": edges_added,
            "raw_file_path": raw_path,
        }
    except Exception as exc:
        logger.exception("OpenAlex ingestion failed")
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {"job_id": job.id, "source": "openalex", "status": "failed", "error": str(exc)}


def ingest_arxiv(
    db: Session,
    queries: Optional[List[Tuple[str, str, List[str]]]] = None,
    per_query: int = 20,
    max_retries: int = 2,
    request_timeout: float = 30.0,
) -> Dict[str, Any]:
    """Fetch real preprints and abstracts from the open arXiv Atom API with retries and per-query isolation."""
    queries = queries or DEPARTMENT_TOPICS[:8]
    job = IngestionJob(
        source="arxiv",
        query_params={"queries": [q[1] for q in queries], "per_query": per_query},
        status="running",
    )
    db.add(job)
    db.commit()

    deduper = PaperDeduplicator()
    existing_cache = db.query(Paper).all()
    raw_entries = []
    fetched = inserted = merged = 0
    succeeded_queries = 0
    query_errors: List[str] = []

    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    try:
        headers = {"User-Agent": f"ChanakyaResearchCommons/1.0 (mailto:{settings.OPENALEX_MAILTO})"}
        base_delay = max(1.5, float(settings.ARXIV_RATE_LIMIT_SECONDS))
        with httpx.Client(timeout=request_timeout, headers=headers, follow_redirects=True) as client:
            for idx, (dept_code, query_str, default_topics) in enumerate(queries):
                if idx > 0:
                    time.sleep(base_delay)
                search_q = " AND ".join(f"all:{tok}" for tok in query_str.split()[:3])
                params = {
                    "search_query": search_q,
                    "start": 0,
                    "max_results": min(per_query, 30),
                    "sortBy": "relevance",
                    "sortOrder": "descending",
                }
                resp = None
                last_exc: Optional[Exception] = None
                for attempt in range(max_retries + 1):
                    try:
                        resp = client.get("https://export.arxiv.org/api/query", params=params)
                        if resp.status_code == 200:
                            last_exc = None
                            break
                        if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                            backoff = base_delay * (2 ** attempt)
                            logger.warning("arXiv query '%s' returned %s; retrying in %.1fs", query_str, resp.status_code, backoff)
                            time.sleep(backoff)
                            continue
                        query_errors.append(f"{query_str}: HTTP {resp.status_code}")
                        resp = None
                        break
                    except (httpx.TimeoutException, httpx.TransportError) as exc:
                        last_exc = exc
                        if attempt < max_retries:
                            backoff = base_delay * (2 ** attempt)
                            logger.warning("arXiv query '%s' failed (%s); retrying in %.1fs", query_str, exc, backoff)
                            time.sleep(backoff)
                        else:
                            query_errors.append(f"{query_str}: {exc}")
                            resp = None

                if resp is None:
                    if last_exc:
                        logger.warning("arXiv query '%s' skipped after retries: %s", query_str, last_exc)
                    continue

                try:
                    root = ET.fromstring(resp.text)
                except ET.ParseError as exc:
                    query_errors.append(f"{query_str}: XML parse error ({exc})")
                    logger.warning("arXiv XML parse failed for '%s': %s", query_str, exc)
                    continue

                succeeded_queries += 1
                entries = root.findall("atom:entry", ns)
                for ent in entries:
                    fetched += 1
                    raw_id = (ent.findtext("atom:id", "", ns) or "").strip()
                    arxiv_id = normalize_arxiv_id(raw_id)
                    title = " ".join((ent.findtext("atom:title", "", ns) or "").split())
                    abstract = " ".join((ent.findtext("atom:summary", "", ns) or "").split())
                    if not title or len(abstract) < 60:
                        continue
                    published = (ent.findtext("atom:published", "", ns) or "")[:10]
                    year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
                    authors = [
                        (a.findtext("atom:name", "", ns) or "").strip()
                        for a in ent.findall("atom:author", ns)
                        if (a.findtext("atom:name", "", ns) or "").strip()
                    ]
                    doi = normalize_doi(ent.findtext("arxiv:doi", "", ns))
                    cats = [c.attrib.get("term", "") for c in ent.findall("atom:category", ns) if c.attrib.get("term")]
                    raw_entries.append(
                        {
                            "arxiv_id": arxiv_id,
                            "title": title,
                            "summary": abstract,
                            "authors": authors,
                            "published": published,
                            "doi": doi,
                            "categories": cats,
                            "department": dept_code,
                        }
                    )
                    rec = {
                        "title": title,
                        "abstract": abstract,
                        "authors": authors,
                        "publication_year": year,
                        "published_date": published,
                        "venue": f"arXiv ({cats[0]})" if cats else "arXiv",
                        "doi": doi,
                        "arxiv_id": arxiv_id,
                        "url": raw_id or f"https://arxiv.org/abs/{arxiv_id}",
                        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else "",
                        "topics": default_topics,
                        "department_hint": dept_code,
                        "primary_source": "arxiv",
                        "external_id": arxiv_id or raw_id,
                        "citation_count": 0,
                        "is_synthetic": False,
                    }
                    _paper, action = upsert_paper_record(db, rec, deduper=deduper, existing_cache=existing_cache)
                    if action == "inserted":
                        inserted += 1
                    elif action == "merged":
                        merged += 1

        raw_path = _save_raw_payload("arxiv", "batch_preprints", raw_entries) if raw_entries else ""
        if succeeded_queries == 0:
            job.status = "failed"
            job.error_message = "; ".join(query_errors[:5]) or "All arXiv queries failed"
        else:
            job.status = "completed"
            job.error_message = "; ".join(query_errors[:5]) if query_errors else ""
        job.records_fetched = fetched
        job.records_inserted = inserted
        job.records_merged = merged
        job.raw_file_path = raw_path
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        if inserted > 0 or merged > 0:
            export_silver_papers_parquet(db)
        return {
            "job_id": job.id,
            "source": "arxiv",
            "status": job.status,
            "queries_succeeded": succeeded_queries,
            "queries_failed": len(query_errors),
            "records_fetched": fetched,
            "records_inserted": inserted,
            "records_merged": merged,
            "raw_file_path": raw_path,
            "errors": query_errors[:5],
        }
    except Exception as exc:
        logger.exception("arXiv ingestion failed")
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {"job_id": job.id, "source": "arxiv", "status": "failed", "error": str(exc)}


def ingest_curated_rss(db: Session, max_per_feed: int = 12) -> Dict[str, Any]:
    """Ingest research news & technical articles from curated open RSS feeds."""
    job = IngestionJob(
        source="rss",
        query_params={"feeds": [f[0] for f in CURATED_RSS_FEEDS]},
        status="running",
    )
    db.add(job)
    db.commit()

    deduper = PaperDeduplicator()
    existing_cache = db.query(Paper).all()
    raw_items = []
    fetched = inserted = merged = 0

    try:
        for feed_name, feed_url, dept_code, topics in CURATED_RSS_FEEDS:
            try:
                parsed = feedparser.parse(feed_url)
            except Exception:
                continue
            for entry in (parsed.entries or [])[:max_per_feed]:
                fetched += 1
                title = " ".join((entry.get("title") or "").split())
                summary = " ".join((entry.get("summary") or entry.get("description") or "").split())
                # Strip simple HTML tags
                import re
                summary = re.sub(r"<[^>]+>", " ", summary)
                summary = re.sub(r"\s+", " ", summary).strip()
                if not title or len(summary) < 40:
                    continue
                link = entry.get("link") or ""
                author = entry.get("author") or feed_name
                pub_year = datetime.now(timezone.utc).year
                if entry.get("published_parsed"):
                    pub_year = entry.published_parsed.tm_year

                raw_items.append({"feed": feed_name, "title": title, "summary": summary, "link": link, "author": author})
                rec = {
                    "title": title,
                    "abstract": summary[:1600],
                    "authors": [author],
                    "publication_year": pub_year,
                    "published_date": str(pub_year),
                    "venue": feed_name,
                    "doi": None,
                    "arxiv_id": normalize_arxiv_id(link) if "arxiv.org" in link else None,
                    "url": link,
                    "pdf_url": "",
                    "topics": topics,
                    "department_hint": dept_code,
                    "primary_source": "rss",
                    "external_id": link or title[:80],
                    "citation_count": 0,
                    "is_synthetic": False,
                }
                _paper, action = upsert_paper_record(db, rec, deduper=deduper, existing_cache=existing_cache)
                if action == "inserted":
                    inserted += 1
                elif action == "merged":
                    merged += 1

        raw_path = _save_raw_payload("rss", "curated_feeds", raw_items)
        job.status = "completed"
        job.records_fetched = fetched
        job.records_inserted = inserted
        job.records_merged = merged
        job.raw_file_path = raw_path
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        export_silver_papers_parquet(db)
        return {
            "job_id": job.id,
            "source": "rss",
            "status": "completed",
            "records_fetched": fetched,
            "records_inserted": inserted,
            "records_merged": merged,
            "raw_file_path": raw_path,
        }
    except Exception as exc:
        logger.exception("RSS ingestion failed")
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {"job_id": job.id, "source": "rss", "status": "failed", "error": str(exc)}


def fetch_paper_metadata_by_identifier(
    doi: Optional[str] = None,
    arxiv_id: Optional[str] = None,
    url: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Live lookup for F3 'Add paper by DOI / arXiv ID / URL' via OpenAlex or arXiv."""
    ndoi = normalize_doi(doi)
    narx = normalize_arxiv_id(arxiv_id)
    if not narx and url and "arxiv.org" in url.lower():
        narx = normalize_arxiv_id(url)
    if not ndoi and url and "doi.org/" in url.lower():
        ndoi = normalize_doi(url)

    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            if ndoi:
                r = client.get(f"https://api.openalex.org/works/https://doi.org/{ndoi}")
                if r.status_code == 200:
                    w = r.json()
                    return {
                        "title": w.get("display_name") or f"Paper DOI:{ndoi}",
                        "abstract": _reconstruct_openalex_abstract(w.get("abstract_inverted_index")),
                        "authors": [a.get("author", {}).get("display_name", "") for a in (w.get("authorships") or [])[:8]],
                        "publication_year": w.get("publication_year"),
                        "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name", ""),
                        "doi": ndoi,
                        "arxiv_id": narx,
                        "url": url or f"https://doi.org/{ndoi}",
                        "topics": [c.get("display_name", "").lower().replace(" ", "-") for c in (w.get("concepts") or [])[:4]],
                        "primary_source": "openalex",
                        "external_id": w.get("id") or ndoi,
                        "citation_count": w.get("cited_by_count") or 0,
                        "is_synthetic": False,
                    }
            if narx:
                r = client.get("https://export.arxiv.org/api/query", params={"id_list": narx})
                if r.status_code == 200:
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    root = ET.fromstring(r.text)
                    ent = root.find("atom:entry", ns)
                    if ent is not None:
                        title = " ".join((ent.findtext("atom:title", "", ns) or "").split())
                        summary = " ".join((ent.findtext("atom:summary", "", ns) or "").split())
                        pub = (ent.findtext("atom:published", "", ns) or "")[:10]
                        authors = [(a.findtext("atom:name", "", ns) or "").strip() for a in ent.findall("atom:author", ns)]
                        return {
                            "title": title,
                            "abstract": summary,
                            "authors": authors,
                            "publication_year": int(pub[:4]) if len(pub) >= 4 and pub[:4].isdigit() else None,
                            "venue": "arXiv",
                            "doi": ndoi,
                            "arxiv_id": narx,
                            "url": url or f"https://arxiv.org/abs/{narx}",
                            "pdf_url": f"https://arxiv.org/pdf/{narx}.pdf",
                            "topics": ["preprint", "arxiv"],
                            "primary_source": "arxiv",
                            "external_id": narx,
                            "citation_count": 0,
                            "is_synthetic": False,
                        }
    except Exception as exc:
        logger.warning("Metadata lookup failed: %s", exc)
    return None


def export_silver_papers_parquet(db: Session) -> str:
    """Write cleaned Silver layer papers dataset to data/processed/papers_silver.parquet."""
    out_dir = Path(settings.PROCESSED_DATA_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    papers = db.query(Paper).all()
    rows = [
        {
            "id": p.id,
            "canonical_key": p.canonical_key,
            "title": p.title,
            "normalized_title": p.normalized_title,
            "abstract": p.abstract,
            "authors": "; ".join(p.authors or []),
            "publication_year": p.publication_year,
            "venue": p.venue,
            "doi": p.doi or "",
            "arxiv_id": p.arxiv_id or "",
            "topics": "; ".join(p.topics or []),
            "department_hint": p.department_hint or "",
            "primary_source": p.primary_source,
            "source_count": len(p.sources or []),
            "citation_count": p.citation_count,
            "pagerank_score": p.pagerank_score,
            "save_count": p.save_count,
            "in_university_library": p.in_university_library,
            "is_synthetic": p.is_synthetic,
        }
        for p in papers
    ]
    out_path = out_dir / "papers_silver.parquet"
    pd.DataFrame(rows).to_parquet(out_path, index=False, engine="pyarrow")
    return str(out_path)
