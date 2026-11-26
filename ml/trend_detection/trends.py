"""
F7 Trending Topics & Sudden Spike Detection.
Uses sliding-window weekly stream statistics with a non-adjacent, outlier-guarded
historical baseline and Poisson-floored Z-score spike detection, plus human-readable
explanations and weekly time-series output for charting.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from backend.app.models.models import ActivityEvent, MonitoringAlert, User


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _week_start_label(now: datetime, week_idx: int) -> str:
    return (now - timedelta(days=week_idx * 7 + 6)).strftime("%Y-%m-%d")


def _robust_baseline_stats(
    baseline_vals: List[int],
    min_baseline_weeks: int,
) -> Tuple[float, float, float]:
    """
    Compute robust baseline (mean, std, denominator) from historical weekly counts.
    Applies a conservative one-pass upper outlier guard (median + 3.5 * MAD/Poisson scale)
    so a secondary genuine spike in another week cannot mask a candidate spike, while
    leaving normal noisy weeks intact. Uses a Poisson count-process std floor sqrt(max(m, 1))
    and minimum 1.0 to eliminate division-by-zero on zero-variance series.
    """
    arr = np.asarray(baseline_vals, dtype=float)
    med = float(np.median(arr))
    mad_sigma = 1.4826 * float(np.median(np.abs(arr - med)))
    robust_scale = max(mad_sigma, math.sqrt(max(med, 1.0)), 1.0)
    inliers = arr[arr <= med + 3.5 * robust_scale]
    if len(inliers) < min_baseline_weeks:
        inliers = arr

    mean_val = float(np.mean(inliers))
    std_val = float(np.std(inliers))
    denom = max(std_val, math.sqrt(max(mean_val, 1.0)), 1.0)
    return mean_val, std_val, denom


def compute_trending_and_spikes(
    db: Session,
    window_days: int = 14,
    z_threshold: float = 3.0,
    min_recent_count: int = 30,
    reference_now: Optional[datetime] = None,
    min_baseline_weeks: int = 4,
) -> Dict[str, Any]:
    """
    Analyze ActivityEvent stream over sliding 7-day buckets (excluding spam-flagged accounts).
    Detects:
      - Trending topics (weighted recent volume + momentum)
      - Sudden topic spikes (weekly count significantly exceeding non-adjacent historical baseline)
      - Weekly topic popularity series for charting
    """
    spam_ids = {u.id for u in db.query(User).filter(User.is_flagged_spam == True).all()}
    q = db.query(ActivityEvent).filter(
        ActivityEvent.topic.isnot(None),
        ActivityEvent.topic != "",
        ActivityEvent.topic != "general",
        ActivityEvent.topic != "promo",
    )
    if spam_ids:
        q = q.filter(~ActivityEvent.user_id.in_(spam_ids))
    events = q.all()
    if not events:
        return {
            "window_days": window_days,
            "z_threshold": z_threshold,
            "trending_topics": [],
            "topic_spikes": [],
            "weekly_series": [],
        }

    timestamps = [_ensure_utc(ev.created_at) for ev in events if ev.created_at]
    if not timestamps:
        return {
            "window_days": window_days,
            "z_threshold": z_threshold,
            "trending_topics": [],
            "topic_spikes": [],
            "weekly_series": [],
        }

    now = _ensure_utc(reference_now) if reference_now else max(timestamps)
    recent_cutoff = now - timedelta(days=window_days)
    prev_cutoff = now - timedelta(days=window_days * 2)

    # Bucket events by topic and 7-day week index relative to `now`
    weekly_topic_counts: Dict[str, Counter] = defaultdict(Counter)
    recent_counts: Counter = Counter()
    prev_counts: Counter = Counter()
    total_counts: Counter = Counter()
    max_week = 0

    for ev in events:
        if not ev.created_at or not ev.topic:
            continue
        topic = str(ev.topic).strip().lower()
        if not topic or topic in ("general", "promo"):
            continue
        ts = _ensure_utc(ev.created_at)
        if reference_now is not None and ts > now:
            continue
        days_ago = max(0, (now - ts).days)
        week_idx = days_ago // 7  # 0 = most recent 7 days, 1 = 7-14 days ago, ...
        weekly_topic_counts[topic][week_idx] += 1
        total_counts[topic] += 1
        if week_idx > max_week:
            max_week = week_idx

        if ts >= recent_cutoff:
            recent_counts[topic] += 1
        elif ts >= prev_cutoff:
            prev_counts[topic] += 1

    if not total_counts:
        return {
            "window_days": window_days,
            "z_threshold": z_threshold,
            "trending_topics": [],
            "topic_spikes": [],
            "weekly_series": [],
        }

    # Evaluate up to 26 weeks (~6 months) of weekly buckets
    horizon_weeks = min(max_week + 1, 26)
    min_active_baseline_weeks = 2

    trending_list = []
    spikes_list = []

    for topic, total_cnt in total_counts.items():
        series = [weekly_topic_counts[topic].get(w, 0) for w in range(horizon_weeks)]
        check_weeks = min(horizon_weeks, 12)

        best_z: Optional[float] = None
        best_week_idx = 0
        best_count = 0
        best_mean = 0.0
        best_std = 0.0
        has_sufficient_history = False

        for w in range(check_weeks):
            # Exclude candidate week w and immediate ±1 adjacent weeks to avoid
            # bucket-boundary spillover contamination from multi-day spikes.
            non_adjacent = [series[k] for k in range(horizon_weeks) if abs(k - w) > 1]
            baseline_vals = (
                non_adjacent
                if len(non_adjacent) >= min_baseline_weeks
                else [series[k] for k in range(horizon_weeks) if k != w]
            )
            if len(baseline_vals) < min_baseline_weeks:
                continue
            if sum(1 for v in baseline_vals if v > 0) < min_active_baseline_weeks:
                continue

            has_sufficient_history = True
            m, s, denom = _robust_baseline_stats(baseline_vals, min_baseline_weeks)
            z = (series[w] - m) / denom
            if best_z is None or z > best_z:
                best_z = z
                best_week_idx = w
                best_count = series[w]
                best_mean = m
                best_std = s

        if best_z is None:
            # Insufficient historical observations to declare a statistical spike
            best_z = 0.0
            if check_weeks > 0:
                best_week_idx = int(np.argmax(series[:check_weeks]))
                best_count = int(series[best_week_idx])
                others = [series[k] for k in range(horizon_weeks) if k != best_week_idx]
                best_mean = float(np.mean(others)) if others else 0.0
                best_std = float(np.std(others)) if others else 0.0

        rec_w = recent_counts.get(topic, 0)
        prv_w = prev_counts.get(topic, 0)
        growth_pct = ((rec_w - prv_w) / max(1, prv_w)) * 100.0
        momentum_score = round(rec_w * (1.0 + max(0.0, growth_pct) / 100.0) + max(0.0, best_z) * 5.0, 2)

        is_spike = (
            has_sufficient_history
            and best_z >= z_threshold
            and best_count >= min_recent_count
            and best_count >= max(2.6 * best_mean, best_mean + 22)
        )

        reason = (
            f"Weekly activity surged to {best_count} events (baseline avg {best_mean:.1f}/wk, Z={best_z:.2f}, +{((best_count - best_mean)/max(1.0, best_mean))*100:.0f}%)"
            if is_spike
            else f"{rec_w} events in last {window_days}d ({'+' if growth_pct >= 0 else ''}{growth_pct:.0f}% vs prior {window_days}d)"
        )

        nice_topic = topic.replace("-", " ").title()
        human_summary = (
            f"Growing interest in {nice_topic} — {best_count} interactions in the peak week compared to a typical average of {best_mean:.0f} per week."
            if is_spike
            else f"{rec_w} research interactions over the past {window_days} days."
        )

        entry = {
            "topic": topic,
            "recent_count": int(rec_w),
            "previous_count": int(prv_w),
            "total_count": int(total_cnt),
            "growth_pct": round(float(growth_pct), 1),
            "momentum_score": float(momentum_score),
            "peak_week_start": _week_start_label(now, best_week_idx),
            "peak_week_count": int(best_count),
            "baseline_weekly_mean": round(float(best_mean), 2),
            "baseline_weekly_std": round(float(best_std), 2),
            "z_score": round(float(best_z), 2),
            "is_spike": bool(is_spike),
            "reason": reason,
            "human_summary": human_summary,
        }
        trending_list.append(entry)
        if is_spike:
            spikes_list.append(entry)

    trending_list.sort(key=lambda x: (x["is_spike"], x["momentum_score"]), reverse=True)
    spikes_list.sort(key=lambda x: x["z_score"], reverse=True)

    # Build chronological weekly series for top 6 topics
    top6_topics = [t["topic"] for t in trending_list[:6]]
    weekly_series = []
    for w in range(min(horizon_weeks, 16) - 1, -1, -1):
        point: Dict[str, Any] = {"week": _week_start_label(now, w)}
        for t in top6_topics:
            point[t] = int(weekly_topic_counts[t].get(w, 0))
        weekly_series.append(point)

    return {
        "window_days": window_days,
        "z_threshold": z_threshold,
        "trending_topics": trending_list[:20],
        "topic_spikes": spikes_list,
        "weekly_series": weekly_series,
    }


def persist_spike_alerts(db: Session, spikes: List[Dict[str, Any]]) -> int:
    """Create MonitoringAlert records for newly detected topic spikes."""
    created = 0
    existing_entities = {
        a.entity_id
        for a in db.query(MonitoringAlert).filter(MonitoringAlert.alert_type == "topic_spike").all()
    }
    for sp in spikes:
        if sp["topic"] in existing_entities:
            continue
        severity = "high" if sp["z_score"] >= 3.2 else "medium"
        alert = MonitoringAlert(
            alert_type="topic_spike",
            severity=severity,
            title=f"Sudden Research Topic Spike: #{sp['topic']}",
            description=sp["reason"],
            entity_type="topic",
            entity_id=sp["topic"],
            metrics_json=sp,
            status="open",
        )
        db.add(alert)
        created += 1
    if created:
        db.commit()
    return created
