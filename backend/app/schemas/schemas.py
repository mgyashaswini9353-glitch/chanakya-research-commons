"""Pydantic v2 request and response schemas for Chanakya Research Commons."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=60)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=140)
    role: str = Field(default="student", pattern="^(student|faculty|researcher)$")
    department_id: Optional[int] = None
    research_interests_text: str = ""
    research_tags: List[str] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    role: str = Field(..., pattern="^(student|faculty|researcher|admin)$")


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    department_id: Optional[int] = None
    bio: Optional[str] = None
    research_interests_text: Optional[str] = None
    research_tags: Optional[List[str]] = None
    publication_links: Optional[List[str]] = None
    personal_website: Optional[str] = None


class TopicFollowRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=100)


class PostCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    content: str = Field(..., min_length=5)
    tags: List[str] = Field(default_factory=list)
    attached_paper_id: Optional[int] = None
    attached_url: str = ""


class PostUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=300)
    content: Optional[str] = Field(default=None, min_length=5)
    tags: Optional[List[str]] = None
    attached_paper_id: Optional[int] = None
    attached_url: Optional[str] = None


class CommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    parent_comment_id: Optional[int] = None


class SavePaperRequest(BaseModel):
    paper_id: int
    collection_id: Optional[int] = None
    private_notes: str = ""


class UpdateSavedPaperRequest(BaseModel):
    collection_id: Optional[int] = None
    private_notes: Optional[str] = None


class AddPaperByIdentifierRequest(BaseModel):
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    collection_id: Optional[int] = None
    private_notes: str = ""


class CollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=140)
    description: str = ""
    is_private: bool = True


class CollectionUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=140)
    description: Optional[str] = None
    is_private: Optional[bool] = None


class AssistantAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)
    only_library: bool = False


class AlertStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(open|reviewed|dismissed|action_taken)$")


class IngestionTriggerRequest(BaseModel):
    source: str = Field(default="all", pattern="^(openalex|arxiv|rss|all)$")
    per_query: int = Field(default=10, ge=3, le=30)
