"""
F7 Spam & Abnormal Activity Detector.
Extracts multi-dimensional behavioral features per user and applies
Isolation Forest (scikit-learn) + interpretable behavioral rules to flag
spam / automated accounts with transparent explanations for admins.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from backend.app.models.models import (
    ActivityEvent,
    Comment,
    Department,
    MonitoringAlert,
    Post,
    User,
    UserFollow,
)


def _duplicate_text_ratio(texts: List[str]) -> float:
    """Measure fraction of posts/comments that are near-duplicates (cosine >= 0.78)."""
    valid = [t.strip() for t in texts if t and len(t.strip()) >= 10]
    if len(valid) < 2:
        return 0.0
    vec = TfidfVectorizer(stop_words="english", max_features=2000)
    try:
        X = vec.fit_transform(valid)
    except ValueError:
        return 0.0
    sim = cosine_similarity(X)
    np.fill_diagonal(sim, 0.0)
    dup_flags = (sim.max(axis=1) >= 0.78).astype(int)
    return float(dup_flags.mean())


def extract_user_behavior_features(db: Session) -> List[Dict[str, Any]]:
    users = db.query(User).all()
    dept_map = {d.id: d.code for d in db.query(Department).all()}
    posts_by_user: Dict[int, List[Post]] = defaultdict(list)
    for po in db.query(Post).all():
        posts_by_user[po.author_id].append(po)

    comments_by_user: Dict[int, List[Comment]] = defaultdict(list)
    for cm in db.query(Comment).all():
        comments_by_user[cm.author_id].append(cm)

    events_by_user: Dict[int, List[ActivityEvent]] = defaultdict(list)
    for ev in db.query(ActivityEvent).all():
        if ev.user_id:
            events_by_user[ev.user_id].append(ev)

    follows_by_user: Counter = Counter()
    for fl in db.query(UserFollow).all():
        follows_by_user[fl.follower_id] += 1

    feature_rows = []
    for u in users:
        u_posts = posts_by_user[u.id]
        u_comments = comments_by_user[u.id]
        u_events = events_by_user[u.id]

        # Hourly burst rate (max events in any single hour bucket)
        hour_buckets: Counter = Counter()
        day_buckets = set()
        night_events = 0
        for ev in u_events:
            if ev.created_at:
                hour_buckets[ev.created_at.strftime("%Y-%m-%d-%H")] += 1
                day_buckets.add(ev.created_at.strftime("%Y-%m-%d"))
                if ev.created_at.hour in (1, 2, 3, 4):
                    night_events += 1
        for po in u_posts:
            if po.created_at:
                hour_buckets[po.created_at.strftime("%Y-%m-%d-%H")] += 1
                day_buckets.add(po.created_at.strftime("%Y-%m-%d"))
        for cm in u_comments:
            if cm.created_at:
                hour_buckets[cm.created_at.strftime("%Y-%m-%d-%H")] += 1

        max_events_per_hour = max(hour_buckets.values(), default=0)
        total_events = len(u_events) + len(u_posts) + len(u_comments)
        active_days = max(1, len(day_buckets))
        events_per_active_day = total_events / active_days

        all_texts = [f"{p.title} {p.content}" for p in u_posts] + [c.content for c in u_comments]
        dup_ratio = _duplicate_text_ratio(all_texts)

        avg_post_len = float(np.mean([len(p.content or "") for p in u_posts])) if u_posts else 120.0
        total_upvotes = sum(p.upvote_count or 0 for p in u_posts)
        upvote_per_post = total_upvotes / max(1, len(u_posts))
        avg_tags_per_post = float(np.mean([len(p.tags or []) for p in u_posts])) if u_posts else 2.0
        night_ratio = night_events / max(1, len(u_events))
        follow_count = follows_by_user[u.id]

        # Spam promotional keyword density
        promo_hits = sum(
            1
            for t in all_texts
            if any(k in t.lower() for k in ("buy now", "click here", "guaranteed acceptance", "free论文", "instant publish", "promo", "discount", "telegram", "whatsapp", "cheap assignment"))
        )
        promo_ratio = promo_hits / max(1, len(all_texts))

        feature_rows.append(
            {
                "user_id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "department_code": dept_map.get(u.department_id, "N/A"),
                "is_active": u.is_active,
                "max_events_per_hour": float(max_events_per_hour),
                "events_per_active_day": round(float(events_per_active_day), 2),
                "dup_text_ratio": round(float(dup_ratio), 4),
                "avg_post_len": round(float(avg_post_len), 1),
                "upvote_per_post": round(float(upvote_per_post), 3),
                "avg_tags_per_post": round(float(avg_tags_per_post), 2),
                "night_ratio": round(float(night_ratio), 3),
                "follow_count": float(follow_count),
                "promo_ratio": round(float(promo_ratio), 4),
                "post_count": len(u_posts),
                "comment_count": len(u_comments),
                "event_count": len(u_events),
            }
        )
    return feature_rows


def detect_spam_accounts(
    db: Session,
    contamination: float = 0.12,
    persist_alerts: bool = False,
) -> Dict[str, Any]:
    """Run Isolation Forest + behavioral scoring to flag suspicious/spam accounts with explanations."""
    rows = extract_user_behavior_features(db)
    if len(rows) < 5:
        return {"total_users_analyzed": len(rows), "flagged_accounts": [], "all_scores": []}

    feat_cols = [
        "max_events_per_hour",
        "events_per_active_day",
        "dup_text_ratio",
        "avg_tags_per_post",
        "night_ratio",
        "follow_count",
        "promo_ratio",
    ]
    X = np.array([[r[c] for c in feat_cols] for r in rows], dtype=np.float64)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(
        n_estimators=150,
        contamination=min(0.25, max(0.05, contamination)),
        random_state=42,
    )
    preds = iso.fit_predict(X_scaled)
    # Higher anomaly_score = more anomalous
    raw_scores = -iso.decision_function(X_scaled)
    min_s, max_s = float(raw_scores.min()), float(raw_scores.max())
    norm_scores = (raw_scores - min_s) / max(max_s - min_s, 1e-9)

    flagged = []
    all_scored = []

    for r, pred, iso_norm in zip(rows, preds, norm_scores):
        reasons = []
        rule_points = 0.0

        if r["dup_text_ratio"] >= 0.45:
            reasons.append(f"High repetitive/duplicate post content ({r['dup_text_ratio']*100:.0f}% similarity)")
            rule_points += 0.35
        if r["max_events_per_hour"] >= 18:
            reasons.append(f"Abnormal burst velocity ({int(r['max_events_per_hour'])} actions in a single hour)")
            rule_points += 0.30
        if r["promo_ratio"] >= 0.25:
            reasons.append(f"Promotional/spam phrase pattern detected ({r['promo_ratio']*100:.0f}% of content)")
            rule_points += 0.35
        if r["avg_tags_per_post"] >= 7.0:
            reasons.append(f"Tag stuffing detected (avg {r['avg_tags_per_post']:.1f} tags/post)")
            rule_points += 0.15
        if r["post_count"] >= 8 and r["upvote_per_post"] < 0.35:
            reasons.append(f"Very low peer engagement ({r['upvote_per_post']:.2f} upvotes/post across {r['post_count']} posts)")
            rule_points += 0.15
        if r["night_ratio"] >= 0.55 and r["event_count"] >= 20:
            reasons.append(f"Automated off-hours activity cadence ({r['night_ratio']*100:.0f}% between 01:00-04:59)")
            rule_points += 0.15

        combined_score = round(float(min(1.0, 0.45 * iso_norm + 0.55 * min(1.0, rule_points))), 4)
        is_suspicious = (
            r["role"] != "admin"
            and (
                (pred == -1 and len(reasons) >= 2)
                or rule_points >= 0.55
                or combined_score >= 0.62
            )
        )

        if is_suspicious and not reasons:
            reasons.append("Statistical multivariate outlier via Isolation Forest behavioral profile")

        risk_level = "high" if combined_score >= 0.72 else ("medium" if combined_score >= 0.52 else "low")
        entry = {
            **r,
            "isolation_forest_score": round(float(iso_norm), 4),
            "combined_anomaly_score": combined_score,
            "is_suspicious": bool(is_suspicious),
            "risk_level": risk_level,
            "reasons": reasons,
        }
        all_scored.append(entry)
        if is_suspicious:
            flagged.append(entry)

    flagged.sort(key=lambda x: x["combined_anomaly_score"], reverse=True)

    if persist_alerts:
        existing = {
            a.entity_id
            for a in db.query(MonitoringAlert).filter(MonitoringAlert.alert_type == "spam_account").all()
        }
        for fl in flagged:
            uid_str = str(fl["user_id"])
            user_obj = db.query(User).filter(User.id == fl["user_id"]).first()
            if user_obj:
                user_obj.is_flagged_spam = True
            if uid_str not in existing:
                db.add(
                    MonitoringAlert(
                        alert_type="spam_account",
                        severity=fl["risk_level"],
                        title=f"Suspicious / Spam Account Flagged: {fl['full_name']} (@{fl['username']})",
                        description="; ".join(fl["reasons"]),
                        entity_type="user",
                        entity_id=uid_str,
                        metrics_json={
                            "combined_anomaly_score": fl["combined_anomaly_score"],
                            "isolation_forest_score": fl["isolation_forest_score"],
                            "dup_text_ratio": fl["dup_text_ratio"],
                            "max_events_per_hour": fl["max_events_per_hour"],
                            "promo_ratio": fl["promo_ratio"],
                            "reasons": fl["reasons"],
                        },
                        status="open",
                    )
                )
        db.commit()

    return {
        "total_users_analyzed": len(rows),
        "flagged_count": len(flagged),
        "flagged_accounts": flagged,
        "all_scores": all_scored,
    }
