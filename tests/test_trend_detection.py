"""Focused regression tests for F7 Trend Spike Detection (`ml/trend_detection/trends.py`)."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.database import Base
from backend.app.models.models import ActivityEvent, MonitoringAlert, User
from ml.trend_detection.trends import compute_trending_and_spikes, persist_spike_alerts


@pytest.fixture()
def db_session():
    """Isolated in-memory SQLite database per test so real project DB is untouched."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _create_user(db, username: str, *, is_spam: bool = False) -> User:
    u = User(
        email=f"{username}@chanakya.edu.in",
        username=username,
        password_hash="not-used-in-unit-test",
        full_name=username.replace("_", " ").title(),
        role="student",
        is_flagged_spam=is_spam,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _add_weekly_events(
    db,
    user_id: int,
    topic: str,
    weekly_counts: dict[int, int],
    anchor: datetime,
) -> None:
    """Insert events for `topic` at exact week offsets (week 0 = 1 day before anchor, etc.)."""
    rows = []
    for week_idx, count in weekly_counts.items():
        base_days_ago = week_idx * 7 + 1
        for i in range(count):
            ts = anchor - timedelta(days=base_days_ago, minutes=i * 3)
            rows.append(
                ActivityEvent(
                    user_id=user_id,
                    event_type="view" if i % 2 == 0 else "search",
                    topic=topic,
                    metadata_json={},
                    is_synthetic=True,
                    created_at=ts,
                )
            )
    db.bulk_save_objects(rows)
    db.commit()


ANCHOR = datetime(2026, 11, 26, 12, 0, 0, tzinfo=timezone.utc)


def test_1_genuine_sudden_topic_spike(db_session):
    """A genuine sudden spike over a normal multi-week baseline is detected with explanation."""
    u = _create_user(db_session, "regular_1")
    counts = {w: 8 + (w % 3) for w in range(1, 14)}
    counts[0] = 68  # sudden surge in week 0
    _add_weekly_events(db_session, u.id, "graph-transformers", counts, ANCHOR)

    res = compute_trending_and_spikes(db_session, reference_now=ANCHOR)
    spike_topics = [s["topic"] for s in res["topic_spikes"]]
    assert spike_topics == ["graph-transformers"]

    sp = res["topic_spikes"][0]
    assert sp["is_spike"] is True
    assert sp["peak_week_count"] == 68
    assert sp["z_score"] >= 3.0
    assert "surged to 68 events" in sp["reason"]
    assert "Growing interest in Graph Transformers" in sp["human_summary"]
    assert len(res["weekly_series"]) > 0

    created = persist_spike_alerts(db_session, res["topic_spikes"])
    assert created == 1
    assert db_session.query(MonitoringAlert).filter(MonitoringAlert.alert_type == "topic_spike").count() == 1


def test_2_multiple_spikes_in_different_weeks_including_boundary_split(db_session):
    """Spikes occurring in different weeks (including a spike split across two adjacent weeks) are all detected."""
    u = _create_user(db_session, "regular_2")

    # Topic A: boundary-split spike across week 0 (62) and week 1 (44), baseline ~10
    topic_a = {w: 10 + (w % 2) for w in range(2, 16)}
    topic_a[0] = 62
    topic_a[1] = 44
    _add_weekly_events(db_session, u.id, "topic-alpha", topic_a, ANCHOR)

    # Topic B: spike in week 2 (75), baseline ~6
    topic_b = {w: 6 for w in range(0, 16)}
    topic_b[2] = 75
    _add_weekly_events(db_session, u.id, "topic-beta", topic_b, ANCHOR)

    # Topic C: spike in week 4 (85), baseline ~15
    topic_c = {w: 15 + (w % 3) for w in range(0, 16)}
    topic_c[4] = 85
    _add_weekly_events(db_session, u.id, "topic-gamma", topic_c, ANCHOR)

    # Ordinary stable control topic
    control = {w: 12 + (w % 4) for w in range(0, 16)}
    _add_weekly_events(db_session, u.id, "ordinary-topic", control, ANCHOR)

    res = compute_trending_and_spikes(db_session, reference_now=ANCHOR)
    detected = {s["topic"] for s in res["topic_spikes"]}
    assert detected == {"topic-alpha", "topic-beta", "topic-gamma"}


def test_3_stable_activity_produces_no_spike(db_session):
    """A topic with normal week-to-week fluctuation around a stable mean is never flagged."""
    u = _create_user(db_session, "regular_3")
    stable = {w: 18 + (w % 5) - 2 for w in range(0, 18)}  # 16..20 events/week
    _add_weekly_events(db_session, u.id, "stable-analytics", stable, ANCHOR)

    res = compute_trending_and_spikes(db_session, reference_now=ANCHOR)
    assert res["topic_spikes"] == []
    assert len(res["trending_topics"]) == 1
    assert res["trending_topics"][0]["is_spike"] is False


def test_4_insufficient_historical_observations(db_session):
    """Short history (< min_baseline_weeks) or brand-new sparse topics must not false-alarm."""
    u = _create_user(db_session, "regular_4")

    # Case A: Entire dataset has only 3 weeks total
    _add_weekly_events(db_session, u.id, "short-history-topic", {0: 55, 1: 4, 2: 3}, ANCHOR)
    res_short = compute_trending_and_spikes(db_session, reference_now=ANCHOR)
    assert res_short["topic_spikes"] == []
    assert res_short["trending_topics"][0]["z_score"] == 0.0

    # Case B: Platform has 12 weeks via another topic, but brand-new topic only has 1 week of activity
    _add_weekly_events(db_session, u.id, "long-background-topic", {w: 10 for w in range(0, 12)}, ANCHOR)
    _add_weekly_events(db_session, u.id, "brand-new-topic", {0: 45}, ANCHOR)
    res_brand_new = compute_trending_and_spikes(db_session, reference_now=ANCHOR)
    assert all(s["topic"] != "brand-new-topic" for s in res_brand_new["topic_spikes"])


def test_5_zero_historical_variance_handled_safely(db_session):
    """Constant baseline (zero variance) must avoid division-by-zero and still detect real surges."""
    u = _create_user(db_session, "regular_5")
    # Constant 5 events/week for 10 baseline weeks, then sudden surge to 45 in week 0
    zero_var_spike = {w: 5 for w in range(1, 11)}
    zero_var_spike[0] = 45
    _add_weekly_events(db_session, u.id, "constant-then-spike", zero_var_spike, ANCHOR)

    res = compute_trending_and_spikes(db_session, reference_now=ANCHOR)
    assert [s["topic"] for s in res["topic_spikes"]] == ["constant-then-spike"]
    sp = res["topic_spikes"][0]
    assert sp["baseline_weekly_mean"] == 5.0
    assert sp["baseline_weekly_std"] == 0.0
    assert sp["z_score"] > 10.0


def test_6_spam_account_events_excluded(db_session):
    """Events from spam-flagged users must be excluded so bot bursts cannot fabricate spikes."""
    regular = _create_user(db_session, "regular_6", is_spam=False)
    spammer = _create_user(db_session, "spam_bot_6", is_spam=True)

    # Regular users have flat baseline of 8/week
    _add_weekly_events(db_session, regular.id, "quantum-computing", {w: 8 for w in range(0, 12)}, ANCHOR)
    # Spam bot blasts 120 events in week 0
    _add_weekly_events(db_session, spammer.id, "quantum-computing", {0: 120}, ANCHOR)

    res = compute_trending_and_spikes(db_session, reference_now=ANCHOR)
    assert res["topic_spikes"] == []
    entry = res["trending_topics"][0]
    assert entry["topic"] == "quantum-computing"
    assert entry["peak_week_count"] == 8


def test_7_uniformly_distributed_activity_no_false_spike(db_session):
    """Uniformly distributed activity (even above min_recent_count) must never trigger a spike."""
    u = _create_user(db_session, "regular_7")
    uniform_high = {w: 40 for w in range(0, 14)}
    uniform_low = {w: 10 for w in range(0, 14)}
    _add_weekly_events(db_session, u.id, "uniform-high", uniform_high, ANCHOR)
    _add_weekly_events(db_session, u.id, "uniform-low", uniform_low, ANCHOR)

    res = compute_trending_and_spikes(db_session, reference_now=ANCHOR)
    assert res["topic_spikes"] == []
    for entry in res["trending_topics"]:
        assert entry["is_spike"] is False
        assert entry["z_score"] == 0.0
