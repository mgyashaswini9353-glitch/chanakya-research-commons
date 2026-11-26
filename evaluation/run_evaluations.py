"""
Reproducible Quantitative Evaluation Suite for Chanakya Research Commons.
Evaluates all intelligent subsystems against baselines and planted ground truth:
  1. Search (F5): Precision@5, Precision@10, Recall@10, NDCG@10 (Keyword vs Semantic vs Hybrid)
  2. Recommendations (F6): Precision@5, Precision@10, Recall@10 (Hybrid Content+CF vs Popularity Baseline)
  3. Duplicate Detection (F5): Precision, Recall, F1 (MinHash+LSH+Author ER vs Exact DOI/Title Baseline)
  4. Spam Detection (F7): Precision, Recall, F1 (Isolation Forest + Behavioral Signals vs Volume Threshold Baseline)
  5. Trend Spike Detection (F7): Detection Rate, Precision, False Alarm Count against planted spikes
  6. RAG Research Assistant (F8): Retrieval Relevance (Hit@5), Citation Correctness, Evidence Coverage, Refusal Accuracy

Outputs:
  - evaluation/results/evaluation_summary.json
  - evaluation/results/evaluation_tables.csv
  - documentation/diagrams/eval_search_comparison.png
  - documentation/diagrams/eval_ml_benchmarks.png
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.models import Paper, SavedPaper, User
from ml.anomaly_detection.spam_detector import detect_spam_accounts, extract_user_behavior_features
from ml.duplicate_detection.deduplicator import PaperDeduplicator, normalize_doi, normalize_title
from ml.recommendations.recommender import recommend_papers_for_user
from ml.search.search_engine import search_papers_ranked
from ml.trend_detection.trends import compute_trending_and_spikes
from research_assistant.rag_engine import answer_research_question


def _dcg(relevances: List[int]) -> float:
    return sum((rel / math.log2(idx + 2)) for idx, rel in enumerate(relevances))


def _ndcg_at_k(ranked_ids: List[int], rel_set: Set[int], k: int = 10) -> float:
    gains = [1 if pid in rel_set else 0 for pid in ranked_ids[:k]]
    ideal = sorted([1] * min(len(rel_set), k), reverse=True)
    idcg = _dcg(ideal)
    return _dcg(gains) / idcg if idcg > 0 else 0.0


def eval_search(db, gt_dir: Path) -> Dict[str, Any]:
    """
    Evaluate Keyword vs Semantic vs Hybrid search transparently:
      - Primary metrics (`keyword`, `semantic`, `hybrid`) are computed on the exact judged
        560-paper corpus (`Paper.id <= judged_max_paper_id`) covered by `search_qrels.json`
        so newly ingested unjudged papers do not distort Precision/NDCG.
      - `full_corpus_conservative` also reports metrics across the entire current corpus
        (e.g. 687 papers), explicitly noting that unjudged papers are treated conservatively as 0.
    """
    with open(gt_dir / "search_qrels.json", "r", encoding="utf-8") as f:
        qrels = json.load(f)

    total_papers = db.query(Paper).count()
    judged_max_id = max(
        (pid for item in qrels for pid in item.get("relevant_paper_ids", [])),
        default=560,
    )
    # Round up to the original 560-paper judged pool boundary when corpus has grown
    judged_pool_bound = max(judged_max_id, 560) if total_papers > 560 else None
    judged_pool_size = (
        db.query(Paper).filter(Paper.id <= judged_pool_bound).count()
        if judged_pool_bound is not None
        else total_papers
    )

    modes = ["keyword", "semantic", "hybrid"]

    def _run_pool(max_pid: int | None) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for mode in modes:
            p5_list, p10_list, r10_list, ndcg10_list = [], [], [], []
            for item in qrels:
                rel_set = set(item["relevant_paper_ids"])
                if not rel_set:
                    continue
                hits = search_papers_ranked(db, query=item["query"], mode=mode, limit=10, max_paper_id=max_pid)
                ranked_ids = [h["id"] for h in hits]
                top5 = ranked_ids[:5]
                top10 = ranked_ids[:10]
                p5_list.append(sum(1 for x in top5 if x in rel_set) / 5.0)
                p10_list.append(sum(1 for x in top10 if x in rel_set) / 10.0)
                r10_list.append(sum(1 for x in top10 if x in rel_set) / min(len(rel_set), 10.0))
                ndcg10_list.append(_ndcg_at_k(ranked_ids, rel_set, k=10))

            out[mode] = {
                "queries_evaluated": len(p10_list),
                "precision_at_5": round(float(np.mean(p5_list)), 4),
                "precision_at_10": round(float(np.mean(p10_list)), 4),
                "recall_at_10": round(float(np.mean(r10_list)), 4),
                "ndcg_at_10": round(float(np.mean(ndcg10_list)), 4),
            }
        return out

    metrics: Dict[str, Any] = _run_pool(judged_pool_bound)
    metrics["evaluation_scope"] = {
        "judged_pool_papers": judged_pool_size,
        "total_corpus_papers": total_papers,
        "unjudged_new_papers": max(0, total_papers - judged_pool_size),
    }
    if judged_pool_bound is not None and total_papers > judged_pool_size:
        metrics["full_corpus_conservative"] = _run_pool(None)
    return metrics


def eval_recommendations(db) -> Dict[str, Any]:
    """
    Hold-out evaluation: for each regular user with >= 6 saved papers, hold out 30% of their
    saved papers (without mutating DB permanently) and compare Hybrid Content+CF vs Popularity Baseline.
    """
    users = db.query(User).filter(User.is_flagged_spam == False, User.is_active == True).all()
    all_papers = db.query(Paper).all()
    pop_ranked_ids = [p.id for p in sorted(all_papers, key=lambda x: (x.save_count or 0, x.citation_count or 0), reverse=True)]

    hybrid_p5, hybrid_p10, hybrid_r10 = [], [], []
    pop_p5, pop_p10, pop_r10 = [], [], []

    rng = np.random.default_rng(42)
    evaluated_users = 0

    for u in users[:35]:
        u_saves = db.query(SavedPaper).filter(SavedPaper.user_id == u.id).all()
        if len(u_saves) < 6:
            continue
        evaluated_users += 1
        saved_ids = [sp.paper_id for sp in u_saves]
        rng.shuffle(saved_ids)
        n_holdout = max(2, len(saved_ids) // 3)
        holdout_set = set(saved_ids[:n_holdout])
        train_set = set(saved_ids[n_holdout:])

        # Popularity baseline (excluding training saves)
        pop_cands = [pid for pid in pop_ranked_ids if pid not in train_set][:10]
        pop_p5.append(sum(1 for x in pop_cands[:5] if x in holdout_set) / 5.0)
        pop_p10.append(sum(1 for x in pop_cands[:10] if x in holdout_set) / 10.0)
        pop_r10.append(sum(1 for x in pop_cands[:10] if x in holdout_set) / len(holdout_set))

        # Temporarily remove holdout rows in a savepoint/nested transaction, evaluate hybrid recommender, rollback
        held_objs = [sp for sp in u_saves if sp.paper_id in holdout_set]
        snapshot = [(sp.user_id, sp.paper_id, sp.collection_id, sp.private_notes, sp.saved_at) for sp in held_objs]
        for sp in held_objs:
            db.delete(sp)
        db.flush()

        rec_res = recommend_papers_for_user(db, u, limit=10, exclude_saved=True)
        rec_ids = [r["id"] for r in rec_res["recommendations"]]

        hybrid_p5.append(sum(1 for x in rec_ids[:5] if x in holdout_set) / 5.0)
        hybrid_p10.append(sum(1 for x in rec_ids[:10] if x in holdout_set) / 10.0)
        hybrid_r10.append(sum(1 for x in rec_ids[:10] if x in holdout_set) / len(holdout_set))

        # Restore held-out saves cleanly
        db.rollback()

    return {
        "users_evaluated": evaluated_users,
        "hybrid_content_cf": {
            "precision_at_5": round(float(np.mean(hybrid_p5)), 4) if hybrid_p5 else 0.0,
            "precision_at_10": round(float(np.mean(hybrid_p10)), 4) if hybrid_p10 else 0.0,
            "recall_at_10": round(float(np.mean(hybrid_r10)), 4) if hybrid_r10 else 0.0,
        },
        "popularity_baseline": {
            "precision_at_5": round(float(np.mean(pop_p5)), 4) if pop_p5 else 0.0,
            "precision_at_10": round(float(np.mean(pop_p10)), 4) if pop_p10 else 0.0,
            "recall_at_10": round(float(np.mean(pop_r10)), 4) if pop_r10 else 0.0,
        },
    }


def eval_duplicate_detection(gt_dir: Path) -> Dict[str, Any]:
    with open(gt_dir / "duplicate_eval_corpus.json", "r", encoding="utf-8") as f:
        corpus = json.load(f)
    with open(gt_dir / "duplicate_pairs.json", "r", encoding="utf-8") as f:
        gt_list = json.load(f)

    gt_pairs = {tuple(sorted((p["id_a"], p["id_b"]))) for p in gt_list}

    # 1. Exact DOI + Exact Raw Title Baseline
    baseline_pairs = set()
    for i in range(len(corpus)):
        for j in range(i + 1, len(corpus)):
            a, b = corpus[i], corpus[j]
            same_doi = a.get("doi") and b.get("doi") and a["doi"].strip().lower() == b["doi"].strip().lower()
            same_title = (a.get("title") or "").strip().lower() == (b.get("title") or "").strip().lower()
            if same_doi or same_title:
                baseline_pairs.add(tuple(sorted((a["record_id"], b["record_id"]))))

    # 2. Our MinHash LSH + Normalized DOI/arXiv + Author Entity Resolution
    deduper = PaperDeduplicator(lsh_threshold=0.50, num_perm=128)
    found = deduper.find_duplicate_pairs(corpus)
    pred_pairs = {tuple(sorted((p["id_a"], p["id_b"]))) for p in found}

    def _prf(preds: Set, truth: Set) -> Dict[str, Any]:
        tp = len(preds & truth)
        fp = len(preds - truth)
        fn = len(truth - preds)
        prec = tp / max(1, tp + fp)
        rec = tp / max(1, tp + fn)
        f1 = 2 * prec * rec / max(1e-9, prec + rec)
        return {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
        }

    return {
        "corpus_records": len(corpus),
        "planted_duplicates": len(gt_pairs),
        "exact_match_baseline": _prf(baseline_pairs, gt_pairs),
        "minhash_lsh_entity_resolution": _prf(pred_pairs, gt_pairs),
    }


def eval_spam_detection(db, gt_dir: Path) -> Dict[str, Any]:
    with open(gt_dir / "spam_accounts.json", "r", encoding="utf-8") as f:
        gt_spam = json.load(f)
    gt_ids = {int(item["user_id"]) for item in gt_spam}

    # Baseline: Simple top-volume post count threshold (>= 12 posts)
    feats = extract_user_behavior_features(db)
    base_preds = {int(r["user_id"]) for r in feats if r["post_count"] >= 12}

    # Our Isolation Forest + Behavioral Anomaly Detector
    det = detect_spam_accounts(db, persist_alerts=False)
    our_preds = {int(a["user_id"]) for a in det["flagged_accounts"]}

    def _prf(preds: Set[int], truth: Set[int]) -> Dict[str, Any]:
        tp = len(preds & truth)
        fp = len(preds - truth)
        fn = len(truth - preds)
        prec = tp / max(1, tp + fp)
        rec = tp / max(1, tp + fn)
        f1 = 2 * prec * rec / max(1e-9, prec + rec)
        return {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
        }

    return {
        "total_accounts": len(feats),
        "planted_spam_accounts": len(gt_ids),
        "volume_threshold_baseline": _prf(base_preds, gt_ids),
        "isolation_forest_behavioral": _prf(our_preds, gt_ids),
    }


def eval_trend_detection(db, gt_dir: Path) -> Dict[str, Any]:
    with open(gt_dir / "topic_spikes.json", "r", encoding="utf-8") as f:
        gt_spikes = json.load(f)
    gt_topics = {s["topic"].lower() for s in gt_spikes}

    res = compute_trending_and_spikes(db, window_days=14, z_threshold=3.0)
    detected_topics = {s["topic"].lower() for s in res["topic_spikes"]}

    tp = len(detected_topics & gt_topics)
    fp = len(detected_topics - gt_topics)
    fn = len(gt_topics - detected_topics)
    det_rate = tp / max(1, len(gt_topics))
    prec = tp / max(1, tp + fp)

    return {
        "planted_spikes": sorted(gt_topics),
        "detected_spikes": sorted(detected_topics),
        "true_positives": tp,
        "false_alarm_count": fp,
        "missed_spikes": fn,
        "detection_rate": round(det_rate, 4),
        "precision": round(prec, 4),
    }


def eval_rag_assistant(db, gt_dir: Path) -> Dict[str, Any]:
    with open(gt_dir / "rag_eval_queries.json", "r", encoding="utf-8") as f:
        queries = json.load(f)

    answerable_total = 0
    retrieval_hits = 0
    total_citations = 0
    verified_citations = 0
    evidence_covered = 0
    unanswerable_total = 0
    unanswerable_refused_correctly = 0

    all_paper_ids = {p.id for p in db.query(Paper.id).all()}

    details = []
    for item in queries:
        resp = answer_research_question(db, question=item["question"], top_k=5)
        if item["expect_answerable"]:
            answerable_total += 1
            passages = resp["retrieved_passages"]
            citations = resp["citations"]
            combined_text = " ".join(p["passage"] + " " + p["title"] for p in passages).lower()
            kw_hit = any(kw in combined_text for kw in item["expected_keywords"])
            if passages and kw_hit:
                retrieval_hits += 1
            for c in citations:
                total_citations += 1
                if c["paper_id"] in all_paper_ids and f"[{c['index']}]" in resp["answer"]:
                    verified_citations += 1
            if resp["sufficient_evidence"] and len(citations) > 0 and len(passages) > 0:
                evidence_covered += 1
        else:
            unanswerable_total += 1
            if not resp["sufficient_evidence"] and len(resp["citations"]) == 0:
                unanswerable_refused_correctly += 1

        details.append(
            {
                "question": item["question"],
                "expect_answerable": item["expect_answerable"],
                "sufficient_evidence": resp["sufficient_evidence"],
                "generation_mode": resp["generation_mode"],
                "citations_returned": len(resp["citations"]),
            }
        )

    return {
        "queries_tested": len(queries),
        "retrieval_relevance_hit_at_5": round(retrieval_hits / max(1, answerable_total), 4),
        "citation_correctness": round(verified_citations / max(1, total_citations), 4),
        "evidence_coverage": round(evidence_covered / max(1, answerable_total), 4),
        "unanswerable_refusal_accuracy": round(unanswerable_refused_correctly / max(1, unanswerable_total), 4),
        "details": details,
    }


def generate_charts(summary: Dict[str, Any], diag_dir: Path) -> None:
    diag_dir.mkdir(parents=True, exist_ok=True)

    # Chart 1: Search Comparison (Keyword vs Semantic vs Hybrid)
    s = summary["search"]
    labels = ["Precision@5", "Precision@10", "Recall@10", "NDCG@10"]
    kw = [s["keyword"]["precision_at_5"], s["keyword"]["precision_at_10"], s["keyword"]["recall_at_10"], s["keyword"]["ndcg_at_10"]]
    sem = [s["semantic"]["precision_at_5"], s["semantic"]["precision_at_10"], s["semantic"]["recall_at_10"], s["semantic"]["ndcg_at_10"]]
    hyb = [s["hybrid"]["precision_at_5"], s["hybrid"]["precision_at_10"], s["hybrid"]["recall_at_10"], s["hybrid"]["ndcg_at_10"]]

    x = np.arange(len(labels))
    w = 0.25
    fig, ax = plt.subplots(figsize=(8.5, 4.6), dpi=150)
    b1 = ax.bar(x - w, kw, w, label="Keyword Search", color="#64748b")
    b2 = ax.bar(x, sem, w, label="Semantic Search (Vector)", color="#0284c7")
    b3 = ax.bar(x + w, hyb, w, label="Hybrid (RRF + PageRank)", color="#0f172a")
    ax.set_ylabel("Score")
    ax.set_title("F5 Unified Search Evaluation: Keyword vs Semantic vs Hybrid")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.12)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend()
    for bars in (b1, b2, b3):
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{h:.2f}", (bar.get_x() + bar.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(diag_dir / "eval_search_comparison.png")
    plt.close(fig)

    # Chart 2: Baseline vs Intelligent Features (Recs, Dedup, Spam, Trends, RAG)
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2), dpi=150)

    # Subplot 1: Recommendations
    r = summary["recommendations"]
    rl = ["P@5", "P@10", "R@10"]
    rx = np.arange(len(rl))
    axes[0].bar(rx - 0.18, [r["popularity_baseline"]["precision_at_5"], r["popularity_baseline"]["precision_at_10"], r["popularity_baseline"]["recall_at_10"]], 0.35, label="Popularity Baseline", color="#94a3b8")
    axes[0].bar(rx + 0.18, [r["hybrid_content_cf"]["precision_at_5"], r["hybrid_content_cf"]["precision_at_10"], r["hybrid_content_cf"]["recall_at_10"]], 0.35, label="Hybrid Content+CF", color="#0d9488")
    axes[0].set_title("F6 Recommendations")
    axes[0].set_xticks(rx)
    axes[0].set_xticklabels(rl)
    axes[0].set_ylim(0, 1.05)
    axes[0].legend(fontsize=8)
    axes[0].grid(axis="y", linestyle="--", alpha=0.35)

    # Subplot 2: Duplicate Detection
    d = summary["duplicate_detection"]
    dl = ["Precision", "Recall", "F1"]
    dx = np.arange(len(dl))
    axes[1].bar(dx - 0.18, [d["exact_match_baseline"]["precision"], d["exact_match_baseline"]["recall"], d["exact_match_baseline"]["f1_score"]], 0.35, label="Exact Baseline", color="#94a3b8")
    axes[1].bar(dx + 0.18, [d["minhash_lsh_entity_resolution"]["precision"], d["minhash_lsh_entity_resolution"]["recall"], d["minhash_lsh_entity_resolution"]["f1_score"]], 0.35, label="MinHash LSH + ER", color="#1d4ed8")
    axes[1].set_title("F5 Duplicate Detection")
    axes[1].set_xticks(dx)
    axes[1].set_xticklabels(dl)
    axes[1].set_ylim(0, 1.12)
    axes[1].legend(fontsize=8)
    axes[1].grid(axis="y", linestyle="--", alpha=0.35)

    # Subplot 3: Spam & Trend & RAG F1/Accuracy
    sp = summary["spam_detection"]
    tr = summary["trend_detection"]
    rg = summary["rag_assistant"]
    ml_labels = ["Spam F1\n(Base)", "Spam F1\n(IsoFor)", "Trend\nDet. Rate", "RAG\nCitation"]
    ml_vals = [
        sp["volume_threshold_baseline"]["f1_score"],
        sp["isolation_forest_behavioral"]["f1_score"],
        tr["detection_rate"],
        rg["citation_correctness"],
    ]
    colors = ["#94a3b8", "#dc2626", "#f59e0b", "#0f766e"]
    bars = axes[2].bar(ml_labels, ml_vals, color=colors, width=0.55)
    axes[2].set_title("F7 Monitoring & F8 RAG")
    axes[2].set_ylim(0, 1.15)
    axes[2].grid(axis="y", linestyle="--", alpha=0.35)
    for b in bars:
        axes[2].annotate(f"{b.get_height():.2f}", (b.get_x() + b.get_width() / 2, b.get_height()), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8)

    fig.tight_layout()
    fig.savefig(diag_dir / "eval_ml_benchmarks.png")
    plt.close(fig)


def main() -> None:
    gt_dir = Path(settings.DATA_DIR) / "ground_truth"
    res_dir = PROJECT_ROOT / "evaluation" / "results"
    diag_dir = PROJECT_ROOT / "documentation" / "diagrams"
    res_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        print("Running F5 Search Evaluation...")
        search_res = eval_search(db, gt_dir)
        print("Running F6 Recommendation Evaluation...")
        rec_res = eval_recommendations(db)
        print("Running F5 Duplicate Detection Evaluation...")
        dup_res = eval_duplicate_detection(gt_dir)
        print("Running F7 Spam Detection Evaluation...")
        spam_res = eval_spam_detection(db, gt_dir)
        print("Running F7 Trend Spike Detection Evaluation...")
        trend_res = eval_trend_detection(db, gt_dir)
        print("Running F8 RAG Research Assistant Evaluation...")
        rag_res = eval_rag_assistant(db, gt_dir)

        summary = {
            "search": search_res,
            "recommendations": rec_res,
            "duplicate_detection": dup_res,
            "spam_detection": spam_res,
            "trend_detection": trend_res,
            "rag_assistant": rag_res,
        }

        with open(res_dir / "evaluation_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Export flattened CSV comparison table
        rows = [
            ["F5 Search", "Keyword Search", f"P@5={search_res['keyword']['precision_at_5']}", f"P@10={search_res['keyword']['precision_at_10']}", f"R@10={search_res['keyword']['recall_at_10']}", f"NDCG@10={search_res['keyword']['ndcg_at_10']}"],
            ["F5 Search", "Semantic Search", f"P@5={search_res['semantic']['precision_at_5']}", f"P@10={search_res['semantic']['precision_at_10']}", f"R@10={search_res['semantic']['recall_at_10']}", f"NDCG@10={search_res['semantic']['ndcg_at_10']}"],
            ["F5 Search", "Hybrid (RRF+PageRank)", f"P@5={search_res['hybrid']['precision_at_5']}", f"P@10={search_res['hybrid']['precision_at_10']}", f"R@10={search_res['hybrid']['recall_at_10']}", f"NDCG@10={search_res['hybrid']['ndcg_at_10']}"],
            ["F6 Recommendations", "Popularity Baseline", f"P@5={rec_res['popularity_baseline']['precision_at_5']}", f"P@10={rec_res['popularity_baseline']['precision_at_10']}", f"R@10={rec_res['popularity_baseline']['recall_at_10']}", "-"],
            ["F6 Recommendations", "Hybrid Content+CF", f"P@5={rec_res['hybrid_content_cf']['precision_at_5']}", f"P@10={rec_res['hybrid_content_cf']['precision_at_10']}", f"R@10={rec_res['hybrid_content_cf']['recall_at_10']}", "-"],
            ["F5 Duplicate Detection", "Exact Match Baseline", f"Prec={dup_res['exact_match_baseline']['precision']}", f"Rec={dup_res['exact_match_baseline']['recall']}", f"F1={dup_res['exact_match_baseline']['f1_score']}", "-"],
            ["F5 Duplicate Detection", "MinHash LSH + Author ER", f"Prec={dup_res['minhash_lsh_entity_resolution']['precision']}", f"Rec={dup_res['minhash_lsh_entity_resolution']['recall']}", f"F1={dup_res['minhash_lsh_entity_resolution']['f1_score']}", "-"],
            ["F7 Spam Detection", "Volume Baseline", f"Prec={spam_res['volume_threshold_baseline']['precision']}", f"Rec={spam_res['volume_threshold_baseline']['recall']}", f"F1={spam_res['volume_threshold_baseline']['f1_score']}", "-"],
            ["F7 Spam Detection", "Isolation Forest + Rules", f"Prec={spam_res['isolation_forest_behavioral']['precision']}", f"Rec={spam_res['isolation_forest_behavioral']['recall']}", f"F1={spam_res['isolation_forest_behavioral']['f1_score']}", "-"],
            ["F7 Trend Detection", "Sliding Window Z-Score", f"DetRate={trend_res['detection_rate']}", f"Prec={trend_res['precision']}", f"FalseAlarms={trend_res['false_alarm_count']}", "-"],
            ["F8 RAG Assistant", "Grounded RAG Pipeline", f"Hit@5={rag_res['retrieval_relevance_hit_at_5']}", f"CiteAcc={rag_res['citation_correctness']}", f"Cov={rag_res['evidence_coverage']}", f"RefusalAcc={rag_res['unanswerable_refusal_accuracy']}"],
        ]
        with open(res_dir / "evaluation_tables.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Subsystem", "Method", "Metric_1", "Metric_2", "Metric_3", "Metric_4"])
            writer.writerows(rows)

        generate_charts(summary, diag_dir)
        print("=== EVALUATION COMPLETE ===")
        print(json.dumps(summary, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
