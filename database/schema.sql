-- ==============================================================================
-- Chanakya Research Commons - Operational PostgreSQL Schema (with pgvector)
-- Supports F1-F9 subsystems with full-text search (tsvector) and semantic search
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. Departments
CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    code VARCHAR(16) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL UNIQUE,
    faculty_head VARCHAR(150),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Users (F1)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('student', 'faculty', 'researcher', 'admin')),
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    bio TEXT DEFAULT '',
    research_interests_text TEXT DEFAULT '',
    research_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    publication_links JSONB NOT NULL DEFAULT '[]'::jsonb,
    personal_website VARCHAR(500) DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_flagged_spam BOOLEAN NOT NULL DEFAULT FALSE,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_department ON users(department_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_fts ON users USING GIN (
    to_tsvector('english', coalesce(full_name,'') || ' ' || coalesce(bio,'') || ' ' || coalesce(research_interests_text,''))
);

-- 3. Follow Relationships (F1)
CREATE TABLE IF NOT EXISTS user_follows (
    follower_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (follower_id, following_id),
    CHECK (follower_id <> following_id)
);
CREATE INDEX IF NOT EXISTS idx_user_follows_following ON user_follows(following_id);

CREATE TABLE IF NOT EXISTS topic_follows (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, topic)
);
CREATE INDEX IF NOT EXISTS idx_topic_follows_topic ON topic_follows(topic);

-- 4. Papers & Articles (F3, F4, F5, F8)
CREATE TABLE IF NOT EXISTS papers (
    id SERIAL PRIMARY KEY,
    canonical_key VARCHAR(128) NOT NULL UNIQUE,
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    abstract TEXT DEFAULT '',
    authors JSONB NOT NULL DEFAULT '[]'::jsonb,
    normalized_authors JSONB NOT NULL DEFAULT '[]'::jsonb,
    publication_year INTEGER,
    published_date VARCHAR(32),
    venue VARCHAR(255) DEFAULT '',
    doi VARCHAR(255),
    arxiv_id VARCHAR(64),
    url VARCHAR(1000) DEFAULT '',
    pdf_url VARCHAR(1000) DEFAULT '',
    topics JSONB NOT NULL DEFAULT '[]'::jsonb,
    department_hint VARCHAR(32),
    sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    primary_source VARCHAR(40) NOT NULL DEFAULT 'openalex',
    citation_count INTEGER NOT NULL DEFAULT 0,
    pagerank_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    save_count INTEGER NOT NULL DEFAULT 0,
    in_university_library BOOLEAN NOT NULL DEFAULT FALSE,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    embedding JSONB,
    embedding_vec vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_arxiv_id ON papers(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_papers_norm_title ON papers(normalized_title);
CREATE INDEX IF NOT EXISTS idx_papers_in_library ON papers(in_university_library);
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(publication_year);
CREATE INDEX IF NOT EXISTS idx_papers_fts ON papers USING GIN (
    to_tsvector('english', coalesce(title,'') || ' ' || coalesce(abstract,'') || ' ' || coalesce(venue,''))
);
CREATE INDEX IF NOT EXISTS idx_papers_embedding_hnsw ON papers USING hnsw (embedding_vec vector_cosine_ops);

-- 5. Citation Graph Edges (F5 PageRank)
CREATE TABLE IF NOT EXISTS paper_citations (
    citing_paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    cited_paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (citing_paper_id, cited_paper_id),
    CHECK (citing_paper_id <> cited_paper_id)
);

-- 6. Personal Collections & Saved Library Items (F3)
CREATE TABLE IF NOT EXISTS collections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    description TEXT DEFAULT '',
    is_private BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_collections_user ON collections(user_id);

CREATE TABLE IF NOT EXISTS saved_papers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    collection_id INTEGER REFERENCES collections(id) ON DELETE SET NULL,
    private_notes TEXT DEFAULT '',
    saved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, paper_id)
);
CREATE INDEX IF NOT EXISTS idx_saved_papers_paper ON saved_papers(paper_id);
CREATE INDEX IF NOT EXISTS idx_saved_papers_user ON saved_papers(user_id);

-- 7. Posts, Comments & Upvotes (F2)
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(300) NOT NULL,
    content TEXT NOT NULL,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    attached_paper_id INTEGER REFERENCES papers(id) ON DELETE SET NULL,
    attached_url VARCHAR(1000) DEFAULT '',
    upvote_count INTEGER NOT NULL DEFAULT 0,
    comment_count INTEGER NOT NULL DEFAULT 0,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_fts ON posts USING GIN (
    to_tsvector('english', coalesce(title,'') || ' ' || coalesce(content,''))
);

CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_comment_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comments_author ON comments(author_id);

CREATE TABLE IF NOT EXISTS post_upvotes (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, post_id)
);

CREATE TABLE IF NOT EXISTS saved_posts (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    saved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, post_id)
);

-- 8. Activity Events Telemetry (F5, F6, F7, F9)
CREATE TABLE IF NOT EXISTS activity_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(32) NOT NULL CHECK (event_type IN ('view', 'save', 'search', 'upvote', 'post', 'comment', 'follow')),
    paper_id INTEGER REFERENCES papers(id) ON DELETE SET NULL,
    post_id INTEGER REFERENCES posts(id) ON DELETE SET NULL,
    query_text TEXT,
    topic VARCHAR(120),
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_type ON activity_events(event_type);
CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_events(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_topic ON activity_events(topic);

-- 9. External Ingestion Job Logs (F4)
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    query_params JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(24) NOT NULL DEFAULT 'running',
    records_fetched INTEGER NOT NULL DEFAULT 0,
    records_inserted INTEGER NOT NULL DEFAULT 0,
    records_merged INTEGER NOT NULL DEFAULT 0,
    raw_file_path VARCHAR(500) DEFAULT '',
    error_message TEXT DEFAULT '',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 10. Trends & Monitoring Alerts (F7)
CREATE TABLE IF NOT EXISTS monitoring_alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(32) NOT NULL CHECK (alert_type IN ('topic_spike', 'spam_account', 'abnormal_activity')),
    severity VARCHAR(16) NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    entity_type VARCHAR(32) NOT NULL,
    entity_id VARCHAR(120) NOT NULL,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(24) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'reviewed', 'dismissed', 'action_taken')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON monitoring_alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON monitoring_alerts(alert_type);
