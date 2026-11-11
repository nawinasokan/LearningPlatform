from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, RevisionSchedule, RevisionStatus, Topic, Subject, LearningActivity
from app.schemas.schemas import RevisionItemResponse, CompleteRevisionRequest

router = APIRouter(prefix="/revision", tags=["revision"])


@router.get("/today", response_model=List[RevisionItemResponse])
async def get_today_revision(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = datetime.now(timezone.utc)

    result = await db.execute(
        select(RevisionSchedule, Topic, Subject)
        .join(Topic, RevisionSchedule.topic_id == Topic.id)
        .join(Subject, Topic.subject_id == Subject.id)
        .where(
            RevisionSchedule.user_id == current_user.id,
            RevisionSchedule.due_date <= today,
            RevisionSchedule.status == RevisionStatus.due,
        )
        .order_by(RevisionSchedule.due_date)
        .limit(20)
    )
    rows = result.all()

    return [
        RevisionItemResponse(
            id=rev.id,
            topic_id=rev.topic_id,
            topic_title=t.title,
            subject_name=s.name,
            due_date=rev.due_date,
            interval_days=rev.interval_days,
            repetitions=rev.repetitions,
        )
        for rev, t, s in rows
    ]


@router.post("/{revision_id}/complete")
async def complete_revision(
    revision_id: uuid.UUID,
    payload: CompleteRevisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(RevisionSchedule).where(
            RevisionSchedule.id == revision_id,
            RevisionSchedule.user_id == current_user.id,
        )
    )
    rev = result.scalar_one_or_none()
    if not rev:
        raise HTTPException(status_code=404, detail="Revision item not found")

    # SM-2 algorithm
    new_ef, new_interval, new_reps = _sm2(
        payload.self_rating,
        rev.easiness_factor,
        rev.interval_days,
        rev.repetitions,
    )

    rev.status = RevisionStatus.completed
    rev.completed_at = datetime.now(timezone.utc)

    # Create next revision
    next_due = datetime.now(timezone.utc) + timedelta(days=new_interval)
    next_rev = RevisionSchedule(
        user_id=current_user.id,
        topic_id=rev.topic_id,
        due_date=next_due,
        interval_days=new_interval,
        easiness_factor=new_ef,
        repetitions=new_reps,
        status=RevisionStatus.due,
    )
    db.add(next_rev)

    # Log activity
    activity = LearningActivity(
        user_id=current_user.id,
        activity_type="revision_complete",
        topic_id=rev.topic_id,
        metadata_json={"self_rating": payload.self_rating, "new_interval": new_interval},
    )
    db.add(activity)

    await db.commit()
    return {"status": "completed", "next_due_days": new_interval}


def _sm2(rating: int, ef: float, interval: int, reps: int):
    """
    SM-2 spaced repetition algorithm.
    rating: 1-5 (1=complete blackout, 5=perfect)
    """
    # Map 1-5 to 0-5 quality scale
    q = max(0, rating - 1)

    if q < 3:
        # Failed — reset
        new_reps = 0
        new_interval = 1
    else:
        new_reps = reps + 1
        if reps == 0:
            new_interval = 1
        elif reps == 1:
            new_interval = 6
        else:
            new_interval = round(interval * ef)

    new_ef = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    new_ef = max(1.3, new_ef)

    return round(new_ef, 2), new_interval, new_reps
