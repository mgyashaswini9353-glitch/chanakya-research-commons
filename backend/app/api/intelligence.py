"""F4-F9: Unified Search, Recommendations, Trends/Monitoring, RAG Assistant, Analytics & Admin API."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from analytics.warehouse_service import drilldown_analytics, get_overview_analytics
from backend.app.core.config import PROJECT_ROOT
from backend.app.core.database import get_db
from backend.app.core.rate_limit import rate_limit_dependency
from backend.app.core.security import get_current_user, get_current_user_optional, require_admin
from backend.app.models.models import (
    ActivityEvent,
    Comment,
    Department,
    IngestionJob,
    MonitoringAlert,
    Paper,
    Post,
    SavedPaper,
    TopicFollow,
    User,
    UserFollow,
)
from backend.app.schemas.schemas import (
    AlertStatusUpdateRequest,
    AssistantAskRequest,
    IngestionTriggerRequest,
    RoleUpdateRequest,
)
from data_warehouse.etl import build_warehouse
from ingestion.pipeline import ingest_arxiv, ingest_curated_rss, ingest_openalex
from ml.anomaly_detection.spam_detector import detect_spam_accounts
from ml.embeddings.embedder import get_embedder, get_embedder_status
from ml.recommendations.recommender import (
    recommend_also_saved_fpgrowth,
    recommend_papers_for_user,
    recommend_researchers_for_user,
)
from ml.search.search_engine import compute_and_store_pagerank, unified_four_panel_search
from ml.trend_detection.trends import compute_trending_and_spikes, persist_spike_alerts
from research_assistant.rag_engine import answer_research_question

logger = logging.getLogger("chanakya_commons.intelligence")
router = APIRouter(tags=["F4-F9: Search, ML, RAG & Institutional Analytics"])


# --- Dashboard Summary ---
@router.get("/api/dashboard/summary")
def dashboard_summary(
    viewer: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    total_papers = db.query(Paper).count()
    library_papers = db.query(Paper).filter(Paper.in_university_library == True).count()
    total_members = db.query(User).filter(User.is_active == True, User.is_flagged_spam == False).count()
    total_posts = db.query(Post).count()
    total_depts = db.query(Department).count()
    total_events = db.query(ActivityEvent).count()

    user_stats = None
    if viewer:
        user_stats = {
            "my_saved_papers": db.query(SavedPaper).filter(SavedPaper.user_id == viewer.id).count(),
            "my_posts": db.query(Post).filter(Post.author_id == viewer.id).count(),
            "my_following": db.query(UserFollow).filter(UserFollow.follower_id == viewer.id).count(),
            "my_followers": db.query(UserFollow).filter(UserFollow.following_id == viewer.id).count(),
            "my_followed_topics": [t.topic for t in db.query(TopicFollow).filter(TopicFollow.user_id == viewer.id).all()],
        }

    return {
        "platform": {
            "total_papers": total_papers,
            "library_papers": library_papers,
            "total_members": total_members,
            "total_posts": total_posts,
            "total_departments": total_depts,
            "total_activity_events": total_events,
            "embedder_backend": get_embedder_status(),
        },
        "user": user_stats,
    }


@router.get("/api/notifications")
def get_notifications(
    limit: int = Query(default=12, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Real platform notifications derived from followers, discussion replies, and emerging topics."""
    items = []

    # 1. Recent followers
    recent_follows = (
        db.query(UserFollow, User)
        .join(User, UserFollow.follower_id == User.id)
        .filter(UserFollow.following_id == current_user.id, User.is_flagged_spam == False)
        .order_by(UserFollow.created_at.desc())
        .limit(4)
        .all()
    )
    for fl, follower in recent_follows:
        items.append(
            {
                "id": f"follow-{fl.follower_id}",
                "type": "follow",
                "title": f"{follower.full_name} started following your research",
                "subtitle": f"{follower.role.title()} profile",
                "link": f"/researchers/{follower.id}",
                "created_at": fl.created_at.isoformat() if fl.created_at else None,
            }
        )

    # 2. Recent comments on the user's posts
    my_post_ids = [p.id for p in db.query(Post.id).filter(Post.author_id == current_user.id).all()]
    if my_post_ids:
        recent_comments = (
            db.query(Comment, User, Post)
            .join(User, Comment.author_id == User.id)
            .join(Post, Comment.post_id == Post.id)
            .filter(
                Comment.post_id.in_(my_post_ids),
                Comment.author_id != current_user.id,
                User.is_flagged_spam == False,
            )
            .order_by(Comment.created_at.desc())
            .limit(5)
            .all()
        )
        for cm, commenter, po in recent_comments:
            items.append(
                {
                    "id": f"comment-{cm.id}",
                    "type": "comment",
                    "title": f"{commenter.full_name} commented on your discussion",
                    "subtitle": po.title[:80],
                    "link": f"/discussions?post={po.id}",
                    "created_at": cm.created_at.isoformat() if cm.created_at else None,
                }
            )

    # 3. Emerging research topics matching university activity
    trends = compute_trending_and_spikes(db, window_days=14)
    for sp in (trends.get("topic_spikes") or [])[:3]:
        nice_topic = sp["topic"].replace("-", " ").title()
        items.append(
            {
                "id": f"trend-{sp['topic']}",
                "type": "trend",
                "title": f"Growing interest in {nice_topic}",
                "subtitle": f"{sp['recent_count']} recent university interactions",
                "link": f"/search?q={sp['topic']}",
                "created_at": None,
            }
        )

    items.sort(key=lambda x: x["created_at"] or "", reverse=True)
    return {"unread_count": len(items[:limit]), "items": items[:limit]}


