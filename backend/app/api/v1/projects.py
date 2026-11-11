import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Subject, Topic, User

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_filter(project_id: str):
    """Projects are addressable by the UUID returned from the list, or by slug."""
    try:
        return Topic.id == uuid.UUID(project_id)
    except ValueError:
        return Topic.slug == project_id


@router.get("")
async def list_projects(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Topic).join(Subject).where(Subject.slug == "project-deep-dive", Topic.is_active == True).order_by(Topic.order_index)
    )
    return [{"id": t.id, "title": t.title, "slug": t.slug, "description": t.description,
             "difficulty": t.difficulty, "estimated_minutes": t.estimated_minutes} for t in result.scalars().all()]


@router.get("/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Topic).join(Subject).where(Subject.slug == "project-deep-dive", _project_filter(project_id))
    )
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"id": topic.id, "title": topic.title, "slug": topic.slug, "description": topic.description,
            "difficulty": topic.difficulty, "estimated_minutes": topic.estimated_minutes}


@router.get("/{project_id}/questions")
async def project_questions(project_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Topic).options(selectinload(Topic.questions)).join(Subject).where(Subject.slug == "project-deep-dive", _project_filter(project_id)))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Project not found")
    return [{"id": q.id, "question_text": q.question_text, "difficulty": q.difficulty, "order_index": q.order_index}
            for q in sorted(topic.questions, key=lambda item: item.order_index)]
