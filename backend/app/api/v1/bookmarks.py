from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, QuestionBookmark, Question, Topic, Subject
from app.schemas.schemas import BookmarkResponse, AddBookmarkRequest

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.get("", response_model=List[BookmarkResponse])
async def get_bookmarks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(QuestionBookmark, Question, Topic, Subject)
        .join(Question, QuestionBookmark.question_id == Question.id)
        .join(Topic, Question.topic_id == Topic.id)
        .join(Subject, Topic.subject_id == Subject.id)
        .where(QuestionBookmark.user_id == current_user.id)
        .order_by(QuestionBookmark.created_at.desc())
    )
    rows = result.all()

    return [
        BookmarkResponse(
            id=bm.id,
            question_id=bm.question_id,
            question_text=q.question_text,
            topic_title=t.title,
            subject_name=s.name,
            notes=bm.notes,
            created_at=bm.created_at,
        )
        for bm, q, t, s in rows
    ]


@router.post("", response_model=BookmarkResponse, status_code=201)
async def add_bookmark(
    payload: AddBookmarkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check question exists
    q_res = await db.execute(select(Question).where(Question.id == payload.question_id))
    question = q_res.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check not already bookmarked
    existing = await db.execute(
        select(QuestionBookmark).where(
            QuestionBookmark.user_id == current_user.id,
            QuestionBookmark.question_id == payload.question_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already bookmarked")

    bm = QuestionBookmark(
        user_id=current_user.id,
        question_id=payload.question_id,
        notes=payload.notes,
    )
    db.add(bm)
    await db.commit()
    await db.refresh(bm)

    # Fetch full data
    result = await db.execute(
        select(QuestionBookmark, Question, Topic, Subject)
        .join(Question, QuestionBookmark.question_id == Question.id)
        .join(Topic, Question.topic_id == Topic.id)
        .join(Subject, Topic.subject_id == Subject.id)
        .where(QuestionBookmark.id == bm.id)
    )
    row = result.first()
    bm_obj, q, t, s = row

    return BookmarkResponse(
        id=bm_obj.id,
        question_id=bm_obj.question_id,
        question_text=q.question_text,
        topic_title=t.title,
        subject_name=s.name,
        notes=bm_obj.notes,
        created_at=bm_obj.created_at,
    )


@router.delete("/{bookmark_id}", status_code=204)
async def delete_bookmark(
    bookmark_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(QuestionBookmark).where(
            QuestionBookmark.id == bookmark_id,
            QuestionBookmark.user_id == current_user.id,
        )
    )
    bm = result.scalar_one_or_none()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.delete(bm)
    await db.commit()
