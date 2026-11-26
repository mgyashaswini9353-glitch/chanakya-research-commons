"""SQLAlchemy ORM models for Chanakya Research Commons (F1-F9)."""
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(16), unique=True, nullable=False, index=True)
    name = Column(String(150), unique=True, nullable=False)
    faculty_head = Column(String(150), default="")
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    members = relationship("User", back_populates="department")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(20), nullable=False, default="student", index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    bio = Column(Text, default="")
    research_interests_text = Column(Text, default="")
    research_tags = Column(JSON, default=list, nullable=False)
    publication_links = Column(JSON, default=list, nullable=False)
    personal_website = Column(String(500), default="")
    is_active = Column(Boolean, default=True, nullable=False)
    is_flagged_spam = Column(Boolean, default=False, nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    department = relationship("Department", back_populates="members")
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan")
    saved_papers = relationship("SavedPaper", back_populates="user", cascade="all, delete-orphan")


class UserFollow(Base):
    __tablename__ = "user_follows"

    follower_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    following_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class TopicFollow(Base):
    __tablename__ = "topic_follows"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    topic = Column(String(120), primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    canonical_key = Column(String(128), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    normalized_title = Column(Text, nullable=False, index=True)
    abstract = Column(Text, default="")
    authors = Column(JSON, default=list, nullable=False)
    normalized_authors = Column(JSON, default=list, nullable=False)
    publication_year = Column(Integer, nullable=True, index=True)
    published_date = Column(String(32), default="")
    venue = Column(String(255), default="")
    doi = Column(String(255), nullable=True, index=True)
    arxiv_id = Column(String(64), nullable=True, index=True)
    url = Column(String(1000), default="")
    pdf_url = Column(String(1000), default="")
    topics = Column(JSON, default=list, nullable=False)
    department_hint = Column(String(32), nullable=True, index=True)
    sources = Column(JSON, default=list, nullable=False)
    primary_source = Column(String(40), default="openalex", nullable=False, index=True)
    citation_count = Column(Integer, default=0, nullable=False)
    pagerank_score = Column(Float, default=0.0, nullable=False)
    save_count = Column(Integer, default=0, nullable=False, index=True)
    in_university_library = Column(Boolean, default=False, nullable=False, index=True)
    is_synthetic = Column(Boolean, default=False, nullable=False, index=True)
    embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    saves = relationship("SavedPaper", back_populates="paper", cascade="all, delete-orphan")


class PaperCitation(Base):
    __tablename__ = "paper_citations"

    citing_paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    cited_paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, default="")
    is_private = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="collections")
    items = relationship("SavedPaper", back_populates="collection")


class SavedPaper(Base):
    __tablename__ = "saved_papers"
    __table_args__ = (UniqueConstraint("user_id", "paper_id", name="uq_user_paper_save"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="SET NULL"), nullable=True, index=True)
    private_notes = Column(Text, default="")
    saved_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="saved_papers")
    paper = relationship("Paper", back_populates="saves")
    collection = relationship("Collection", back_populates="items")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    attached_paper_id = Column(Integer, ForeignKey("papers.id", ondelete="SET NULL"), nullable=True)
    attached_url = Column(String(1000), default="")
    upvote_count = Column(Integer, default=0, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    author = relationship("User", back_populates="posts")
    attached_paper = relationship("Paper")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")


class PostUpvote(Base):
    __tablename__ = "post_upvotes"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class SavedPost(Base):
    __tablename__ = "saved_posts"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    saved_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(32), nullable=False, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="SET NULL"), nullable=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="SET NULL"), nullable=True)
    query_text = Column(Text, nullable=True)
    topic = Column(String(120), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("idx_activity_type_created", "event_type", "created_at"),
    )


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False, index=True)
    query_params = Column(JSON, default=dict, nullable=False)
    status = Column(String(24), default="running", nullable=False)
    records_fetched = Column(Integer, default=0, nullable=False)
    records_inserted = Column(Integer, default=0, nullable=False)
    records_merged = Column(Integer, default=0, nullable=False)
    raw_file_path = Column(String(500), default="")
    error_message = Column(Text, default="")
    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class MonitoringAlert(Base):
    __tablename__ = "monitoring_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(32), nullable=False, index=True)
    severity = Column(String(16), nullable=False, default="medium")
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    entity_type = Column(String(32), nullable=False)
    entity_id = Column(String(120), nullable=False)
    metrics_json = Column(JSON, default=dict, nullable=False)
    status = Column(String(24), default="open", nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
