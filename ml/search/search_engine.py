"""
F5 Unified Research Search Engine + Citation Graph PageRank.
Supports:
  - Keyword search (TF-IDF / BM25-weighted multi-field matching + filters)
  - Semantic search (384-dim cosine similarity via pgvector/embeddings)
  - Hybrid search (Reciprocal Rank Fusion + Citation Graph PageRank boost)
  - Four unified panels: External Papers, Chanakya Library, Researchers, Posts & Discussions
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional

import networkx as nx
import numpy as np
from sqlalchemy.orm import Session

from backend.app.models.models import Department, Paper, PaperCitation, Post, User
from ml.embeddings.embedder import cosine_similarity_matrix, get_embedder


def compute_and_store_pagerank(db: Session) -> int:
    """Compute PageRank on the citation graph using NetworkX and update papers.pagerank_score."""
    papers = db.query(Paper).all()
    if not papers:
        return 0

    G = nx.DiGraph()
    for p in papers:
        G.add_node(p.id)
    for edge in db.query(PaperCitation).all():
        if G.has_node(edge.citing_paper_id) and G.has_node(edge.cited_paper_id):
            G.add_edge(edge.citing_paper_id, edge.cited_paper_id)

    if G.number_of_edges() > 0:
        pr = nx.pagerank(G, alpha=0.85)
    else:
        total_cites = sum((p.citation_count or 0) + 1 for p in papers)
        pr = {p.id: ((p.citation_count or 0) + 1) / max(1, total_cites) for p in papers}

    # Normalize to [0, 1] scale for interpretable display & hybrid ranking
    max_pr = max(pr.values()) if pr else 1.0
    for p in papers:
        p.pagerank_score = round(float(pr.get(p.id, 0.0) / max(max_pr, 1e-9)), 6)
    db.commit()
    return len(papers)


def _tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) >= 2]


def _keyword_score_paper(query_tokens: List[str], query_phrase: str, paper: Paper) -> float:
    if not query_tokens:
        return 0.0
    title_l = (paper.title or "").lower()
    abs_l = (paper.abstract or "").lower()
    topics_l = " ".join(paper.topics or []).lower()
    authors_l = " ".join(paper.authors or []).lower()
    venue_l = (paper.venue or "").lower()

    score = 0.0
    if query_phrase and len(query_phrase) >= 3 and query_phrase in title_l:
        score += 4.5
    if query_phrase and len(query_phrase) >= 3 and query_phrase in abs_l:
        score += 2.0

    matched_terms = 0
    for tok in set(query_tokens):
        term_score = 0.0
        if tok in title_l:
            term_score += 2.6
        if tok in topics_l:
            term_score += 2.2
        if tok in authors_l:
            term_score += 1.6
        if tok in venue_l:
            term_score += 0.9
        cnt_abs = abs_l.count(tok)
        if cnt_abs > 0:
            term_score += min(2.0, 0.65 * (1.0 + math.log(1 + cnt_abs)))
        if term_score > 0:
            matched_terms += 1
            score += term_score

    coverage = matched_terms / max(1, len(set(query_tokens)))
    return round(score * (0.45 + 0.55 * coverage), 6)


def search_papers_ranked(
    db: Session,
    query: str,
    mode: str = "hybrid",
    only_library: bool = False,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    source: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 20,
    max_paper_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    q = db.query(Paper)
    if max_paper_id is not None:
        q = q.filter(Paper.id <= max_paper_id)
    if only_library:
        q = q.filter(Paper.in_university_library == True)
    if year_from is not None:
        q = q.filter(Paper.publication_year >= year_from)
    if year_to is not None:
        q = q.filter(Paper.publication_year <= year_to)
    if source:
        q = q.filter(Paper.primary_source == source)

    papers = q.all()
    if tag:
        tag_l = tag.strip().lower()
        papers = [p for p in papers if any(tag_l in str(t).lower() for t in (p.topics or []))]

    if not papers:
        return []

    query_clean = (query or "").strip()
    if not query_clean:
        papers.sort(key=lambda p: (p.save_count or 0, p.pagerank_score or 0.0, p.citation_count or 0), reverse=True)
        return [_serialize_paper_hit(p, score=float(p.pagerank_score or 0.0), kw=0.0, sem=0.0) for p in papers[:limit]]

    query_tokens = _tokenize(query_clean)
    query_phrase = query_clean.lower()

    # 1. Keyword scores
    kw_scores = np.array([_keyword_score_paper(query_tokens, query_phrase, p) for p in papers], dtype=np.float32)

    # 2. Semantic scores
    sem_scores = np.zeros(len(papers), dtype=np.float32)
    if mode in ("semantic", "hybrid"):
        embedder = get_embedder()
        q_vec = embedder.encode([query_clean])[0]
        valid_idx = [i for i, p in enumerate(papers) if p.embedding and len(p.embedding) > 0]
        if valid_idx:
            mat = np.array([papers[i].embedding for i in valid_idx], dtype=np.float32)
            sims = cosine_similarity_matrix(q_vec, mat)
            for idx_pos, sim_val in zip(valid_idx, sims):
                sem_scores[idx_pos] = max(0.0, float(sim_val))

    # 3. Combine depending on mode (anisotropy-adjusted semantic score + calibrated RRF k=60 + gentle PageRank)
    kw_max = float(kw_scores.max()) if kw_scores.size and kw_scores.max() > 0 else 1.0
    sem_max = float(sem_scores.max()) if sem_scores.size and sem_scores.max() > 0 else 1.0
    sem_floor = float(np.median(sem_scores)) if sem_scores.size else 0.0
    sem_span = max(sem_max - sem_floor, 1e-6)

    # Reciprocal Rank Fusion (Cormack et al., k=60) normalized to [0, 1]
    rrf_k = 60.0
    rrf_max_single = 1.0 / (rrf_k + 1.0)
    kw_order = np.argsort(-kw_scores)
    sem_order = np.argsort(-sem_scores)
    kw_rank = np.empty_like(kw_order)
    sem_rank = np.empty_like(sem_order)
    kw_rank[kw_order] = np.arange(1, len(papers) + 1)
    sem_rank[sem_order] = np.arange(1, len(papers) + 1)

    scored = []
    for i, p in enumerate(papers):
        kw_val = float(kw_scores[i])
        sem_val = float(sem_scores[i])
        kw_norm = kw_val / kw_max if kw_val > 0 else 0.0
        sem_excess = max(0.0, sem_val - sem_floor) / sem_span if sem_val > sem_floor else 0.0
        pr_boost = 0.03 * float(p.pagerank_score or 0.0)
        lib_boost = 0.04 * math.log1p(p.save_count or 0) if only_library else 0.0

        if mode == "keyword":
            if kw_val <= 0:
                continue
            final = kw_norm + pr_boost + lib_boost
        elif mode == "semantic":
            if sem_val <= 0.04:
                continue
            final = sem_val + pr_boost + lib_boost
        else:
            # Hybrid: combine lexical relevance, anisotropy-adjusted semantic excess, and weighted RRF
            if kw_val <= 0 and sem_excess <= 0.15:
                continue
            rrf_kw = (1.0 / (rrf_k + kw_rank[i])) / rrf_max_single if kw_val > 0 else 0.0
            rrf_sem = (1.0 / (rrf_k + sem_rank[i])) / rrf_max_single if sem_excess > 0.05 else 0.0
            rrf_norm = 0.58 * rrf_kw + 0.42 * rrf_sem
            final = 0.48 * kw_norm + 0.27 * sem_excess + 0.25 * rrf_norm + pr_boost + lib_boost

        scored.append((final, kw_val, sem_val, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [_serialize_paper_hit(p, score=round(sc, 4), kw=round(kw, 4), sem=round(sem, 4)) for sc, kw, sem, p in scored[:limit]]


def _serialize_paper_hit(paper: Paper, score: float, kw: float, sem: float) -> Dict[str, Any]:
    return {
        "id": paper.id,
        "title": paper.title,
        "abstract": paper.abstract,
        "authors": paper.authors or [],
        "publication_year": paper.publication_year,
        "venue": paper.venue,
        "doi": paper.doi,
        "arxiv_id": paper.arxiv_id,
        "url": paper.url,
        "pdf_url": paper.pdf_url,
        "topics": paper.topics or [],
        "department_hint": paper.department_hint,
        "primary_source": paper.primary_source,
        "sources": paper.sources or [],
        "citation_count": paper.citation_count,
        "pagerank_score": paper.pagerank_score,
        "save_count": paper.save_count,
        "in_university_library": paper.in_university_library,
        "is_synthetic": paper.is_synthetic,
        "relevance_score": score,
        "keyword_score": kw,
        "semantic_score": sem,
    }


def search_researchers(
    db: Session,
    query: str,
    department_code: Optional[str] = None,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    users_q = db.query(User).filter(User.is_active == True)
    dept_map = {d.id: d for d in db.query(Department).all()}
    users = users_q.all()
    if department_code:
        users = [u for u in users if u.department_id in dept_map and dept_map[u.department_id].code == department_code]

    q_clean = (query or "").strip().lower()
    tokens = _tokenize(q_clean)

    results = []
    for u in users:
        dept = dept_map.get(u.department_id)
        haystack = " ".join(
            [
                u.full_name or "",
                u.username or "",
                u.role or "",
                dept.name if dept else "",
                dept.code if dept else "",
                u.bio or "",
                u.research_interests_text or "",
                " ".join(u.research_tags or []),
            ]
        ).lower()
        if not tokens:
            score = 1.0
        else:
            score = 0.0
            if q_clean in (u.full_name or "").lower():
                score += 4.0
            if q_clean in " ".join(u.research_tags or []).lower():
                score += 3.0
            for t in set(tokens):
                if t in (u.full_name or "").lower():
                    score += 2.0
                if t in " ".join(u.research_tags or []).lower():
                    score += 2.2
                if t in haystack:
                    score += 1.0
            if score <= 0:
                continue
        results.append(
            {
                "id": u.id,
                "full_name": u.full_name,
                "username": u.username,
                "role": u.role,
                "department_code": dept.code if dept else None,
                "department_name": dept.name if dept else None,
                "bio": u.bio,
                "research_interests_text": u.research_interests_text,
                "research_tags": u.research_tags or [],
                "personal_website": u.personal_website,
                "relevance_score": round(score, 4),
            }
        )
    results.sort(key=lambda r: r["relevance_score"], reverse=True)
    return results[:limit]


def search_posts(
    db: Session,
    query: str,
    tag: Optional[str] = None,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    posts = db.query(Post).all()
    if tag:
        tl = tag.strip().lower()
        posts = [p for p in posts if any(tl in str(t).lower() for t in (p.tags or []))]

    q_clean = (query or "").strip().lower()
    tokens = _tokenize(q_clean)
    user_map = {u.id: u for u in db.query(User).all()}
    dept_map = {d.id: d for d in db.query(Department).all()}

    results = []
    for po in posts:
        tags_str = " ".join(po.tags or []).lower()
        title_l = (po.title or "").lower()
        content_l = (po.content or "").lower()
        if not tokens:
            score = float((po.upvote_count or 0) + (po.comment_count or 0))
        else:
            score = 0.0
            if q_clean in title_l:
                score += 3.5
            for t in set(tokens):
                if t in title_l:
                    score += 2.2
                if t in tags_str:
                    score += 2.0
                if t in content_l:
                    score += 1.0
            if score <= 0:
                continue
            score += 0.1 * math.log1p((po.upvote_count or 0) + (po.comment_count or 0))

        author = user_map.get(po.author_id)
        dept = dept_map.get(author.department_id) if author else None
        results.append(
            {
                "id": po.id,
                "title": po.title,
                "content": po.content[:320],
                "tags": po.tags or [],
                "author_id": po.author_id,
                "author_name": author.full_name if author else "Unknown",
                "author_role": author.role if author else "student",
                "department_code": dept.code if dept else None,
                "attached_paper_id": po.attached_paper_id,
                "upvote_count": po.upvote_count,
                "comment_count": po.comment_count,
                "created_at": po.created_at.isoformat() if po.created_at else None,
                "relevance_score": round(score, 4),
            }
        )
    results.sort(key=lambda r: r["relevance_score"], reverse=True)
    return results[:limit]


def unified_four_panel_search(
    db: Session,
    query: str,
    mode: str = "hybrid",
    department_code: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    source: Optional[str] = None,
    tag: Optional[str] = None,
    limit_per_panel: int = 12,
) -> Dict[str, Any]:
    """Execute F5 Unified Search returning all 4 required panels in one response."""
    external_papers = search_papers_ranked(
        db=db,
        query=query,
        mode=mode,
        only_library=False,
        year_from=year_from,
        year_to=year_to,
        source=source,
        tag=tag,
        limit=limit_per_panel,
    )
    university_library = search_papers_ranked(
        db=db,
        query=query,
        mode=mode,
        only_library=True,
        year_from=year_from,
        year_to=year_to,
        source=source,
        tag=tag,
        limit=limit_per_panel,
    )
    researchers = search_researchers(
        db=db,
        query=query,
        department_code=department_code,
        limit=limit_per_panel,
    )
    posts = search_posts(
        db=db,
        query=query,
        tag=tag,
        limit=limit_per_panel,
    )
    return {
        "query": query,
        "mode": mode,
        "embedder_backend": get_embedder().backend_name,
        "counts": {
            "external_papers": len(external_papers),
            "university_library": len(university_library),
            "researchers": len(researchers),
            "posts": len(posts),
        },
        "panels": {
            "external_papers": external_papers,
            "university_library": university_library,
            "researchers": researchers,
            "posts": posts,
        },
    }
