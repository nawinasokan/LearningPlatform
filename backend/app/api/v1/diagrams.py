from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, Diagram
from app.schemas.schemas import DiagramResponse

router = APIRouter(prefix="/diagrams", tags=["diagrams"])


@router.get("", response_model=List[DiagramResponse])
async def get_diagrams(
    subject_slug: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Diagram)
    if subject_slug:
        q = q.where(Diagram.subject_slug == subject_slug)
    q = q.order_by(Diagram.title)
    result = await db.execute(q)
    diagrams = result.scalars().all()
    return [DiagramResponse.model_validate(d) for d in diagrams]


@router.get("/{diagram_id}", response_model=DiagramResponse)
async def get_diagram(
    diagram_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Diagram).where(Diagram.id == diagram_id))
    diagram = result.scalar_one_or_none()
    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return DiagramResponse.model_validate(diagram)
