-- ==============================================================================
-- Chanakya Research Commons - OLAP Analytical SQL Queries (DuckDB Star Schema)
-- ==============================================================================

-- Q1: Department-wise research activity breakdown
-- Roll-up from fact_research_activity joined with dim_department
SELECT
    d.department_code,
    d.department_name,
    COUNT(*) AS total_events,
    SUM(CASE WHEN f.event_type = 'save' THEN 1 ELSE 0 END) AS paper_saves,
    SUM(CASE WHEN f.event_type = 'view' THEN 1 ELSE 0 END) AS paper_views,
    SUM(CASE WHEN f.event_type = 'search' THEN 1 ELSE 0 END) AS search_queries,
    SUM(CASE WHEN f.event_type = 'post' THEN 1 ELSE 0 END) AS posts_created,
    SUM(CASE WHEN f.event_type = 'comment' THEN 1 ELSE 0 END) AS comments_made,
    COUNT(DISTINCT f.member_key) AS active_members
FROM fact_research_activity f
JOIN dim_department d ON f.department_key = d.department_key
GROUP BY d.department_code, d.department_name
ORDER BY total_events DESC;

-- Q2: Monthly activity trends across the university
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
GROUP BY dt.year_month, dt.month_name
ORDER BY dt.year_month ASC;

-- Q3: Research topics by department over time
SELECT
    dt.year_month,
    d.department_code,
    t.topic_name,
    COUNT(*) AS activity_count
FROM fact_research_activity f
JOIN dim_date dt ON f.date_key = dt.date_key
JOIN dim_department d ON f.department_key = d.department_key
JOIN dim_topic t ON f.topic_key = t.topic_key
WHERE t.topic_name IS NOT NULL AND t.topic_name <> 'general'
GROUP BY dt.year_month, d.department_code, t.topic_name
ORDER BY dt.year_month ASC, activity_count DESC;

-- Q4: Most saved research papers in the Chanakya University Library
SELECT
    p.paper_key,
    p.title,
    p.primary_source,
    p.publication_year,
    p.citation_count,
    p.pagerank_score,
    COUNT(fs.save_id) AS warehouse_save_count,
    COUNT(DISTINCT fs.department_key) AS departments_saving
FROM fact_paper_saves fs
JOIN dim_paper p ON fs.paper_key = p.paper_key
GROUP BY p.paper_key, p.title, p.primary_source, p.publication_year, p.citation_count, p.pagerank_score
ORDER BY warehouse_save_count DESC, p.citation_count DESC
LIMIT 20;

-- Q5: Most discussed papers & posts engagement
SELECT
    pe.post_key,
    pe.post_title,
    m.full_name AS author_name,
    d.department_code,
    pe.upvote_count,
    pe.comment_count,
    (pe.upvote_count * 2 + pe.comment_count * 3) AS engagement_score,
    p.title AS attached_paper_title
FROM fact_post_engagement pe
JOIN dim_member m ON pe.member_key = m.member_key
JOIN dim_department d ON pe.department_key = d.department_key
LEFT JOIN dim_paper p ON pe.paper_key = p.paper_key
ORDER BY engagement_score DESC
LIMIT 20;

-- Q6: Cross-department collaboration (co-saved papers across pairs of departments)
SELECT
    d1.department_code AS dept_a,
    d2.department_code AS dept_b,
    COUNT(DISTINCT s1.paper_key) AS shared_papers_count
FROM fact_paper_saves s1
JOIN fact_paper_saves s2
  ON s1.paper_key = s2.paper_key
 AND s1.department_key < s2.department_key
JOIN dim_department d1 ON s1.department_key = d1.department_key
JOIN dim_department d2 ON s2.department_key = d2.department_key
GROUP BY d1.department_code, d2.department_code
ORDER BY shared_papers_count DESC;

-- Q7: Member engagement leaderboard (drill-down level: Member)
SELECT
    m.member_key,
    m.full_name,
    m.role,
    d.department_code,
    COUNT(*) AS total_actions,
    SUM(CASE WHEN f.event_type = 'save' THEN 1 ELSE 0 END) AS saves,
    SUM(CASE WHEN f.event_type = 'post' THEN 1 ELSE 0 END) AS posts,
    SUM(CASE WHEN f.event_type = 'comment' THEN 1 ELSE 0 END) AS comments,
    SUM(CASE WHEN f.event_type = 'search' THEN 1 ELSE 0 END) AS searches
FROM fact_research_activity f
JOIN dim_member m ON f.member_key = m.member_key
JOIN dim_department d ON m.department_key = d.department_key
GROUP BY m.member_key, m.full_name, m.role, d.department_code
ORDER BY total_actions DESC
LIMIT 25;
