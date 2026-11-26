"""DuckDB-powered Institutional Analytics Service (F9) over Star Schema Parquet tables."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.app.core.config import settings


def _connect_dw() -> duckdb.DuckDBPyConnection:
    duckdb_path = Path(settings.DUCKDB_PATH)
    if not duckdb_path.exists():
        raise FileNotFoundError(
            f"DuckDB warehouse not found at {duckdb_path}. Run warehouse ETL first."
        )
    return duckdb.connect(str(duckdb_path), read_only=True)


def _query_dicts(con: duckdb.DuckDBPyConnection, sql: str, params: Optional[list] = None) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params or [])
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    result = []
    for row in rows:
        item = {}
        for c, v in zip(cols, row):
            if isinstance(v, (np.integer,)):
                item[c] = int(v)
            elif isinstance(v, (np.floating,)):
                item[c] = float(v)
            else:
                item[c] = v
        result.append(item)
    return result


def get_overview_analytics() -> Dict[str, Any]:
    con = _connect_dw()
    try:
        kpis = _query_dicts(
            con,
            """
            SELECT
                (SELECT COUNT(*) FROM dim_paper WHERE paper_key > 0) AS total_papers,
                (SELECT COUNT(*) FROM dim_paper WHERE in_university_library = TRUE) AS university_library_papers,
                (SELECT COUNT(*) FROM dim_paper WHERE is_synthetic = FALSE AND paper_key > 0) AS external_real_papers,
                (SELECT COUNT(*) FROM dim_member WHERE member_key > 0) AS total_members,
                (SELECT COUNT(*) FROM dim_department WHERE department_key > 0) AS total_departments,
                (SELECT COUNT(*) FROM fact_research_activity WHERE activity_id > 0) AS total_activity_events,
                (SELECT COUNT(*) FROM fact_paper_saves WHERE save_id > 0) AS total_saves,
                (SELECT COUNT(*) FROM fact_post_engagement WHERE post_key > 0) AS total_posts,
                (SELECT COALESCE(SUM(comment_count), 0) FROM fact_post_engagement WHERE post_key > 0) AS total_comments
            """,
        )[0]

        dept_comparison = _query_dicts(
            con,
            """
            SELECT
                d.department_key,
                d.department_code,
                d.department_name,
                COUNT(DISTINCT m.member_key) AS members,
                COUNT(f.activity_id) AS total_events,
                SUM(CASE WHEN f.event_type = 'save' THEN 1 ELSE 0 END) AS saves,
                SUM(CASE WHEN f.event_type = 'view' THEN 1 ELSE 0 END) AS views,
                SUM(CASE WHEN f.event_type = 'search' THEN 1 ELSE 0 END) AS searches,
                SUM(CASE WHEN f.event_type IN ('post', 'comment') THEN 1 ELSE 0 END) AS discussions
            FROM dim_department d
            LEFT JOIN dim_member m ON m.department_key = d.department_key
            LEFT JOIN fact_research_activity f ON f.department_key = d.department_key
            WHERE d.department_key > 0
            GROUP BY d.department_key, d.department_code, d.department_name
            ORDER BY total_events DESC
            """,
        )

        monthly_trends = _query_dicts(
            con,
            """
            SELECT
                dt.year_month,
                dt.month_name,
                COUNT(*) AS total_events,
                SUM(CASE WHEN f.event_type = 'save' THEN 1 ELSE 0 END) AS saves,
                SUM(CASE WHEN f.event_type = 'view' THEN 1 ELSE 0 END) AS views,
                SUM(CASE WHEN f.event_type = 'search' THEN 1 ELSE 0 END) AS searches,
                SUM(CASE WHEN f.event_type IN ('post', 'comment') THEN 1 ELSE 0 END) AS discussions
            FROM fact_research_activity f
            JOIN dim_date dt ON f.date_key = dt.date_key
            WHERE f.activity_id > 0
            GROUP BY dt.year_month, dt.month_name
            ORDER BY dt.year_month ASC
            """,
        )

        topics_by_dept = _query_dicts(
            con,
            """
            SELECT
                d.department_code,
                t.topic_name,
                COUNT(*) AS activity_count
            FROM fact_research_activity f
            JOIN dim_department d ON f.department_key = d.department_key
            JOIN dim_topic t ON f.topic_key = t.topic_key
            WHERE t.topic_name <> 'general' AND d.department_key > 0
            GROUP BY d.department_code, t.topic_name
            ORDER BY activity_count DESC
            LIMIT 40
            """,
        )

        most_saved_papers = _query_dicts(
            con,
            """
            SELECT
                p.paper_key AS id,
                p.title,
                p.primary_source,
                p.publication_year,
                p.citation_count,
                ROUND(p.pagerank_score, 6) AS pagerank_score,
                COUNT(fs.save_id) AS save_count,
                COUNT(DISTINCT fs.department_key) AS dept_reach
            FROM fact_paper_saves fs
            JOIN dim_paper p ON fs.paper_key = p.paper_key
            WHERE fs.save_id > 0
            GROUP BY p.paper_key, p.title, p.primary_source, p.publication_year, p.citation_count, p.pagerank_score
            ORDER BY save_count DESC, p.citation_count DESC
            LIMIT 12
            """,
        )

        most_discussed_papers = _query_dicts(
            con,
            """
            SELECT
                pe.post_key AS post_id,
                pe.post_title,
                m.full_name AS author_name,
                d.department_code,
                pe.upvote_count,
                pe.comment_count,
                (pe.upvote_count * 2 + pe.comment_count * 3) AS engagement_score,
                p.paper_key AS paper_id,
                p.title AS paper_title
            FROM fact_post_engagement pe
            JOIN dim_member m ON pe.member_key = m.member_key
            JOIN dim_department d ON pe.department_key = d.department_key
            LEFT JOIN dim_paper p ON pe.paper_key = p.paper_key AND pe.paper_key > 0
            WHERE pe.post_key > 0
            ORDER BY engagement_score DESC
            LIMIT 12
            """,
        )

        cross_dept_collab = _query_dicts(
            con,
            """
            SELECT
                d1.department_code AS dept_a,
                d2.department_code AS dept_b,
                COUNT(DISTINCT s1.paper_key) AS shared_papers
            FROM fact_paper_saves s1
            JOIN fact_paper_saves s2
              ON s1.paper_key = s2.paper_key
             AND s1.department_key < s2.department_key
            JOIN dim_department d1 ON s1.department_key = d1.department_key
            JOIN dim_department d2 ON s2.department_key = d2.department_key
            WHERE s1.save_id > 0 AND s2.save_id > 0
            GROUP BY d1.department_code, d2.department_code
            ORDER BY shared_papers DESC
            """,
        )

        top_members = _query_dicts(
            con,
            """
            SELECT
                m.member_key AS id,
                m.full_name,
                m.role,
                d.department_code,
                COUNT(f.activity_id) AS total_actions,
                SUM(CASE WHEN f.event_type = 'save' THEN 1 ELSE 0 END) AS saves,
                SUM(CASE WHEN f.event_type = 'post' THEN 1 ELSE 0 END) AS posts,
                SUM(CASE WHEN f.event_type = 'comment' THEN 1 ELSE 0 END) AS comments,
                SUM(CASE WHEN f.event_type = 'search' THEN 1 ELSE 0 END) AS searches
            FROM dim_member m
            JOIN dim_department d ON m.department_key = d.department_key
            LEFT JOIN fact_research_activity f ON f.member_key = m.member_key
            WHERE m.member_key > 0 AND m.is_flagged_spam = FALSE
            GROUP BY m.member_key, m.full_name, m.role, d.department_code
            ORDER BY total_actions DESC
            LIMIT 15
            """,
        )

        topic_clusters = _compute_topic_clusters(con)

        return {
            "kpis": kpis,
            "department_comparison": dept_comparison,
            "monthly_trends": monthly_trends,
            "topics_by_department": topics_by_dept,
            "most_saved_papers": most_saved_papers,
            "most_discussed_papers": most_discussed_papers,
            "cross_department_collaboration": cross_dept_collab,
            "top_members": top_members,
            "topic_clusters": topic_clusters,
        }
    finally:
        con.close()


def _compute_topic_clusters(con: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
    """Hierarchical clustering (AgglomerativeClustering) of research topics by co-activity across departments."""
    rows = _query_dicts(
        con,
        """
        SELECT
            t.topic_name,
            STRING_AGG(d.department_code, ' ') AS dept_profile,
            COUNT(*) AS total_activity
        FROM fact_research_activity f
        JOIN dim_topic t ON f.topic_key = t.topic_key
        JOIN dim_department d ON f.department_key = d.department_key
        WHERE t.topic_name <> 'general' AND d.department_key > 0
        GROUP BY t.topic_name
        HAVING COUNT(*) >= 5
        ORDER BY total_activity DESC
        LIMIT 30
        """,
    )
    if len(rows) < 4:
        return []

    corpus = [f"{r['topic_name']} {r['dept_profile']}" for r in rows]
    vec = TfidfVectorizer(ngram_range=(1, 2))
    X = vec.fit_transform(corpus).toarray()
    n_clusters = min(5, max(2, len(rows) // 5))
    model = AgglomerativeClustering(n_clusters=n_clusters, linkage="ward")
    labels = model.fit_predict(X)

    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for row, lbl in zip(rows, labels):
        grouped.setdefault(int(lbl), []).append(
            {"topic": row["topic_name"], "activity": int(row["total_activity"])}
        )

    clusters = []
    for cid, items in sorted(grouped.items()):
        items.sort(key=lambda x: x["activity"], reverse=True)
        clusters.append(
            {
                "cluster_id": cid + 1,
                "label": f"Cluster {cid + 1}: {items[0]['topic'].title()}",
                "total_activity": sum(i["activity"] for i in items),
                "topics": items,
            }
        )
    clusters.sort(key=lambda c: c["total_activity"], reverse=True)
    return clusters


def drilldown_analytics(
    department_code: Optional[str] = None,
    topic_name: Optional[str] = None,
    member_id: Optional[int] = None,
) -> Dict[str, Any]:
    """4-level OLAP drill-down: University -> Department -> Topic -> Member."""
    con = _connect_dw()
    try:
        if member_id is not None:
            member_info = _query_dicts(
                con,
                """
                SELECT m.member_key AS id, m.full_name, m.username, m.role, d.department_code, d.department_name
                FROM dim_member m
                LEFT JOIN dim_department d ON m.department_key = d.department_key
                WHERE m.member_key = ?
                """,
                [member_id],
            )
            timeline = _query_dicts(
                con,
                """
                SELECT dt.year_month, COUNT(*) AS events,
                       SUM(CASE WHEN f.event_type='save' THEN 1 ELSE 0 END) AS saves,
                       SUM(CASE WHEN f.event_type='search' THEN 1 ELSE 0 END) AS searches,
                       SUM(CASE WHEN f.event_type IN ('post','comment') THEN 1 ELSE 0 END) AS discussions
                FROM fact_research_activity f
                JOIN dim_date dt ON f.date_key = dt.date_key
                WHERE f.member_key = ?
                GROUP BY dt.year_month
                ORDER BY dt.year_month
                """,
                [member_id],
            )
            topics = _query_dicts(
                con,
                """
                SELECT t.topic_name, COUNT(*) AS events
                FROM fact_research_activity f
                JOIN dim_topic t ON f.topic_key = t.topic_key
                WHERE f.member_key = ? AND t.topic_name <> 'general'
                GROUP BY t.topic_name
                ORDER BY events DESC
                LIMIT 10
                """,
                [member_id],
            )
            saved = _query_dicts(
                con,
                """
                SELECT p.paper_key AS id, p.title, p.publication_year, p.primary_source, p.save_count
                FROM fact_paper_saves fs
                JOIN dim_paper p ON fs.paper_key = p.paper_key
                WHERE fs.member_key = ?
                ORDER BY fs.date_key DESC
                LIMIT 15
                """,
                [member_id],
            )
            return {
                "level": "member",
                "member": member_info[0] if member_info else None,
                "monthly_timeline": timeline,
                "top_topics": topics,
                "saved_papers": saved,
            }

        if department_code and topic_name:
            members = _query_dicts(
                con,
                """
                SELECT m.member_key AS id, m.full_name, m.role, COUNT(*) AS events,
                       SUM(CASE WHEN f.event_type='save' THEN 1 ELSE 0 END) AS saves,
                       SUM(CASE WHEN f.event_type IN ('post','comment') THEN 1 ELSE 0 END) AS discussions
                FROM fact_research_activity f
                JOIN dim_department d ON f.department_key = d.department_key
                JOIN dim_topic t ON f.topic_key = t.topic_key
                JOIN dim_member m ON f.member_key = m.member_key
                WHERE d.department_code = ? AND t.topic_name = ? AND m.member_key > 0
                GROUP BY m.member_key, m.full_name, m.role
                ORDER BY events DESC
                """,
                [department_code, topic_name.lower()],
            )
            timeline = _query_dicts(
                con,
                """
                SELECT dt.year_month, COUNT(*) AS events
                FROM fact_research_activity f
                JOIN dim_department d ON f.department_key = d.department_key
                JOIN dim_topic t ON f.topic_key = t.topic_key
                JOIN dim_date dt ON f.date_key = dt.date_key
                WHERE d.department_code = ? AND t.topic_name = ?
                GROUP BY dt.year_month
                ORDER BY dt.year_month
                """,
                [department_code, topic_name.lower()],
            )
            return {
                "level": "topic",
                "department_code": department_code,
                "topic_name": topic_name.lower(),
                "members": members,
                "monthly_timeline": timeline,
            }

        if department_code:
            topics = _query_dicts(
                con,
                """
                SELECT t.topic_name, COUNT(*) AS events,
                       COUNT(DISTINCT f.member_key) AS active_members,
                       SUM(CASE WHEN f.event_type='save' THEN 1 ELSE 0 END) AS saves
                FROM fact_research_activity f
                JOIN dim_department d ON f.department_key = d.department_key
                JOIN dim_topic t ON f.topic_key = t.topic_key
                LEFT JOIN dim_member m ON f.member_key = m.member_key
                WHERE d.department_code = ? AND t.topic_name NOT IN ('general', 'promo') AND COALESCE(m.is_flagged_spam, FALSE) = FALSE
                GROUP BY t.topic_name
                ORDER BY events DESC
                LIMIT 20
                """,
                [department_code],
            )
            timeline = _query_dicts(
                con,
                """
                SELECT dt.year_month, COUNT(*) AS events,
                       SUM(CASE WHEN f.event_type='save' THEN 1 ELSE 0 END) AS saves,
                       SUM(CASE WHEN f.event_type='search' THEN 1 ELSE 0 END) AS searches
                FROM fact_research_activity f
                JOIN dim_department d ON f.department_key = d.department_key
                JOIN dim_date dt ON f.date_key = dt.date_key
                WHERE d.department_code = ?
                GROUP BY dt.year_month
                ORDER BY dt.year_month
                """,
                [department_code],
            )
            return {
                "level": "department",
                "department_code": department_code,
                "topics": topics,
                "monthly_timeline": timeline,
            }

        departments = _query_dicts(
            con,
            """
            SELECT d.department_code, d.department_name, COUNT(f.activity_id) AS events,
                   COUNT(DISTINCT f.member_key) AS active_members
            FROM dim_department d
            LEFT JOIN fact_research_activity f ON f.department_key = d.department_key
            WHERE d.department_key > 0
            GROUP BY d.department_code, d.department_name
            ORDER BY events DESC
            """,
        )
        return {"level": "university", "departments": departments}
    finally:
        con.close()
