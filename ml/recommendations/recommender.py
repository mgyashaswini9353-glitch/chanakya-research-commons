"""
F6 Recommendation Engine.
Implements:
  1. Personalized Paper Recommendations (Content-Based + User-Item Collaborative Filtering + Cold-Start)
  2. Personalized Researcher Recommendations (Shared interests + Dept affinity + Graph proximity + Community Detection)
  3. "Members who saved this also saved" via FP-Growth Association Rules (mlxtend) + Co-save Lift
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder
from sqlalchemy.orm import Session

from backend.app.models.models import (
    ActivityEvent,
    Department,
    Paper,
    SavedPaper,
    TopicFollow,
    User,
    UserFollow,
)
from ml.embeddings.embedder import cosine_similarity_matrix, get_embedder


def recommend_papers_for_user(
    db: Session,
    user: User,
    limit: int = 10,
    exclude_saved: bool = True,
) -> Dict[str, Any]:
    """Hybrid Content-Based + Collaborative Filtering paper recommender with explicit cold-start handling."""
    all_papers = db.query(Paper).all()
    if not all_papers:
        return {"strategy": "empty", "is_cold_start": True, "recommendations": []}

    paper_map = {p.id: p for p in all_papers}
    all_saves = db.query(SavedPaper).all()
    user_saves_map: Dict[int, Set[int]] = defaultdict(set)
    for sp in all_saves:
        user_saves_map[sp.user_id].add(sp.paper_id)

    my_saved = user_saves_map.get(user.id, set())
    my_followed_topics = {
        tf.topic.lower()
        for tf in db.query(TopicFollow).filter(TopicFollow.user_id == user.id).all()
    }
    my_tags = {str(t).lower() for t in (user.research_tags or [])} | my_followed_topics
    dept = db.query(Department).filter(Department.id == user.department_id).first()
    dept_code = dept.code if dept else None

    is_cold_start = len(my_saved) == 0

    # --- 1. Build User Interest Embedding (profile + saved papers centroid) ---
    embedder = get_embedder()
    profile_text = " ".join(
        [
            user.research_interests_text or "",
            " ".join(sorted(my_tags)),
            dept.name if dept else "",
            user.bio or "",
        ]
    ).strip()

    user_vecs = []
    if profile_text:
        user_vecs.append(embedder.encode([profile_text])[0])
    for pid in my_saved:
        p = paper_map.get(pid)
        if p and p.embedding:
            user_vecs.append(np.asarray(p.embedding, dtype=np.float32))

    if user_vecs:
        user_centroid = np.mean(np.vstack(user_vecs), axis=0)
    else:
        user_centroid = None

    # Content similarity across all papers
    content_scores: Dict[int, float] = {}
    if user_centroid is not None:
        valid_papers = [p for p in all_papers if p.embedding]
        if valid_papers:
            mat = np.array([p.embedding for p in valid_papers], dtype=np.float32)
            sims = cosine_similarity_matrix(user_centroid, mat)
            for p, s in zip(valid_papers, sims):
                content_scores[p.id] = max(0.0, float(s))

    # --- 2. User-Item Collaborative Filtering (Jaccard/Cosine similarity over saved sets) ---
    cf_scores: Dict[int, float] = defaultdict(float)
    if not is_cold_start:
        for other_uid, other_saved in user_saves_map.items():
            if other_uid == user.id or not other_saved:
                continue
            inter = len(my_saved & other_saved)
            if inter == 0:
                continue
            sim = inter / math.sqrt(len(my_saved) * len(other_saved))
            for cand_pid in other_saved:
                if cand_pid not in my_saved:
                    cf_scores[cand_pid] += sim
        max_cf = max(cf_scores.values()) if cf_scores else 1.0
        for pid in list(cf_scores.keys()):
            cf_scores[pid] = cf_scores[pid] / max(max_cf, 1e-9)

    # --- 3. Combine scores & generate explainable reasons ---
    max_saves = max((p.save_count or 0 for p in all_papers), default=1) or 1
    candidates = []
    for p in all_papers:
        if exclude_saved and p.id in my_saved:
            continue
        c_score = content_scores.get(p.id, 0.0)
        cf_score = cf_scores.get(p.id, 0.0)
        p_topics = {str(t).lower() for t in (p.topics or [])}
        tag_overlap = len(my_tags & p_topics) / max(1, len(my_tags | p_topics)) if my_tags else 0.0
        dept_match = 1.0 if (dept_code and p.department_hint == dept_code) else 0.0
        pop_score = 0.6 * ((p.save_count or 0) / max_saves) + 0.4 * float(p.pagerank_score or 0.0)

        if is_cold_start:
            final = 0.45 * c_score + 0.25 * tag_overlap + 0.15 * dept_match + 0.15 * pop_score
        else:
            final = 0.42 * c_score + 0.35 * cf_score + 0.13 * tag_overlap + 0.10 * pop_score

        reasons = []
        if cf_score >= 0.25:
            reasons.append("Members with similar research interests saved this")
        if c_score >= 0.25:
            reasons.append("Related to your research interests")
        shared_tags = sorted(my_tags & p_topics)
        if shared_tags:
            nice_tags = ", ".join(t.replace("-", " ").title() for t in shared_tags[:2])
            reasons.append(f"Because you follow {nice_tags}")
        if dept_match > 0 and is_cold_start:
            reasons.append(f"Popular in {dept.name if dept else dept_code}")
        if not reasons:
            reasons.append("Widely cited and saved across the university")

        candidates.append(
            {
                "id": p.id,
                "title": p.title,
                "abstract": (p.abstract or "")[:320],
                "authors": p.authors or [],
                "publication_year": p.publication_year,
                "venue": p.venue,
                "topics": p.topics or [],
                "primary_source": p.primary_source,
                "sources": p.sources or [],
                "save_count": p.save_count,
                "citation_count": p.citation_count,
                "pagerank_score": p.pagerank_score,
                "in_university_library": p.in_university_library,
                "score": round(float(final), 4),
                "content_score": round(float(c_score), 4),
                "collaborative_score": round(float(cf_score), 4),
                "reasons": reasons,
            }
        )

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return {
        "strategy": "cold_start_content_dept_popularity" if is_cold_start else "hybrid_content_collaborative",
        "is_cold_start": is_cold_start,
        "recommendations": candidates[:limit],
    }


def recommend_also_saved_fpgrowth(
    db: Session,
    paper_id: int,
    limit: int = 6,
) -> Dict[str, Any]:
    """
    'Members who saved this also saved' using FP-Growth Association Rules (mlxtend)
    over member paper-save transactions, with co-save lift fallback for rare papers.
    """
    saves = db.query(SavedPaper).all()
    baskets_by_user: Dict[int, List[int]] = defaultdict(list)
    for sp in saves:
        baskets_by_user[sp.user_id].append(sp.paper_id)

    transactions = [sorted(set(pids)) for pids in baskets_by_user.values() if len(set(pids)) >= 2]
    paper_map = {p.id: p for p in db.query(Paper).all()}
    target_paper = paper_map.get(paper_id)
    if not target_paper or not transactions:
        return {"paper_id": paper_id, "method": "none", "items": []}

    # --- 1. FP-Growth Association Rules ---
    fp_results: Dict[int, Dict[str, Any]] = {}
    try:
        # Filter to transactions containing papers saved at least twice to keep FP-tree compact & fast
        item_counts = Counter(pid for tx in transactions for pid in tx)
        min_support = max(2 / max(1, len(transactions)), 0.035)
        filtered_tx = [[str(pid) for pid in tx if item_counts[pid] >= 2] for tx in transactions]
        filtered_tx = [tx for tx in filtered_tx if len(tx) >= 2]
        if filtered_tx and str(paper_id) in {x for tx in filtered_tx for x in tx}:
            te = TransactionEncoder()
            te_ary = te.fit(filtered_tx).transform(filtered_tx)
            df_tx = pd.DataFrame(te_ary, columns=te.columns_)
            freq = fpgrowth(df_tx, min_support=min_support, use_colnames=True, max_len=2)
            if not freq.empty:
                rules = association_rules(freq, metric="confidence", min_threshold=0.15)
                target_str = str(paper_id)
                for _, row in rules.iterrows():
                    ants = set(row["antecedents"])
                    cons = set(row["consequents"])
                    if ants == {target_str} and len(cons) == 1:
                        rec_pid = int(next(iter(cons)))
                        if rec_pid in paper_map and rec_pid != paper_id:
                            fp_results[rec_pid] = {
                                "confidence": round(float(row["confidence"]), 4),
                                "lift": round(float(row["lift"]), 4),
                                "support": round(float(row["support"]), 4),
                                "method": "fp_growth",
                            }
    except Exception:
        pass

    # --- 2. Co-occurrence fallback if FP-Growth yields fewer than `limit` ---
    co_counts: Counter = Counter()
    target_tx_count = 0
    for tx in transactions:
        if paper_id in tx:
            target_tx_count += 1
            for other in tx:
                if other != paper_id:
                    co_counts[other] += 1

    total_tx = max(1, len(transactions))
    item_tx_freq = Counter(pid for tx in transactions for pid in tx)

    for other_pid, co_cnt in co_counts.most_common(limit * 2):
        if other_pid not in fp_results and other_pid in paper_map:
            conf = co_cnt / max(1, target_tx_count)
            supp_b = item_tx_freq[other_pid] / total_tx
            lift = conf / max(supp_b, 1e-6)
            fp_results[other_pid] = {
                "confidence": round(float(conf), 4),
                "lift": round(float(lift), 4),
                "support": round(float(co_cnt / total_tx), 4),
                "method": "co_save_lift",
            }

    # --- 3. Semantic fallback for brand-new unsaved library papers ---
    if len(fp_results) < limit and target_paper.embedding:
        other_papers = [p for p in paper_map.values() if p.id != paper_id and p.id not in fp_results and p.embedding]
        if other_papers:
            sims = cosine_similarity_matrix(
                np.asarray(target_paper.embedding, dtype=np.float32),
                np.array([p.embedding for p in other_papers], dtype=np.float32),
            )
            top_idx = np.argsort(-sims)[: (limit - len(fp_results))]
            for idx in top_idx:
                p = other_papers[int(idx)]
                fp_results[p.id] = {
                    "confidence": round(float(max(0.0, sims[int(idx)])), 4),
                    "lift": 1.0,
                    "support": 0.0,
                    "method": "semantic_fallback",
                }

    ranked = sorted(
        fp_results.items(),
        key=lambda kv: (kv[1]["method"] == "fp_growth", kv[1]["lift"], kv[1]["confidence"]),
        reverse=True,
    )[:limit]

    items = []
    for pid, metrics in ranked:
        p = paper_map[pid]
        items.append(
            {
                "id": p.id,
                "title": p.title,
                "authors": p.authors or [],
                "publication_year": p.publication_year,
                "venue": p.venue,
                "topics": p.topics or [],
                "save_count": p.save_count,
                "confidence": metrics["confidence"],
                "lift": metrics["lift"],
                "support": metrics["support"],
                "method": metrics["method"],
            }
        )

    primary_method = "fp_growth" if any(i["method"] == "fp_growth" for i in items) else (
        items[0]["method"] if items else "none"
    )
    return {"paper_id": paper_id, "method": primary_method, "items": items}


def recommend_researchers_for_user(
    db: Session,
    user: User,
    limit: int = 8,
) -> Dict[str, Any]:
    """Recommend colleagues to connect with using shared interests, dept affinity, and NetworkX community detection."""
    users = db.query(User).filter(User.is_active == True, User.is_flagged_spam == False).all()
    dept_map = {d.id: d for d in db.query(Department).all()}
    follows = db.query(UserFollow).all()
    saves = db.query(SavedPaper).all()

    already_following = {f.following_id for f in follows if f.follower_id == user.id}

    # Build collaboration + follow graph for community detection and 2-hop proximity
    G = nx.Graph()
    for u in users:
        G.add_node(u.id)
    for f in follows:
        if G.has_node(f.follower_id) and G.has_node(f.following_id):
            G.add_edge(f.follower_id, f.following_id, weight=2.0)

    paper_savers: Dict[int, List[int]] = defaultdict(list)
    for sp in saves:
        paper_savers[sp.paper_id].append(sp.user_id)
    for savers in paper_savers.values():
        unique_savers = list(set(savers))
        for i in range(len(unique_savers)):
            for j in range(i + 1, len(unique_savers)):
                a, b = unique_savers[i], unique_savers[j]
                if G.has_node(a) and G.has_node(b):
                    if G.has_edge(a, b):
                        G[a][b]["weight"] += 0.5
                    else:
                        G.add_edge(a, b, weight=0.5)

    # Community detection (greedy modularity)
    community_of: Dict[int, int] = {}
    if G.number_of_edges() > 0:
        try:
            comms = list(nx.algorithms.community.greedy_modularity_communities(G, weight="weight"))
            for cid, members in enumerate(comms):
                for m in members:
                    community_of[m] = cid
        except Exception:
            pass

    my_community = community_of.get(user.id, -1)
    my_neighbors = set(G.neighbors(user.id)) if G.has_node(user.id) else set()
    my_tags = {str(t).lower() for t in (user.research_tags or [])}
    my_saved = {sp.paper_id for sp in saves if sp.user_id == user.id}

    embedder = get_embedder()
    texts = [
        f"{u.research_interests_text or ''} {' '.join(u.research_tags or [])} {u.bio or ''}"
        for u in users
    ]
    vecs = embedder.encode(texts)
    id_to_idx = {u.id: i for i, u in enumerate(users)}
    my_vec = vecs[id_to_idx[user.id]] if user.id in id_to_idx else None

    recs = []
    for idx, other in enumerate(users):
        if other.id == user.id or other.id in already_following:
            continue
        other_tags = {str(t).lower() for t in (other.research_tags or [])}
        shared_tags = sorted(my_tags & other_tags)
        tag_jacc = len(shared_tags) / max(1, len(my_tags | other_tags)) if (my_tags or other_tags) else 0.0

        sem_sim = float(np.dot(my_vec, vecs[idx])) if my_vec is not None else 0.0
        sem_sim = max(0.0, sem_sim)

        other_saved = {sp.paper_id for sp in saves if sp.user_id == other.id}
        shared_papers = len(my_saved & other_saved)
        paper_jacc = shared_papers / max(1, len(my_saved | other_saved)) if (my_saved and other_saved) else 0.0

        other_neighbors = set(G.neighbors(other.id)) if G.has_node(other.id) else set()
        mutual_connections = len(my_neighbors & other_neighbors)
        graph_score = min(1.0, mutual_connections / 4.0)
        same_comm = 1.0 if (my_community != -1 and community_of.get(other.id) == my_community) else 0.0
        same_dept = 1.0 if (user.department_id and user.department_id == other.department_id) else 0.0

        score = (
            0.35 * sem_sim
            + 0.25 * tag_jacc
            + 0.15 * paper_jacc
            + 0.12 * graph_score
            + 0.08 * same_comm
            + 0.05 * same_dept
        )

        reasons = []
        if shared_tags:
            reasons.append(f"Shared interests: {', '.join(shared_tags[:3])}")
        if shared_papers > 0:
            reasons.append(f"{shared_papers} paper(s) saved in common")
        if mutual_connections > 0:
            reasons.append(f"{mutual_connections} mutual research connections")
        if same_comm > 0:
            reasons.append("Same research collaboration cluster")
        if same_dept > 0:
            reasons.append("Same Chanakya department")
        if not reasons:
            reasons.append("Complementary research focus")

        dept = dept_map.get(other.department_id)
        recs.append(
            {
                "id": other.id,
                "full_name": other.full_name,
                "username": other.username,
                "role": other.role,
                "department_code": dept.code if dept else None,
                "department_name": dept.name if dept else None,
                "research_tags": other.research_tags or [],
                "research_interests_text": other.research_interests_text,
                "community_id": community_of.get(other.id),
                "score": round(float(score), 4),
                "reasons": reasons,
            }
        )

    recs.sort(key=lambda r: r["score"], reverse=True)
    return {
        "community_count": len(set(community_of.values())),
        "recommendations": recs[:limit],
    }
