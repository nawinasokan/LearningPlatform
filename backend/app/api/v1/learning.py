from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import (
    Subject, Topic, LearningContent, Question, LearningProgress,
    UserAnswer, User, LearningActivity
)
from app.schemas.schemas import (
    SubjectResponse, TopicResponse, TopicDetailResponse,
    LearningContentResponse, PaginatedResponse, CompleteQuestionRequest, QuestionResponse
)
from datetime import datetime, timezone

router = APIRouter(tags=["learning"])


# ─── Subjects ───────────────────────────────────────────────
@router.get("/subjects", response_model=List[SubjectResponse])
async def get_subjects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Subject).where(Subject.is_active == True).order_by(Subject.priority, Subject.name)
    )
    subjects = result.scalars().all()

    out = []
    for s in subjects:
        # Count topics
        tc_res = await db.execute(select(func.count(Topic.id)).where(Topic.subject_id == s.id, Topic.is_active == True))
        topic_count = tc_res.scalar() or 0

        # Completed topics for this user
        prog_res = await db.execute(
            select(func.count(LearningProgress.id)).where(
                LearningProgress.user_id == current_user.id,
                LearningProgress.is_completed == True,
            ).join(Topic, LearningProgress.topic_id == Topic.id).where(Topic.subject_id == s.id)
        )
        completed = prog_res.scalar() or 0

        pct = (completed / topic_count * 100) if topic_count > 0 else 0.0

        out.append(SubjectResponse(
            id=s.id,
            name=s.name,
            slug=s.slug,
            description=s.description,
            icon=s.icon,
            color=s.color,
            priority=s.priority,
            topic_count=topic_count,
            progress_percentage=round(pct, 1),
        ))
    return out


# ─── Topics ─────────────────────────────────────────────────
@router.get("/subjects/{subject_id}/topics", response_model=List[TopicResponse])
async def get_topics(
    subject_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        parsed_id = uuid.UUID(subject_id)
        subject_filter = Subject.id == parsed_id
    except ValueError:
        subject_filter = Subject.slug == subject_id
    subject_result = await db.execute(select(Subject.id).where(subject_filter))
    resolved_subject_id = subject_result.scalar_one_or_none()
    if resolved_subject_id is None:
        return []
    result = await db.execute(
        select(Topic).where(
            Topic.subject_id == resolved_subject_id,
            Topic.is_active == True,
        ).order_by(Topic.order_index)
    )
    topics = result.scalars().all()

    out = []
    for t in topics:
        prog_res = await db.execute(
            select(LearningProgress).where(
                LearningProgress.user_id == current_user.id,
                LearningProgress.topic_id == t.id,
            )
        )
        prog = prog_res.scalar_one_or_none()

        out.append(TopicResponse(
            id=t.id,
            subject_id=t.subject_id,
            title=t.title,
            slug=t.slug,
            description=t.description,
            difficulty=t.difficulty,
            order_index=t.order_index,
            estimated_minutes=t.estimated_minutes,
            is_completed=prog.is_completed if prog else False,
            completion_percentage=prog.completion_percentage if prog else 0.0,
        ))
    return out


@router.get("/topics/{topic_id}", response_model=TopicDetailResponse)
async def get_topic(
    topic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Topic).options(selectinload(Topic.content)).where(Topic.id == topic_id)
    )
    topic = result.scalar_one_or_none()
    if not topic:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Topic not found")

    # Log activity
    activity = LearningActivity(
        user_id=current_user.id,
        activity_type="topic_view",
        topic_id=topic_id,
        subject_slug=None,
        duration_minutes=0,
    )
    db.add(activity)

    # Upsert progress
    prog_res = await db.execute(
        select(LearningProgress).where(
            LearningProgress.user_id == current_user.id,
            LearningProgress.topic_id == topic_id,
        )
    )
    prog = prog_res.scalar_one_or_none()
    if not prog:
        prog = LearningProgress(
            user_id=current_user.id,
            topic_id=topic_id,
            is_started=True,
            last_accessed=datetime.now(timezone.utc),
        )
        db.add(prog)
    else:
        prog.is_started = True
        prog.last_accessed = datetime.now(timezone.utc)

    await db.commit()

    # Question count
    qc_res = await db.execute(
        select(func.count(Question.id)).where(Question.topic_id == topic_id, Question.is_active == True)
    )
    q_count = qc_res.scalar() or 0

    content_obj = topic.content[0] if topic.content else None
    content_resp = None
    if content_obj:
        content_resp = LearningContentResponse(
            id=content_obj.id,
            definition=content_obj.definition,
            easy_explanation=content_obj.easy_explanation,
            analogy=content_obj.analogy,
            technical_explanation=content_obj.technical_explanation,
            internal_working=content_obj.internal_working,
            code_example=content_obj.code_example,
            code_language=content_obj.code_language,
            step_by_step=content_obj.step_by_step,
            use_cases=content_obj.use_cases,
            common_mistakes=content_obj.common_mistakes,
            interview_answer=content_obj.interview_answer,
            follow_up_questions=content_obj.follow_up_questions,
            practice_exercises=content_obj.practice_exercises,
            revision_notes=content_obj.revision_notes,
        )

    return TopicDetailResponse(
        id=topic.id,
        subject_id=topic.subject_id,
        title=topic.title,
        slug=topic.slug,
        description=topic.description,
        difficulty=topic.difficulty,
        order_index=topic.order_index,
        estimated_minutes=topic.estimated_minutes,
        is_completed=prog.is_completed if prog else False,
        completion_percentage=prog.completion_percentage if prog else 0.0,
        content=content_resp,
        question_count=q_count,
    )


