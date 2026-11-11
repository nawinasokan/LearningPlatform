"""Global search and the personalised learning feed."""
import hashlib
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import (
    CodingProblem, ExplanationMode, Question, QuestionAnswer, QuestionBookmark,
    SQLProblem, Subject, Topic, User, UserAnswer,
)

router = APIRouter(tags=["discover"])


def _like(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _snippet(text: str, term: Optional[str] = None, size: int = 220) -> str:
    text = " ".join((text or "").split())
    if term:
        i = text.lower().find(term.lower())
        if i > size // 2:
            start = i - size // 3
            return "…" + text[start:start + size] + "…"
    return text[:size] + ("…" if len(text) > size else "")


@router.get("/search")
async def search(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(8, ge=1, le=25),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search questions (text and answers), topics, coding problems and SQL problems."""
    pattern = _like(q.strip())

    # Questions whose text matches rank first; answer-body matches follow.
    in_text = Question.question_text.ilike(pattern, escape="\\")
    in_answer = Question.id.in_(select(QuestionAnswer.question_id).where(QuestionAnswer.answer_text.ilike(pattern, escape="\\")))
    rows = (await db.execute(
        select(Question, Topic, Subject)
        .join(Topic, Question.topic_id == Topic.id).join(Subject, Topic.subject_id == Subject.id)
        .where(Question.is_active == True, Topic.is_active == True, Subject.is_active == True, or_(in_text, in_answer))  # noqa: E712
        .order_by((~in_text).asc(), Subject.priority, Question.order_index).limit(limit)
    )).all()
    questions = [{
        "id": str(qu.id), "topic_id": str(t.id), "question_text": qu.question_text, "difficulty": qu.difficulty.value,
        "topic_title": t.title, "subject_name": s.name, "subject_slug": s.slug,
    } for qu, t, s in rows]

    topic_rows = (await db.execute(
        select(Topic, Subject).join(Subject, Topic.subject_id == Subject.id)
        .where(Topic.is_active == True, or_(Topic.title.ilike(pattern, escape="\\"), Topic.description.ilike(pattern, escape="\\")))  # noqa: E712
        .order_by(Subject.priority, Topic.order_index).limit(limit)
    )).all()
    topics = [{"id": str(t.id), "title": t.title, "description": t.description, "subject_name": s.name, "subject_slug": s.slug}
              for t, s in topic_rows]

    coding = (await db.execute(
        select(CodingProblem).where(CodingProblem.is_active == True, or_(  # noqa: E712
            CodingProblem.title.ilike(pattern, escape="\\"), CodingProblem.category.ilike(pattern, escape="\\"))).limit(limit)
    )).scalars().all()
    sql = (await db.execute(
        select(SQLProblem).where(SQLProblem.is_active == True, or_(  # noqa: E712
            SQLProblem.title.ilike(pattern, escape="\\"), SQLProblem.category.ilike(pattern, escape="\\"))).limit(limit)
    )).scalars().all()

    return {
        "query": q,
        "questions": questions,
        "topics": topics,
        "coding_problems": [{"id": str(p.id), "title": p.title, "difficulty": p.difficulty.value, "category": p.category} for p in coding],
        "sql_problems": [{"id": str(p.id), "title": p.title, "difficulty": p.difficulty.value, "category": p.category} for p in sql],
    }


async def _card(db, question, topic, subject, kind, reason):
    interview = (await db.execute(
        select(QuestionAnswer.answer_text).where(QuestionAnswer.question_id == question.id, QuestionAnswer.mode == ExplanationMode.interview)
    )).scalar()
    return {
        "kind": kind, "reason": reason, "question_id": str(question.id), "topic_id": str(topic.id),
        "question_text": question.question_text, "difficulty": question.difficulty.value,
        "topic_title": topic.title, "subject_name": subject.name, "subject_slug": subject.slug,
        "subject_icon": subject.icon, "preview": _snippet(interview, size=260),
    }


@router.get("/feed")
async def feed(
    limit: int = Query(12, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """A mixed feed: daily picks, continue-where-you-left-off, low-rated review items and unseen questions."""
    base = (select(Question, Topic, Subject)
            .join(Topic, Question.topic_id == Topic.id).join(Subject, Topic.subject_id == Subject.id)
            .where(Question.is_active == True, Topic.is_active == True, Subject.is_active == True))  # noqa: E712
    done_ids = select(UserAnswer.question_id).where(UserAnswer.user_id == current_user.id, UserAnswer.is_completed == True)  # noqa: E712
    cards, used = [], set()

    async def add(rows, kind, reason, cap):
        for qu, t, s in rows[:cap]:
            if qu.id not in used and len(cards) < limit:
                used.add(qu.id)
                cards.append(await _card(db, qu, t, s, kind, reason))

    # 1) Review: questions the user rated low (<=2).
    weak = (await db.execute(base.join(UserAnswer, and_(UserAnswer.question_id == Question.id, UserAnswer.user_id == current_user.id))
                             .where(UserAnswer.self_rating <= 2).limit(3))).all()
    await add(weak, "review", "You rated this low — worth another pass", 3)

    # 2) Daily picks: one stable-per-day question from each subject, rotated by date.
    today = date.today().isoformat()
    subjects = (await db.execute(select(Subject).where(Subject.is_active == True).order_by(Subject.priority, Subject.name))).scalars().all()  # noqa: E712
    daily = []
    for s in subjects:
        count = (await db.execute(base.with_only_columns(func.count(Question.id)).where(Subject.id == s.id))).scalar() or 0
        if not count:
            continue
        offset = int(hashlib.sha256(f"{today}:{s.slug}:{current_user.id}".encode()).hexdigest(), 16) % count
        row = (await db.execute(base.where(Subject.id == s.id).order_by(Topic.order_index, Question.order_index).offset(offset).limit(1))).first()
        if row:
            daily.append(row)
    start = int(hashlib.sha256(f"{today}:{current_user.id}".encode()).hexdigest(), 16) % max(len(daily), 1)
    daily = daily[start:] + daily[:start]
    await add(daily, "daily", "Today's pick", 5)

    # 3) Continue: the next unanswered question in the topic(s) the user touched most recently.
    recent_topic_ids = select(Question.topic_id).join(UserAnswer, UserAnswer.question_id == Question.id).where(
        UserAnswer.user_id == current_user.id).order_by(UserAnswer.updated_at.desc()).limit(3)
    nxt = (await db.execute(base.where(Question.topic_id.in_(recent_topic_ids), Question.id.not_in(done_ids))
                            .order_by(Topic.order_index, Question.order_index).limit(4))).all()
    await add(nxt, "continue", "Pick up where you left off", 4)

    # 4) Fresh: unseen questions across higher-priority subjects.
    fresh = (await db.execute(base.where(Question.id.not_in(done_ids)).order_by(Subject.priority, Topic.order_index, Question.order_index).limit(limit * 2))).all()
    await add(fresh, "new", "New for you", limit)

    return {"items": cards, "generated_for": today}