# --- F5: Unified 4-Panel Research Search ---
@router.get("/api/search/unified")
def unified_search(
    q: str = Query(default="", max_length=300),
    mode: str = Query(default="hybrid", pattern="^(hybrid|keyword|semantic)$"),
    department: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    source: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = Query(default=12, ge=1, le=30),
    viewer: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if q.strip():
        db.add(
            ActivityEvent(
                user_id=viewer.id if viewer else None,
                event_type="search",
                query_text=q.strip(),
                topic=(tag.lower() if tag else q.strip().lower().split()[0][:60]),
                department_id=viewer.department_id if viewer else None,
                metadata_json={"mode": mode},
            )
        )
        db.commit()

    res = unified_four_panel_search(
        db=db,
        query=q,
        mode=mode,
        department_code=department,
        year_from=year_from,
        year_to=year_to,
        source=source,
        tag=tag,
        limit_per_panel=limit,
    )

    if viewer:
        saved_ids = {sp.paper_id for sp in db.query(SavedPaper).filter(SavedPaper.user_id == viewer.id).all()}
        for panel_name in ("external_papers", "university_library"):
            for item in res["panels"][panel_name]:
                item["is_saved_by_me"] = item["id"] in saved_ids
    return res


# --- F6: Recommendation Engine ---
@router.get("/api/recommendations/papers")
def get_paper_recommendations(
    limit: int = Query(default=10, ge=1, le=25),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return recommend_papers_for_user(db, current_user, limit=limit)


@router.get("/api/recommendations/researchers")
def get_researcher_recommendations(
    limit: int = Query(default=8, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return recommend_researchers_for_user(db, current_user, limit=limit)


@router.get("/api/recommendations/also-saved/{paper_id}")
def get_also_saved(
    paper_id: int,
    limit: int = Query(default=6, ge=1, le=12),
    db: Session = Depends(get_db),
):
    return recommend_also_saved_fpgrowth(db, paper_id, limit=limit)


# --- F7: Trends & Spike Detection ---
@router.get("/api/trends")
def get_trends(
    window_days: int = Query(default=14, ge=7, le=60),
    z_threshold: float = Query(default=3.0, ge=1.2, le=5.0),
    db: Session = Depends(get_db),
):
    return compute_trending_and_spikes(db, window_days=window_days, z_threshold=z_threshold)


# --- F8: Grounded RAG AI Research Assistant ---
@router.post(
    "/api/assistant/ask",
    dependencies=[Depends(rate_limit_dependency("rag_assistant", max_requests=25, window_seconds=60))],
)
def ask_research_assistant(
    payload: AssistantAskRequest,
    viewer: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if viewer:
        db.add(
            ActivityEvent(
                user_id=viewer.id,
                event_type="search",
                query_text=payload.question,
                topic="research-assistant",
                department_id=viewer.department_id,
                metadata_json={"mode": "rag_assistant"},
            )
        )
        db.commit()
    return answer_research_question(
        db=db,
        question=payload.question,
        top_k=payload.top_k,
        only_library=payload.only_library,
    )


# --- F9: Institutional Analytics Dashboard (Admin-Only, DuckDB over Star Schema Parquet) ---
@router.get("/api/analytics/overview")
def analytics_overview(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        return get_overview_analytics()
    except FileNotFoundError:
        build_warehouse(db)
        return get_overview_analytics()


@router.get("/api/analytics/drilldown")
def analytics_drilldown(
    department_code: Optional[str] = None,
    topic_name: Optional[str] = None,
    member_id: Optional[int] = None,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return drilldown_analytics(
            department_code=department_code,
            topic_name=topic_name,
            member_id=member_id,
        )
    except FileNotFoundError:
        build_warehouse(db)
        return drilldown_analytics(
            department_code=department_code,
            topic_name=topic_name,
            member_id=member_id,
        )


@router.post("/api/analytics/rebuild-warehouse")
def rebuild_warehouse_endpoint(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    counts = build_warehouse(db)
    return {"status": "rebuilt", "table_counts": counts}


# --- Admin Monitoring, Spam Flags, Ingestion & Evaluation Reports ---
@router.get("/api/admin/alerts")
def list_alerts(
    alert_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(MonitoringAlert)
    if alert_type:
        q = q.filter(MonitoringAlert.alert_type == alert_type)
    if status_filter:
        q = q.filter(MonitoringAlert.status == status_filter)
    rows = q.order_by(MonitoringAlert.created_at.desc()).limit(100).all()
    return [
        {
            "id": a.id,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "title": a.title,
            "description": a.description,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "metrics": a.metrics_json or {},
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        }
        for a in rows
    ]


@router.patch("/api/admin/alerts/{alert_id}")
def update_alert_status(
    alert_id: int,
    payload: AlertStatusUpdateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    alert = db.query(MonitoringAlert).filter(MonitoringAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = payload.status
    if payload.status in ("reviewed", "dismissed", "action_taken"):
        alert.resolved_at = datetime.now(timezone.utc)
    if payload.status == "action_taken" and alert.entity_type == "user":
        u = db.query(User).filter(User.id == int(alert.entity_id)).first()
        if u and u.role != "admin":
            u.is_active = False
            u.is_flagged_spam = True
    elif payload.status == "dismissed" and alert.entity_type == "user":
        u = db.query(User).filter(User.id == int(alert.entity_id)).first()
        if u:
            u.is_flagged_spam = False
            u.is_active = True
    db.commit()
    return {"id": alert.id, "status": alert.status}


@router.get("/api/admin/spam-report")
def get_spam_report(
    rescan: bool = False,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    report = detect_spam_accounts(db, persist_alerts=rescan)
    if rescan:
        trends = compute_trending_and_spikes(db)
        persist_spike_alerts(db, trends["topic_spikes"])
    return {
        "total_users_analyzed": report["total_users_analyzed"],
        "flagged_count": report["flagged_count"],
        "flagged_accounts": report["flagged_accounts"],
    }


@router.post("/api/admin/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot suspend an administrator account")
    u.is_active = not u.is_active
    db.commit()
    return {"user_id": u.id, "is_active": u.is_active}


@router.patch("/api/admin/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: RoleUpdateRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.id == admin_user.id and payload.role != "admin":
        raise HTTPException(status_code=400, detail="Administrators cannot demote their own active account")
    if u.role == "admin" and payload.role != "admin":
        active_admins = db.query(User).filter(User.role == "admin", User.is_active == True).count()
        if active_admins <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last active administrator")
    previous_role = u.role
    u.role = payload.role
    db.commit()
    logger.info(
        "ADMIN_AUDIT role_change actor_id=%s target_user_id=%s old_role=%s new_role=%s at=%s",
        admin_user.id,
        u.id,
        previous_role,
        u.role,
        datetime.now(timezone.utc).isoformat(),
    )
    return {"user_id": u.id, "previous_role": previous_role, "role": u.role}


@router.get("/api/admin/ingestion-jobs")
def list_ingestion_jobs(_admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    jobs = db.query(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(40).all()
    return [
        {
            "id": j.id,
            "source": j.source,
            "status": j.status,
            "records_fetched": j.records_fetched,
            "records_inserted": j.records_inserted,
            "records_merged": j.records_merged,
            "raw_file_path": j.raw_file_path,
            "error_message": j.error_message,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]


@router.post("/api/admin/ingestion/run")
def trigger_ingestion(
    payload: IngestionTriggerRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    results = []
    if payload.source in ("openalex", "all"):
        results.append(ingest_openalex(db, per_query=payload.per_query))
    if payload.source in ("arxiv", "all"):
        results.append(ingest_arxiv(db, per_query=max(5, payload.per_query // 2)))
    if payload.source in ("rss", "all"):
        results.append(ingest_curated_rss(db, max_per_feed=8))

    # Re-embed any newly inserted papers without embeddings + refresh PageRank & Warehouse
    embedder = get_embedder()
    new_papers = db.query(Paper).filter(Paper.embedding.is_(None)).all()
    if new_papers:
        texts = [f"{p.title}. {p.abstract or ''}" for p in new_papers]
        vecs = embedder.encode(texts)
        for p, v in zip(new_papers, vecs):
            p.embedding = [round(float(x), 5) for x in v]
        db.commit()

    compute_and_store_pagerank(db)
    wh = build_warehouse(db)
    return {"jobs": results, "newly_embedded": len(new_papers), "warehouse_tables": wh}


@router.get("/api/admin/evaluations")
def get_evaluation_results(_admin: User = Depends(require_admin)):
    res_file = PROJECT_ROOT / "evaluation" / "results" / "evaluation_summary.json"
    if not res_file.exists():
        return {"available": False, "message": "Run python evaluation/run_evaluations.py to generate metrics."}
    with open(res_file, "r", encoding="utf-8") as f:
        return {"available": True, "results": json.load(f)}
