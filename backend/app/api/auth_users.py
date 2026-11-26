"""F1: User Accounts, Authentication, RBAC, Profiles, and Following API."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.rate_limit import rate_limit_dependency
from backend.app.core.security import (
    create_access_token,
    get_current_user,
    get_current_user_optional,
    hash_password,
    verify_password,
)
from backend.app.models.models import (
    ActivityEvent,
    Department,
    Post,
    SavedPaper,
    TopicFollow,
    User,
    UserFollow,
)
from backend.app.schemas.schemas import (
    LoginRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    TopicFollowRequest,
)

router = APIRouter(tags=["F1: Accounts & Profiles"])


def serialize_user(
    db: Session,
    u: User,
    viewer_id: Optional[int] = None,
    include_stats: bool = True,
) -> dict:
    dept = db.query(Department).filter(Department.id == u.department_id).first() if u.department_id else None
    data = {
        "id": u.id,
        "email": u.email,
        "username": u.username,
        "full_name": u.full_name,
        "role": u.role,
        "department_id": u.department_id,
        "department_code": dept.code if dept else None,
        "department_name": dept.name if dept else None,
        "bio": u.bio or "",
        "research_interests_text": u.research_interests_text or "",
        "research_tags": u.research_tags or [],
        "publication_links": u.publication_links or [],
        "personal_website": u.personal_website or "",
        "is_active": u.is_active,
        "is_flagged_spam": u.is_flagged_spam,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }
    if include_stats:
        data["followers_count"] = db.query(func.count(UserFollow.follower_id)).filter(UserFollow.following_id == u.id).scalar() or 0
        data["following_count"] = db.query(func.count(UserFollow.following_id)).filter(UserFollow.follower_id == u.id).scalar() or 0
        data["posts_count"] = db.query(func.count(Post.id)).filter(Post.author_id == u.id).scalar() or 0
        data["saved_papers_count"] = db.query(func.count(SavedPaper.id)).filter(SavedPaper.user_id == u.id).scalar() or 0
        data["followed_topics"] = [
            t.topic for t in db.query(TopicFollow).filter(TopicFollow.user_id == u.id).all()
        ]
        if viewer_id is not None and viewer_id != u.id:
            data["is_following"] = (
                db.query(UserFollow)
                .filter(UserFollow.follower_id == viewer_id, UserFollow.following_id == u.id)
                .first()
                is not None
            )
        else:
            data["is_following"] = False
    return data


@router.get("/api/departments")
def list_departments(db: Session = Depends(get_db)):
    depts = db.query(Department).order_by(Department.code.asc()).all()
    out = []
    for d in depts:
        mc = db.query(func.count(User.id)).filter(User.department_id == d.id, User.is_active == True).scalar() or 0
        out.append(
            {
                "id": d.id,
                "code": d.code,
                "name": d.name,
                "faculty_head": d.faculty_head,
                "description": d.description,
                "member_count": mc,
            }
        )
    return out


PUBLIC_ALLOWED_ROLES = {"student", "faculty", "researcher"}


@router.post(
    "/api/auth/register",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_dependency("auth_register", max_requests=6, window_seconds=60))],
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if payload.role not in PUBLIC_ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration is restricted to student, faculty, and researcher roles",
        )
    email_l = payload.email.strip().lower()
    uname_l = payload.username.strip().lower()
    if db.query(User).filter((User.email == email_l) | (User.username == uname_l)).first():
        raise HTTPException(status_code=400, detail="Email or username is already registered")

    dept_id = payload.department_id
    if dept_id is None:
        first_dept = db.query(Department).first()
        dept_id = first_dept.id if first_dept else None

    user = User(
        email=email_l,
        username=uname_l,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
        department_id=dept_id,
        research_interests_text=payload.research_interests_text.strip(),
        research_tags=[t.strip().lower() for t in payload.research_tags if t.strip()],
        is_synthetic=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    for tag in user.research_tags[:5]:
        db.add(TopicFollow(user_id=user.id, topic=tag))
    db.commit()

    token = create_access_token(user.id, user.role, user.email)
    return {"access_token": token, "token_type": "bearer", "user": serialize_user(db, user, viewer_id=user.id)}


@router.post(
    "/api/auth/login",
    dependencies=[Depends(rate_limit_dependency("auth_login", max_requests=12, window_seconds=60))],
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    ident = payload.email.strip().lower()
    user = db.query(User).filter((User.email == ident) | (User.username == ident)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email/username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been suspended by an administrator")

    token = create_access_token(user.id, user.role, user.email)
    return {"access_token": token, "token_type": "bearer", "user": serialize_user(db, user, viewer_id=user.id)}


@router.post("/api/auth/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out successfully", "user_id": current_user.id}


@router.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_user(db, current_user, viewer_id=current_user.id)


@router.patch("/api/users/me")
def update_my_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()
    if payload.department_id is not None:
        current_user.department_id = payload.department_id
    if payload.bio is not None:
        current_user.bio = payload.bio.strip()
    if payload.research_interests_text is not None:
        current_user.research_interests_text = payload.research_interests_text.strip()
    if payload.research_tags is not None:
        current_user.research_tags = sorted(set(t.strip().lower() for t in payload.research_tags if t.strip()))
    if payload.publication_links is not None:
        current_user.publication_links = [l.strip() for l in payload.publication_links if l.strip()]
    if payload.personal_website is not None:
        current_user.personal_website = payload.personal_website.strip()
    db.commit()
    db.refresh(current_user)
    return serialize_user(db, current_user, viewer_id=current_user.id)


@router.get("/api/users")
def list_users(
    q: Optional[str] = None,
    department_code: Optional[str] = None,
    role: Optional[str] = None,
    tag: Optional[str] = None,
    include_flagged: bool = False,
    limit: int = Query(default=60, ge=1, le=200),
    viewer: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(User.is_active == True)
    if not include_flagged:
        query = query.filter(User.is_flagged_spam == False)
    if role:
        query = query.filter(User.role == role)
    if department_code:
        dept = db.query(Department).filter(Department.code == department_code).first()
        if dept:
            query = query.filter(User.department_id == dept.id)
    users = query.order_by(User.full_name.asc()).all()

    if q:
        ql = q.strip().lower()
        users = [
            u
            for u in users
            if ql in (u.full_name or "").lower()
            or ql in (u.username or "").lower()
            or ql in (u.research_interests_text or "").lower()
            or any(ql in str(t).lower() for t in (u.research_tags or []))
        ]
    if tag:
        tl = tag.strip().lower()
        users = [u for u in users if any(tl in str(t).lower() for t in (u.research_tags or []))]

    vid = viewer.id if viewer else None
    return [serialize_user(db, u, viewer_id=vid) for u in users[:limit]]


@router.get("/api/users/{user_id}")
def get_user_profile(
    user_id: int,
    viewer: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Member not found")
    profile = serialize_user(db, user, viewer_id=(viewer.id if viewer else None))

    recent_posts = (
        db.query(Post).filter(Post.author_id == user_id).order_by(Post.created_at.desc()).limit(10).all()
    )
    profile["recent_posts"] = [
        {
            "id": p.id,
            "title": p.title,
            "tags": p.tags or [],
            "upvote_count": p.upvote_count,
            "comment_count": p.comment_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in recent_posts
    ]
    saved = (
        db.query(SavedPaper)
        .filter(SavedPaper.user_id == user_id)
        .order_by(SavedPaper.saved_at.desc())
        .limit(10)
        .all()
    )
    profile["recent_saved_papers"] = [
        {
            "id": sp.paper.id,
            "title": sp.paper.title,
            "publication_year": sp.paper.publication_year,
            "venue": sp.paper.venue,
            "save_count": sp.paper.save_count,
            "topics": sp.paper.topics or [],
        }
        for sp in saved
        if sp.paper
    ]
    return profile


@router.post("/api/users/{user_id}/follow")
def follow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target member not found")

    existing = (
        db.query(UserFollow)
        .filter(UserFollow.follower_id == current_user.id, UserFollow.following_id == user_id)
        .first()
    )
    if not existing:
        db.add(UserFollow(follower_id=current_user.id, following_id=user_id))
        db.add(
            ActivityEvent(
                user_id=current_user.id,
                event_type="follow",
                department_id=current_user.department_id,
                metadata_json={"following_id": user_id},
            )
        )
        db.commit()
    return {"following": True, "target_user_id": user_id}


@router.delete("/api/users/{user_id}/follow")
def unfollow_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(UserFollow)
        .filter(UserFollow.follower_id == current_user.id, UserFollow.following_id == user_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
    return {"following": False, "target_user_id": user_id}


@router.get("/api/users/me/topics")
def get_followed_topics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(TopicFollow).filter(TopicFollow.user_id == current_user.id).order_by(TopicFollow.topic.asc()).all()
    return [r.topic for r in rows]


@router.post("/api/users/me/topics/follow")
def follow_topic(
    payload: TopicFollowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = payload.topic.strip().lower()
    if not db.query(TopicFollow).filter(TopicFollow.user_id == current_user.id, TopicFollow.topic == t).first():
        db.add(TopicFollow(user_id=current_user.id, topic=t))
        db.commit()
    return {"topic": t, "following": True}


@router.delete("/api/users/me/topics/follow/{topic}")
def unfollow_topic(
    topic: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = topic.strip().lower()
    row = db.query(TopicFollow).filter(TopicFollow.user_id == current_user.id, TopicFollow.topic == t).first()
    if row:
        db.delete(row)
        db.commit()
    return {"topic": t, "following": False}
