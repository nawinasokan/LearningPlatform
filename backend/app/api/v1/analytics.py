from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
import uuid
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import (
    User, Subject, Topic, LearningProgress, UserAnswer, Question,
    CodingSubmission, LearningActivity, RevisionSchedule, RevisionStatus
)
from app.schemas.schemas import DashboardResponse, SubjectProgressSchema, TopicResponse
from datetime import datetime, timezone, timedelta

router = APIRouter(tags=["analytics"])


@router.get("/analytics/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Total topics
    total_topics_res = await db.execute(select(func.count(Topic.id)).where(Topic.is_active == True))
    total_topics = total_topics_res.scalar() or 0

    # Completed topics for user
    completed_topics_res = await db.execute(
        select(func.count(LearningProgress.id)).where(
            LearningProgress.user_id == current_user.id,
            LearningProgress.is_completed == True,
        )
    )
    completed_topics = completed_topics_res.scalar() or 0

    # Overall progress
    overall_progress = (completed_topics / total_topics * 100) if total_topics > 0 else 0.0

    # Questions
    total_q_res = await db.execute(select(func.count(Question.id)).where(Question.is_active == True))
    total_questions = total_q_res.scalar() or 0

    completed_q_res = await db.execute(
        select(func.count(UserAnswer.id)).where(
            UserAnswer.user_id == current_user.id,
            UserAnswer.is_completed == True,
        )
    )
    questions_completed = completed_q_res.scalar() or 0

    # Coding problems solved
    coding_res = await db.execute(
        select(func.count(CodingSubmission.id)).where(
            CodingSubmission.user_id == current_user.id,
            CodingSubmission.status == "passed",
        )
    )
    coding_solved = coding_res.scalar() or 0

    # Streak calculation
    streak_days = await _calculate_streak(db, current_user.id)

    # Per-subject progress
    subjects_res = await db.execute(
        select(Subject).where(Subject.is_active == True).order_by(Subject.priority)
    )
    subjects = subjects_res.scalars().all()

    subject_progress = []
    for s in subjects:
        t_res = await db.execute(
            select(func.count(Topic.id)).where(Topic.subject_id == s.id, Topic.is_active == True)
        )
        t_count = t_res.scalar() or 0

        c_res = await db.execute(
            select(func.count(LearningProgress.id))
            .join(Topic, LearningProgress.topic_id == Topic.id)
            .where(
                Topic.subject_id == s.id,
                LearningProgress.user_id == current_user.id,
                LearningProgress.is_completed == True,
            )
        )
        c_count = c_res.scalar() or 0

        # Questions for this subject
        sq_res = await db.execute(
            select(func.count(Question.id))
            .join(Topic, Question.topic_id == Topic.id)
            .where(Topic.subject_id == s.id, Question.is_active == True)
        )
        sq_count = sq_res.scalar() or 0

        cq_res = await db.execute(
            select(func.count(UserAnswer.id))
            .join(Question, UserAnswer.question_id == Question.id)
            .join(Topic, Question.topic_id == Topic.id)
            .where(
                Topic.subject_id == s.id,
                UserAnswer.user_id == current_user.id,
                UserAnswer.is_completed == True,
            )
        )
        cq_count = cq_res.scalar() or 0

        pct = (c_count / t_count * 100) if t_count > 0 else 0.0
        subject_progress.append(SubjectProgressSchema(
            subject_id=s.id,
            subject_name=s.name,
            slug=s.slug,
            color=s.color,
            total_topics=t_count,
            completed_topics=c_count,
            progress_percentage=round(pct, 1),
            questions_completed=cq_count,
            total_questions=sq_count,
        ))

    # Weak topics: low completion but started
    weak_res = await db.execute(
        select(LearningProgress, Topic)
        .join(Topic, LearningProgress.topic_id == Topic.id)
        .where(
            LearningProgress.user_id == current_user.id,
            LearningProgress.is_started == True,
            LearningProgress.is_completed == False,
            LearningProgress.completion_percentage < 30.0,
        )
        .order_by(LearningProgress.completion_percentage)
        .limit(5)
    )
    weak_rows = weak_res.all()
    weak_topics = [
        TopicResponse(
            id=t.id,
            subject_id=t.subject_id,
            title=t.title,
            slug=t.slug,
            description=t.description,
            difficulty=t.difficulty,
            order_index=t.order_index,
            estimated_minutes=t.estimated_minutes,
            is_completed=False,
            completion_percentage=p.completion_percentage,
        )
        for p, t in weak_rows
    ]

    # Recently studied
    recent_res = await db.execute(
        select(LearningProgress, Topic)
        .join(Topic, LearningProgress.topic_id == Topic.id)
        .where(
            LearningProgress.user_id == current_user.id,
            LearningProgress.last_accessed.isnot(None),
        )
        .order_by(LearningProgress.last_accessed.desc())
        .limit(5)
    )
    recent_rows = recent_res.all()
    recently_studied = [
        TopicResponse(
            id=t.id,
            subject_id=t.subject_id,
            title=t.title,
            slug=t.slug,
            description=t.description,
            difficulty=t.difficulty,
            order_index=t.order_index,
            estimated_minutes=t.estimated_minutes,
            is_completed=p.is_completed,
            completion_percentage=p.completion_percentage,
        )
        for p, t in recent_rows
    ]

    # Due for revision
    today = datetime.now(timezone.utc)
    rev_res = await db.execute(
        select(func.count(RevisionSchedule.id)).where(
            RevisionSchedule.user_id == current_user.id,
            RevisionSchedule.due_date <= today,
            RevisionSchedule.status == RevisionStatus.due,
        )
    )
    due_for_revision = rev_res.scalar() or 0

    return DashboardResponse(
        overall_progress=round(overall_progress, 1),
        total_topics=total_topics,
        completed_topics=completed_topics,
        questions_completed=questions_completed,
        total_questions=total_questions,
        coding_solved=coding_solved,
        sql_completed=0,
        streak_days=streak_days,
        subjects=subject_progress,
        weak_topics=weak_topics,
        recently_studied=recently_studied,
        due_for_revision=due_for_revision,
    )


async def _calculate_streak(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Calculate consecutive days with learning activity."""
    today = datetime.now(timezone.utc).date()
    streak = 0
    check_date = today

    for _ in range(365):
        day_start = datetime.combine(check_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        act_res = await db.execute(
            select(func.count(LearningActivity.id)).where(
                LearningActivity.user_id == user_id,
                LearningActivity.created_at >= day_start,
                LearningActivity.created_at < day_end,
            )
        )
        count = act_res.scalar() or 0
        if count > 0:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    return streak


@router.get("/analytics/subjects")
async def get_subject_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Return per-subject detailed breakdown
    dashboard = await get_dashboard(db=db, current_user=current_user)
    return dashboard.subjects


@router.get("/analytics/weak-topics")
async def get_weak_topics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dashboard = await get_dashboard(db=db, current_user=current_user)
    return dashboard.weak_topics


@router.get("/analytics/history")
async def get_activity_history(
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.schemas.schemas import ActivityHistorySchema
    since = datetime.now(timezone.utc) - timedelta(days=days)

    res = await db.execute(
        select(LearningActivity).where(
            LearningActivity.user_id == current_user.id,
            LearningActivity.created_at >= since,
        ).order_by(LearningActivity.created_at)
    )
    activities = res.scalars().all()

    # Group by date
    by_date = {}
    for a in activities:
        d = a.created_at.date().isoformat()
        if d not in by_date:
            by_date[d] = {"activities": 0, "minutes": 0}
        by_date[d]["activities"] += 1
        by_date[d]["minutes"] += a.duration_minutes or 0

    return [
        ActivityHistorySchema(date=d, activities=v["activities"], minutes=v["minutes"])
        for d, v in sorted(by_date.items())
    ]
