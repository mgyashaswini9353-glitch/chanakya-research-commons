"""F2: Posts, Discussions, Comments, Nested Replies, Upvotes, and Personalized Feeds API."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, get_current_user_optional
from backend.app.models.models import (
    ActivityEvent,
    Comment,
    Department,
    Paper,
    Post,
    PostUpvote,
    SavedPost,
    TopicFollow,
    User,
    UserFollow,
)
from backend.app.schemas.schemas import (
    CommentCreateRequest,
    PostCreateRequest,
    PostUpdateRequest,
)

router = APIRouter(prefix="/api/posts", tags=["F2: Posts & Discussions"])


def _serialize_post(
    db: Session,
    post: Post,
    viewer_id: Optional[int] = None,
    include_comments: bool = False,
) -> dict:
    author = db.query(User).filter(User.id == post.author_id).first()
    dept = db.query(Department).filter(Department.id == author.department_id).first() if author and author.department_id else None
    attached_paper = None
    if post.attached_paper_id:
        p = db.query(Paper).filter(Paper.id == post.attached_paper_id).first()
        if p:
            attached_paper = {
                "id": p.id,
                "title": p.title,
                "authors": (p.authors or [])[:3],
                "publication_year": p.publication_year,
                "venue": p.venue,
                "save_count": p.save_count,
            }
    upvoted = False
    saved_post = False
    if viewer_id is not None:
        upvoted = (
            db.query(PostUpvote)
            .filter(PostUpvote.user_id == viewer_id, PostUpvote.post_id == post.id)
            .first()
            is not None
        )
        saved_post = (
            db.query(SavedPost)
            .filter(SavedPost.user_id == viewer_id, SavedPost.post_id == post.id)
            .first()
            is not None
        )

    out = {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "tags": post.tags or [],
        "attached_paper_id": post.attached_paper_id,
        "attached_paper": attached_paper,
        "attached_url": post.attached_url or "",
        "upvote_count": post.upvote_count,
        "comment_count": post.comment_count,
        "has_upvoted": upvoted,
        "is_saved_by_me": saved_post,
        "is_synthetic": bool(post.is_synthetic),
        "author": {
            "id": author.id if author else None,
            "full_name": author.full_name if author else "Unknown",
            "username": author.username if author else "unknown",
            "role": author.role if author else "student",
            "department_code": dept.code if dept else None,
            "is_flagged_spam": author.is_flagged_spam if author else False,
        },
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }

    if include_comments:
        comments = (
            db.query(Comment)
            .filter(Comment.post_id == post.id)
            .order_by(Comment.created_at.asc())
            .all()
        )
        u_map = {u.id: u for u in db.query(User).filter(User.id.in_([c.author_id for c in comments])).all()} if comments else {}
        d_map = {d.id: d.code for d in db.query(Department).all()}
        serialized_comments = []
        for c in comments:
            ca = u_map.get(c.author_id)
            serialized_comments.append(
                {
                    "id": c.id,
                    "post_id": c.post_id,
                    "parent_comment_id": c.parent_comment_id,
                    "content": c.content,
                    "author_id": c.author_id,
                    "author_name": ca.full_name if ca else "Unknown",
                    "author_role": ca.role if ca else "student",
                    "department_code": d_map.get(ca.department_id) if ca else None,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
            )
        out["comments"] = serialized_comments
    return out


@router.get("")
def list_posts(
    feed: str = Query(default="all", pattern="^(all|personalized|following|topics|saved)$"),
    tag: Optional[str] = None,
    author_id: Optional[int] = None,
    paper_id: Optional[int] = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    viewer: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    # Exclude flagged spam accounts from normal feeds unless author_id explicitly requested
    spam_ids = {u.id for u in db.query(User).filter(User.is_flagged_spam == True).all()}
    q = db.query(Post)
    if author_id:
        q = q.filter(Post.author_id == author_id)
    elif spam_ids:
        q = q.filter(~Post.author_id.in_(spam_ids))
    if paper_id:
        q = q.filter(Post.attached_paper_id == paper_id)

    posts = q.order_by(Post.created_at.desc()).all()

    if tag:
        tl = tag.strip().lower()
        posts = [p for p in posts if any(tl == str(t).lower() or tl in str(t).lower() for t in (p.tags or []))]

    if feed == "saved":
        if not viewer:
            posts = []
        else:
            saved_ids = {sp.post_id for sp in db.query(SavedPost).filter(SavedPost.user_id == viewer.id).all()}
            posts = [p for p in posts if p.id in saved_ids]

    if viewer and feed in ("following", "topics", "personalized"):
        followed_ids = {
            f.following_id for f in db.query(UserFollow).filter(UserFollow.follower_id == viewer.id).all()
        }
        followed_topics = {
            tf.topic.lower() for tf in db.query(TopicFollow).filter(TopicFollow.user_id == viewer.id).all()
        } | {str(t).lower() for t in (viewer.research_tags or [])}

        if feed == "following":
            posts = [p for p in posts if p.author_id in followed_ids or p.author_id == viewer.id]
        elif feed == "topics":
            posts = [
                p for p in posts if len({str(t).lower() for t in (p.tags or [])} & followed_topics) > 0
            ]
        elif feed == "personalized":
            # Score by followed author + followed topics + engagement + recency
            scored = []
            for idx, p in enumerate(posts):
                p_tags = {str(t).lower() for t in (p.tags or [])}
                score = 0.0
                if p.author_id in followed_ids:
                    score += 4.0
                score += 2.5 * len(p_tags & followed_topics)
                score += 0.35 * (p.upvote_count or 0) + 0.25 * (p.comment_count or 0)
                score += max(0.0, 3.0 - idx * 0.02)
                scored.append((score, p))
            scored.sort(key=lambda x: x[0], reverse=True)
            posts = [p for _s, p in scored]

    total = len(posts)
    page = posts[offset : offset + limit]
    vid = viewer.id if viewer else None
    return {
        "total": total,
        "feed": feed,
        "items": [_serialize_post(db, p, viewer_id=vid, include_comments=False) for p in page],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tags = sorted(set(t.strip().lower().lstrip("#") for t in payload.tags if t.strip()))
    if payload.attached_paper_id:
        paper = db.query(Paper).filter(Paper.id == payload.attached_paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Attached paper not found")

    post = Post(
        author_id=current_user.id,
        title=payload.title.strip(),
        content=payload.content.strip(),
        tags=tags,
        attached_paper_id=payload.attached_paper_id,
        attached_url=payload.attached_url.strip(),
        is_synthetic=False,
    )
    db.add(post)
    db.flush()
    db.add(
        ActivityEvent(
            user_id=current_user.id,
            event_type="post",
            post_id=post.id,
            paper_id=payload.attached_paper_id,
            topic=tags[0] if tags else "general",
            department_id=current_user.department_id,
        )
    )
    db.commit()
    db.refresh(post)
    return _serialize_post(db, post, viewer_id=current_user.id, include_comments=True)


@router.get("/{post_id}")
def get_post(
    post_id: int,
    viewer: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return _serialize_post(db, post, viewer_id=(viewer.id if viewer else None), include_comments=True)


@router.patch("/{post_id}")
def update_post(
    post_id: int,
    payload: PostUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to edit this post")

    if payload.title is not None:
        post.title = payload.title.strip()
    if payload.content is not None:
        post.content = payload.content.strip()
    if payload.tags is not None:
        post.tags = sorted(set(t.strip().lower().lstrip("#") for t in payload.tags if t.strip()))
    if payload.attached_paper_id is not None:
        post.attached_paper_id = payload.attached_paper_id
    if payload.attached_url is not None:
        post.attached_url = payload.attached_url.strip()
    db.commit()
    db.refresh(post)
    return _serialize_post(db, post, viewer_id=current_user.id, include_comments=True)


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    db.delete(post)
    db.commit()
    return {"deleted": True, "post_id": post_id}


@router.post("/{post_id}/comments", status_code=status.HTTP_201_CREATED)
def add_comment(
    post_id: int,
    payload: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if payload.parent_comment_id:
        parent = db.query(Comment).filter(Comment.id == payload.parent_comment_id, Comment.post_id == post_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found")

    comment = Comment(
        post_id=post_id,
        author_id=current_user.id,
        parent_comment_id=payload.parent_comment_id,
        content=payload.content.strip(),
        is_synthetic=False,
    )
    db.add(comment)
    post.comment_count = (post.comment_count or 0) + 1
    db.add(
        ActivityEvent(
            user_id=current_user.id,
            event_type="comment",
            post_id=post_id,
            topic=(post.tags[0] if post.tags else "general"),
            department_id=current_user.department_id,
        )
    )
    db.commit()
    db.refresh(comment)
    dept = db.query(Department).filter(Department.id == current_user.department_id).first() if current_user.department_id else None
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "parent_comment_id": comment.parent_comment_id,
        "content": comment.content,
        "author_id": current_user.id,
        "author_name": current_user.full_name,
        "author_role": current_user.role,
        "department_code": dept.code if dept else None,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


@router.post("/{post_id}/upvote")
def toggle_upvote(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = (
        db.query(PostUpvote)
        .filter(PostUpvote.user_id == current_user.id, PostUpvote.post_id == post_id)
        .first()
    )
    if existing:
        db.delete(existing)
        post.upvote_count = max(0, (post.upvote_count or 0) - 1)
        upvoted = False
    else:
        db.add(PostUpvote(user_id=current_user.id, post_id=post_id))
        post.upvote_count = (post.upvote_count or 0) + 1
        db.add(
            ActivityEvent(
                user_id=current_user.id,
                event_type="upvote",
                post_id=post_id,
                topic=(post.tags[0] if post.tags else "general"),
                department_id=current_user.department_id,
            )
        )
        upvoted = True
    db.commit()
    return {"post_id": post_id, "upvoted": upvoted, "upvote_count": post.upvote_count}


@router.post("/{post_id}/save")
def toggle_save_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = (
        db.query(SavedPost)
        .filter(SavedPost.user_id == current_user.id, SavedPost.post_id == post_id)
        .first()
    )
    if existing:
        db.delete(existing)
        saved = False
    else:
        db.add(SavedPost(user_id=current_user.id, post_id=post_id))
        saved = True
    db.commit()
    return {"post_id": post_id, "saved": saved}
