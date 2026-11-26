"""Comprehensive automated Pytest suite for Chanakya Research Commons (F1-F9)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["APP_ENV"] = "test"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _login(email: str, password: str = "Chanakya@2026") -> dict:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_and_departments():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    d = client.get("/api/departments")
    assert d.status_code == 200
    assert len(d.json()) >= 6


def test_dataset_minimum_requirements():
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    p = r.json()["platform"]
    assert p["total_papers"] >= 500
    assert p["total_departments"] >= 6
    assert p["total_members"] >= 50
    assert p["total_activity_events"] >= 10000


def test_security_admin_self_registration_blocked():
    """Public registration must reject role='admin' to prevent privilege escalation."""
    bad_reg = client.post(
        "/api/auth/register",
        json={
            "email": "attacker_admin@chanakya.edu.in",
            "username": "attacker_admin_u",
            "password": "TestPassword123!",
            "full_name": "Unauthorized Admin Attempt",
            "role": "admin",
        },
    )
    assert bad_reg.status_code in (403, 422), bad_reg.text

    # Non-admin cannot invoke admin role update endpoint
    h_stu = _login("student@chanakya.edu.in")
    r_forbid = client.patch("/api/admin/users/4/role", headers=h_stu, json={"role": "admin"})
    assert r_forbid.status_code == 403

    # Admin cannot demote their own active account
    h_adm = _login("admin@chanakya.edu.in")
    me_adm = client.get("/api/auth/me", headers=h_adm).json()
    r_self = client.patch(f"/api/admin/users/{me_adm['id']}/role", headers=h_adm, json={"role": "student"})
    assert r_self.status_code == 400


def test_security_rate_limiting_and_production_config_guard():
    """Verify sliding-window rate limiter triggers HTTP 429 and production security guard enforces strong secrets."""
    from backend.app.core.config import Settings
    from backend.app.core.rate_limit import rate_limiter

    rate_limiter.reset()
    # Auth login limit is 12/min; 13th call with x-enforce-rate-limit=1 must return 429
    statuses = []
    for _ in range(13):
        r = client.post(
            "/api/auth/login",
            json={"email": "nonexistent_rate_limit@chanakya.edu.in", "password": "wrongpassword"},
            headers={"x-enforce-rate-limit": "1", "x-forwarded-for": "198.51.100.42"},
        )
        statuses.append(r.status_code)
    assert statuses[-1] == 429
    rate_limiter.reset()

    # Production config guard must reject weak/default JWT, SQLite, DEBUG=True, wildcard CORS
    import pytest as _pytest

    with _pytest.raises(RuntimeError):
        Settings(APP_ENV="production", DEBUG=False, DATABASE_URL="postgresql+psycopg://u:StrongPass123!@db/d", JWT_SECRET_KEY="chanakya-docker-secret-key-change-me-32chars", CORS_ORIGINS="https://commons.example.edu", MINIO_ENABLED=False).validate_production_security()

    with _pytest.raises(RuntimeError):
        Settings(APP_ENV="production", DEBUG=False, DATABASE_URL="sqlite:///./local.db", JWT_SECRET_KEY="a" * 64, CORS_ORIGINS="https://commons.example.edu", MINIO_ENABLED=False).validate_production_security()

    with _pytest.raises(RuntimeError):
        Settings(APP_ENV="production", DEBUG=False, DATABASE_URL="postgresql+psycopg://u:StrongPass123!@db/d", JWT_SECRET_KEY="a" * 64, CORS_ORIGINS="*", MINIO_ENABLED=False).validate_production_security()

    # Valid production configuration must pass cleanly
    Settings(
        APP_ENV="production",
        DEBUG=False,
        DATABASE_URL="postgresql+psycopg://u:StrongPass123!@postgres:5432/chanakya_commons",
        JWT_SECRET_KEY="a" * 64,
        CORS_ORIGINS="https://commons.example.edu",
        MINIO_ENABLED=True,
        MINIO_ROOT_PASSWORD="StrongMinioPassword123!",
    ).validate_production_security()


def test_f1_auth_roles_profile_and_follow():
    # Login all 4 roles
    for email, expected_role in [
        ("admin@chanakya.edu.in", "admin"),
        ("faculty@chanakya.edu.in", "faculty"),
        ("researcher@chanakya.edu.in", "researcher"),
        ("student@chanakya.edu.in", "student"),
    ]:
        headers = _login(email)
        me = client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["role"] == expected_role

    # Register a new user, update profile, follow member & topic
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "pytest_new_student@chanakya.edu.in",
            "username": "pytest_student_u",
            "password": "TestPassword123!",
            "full_name": "Pytest Research Student",
            "role": "student",
            "research_interests_text": "Graph neural networks and data mining",
            "research_tags": ["graph-neural-networks", "data-mining"],
        },
    )
    if reg.status_code == 201:
        headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    else:
        headers = _login("pytest_new_student@chanakya.edu.in", "TestPassword123!")

    upd = client.patch(
        "/api/users/me",
        headers=headers,
        json={"bio": "Updated bio via automated test", "personal_website": "https://example.edu/pytest"},
    )
    assert upd.status_code == 200
    assert "Updated bio" in upd.json()["bio"]

    # Follow topic & unfollow
    tf = client.post("/api/users/me/topics/follow", headers=headers, json={"topic": "lakehouse-analytics"})
    assert tf.status_code == 200
    assert tf.json()["following"] is True

    # Follow faculty member
    users = client.get("/api/users?role=faculty", headers=headers).json()
    assert len(users) >= 1
    target_id = users[0]["id"]
    fl = client.post(f"/api/users/{target_id}/follow", headers=headers)
    assert fl.status_code == 200
    assert fl.json()["following"] is True


def test_f2_posts_comments_replies_upvotes_and_feeds():
    headers = _login("student@chanakya.edu.in")
    # Create post
    cr = client.post(
        "/api/posts",
        headers=headers,
        json={
            "title": "Pytest Discussion on Lakehouse Query Performance",
            "content": "Comparing DuckDB over Parquet against row-oriented OLTP scans for university analytics.",
            "tags": ["data-warehousing", "lakehouse-analytics"],
        },
    )
    assert cr.status_code == 201
    post_id = cr.json()["id"]

    # Add comment and nested reply
    c1 = client.post(f"/api/posts/{post_id}/comments", headers=headers, json={"content": "DuckDB vectorized execution is super fast!"})
    assert c1.status_code == 201
    parent_id = c1.json()["id"]

    c2 = client.post(
        f"/api/posts/{post_id}/comments",
        headers=headers,
        json={"content": "Agreed, especially with Parquet projection pushdown.", "parent_comment_id": parent_id},
    )
    assert c2.status_code == 201
    assert c2.json()["parent_comment_id"] == parent_id

    # Toggle upvote on and off
    u1 = client.post(f"/api/posts/{post_id}/upvote", headers=headers)
    assert u1.status_code == 200 and u1.json()["upvoted"] is True
    u2 = client.post(f"/api/posts/{post_id}/upvote", headers=headers)
    assert u2.status_code == 200 and u2.json()["upvoted"] is False

    # Toggle save post on and verify saved feed includes it
    sv1 = client.post(f"/api/posts/{post_id}/save", headers=headers)
    assert sv1.status_code == 200 and sv1.json()["saved"] is True
    sf = client.get("/api/posts?feed=saved", headers=headers)
    assert sf.status_code == 200 and any(p["id"] == post_id for p in sf.json()["items"])
    sv2 = client.post(f"/api/posts/{post_id}/save", headers=headers)
    assert sv2.status_code == 200 and sv2.json()["saved"] is False

    # Personalized feed works
    pf = client.get("/api/posts?feed=personalized", headers=headers)
    assert pf.status_code == 200 and len(pf.json()["items"]) > 0

    # Clean up test post
    dl = client.delete(f"/api/posts/{post_id}", headers=headers)
    assert dl.status_code == 200 and dl.json()["deleted"] is True


def test_f3_library_collections_and_save():
    headers = _login("faculty@chanakya.edu.in")
    col = client.post("/api/collections", headers=headers, json={"name": "Pytest Reading Group", "description": "Temp test collection"})
    assert col.status_code == 201
    col_id = col.json()["id"]

    papers = client.get("/api/papers?limit=3", headers=headers).json()["items"]
    assert len(papers) >= 1
    pid = papers[0]["id"]

    sv = client.post("/api/library/save", headers=headers, json={"paper_id": pid, "collection_id": col_id, "private_notes": "Important baseline"})
    assert sv.status_code == 200 and sv.json()["saved"] is True

    det = client.get(f"/api/papers/{pid}", headers=headers)
    assert det.status_code == 200
    assert "also_saved" in det.json()

    # Delete temp collection
    dc = client.delete(f"/api/collections/{col_id}", headers=headers)
    assert dc.status_code == 200


def test_f5_unified_four_panel_search_modes():
    for mode in ("keyword", "semantic", "hybrid"):
        r = client.get(f"/api/search/unified?q=retrieval+augmented+generation&mode={mode}")
        assert r.status_code == 200
        data = r.json()
        assert set(data["panels"].keys()) == {"external_papers", "university_library", "researchers", "posts"}
        assert data["counts"]["external_papers"] > 0


def test_f6_recommendations_and_cold_start():
    # Regular user with history
    h_stu = _login("student@chanakya.edu.in")
    rp = client.get("/api/recommendations/papers", headers=h_stu)
    assert rp.status_code == 200 and len(rp.json()["recommendations"]) > 0

    rr = client.get("/api/recommendations/researchers", headers=h_stu)
    assert rr.status_code == 200 and len(rr.json()["recommendations"]) > 0

    # Cold-start user (pytest_new_student has 0 saves)
    h_new = _login("pytest_new_student@chanakya.edu.in", "TestPassword123!")
    cs = client.get("/api/recommendations/papers", headers=h_new)
    assert cs.status_code == 200
    assert cs.json()["is_cold_start"] is True
    assert len(cs.json()["recommendations"]) > 0


def test_f7_trends_and_admin_monitoring():
    tr = client.get("/api/trends")
    assert tr.status_code == 200
    assert len(tr.json()["trending_topics"]) > 0
    assert len(tr.json()["topic_spikes"]) >= 1

    # Non-admin blocked from admin routes
    h_stu = _login("student@chanakya.edu.in")
    assert client.get("/api/analytics/overview", headers=h_stu).status_code == 403
    assert client.get("/api/admin/alerts", headers=h_stu).status_code == 403

    # Admin can access spam report & alerts
    h_adm = _login("admin@chanakya.edu.in")
    sp = client.get("/api/admin/spam-report", headers=h_adm)
    assert sp.status_code == 200
    assert sp.json()["flagged_count"] >= 4


def test_f8_rag_assistant_grounding_and_refusal():
    # Answerable research question
    r1 = client.post("/api/assistant/ask", json={"question": "How does retrieval augmented generation help large language models?"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["sufficient_evidence"] is True
    assert len(d1["citations"]) >= 1
    assert len(d1["retrieved_passages"]) >= 1

    # Unanswerable out-of-scope question must NOT hallucinate
    r2 = client.post("/api/assistant/ask", json={"question": "What are the ancient Martian underwater coral reef recipes of 1742?"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["sufficient_evidence"] is False
    assert len(d2["citations"]) == 0


def test_f9_duckdb_warehouse_analytics_and_drilldown():
    h_adm = _login("admin@chanakya.edu.in")
    ov = client.get("/api/analytics/overview", headers=h_adm)
    assert ov.status_code == 200
    data = ov.json()
    assert data["kpis"]["total_papers"] >= 500
    assert data["kpis"]["total_activity_events"] >= 10000
    assert len(data["department_comparison"]) >= 6
    assert len(data["monthly_trends"]) >= 5

    # Drill-down Department -> Topic -> Member
    dd_dept = client.get("/api/analytics/drilldown?department_code=CSAI", headers=h_adm)
    assert dd_dept.status_code == 200 and dd_dept.json()["level"] == "department"
    if dd_dept.json()["topics"]:
        tname = dd_dept.json()["topics"][0]["topic_name"]
        dd_top = client.get(f"/api/analytics/drilldown?department_code=CSAI&topic_name={tname}", headers=h_adm)
        assert dd_top.status_code == 200 and dd_top.json()["level"] == "topic"


def test_notifications_and_recently_viewed():
    h_stu = _login("student@chanakya.edu.in")
    notif = client.get("/api/notifications", headers=h_stu)
    assert notif.status_code == 200
    assert "items" in notif.json()

    # View a paper then confirm recently viewed includes it
    papers = client.get("/api/papers?limit=2", headers=h_stu).json()["items"]
    pid = papers[0]["id"]
    client.get(f"/api/papers/{pid}", headers=h_stu)
    rv = client.get("/api/library/recently-viewed?limit=5", headers=h_stu)
    assert rv.status_code == 200
    assert any(item["id"] == pid for item in rv.json()["items"])