# ─── Questions ──────────────────────────────────────────────
@router.get("/questions")
async def get_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    subject_slug: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Question).join(Topic).join(Subject).where(Question.is_active == True)
    if subject_slug:
        q = q.where(Subject.slug == subject_slug)
    if difficulty:
        q = q.where(Question.difficulty == difficulty)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    rows = (await db.execute(q.order_by(Question.order_index).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return {"items": [QuestionResponse.model_validate(item) for item in rows], "total": total,
            "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}


@router.get("/topics/{topic_id}/questions")
async def get_topic_questions(
    topic_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    difficulty: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.schemas.schemas import QuestionResponse
    from app.models.models import DifficultyLevel

    q = select(Question).where(Question.topic_id == topic_id, Question.is_active == True)
    if difficulty:
        q = q.where(Question.difficulty == difficulty)
    q = q.order_by(Question.order_index)

    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar() or 0

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    questions = result.scalars().all()

    # Get user answer status
    q_ids = [qu.id for qu in questions]
    answered_res = await db.execute(
        select(UserAnswer.question_id).where(
            UserAnswer.user_id == current_user.id,
            UserAnswer.question_id.in_(q_ids),
            UserAnswer.is_completed == True,
        )
    )
    completed_ids = {r for r in answered_res.scalars()}

    # Bookmarks
    from app.models.models import QuestionBookmark
    bm_res = await db.execute(
        select(QuestionBookmark.question_id).where(
            QuestionBookmark.user_id == current_user.id,
            QuestionBookmark.question_id.in_(q_ids),
        )
    )
    bookmarked_ids = {r for r in bm_res.scalars()}

    items = [
        QuestionResponse(
            id=qu.id,
            topic_id=qu.topic_id,
            question_text=qu.question_text,
            difficulty=qu.difficulty,
            order_index=qu.order_index,
            is_completed=qu.id in completed_ids,
            is_bookmarked=qu.id in bookmarked_ids,
        )
        for qu in questions
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/questions/{question_id}")
async def get_question_detail(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.schemas.schemas import QuestionDetailResponse, QuestionAnswerSchema
    result = await db.execute(
        select(Question).options(selectinload(Question.answers)).where(Question.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Question not found")

    # Completion status
    ua_res = await db.execute(
        select(UserAnswer).where(
            UserAnswer.user_id == current_user.id,
            UserAnswer.question_id == question_id,
        )
    )
    ua = ua_res.scalar_one_or_none()

    # Bookmark status
    from app.models.models import QuestionBookmark
    bm_res = await db.execute(
        select(QuestionBookmark).where(
            QuestionBookmark.user_id == current_user.id,
            QuestionBookmark.question_id == question_id,
        )
    )
    bm = bm_res.scalar_one_or_none()

    answers = [
        QuestionAnswerSchema(
            id=a.id,
            mode=a.mode,
            answer_text=a.answer_text,
            code_example=a.code_example,
            key_points=a.key_points,
        )
        for a in question.answers
    ]

    return QuestionDetailResponse(
        id=question.id,
        topic_id=question.topic_id,
        question_text=question.question_text,
        difficulty=question.difficulty,
        order_index=question.order_index,
        is_completed=ua.is_completed if ua else False,
        is_bookmarked=bm is not None,
        answers=answers,
    )


@router.get("/questions/{question_id}/answers")
async def get_question_answers(question_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Question).options(selectinload(Question.answers)).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Question not found")
    from app.schemas.schemas import QuestionAnswerSchema
    return [QuestionAnswerSchema.model_validate(answer) for answer in question.answers]


@router.post("/questions/{question_id}/complete")
async def complete_question(
    question_id: uuid.UUID,
    payload: CompleteQuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import UserAnswer, ExplanationMode

    # Verify question exists
    q_res = await db.execute(select(Question).where(Question.id == question_id))
    question = q_res.scalar_one_or_none()
    if not question:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Question not found")

    ua_res = await db.execute(
        select(UserAnswer).where(
            UserAnswer.user_id == current_user.id,
            UserAnswer.question_id == question_id,
        )
    )
    ua = ua_res.scalar_one_or_none()

    if not ua:
        ua = UserAnswer(
            user_id=current_user.id,
            question_id=question_id,
            is_completed=True,
            mode_viewed=payload.mode_viewed,
            self_rating=payload.self_rating,
        )
        db.add(ua)
    else:
        ua.is_completed = True
        if payload.mode_viewed:
            ua.mode_viewed = payload.mode_viewed
        if payload.self_rating:
            ua.self_rating = payload.self_rating

    await db.commit()
    return {"status": "completed"}
