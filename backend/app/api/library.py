"""F3: Shared University Research Library, Personal Collections, Private Notes, and DOI/arXiv/URL Import API."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, get_current_user_optional
from backend.app.models.models import (
    ActivityEvent,
    Collection,
    Department,
    Paper,
    Post,
    SavedPaper,
    User,
)
from backend.app.schemas.schemas import (
    AddPaperByIdentifierRequest,
    CollectionCreateRequest,
    CollectionUpdateRequest,
    SavePaperRequest,
    UpdateSavedPaperRequest,
)
from ingestion.pipeline import fetch_paper_metadata_by_identifier, upsert_paper_record
from ml.embeddings.embedder import get_embedder
from ml.recommendations.recommender import recommend_also_saved_fpgrowth

router = APIRouter(tags=["F3: Research Library & Collections"])


def serialize_paper(paper: Paper, saved_entry: Optional[SavedPaper] = None) -> dict:
    return {
        "id": paper.id,
        "title": paper.title,
        "abstract": paper.abstract or "",
        "authors": paper.authors or [],
        "publication_year": paper.publication_year,
        "published_date": paper.published_date or "",
        "venue": paper.venue or "",
        "doi": paper.doi,
        "arxiv_id": paper.arxiv_id,
        "url": paper.url or "",
        "pdf_url": paper.pdf_url or "",
        "topics": paper.topics or [],
        "department_hint": paper.department_hint,
        "primary_source": paper.primary_source,
        "sources": paper.sources or [],
        "citation_count": paper.citation_count,
        "pagerank_score": paper.pagerank_score,
        "save_count": paper.save_count,
        "in_university_library": paper.in_university_library,
        "is_synthetic": paper.is_synthetic,
        "is_saved_by_me": saved_entry is not None,
        "my_collection_id": saved_entry.collection_id if saved_entry else None,
        "my_private_notes": saved_entry.private_notes if saved_entry else "",
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
    }


@router.get("/api/papers")
def list_papers(
    q: Optional[str] = None,
    author: Optional[str] = None,
    only_library: bool = False,
    source: Optional[str] = None,
    department: Optional[str] = None,
    topic: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    sort: str = Query(default="saves", pattern="^(saves|citations|pagerank|recent)$"),
    limit: int = Query(default=30, ge=1, le=120),
    offset: int = Query(default=0, ge=0),
    viewer: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    query = db.query(Paper)
    if only_library:
        query = query.filter(Paper.in_university_library == True)
    if source:
        query = query.filter(Paper.primary_source == source)
    if department:
        query = query.filter(Paper.department_hint == department)
    if year_from:
        query = query.filter(Paper.publication_year >= year_from)
    if year_to:
        query = query.filter(Paper.publication_year <= year_to)

    if sort == "saves":
        query = query.order_by(Paper.save_count.desc(), Paper.citation_count.desc())
    elif sort == "citations":
        query = query.order_by(Paper.citation_count.desc(), Paper.pagerank_score.desc())
    elif sort == "pagerank":
        query = query.order_by(Paper.pagerank_score.desc(), Paper.citation_count.desc())
    else:
        query = query.order_by(Paper.publication_year.desc(), Paper.id.desc())

    papers = query.all()
    if topic:
        tl = topic.strip().lower()
        papers = [p for p in papers if any(tl in str(t).lower() for t in (p.topics or []))]
    if author:
        al = author.strip().lower()
        papers = [p for p in papers if any(al in str(a).lower() for a in (p.authors or []))]
    if q and q.strip():
        ql = q.strip().lower()
        papers = [
            p for p in papers
            if ql in (p.title or "").lower()
            or ql in (p.abstract or "").lower()
            or any(ql in str(t).lower() for t in (p.topics or []))
            or any(ql in str(a).lower() for a in (p.authors or []))
        ]

    total = len(papers)
    page = papers[offset : offset + limit]

    saved_map = {}
    if viewer:
        for sp in db.query(SavedPaper).filter(SavedPaper.user_id == viewer.id).all():
            saved_map[sp.paper_id] = sp

    return {
        "total": total,
        "items": [serialize_paper(p, saved_map.get(p.id)) for p in page],
    }


@router.get("/api/library/recently-viewed")
def get_recently_viewed(
    limit: int = Query(default=10, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    events = (
        db.query(ActivityEvent)
        .filter(
            ActivityEvent.user_id == current_user.id,
            ActivityEvent.event_type == "view",
            ActivityEvent.paper_id.isnot(None),
        )
        .order_by(ActivityEvent.created_at.desc())
        .limit(80)
        .all()
    )
    seen = set()
    ordered_ids = []
    viewed_at_map = {}
    for ev in events:
        if ev.paper_id and ev.paper_id not in seen:
            seen.add(ev.paper_id)
            ordered_ids.append(ev.paper_id)
            viewed_at_map[ev.paper_id] = ev.created_at.isoformat() if ev.created_at else None
            if len(ordered_ids) >= limit:
                break

    if not ordered_ids:
        return {"items": []}

    paper_map = {p.id: p for p in db.query(Paper).filter(Paper.id.in_(ordered_ids)).all()}
    saved_map = {
        sp.paper_id: sp
        for sp in db.query(SavedPaper).filter(SavedPaper.user_id == current_user.id, SavedPaper.paper_id.in_(ordered_ids)).all()
    }
    items = []
    for pid in ordered_ids:
        p = paper_map.get(pid)
        if p:
            d = serialize_paper(p, saved_map.get(pid))
            d["viewed_at"] = viewed_at_map.get(pid)
            items.append(d)
    return {"items": items}


@router.get("/api/papers/{paper_id}")
def get_paper_detail(
    paper_id: int,
    viewer: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Log view event for analytics & trend mining
    db.add(
        ActivityEvent(
            user_id=viewer.id if viewer else None,
            event_type="view",
            paper_id=paper.id,
            topic=(paper.topics[0] if paper.topics else "general"),
            department_id=viewer.department_id if viewer else None,
        )
    )
    db.commit()

    saved_entry = (
        db.query(SavedPaper).filter(SavedPaper.user_id == viewer.id, SavedPaper.paper_id == paper.id).first()
        if viewer
        else None
    )
    data = serialize_paper(paper, saved_entry)

    # University members who saved this paper
    savers = (
        db.query(SavedPaper, User, Department)
        .join(User, SavedPaper.user_id == User.id)
        .outerjoin(Department, User.department_id == Department.id)
        .filter(SavedPaper.paper_id == paper.id, User.is_flagged_spam == False)
        .limit(12)
        .all()
    )
    data["saved_by_members"] = [
        {
            "id": u.id,
            "full_name": u.full_name,
            "role": u.role,
            "department_code": d.code if d else None,
            "saved_at": sp.saved_at.isoformat() if sp.saved_at else None,
        }
        for sp, u, d in savers
    ]

    # Related discussions referencing this paper
    related_posts = (
        db.query(Post).filter(Post.attached_paper_id == paper.id).order_by(Post.created_at.desc()).limit(6).all()
    )
    data["related_discussions"] = [
        {
            "id": po.id,
            "title": po.title,
            "upvote_count": po.upvote_count,
            "comment_count": po.comment_count,
            "created_at": po.created_at.isoformat() if po.created_at else None,
        }
        for po in related_posts
    ]

    # F6 "Members who saved this also saved" (FP-Growth Association Rules)
    data["also_saved"] = recommend_also_saved_fpgrowth(db, paper.id, limit=6)
    return data


@router.post("/api/papers/add-by-identifier", status_code=status.HTTP_201_CREATED)
def add_paper_by_identifier(
    payload: AddPaperByIdentifierRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """F3: Add paper to Chanakya Library by DOI, arXiv ID, or URL with automatic metadata fetch & deduplication."""
    if not any([payload.doi, payload.arxiv_id, payload.url, payload.title]):
        raise HTTPException(status_code=400, detail="Provide at least one of DOI, arXiv ID, URL, or Title")

    fetched = fetch_paper_metadata_by_identifier(doi=payload.doi, arxiv_id=payload.arxiv_id, url=payload.url)
    dept = db.query(Department).filter(Department.id == current_user.department_id).first()

    if fetched:
        rec = {
            **fetched,
            "title": payload.title.strip() if payload.title else fetched["title"],
            "abstract": payload.abstract.strip() if payload.abstract else fetched.get("abstract", ""),
            "topics": list(dict.fromkeys([t.lower() for t in payload.topics] + fetched.get("topics", []))),
            "department_hint": dept.code if dept else None,
        }
    else:
        inferred_title = payload.title or (
            f"Research Paper ({payload.doi or payload.arxiv_id or payload.url})"
        )
        rec = {
            "title": inferred_title.strip(),
            "abstract": (payload.abstract or f"Submitted to Chanakya University Library by {current_user.full_name}.").strip(),
            "authors": payload.authors or [current_user.full_name],
            "publication_year": 2026,
            "venue": "Chanakya Library Submission",
            "doi": payload.doi,
            "arxiv_id": payload.arxiv_id,
            "url": payload.url or (f"https://doi.org/{payload.doi}" if payload.doi else ""),
            "topics": [t.strip().lower() for t in payload.topics if t.strip()] or (current_user.research_tags or ["general"])[:3],
            "department_hint": dept.code if dept else None,
            "primary_source": "user_submission",
            "external_id": payload.doi or payload.arxiv_id or payload.url or inferred_title[:60],
            "citation_count": 0,
            "is_synthetic": False,
        }

    existing_cache = db.query(Paper).all()
    paper, action = upsert_paper_record(db, rec, existing_cache=existing_cache)

    # Compute embedding if missing
    if not paper.embedding:
        embedder = get_embedder()
        paper.embedding = embedder.encode_one(f"{paper.title}. {paper.abstract or ''}")

    # Save to user's personal library & university library
    sp = db.query(SavedPaper).filter(SavedPaper.user_id == current_user.id, SavedPaper.paper_id == paper.id).first()
    if not sp:
        sp = SavedPaper(
            user_id=current_user.id,
            paper_id=paper.id,
            collection_id=payload.collection_id,
            private_notes=payload.private_notes.strip(),
        )
        db.add(sp)
        paper.save_count = (paper.save_count or 0) + 1
        paper.in_university_library = True
        db.add(
            ActivityEvent(
                user_id=current_user.id,
                event_type="save",
                paper_id=paper.id,
                topic=(paper.topics[0] if paper.topics else "general"),
                department_id=current_user.department_id,
            )
        )
    else:
        if payload.collection_id is not None:
            sp.collection_id = payload.collection_id
        if payload.private_notes:
            sp.private_notes = payload.private_notes.strip()

    db.commit()
    db.refresh(paper)
    return {
        "action": action,
        "metadata_fetched_live": fetched is not None,
        "paper": serialize_paper(paper, sp),
    }


@router.post("/api/library/save")
def save_paper(
    payload: SavePaperRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paper = db.query(Paper).filter(Paper.id == payload.paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if payload.collection_id is not None:
        col = db.query(Collection).filter(Collection.id == payload.collection_id, Collection.user_id == current_user.id).first()
        if not col:
            raise HTTPException(status_code=404, detail="Collection not found")

    existing = (
        db.query(SavedPaper)
        .filter(SavedPaper.user_id == current_user.id, SavedPaper.paper_id == paper.id)
        .first()
    )
    if existing:
        existing.collection_id = payload.collection_id
        if payload.private_notes is not None:
            existing.private_notes = payload.private_notes
        db.commit()
        return {"saved": True, "already_saved": True, "paper": serialize_paper(paper, existing)}

    sp = SavedPaper(
        user_id=current_user.id,
        paper_id=paper.id,
        collection_id=payload.collection_id,
        private_notes=payload.private_notes.strip(),
    )
    db.add(sp)
    paper.save_count = (paper.save_count or 0) + 1
    paper.in_university_library = True
    db.add(
        ActivityEvent(
            user_id=current_user.id,
            event_type="save",
            paper_id=paper.id,
            topic=(paper.topics[0] if paper.topics else "general"),
            department_id=current_user.department_id,
        )
    )
    db.commit()
    db.refresh(paper)
    return {"saved": True, "already_saved": False, "paper": serialize_paper(paper, sp)}


@router.patch("/api/library/save/{paper_id}")
def update_saved_paper(
    paper_id: int,
    payload: UpdateSavedPaperRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sp = (
        db.query(SavedPaper)
        .filter(SavedPaper.user_id == current_user.id, SavedPaper.paper_id == paper_id)
        .first()
    )
    if not sp:
        raise HTTPException(status_code=404, detail="Paper is not in your library")
    if payload.collection_id is not None:
        if payload.collection_id == 0:
            sp.collection_id = None
        else:
            col = db.query(Collection).filter(Collection.id == payload.collection_id, Collection.user_id == current_user.id).first()
            if not col:
                raise HTTPException(status_code=404, detail="Collection not found")
            sp.collection_id = payload.collection_id
    if payload.private_notes is not None:
        sp.private_notes = payload.private_notes
    db.commit()
    return serialize_paper(sp.paper, sp)


@router.delete("/api/library/save/{paper_id}")
def unsave_paper(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sp = (
        db.query(SavedPaper)
        .filter(SavedPaper.user_id == current_user.id, SavedPaper.paper_id == paper_id)
        .first()
    )
    if not sp:
        return {"saved": False, "paper_id": paper_id}
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    db.delete(sp)
    if paper:
        paper.save_count = max(0, (paper.save_count or 0) - 1)
        if paper.save_count == 0:
            paper.in_university_library = False
    db.commit()
    return {"saved": False, "paper_id": paper_id, "save_count": paper.save_count if paper else 0}


@router.get("/api/library/my")
def get_my_library(
    collection_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(SavedPaper).filter(SavedPaper.user_id == current_user.id)
    if collection_id is not None:
        q = q.filter(SavedPaper.collection_id == collection_id)
    rows = q.order_by(SavedPaper.saved_at.desc()).all()
    items = []
    for sp in rows:
        if sp.paper:
            d = serialize_paper(sp.paper, sp)
            d["saved_at"] = sp.saved_at.isoformat() if sp.saved_at else None
            items.append(d)
    return {"total": len(items), "items": items}


@router.get("/api/collections")
def list_my_collections(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cols = db.query(Collection).filter(Collection.user_id == current_user.id).order_by(Collection.created_at.desc()).all()
    out = []
    for c in cols:
        cnt = db.query(SavedPaper).filter(SavedPaper.collection_id == c.id).count()
        out.append(
            {
                "id": c.id,
                "name": c.name,
                "description": c.description or "",
                "is_private": c.is_private,
                "item_count": cnt,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
        )
    return out


@router.post("/api/collections", status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    col = Collection(
        user_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        is_private=payload.is_private,
    )
    db.add(col)
    db.commit()
    db.refresh(col)
    return {
        "id": col.id,
        "name": col.name,
        "description": col.description,
        "is_private": col.is_private,
        "item_count": 0,
        "created_at": col.created_at.isoformat() if col.created_at else None,
    }


@router.patch("/api/collections/{collection_id}")
def update_collection(
    collection_id: int,
    payload: CollectionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    col = db.query(Collection).filter(Collection.id == collection_id, Collection.user_id == current_user.id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    if payload.name is not None:
        col.name = payload.name.strip()
    if payload.description is not None:
        col.description = payload.description.strip()
    if payload.is_private is not None:
        col.is_private = payload.is_private
    db.commit()
    return {"id": col.id, "name": col.name, "description": col.description, "is_private": col.is_private}


@router.delete("/api/collections/{collection_id}")
def delete_collection(
    collection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    col = db.query(Collection).filter(Collection.id == collection_id, Collection.user_id == current_user.id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    db.delete(col)
    db.commit()
    return {"deleted": True, "collection_id": collection_id}
