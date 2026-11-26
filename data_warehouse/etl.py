"""
Data Warehouse ETL Pipeline (Silver Operational DB -> Gold Star Schema Parquet -> DuckDB).
Builds Kimball Star Schema:
  Dimensions: dim_date, dim_department, dim_member, dim_topic, dim_paper
  Facts:      fact_research_activity, fact_paper_saves, fact_search_events, fact_post_engagement
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import duckdb
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.models import (
    ActivityEvent,
    Department,
    Paper,
    Post,
    SavedPaper,
    User,
)


def _normalize_topic(topic: str | None) -> str:
    if not topic:
        return "general"
    return str(topic).strip().lower()


def _date_key(dt: datetime | None) -> int:
    if dt is None:
        dt = datetime.now(timezone.utc)
    return int(dt.strftime("%Y%m%d"))


def build_warehouse(db: Session) -> Dict[str, int]:
    """Extract operational tables, transform into Star Schema Parquet files, and load DuckDB."""
    parquet_dir = Path(settings.PARQUET_DIR)
    parquet_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = Path(settings.DUCKDB_PATH)
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)

    departments = db.query(Department).all()
    users = db.query(User).all()
    papers = db.query(Paper).all()
    saves = db.query(SavedPaper).all()
    posts = db.query(Post).all()
    events = db.query(ActivityEvent).all()

    user_dept_map = {u.id: (u.department_id or 0) for u in users}
    paper_topic_map = {
        p.id: (_normalize_topic(p.topics[0]) if p.topics else "general")
        for p in papers
    }

    # --- 1. DimDepartment ---
    dim_department_rows = [
        {
            "department_key": d.id,
            "department_code": d.code,
            "department_name": d.name,
            "faculty_head": d.faculty_head or "",
        }
        for d in departments
    ]
    if not dim_department_rows:
        dim_department_rows = [{"department_key": 0, "department_code": "GEN", "department_name": "General", "faculty_head": ""}]
    df_dim_department = pd.DataFrame(dim_department_rows)

    # --- 2. DimMember ---
    dim_member_rows = [
        {
            "member_key": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "department_key": u.department_id or 0,
            "is_flagged_spam": bool(u.is_flagged_spam),
            "is_synthetic": bool(u.is_synthetic),
            "created_date_key": _date_key(u.created_at),
        }
        for u in users
    ]
    df_dim_member = pd.DataFrame(
        dim_member_rows
        or [
            {
                "member_key": 0,
                "username": "system",
                "full_name": "System",
                "role": "admin",
                "department_key": 0,
                "is_flagged_spam": False,
                "is_synthetic": True,
                "created_date_key": _date_key(None),
            }
        ]
    )

    # --- 3. DimPaper ---
    dim_paper_rows = [
        {
            "paper_key": p.id,
            "title": p.title,
            "primary_source": p.primary_source,
            "source_count": len(p.sources or []),
            "publication_year": int(p.publication_year or 2024),
            "venue": p.venue or "",
            "doi": p.doi or "",
            "arxiv_id": p.arxiv_id or "",
            "primary_topic": paper_topic_map[p.id],
            "department_hint": p.department_hint or "",
            "citation_count": int(p.citation_count or 0),
            "pagerank_score": float(p.pagerank_score or 0.0),
            "save_count": int(p.save_count or 0),
            "in_university_library": bool(p.in_university_library),
            "is_synthetic": bool(p.is_synthetic),
        }
        for p in papers
    ]
    df_dim_paper = pd.DataFrame(
        dim_paper_rows
        or [
            {
                "paper_key": 0,
                "title": "Placeholder",
                "primary_source": "none",
                "source_count": 0,
                "publication_year": 2024,
                "venue": "",
                "doi": "",
                "arxiv_id": "",
                "primary_topic": "general",
                "department_hint": "",
                "citation_count": 0,
                "pagerank_score": 0.0,
                "save_count": 0,
                "in_university_library": False,
                "is_synthetic": True,
            }
        ]
    )

    # --- 4. DimTopic ---
    topic_set = {"general"}
    for p in papers:
        for t in (p.topics or []):
            topic_set.add(_normalize_topic(t))
    for u in users:
        for t in (u.research_tags or []):
            topic_set.add(_normalize_topic(t))
    for po in posts:
        for t in (po.tags or []):
            topic_set.add(_normalize_topic(t))
    for ev in events:
        if ev.topic:
            topic_set.add(_normalize_topic(ev.topic))

    sorted_topics = sorted(topic_set)
    topic_key_map = {t: idx + 1 for idx, t in enumerate(sorted_topics)}
    df_dim_topic = pd.DataFrame(
        [{"topic_key": idx + 1, "topic_name": t} for idx, t in enumerate(sorted_topics)]
    )

    # --- 5. DimDate (collect all dates across events, saves, posts, users) ---
    all_dates = set()
    for ev in events:
        if ev.created_at:
            all_dates.add(ev.created_at.date())
    for sp in saves:
        if sp.saved_at:
            all_dates.add(sp.saved_at.date())
    for po in posts:
        if po.created_at:
            all_dates.add(po.created_at.date())
    if not all_dates:
        all_dates.add(datetime.now(timezone.utc).date())

    dim_date_rows = []
    for d in sorted(all_dates):
        dim_date_rows.append(
            {
                "date_key": int(d.strftime("%Y%m%d")),
                "full_date": d.isoformat(),
                "year": d.year,
                "quarter": (d.month - 1) // 3 + 1,
                "month": d.month,
                "month_name": d.strftime("%b %Y"),
                "year_month": d.strftime("%Y-%m"),
                "iso_week": f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}",
                "day_of_week": d.strftime("%A"),
            }
        )
    df_dim_date = pd.DataFrame(dim_date_rows)

    # --- 6. FactResearchActivity ---
    fact_activity_rows = []
    for ev in events:
        t_name = _normalize_topic(ev.topic or (paper_topic_map.get(ev.paper_id) if ev.paper_id else "general"))
        dept_key = ev.department_id or (user_dept_map.get(ev.user_id, 0) if ev.user_id else 0)
        fact_activity_rows.append(
            {
                "activity_id": ev.id,
                "date_key": _date_key(ev.created_at),
                "member_key": ev.user_id or 0,
                "department_key": dept_key,
                "topic_key": topic_key_map.get(t_name, topic_key_map["general"]),
                "paper_key": ev.paper_id or 0,
                "post_key": ev.post_id or 0,
                "event_type": ev.event_type,
                "is_synthetic": bool(ev.is_synthetic),
                "event_timestamp": ev.created_at.isoformat() if ev.created_at else datetime.now(timezone.utc).isoformat(),
            }
        )
    df_fact_activity = pd.DataFrame(
        fact_activity_rows
        or [
            {
                "activity_id": 0,
                "date_key": int(df_dim_date["date_key"].iloc[0]),
                "member_key": 0,
                "department_key": 0,
                "topic_key": topic_key_map["general"],
                "paper_key": 0,
                "post_key": 0,
                "event_type": "view",
                "is_synthetic": True,
                "event_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )

    # --- 7. FactPaperSaves ---
    fact_save_rows = []
    for sp in saves:
        t_name = paper_topic_map.get(sp.paper_id, "general")
        fact_save_rows.append(
            {
                "save_id": sp.id,
                "date_key": _date_key(sp.saved_at),
                "member_key": sp.user_id,
                "department_key": user_dept_map.get(sp.user_id, 0),
                "paper_key": sp.paper_id,
                "topic_key": topic_key_map.get(t_name, topic_key_map["general"]),
                "has_notes": bool(sp.private_notes and sp.private_notes.strip()),
            }
        )
    df_fact_saves = pd.DataFrame(
        fact_save_rows
        or [
            {
                "save_id": 0,
                "date_key": int(df_dim_date["date_key"].iloc[0]),
                "member_key": 0,
                "department_key": 0,
                "paper_key": 0,
                "topic_key": topic_key_map["general"],
                "has_notes": False,
            }
        ]
    )

    # --- 8. FactSearchEvents ---
    fact_search_rows = []
    for ev in events:
        if ev.event_type == "search":
            t_name = _normalize_topic(ev.topic)
            fact_search_rows.append(
                {
                    "search_id": ev.id,
                    "date_key": _date_key(ev.created_at),
                    "member_key": ev.user_id or 0,
                    "department_key": ev.department_id or user_dept_map.get(ev.user_id or 0, 0),
                    "topic_key": topic_key_map.get(t_name, topic_key_map["general"]),
                    "query_text": ev.query_text or "",
                    "search_mode": (ev.metadata_json or {}).get("mode", "hybrid"),
                }
            )
    df_fact_search = pd.DataFrame(
        fact_search_rows
        or [
            {
                "search_id": 0,
                "date_key": int(df_dim_date["date_key"].iloc[0]),
                "member_key": 0,
                "department_key": 0,
                "topic_key": topic_key_map["general"],
                "query_text": "",
                "search_mode": "hybrid",
            }
        ]
    )

    # --- 9. FactPostEngagement ---
    fact_post_rows = []
    for po in posts:
        first_tag = _normalize_topic(po.tags[0]) if po.tags else "general"
        fact_post_rows.append(
            {
                "post_key": po.id,
                "post_title": po.title,
                "date_key": _date_key(po.created_at),
                "member_key": po.author_id,
                "department_key": user_dept_map.get(po.author_id, 0),
                "topic_key": topic_key_map.get(first_tag, topic_key_map["general"]),
                "paper_key": po.attached_paper_id or 0,
                "upvote_count": int(po.upvote_count or 0),
                "comment_count": int(po.comment_count or 0),
            }
        )
    df_fact_posts = pd.DataFrame(
        fact_post_rows
        or [
            {
                "post_key": 0,
                "post_title": "",
                "date_key": int(df_dim_date["date_key"].iloc[0]),
                "member_key": 0,
                "department_key": 0,
                "topic_key": topic_key_map["general"],
                "paper_key": 0,
                "upvote_count": 0,
                "comment_count": 0,
            }
        ]
    )

    tables = {
        "dim_date": df_dim_date,
        "dim_department": df_dim_department,
        "dim_member": df_dim_member,
        "dim_topic": df_dim_topic,
        "dim_paper": df_dim_paper,
        "fact_research_activity": df_fact_activity,
        "fact_paper_saves": df_fact_saves,
        "fact_search_events": df_fact_search,
        "fact_post_engagement": df_fact_posts,
    }

    counts: Dict[str, int] = {}
    for name, df in tables.items():
        out_path = parquet_dir / f"{name}.parquet"
        df.to_parquet(out_path, index=False, engine="pyarrow")
        counts[name] = len(df)

    # Materialize DuckDB analytical database over Parquet files
    con = duckdb.connect(str(duckdb_path))
    try:
        for name in tables.keys():
            pq_file = (parquet_dir / f"{name}.parquet").as_posix()
            con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_parquet('{pq_file}');")
    finally:
        con.close()

    return counts
