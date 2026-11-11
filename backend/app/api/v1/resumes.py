from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
import uuid
import os
import shutil
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.models import User, Resume, ResumeSkill, ResumeProject, ResumeFact
from app.schemas.schemas import ResumeResponse, FactUpdateRequest
from app.services.resume_parser import parse_resume

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    # Save file
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{current_user.id}_{file.filename}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse resume
    parsed = parse_resume(file_path, file.filename)

    # Mark old resumes as not latest
    await db.execute(
        update(Resume).where(Resume.user_id == current_user.id).values(is_latest=False)
    )

    # Get latest version
    res_ver = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.version.desc())
    )
    last = res_ver.scalars().first()
    version = (last.version + 1) if last else 1

    # Create resume
    resume = Resume(
        user_id=current_user.id,
        version=version,
        filename=file.filename,
        file_path=file_path,
        raw_text=parsed.get("raw_text", ""),
        is_latest=True,
    )
    db.add(resume)
    await db.flush()

    # Add skills
    for skill_data in parsed.get("skills", []):
        skill = ResumeSkill(
            resume_id=resume.id,
            skill_name=skill_data.get("name", ""),
            category=skill_data.get("category"),
            proficiency=skill_data.get("proficiency"),
            subject_slug=skill_data.get("subject_slug"),
        )
        db.add(skill)

    # Add projects
    for proj_data in parsed.get("projects", []):
        project = ResumeProject(
            resume_id=resume.id,
            title=proj_data.get("title", ""),
            description=proj_data.get("description"),
            technologies=proj_data.get("technologies"),
            achievements=proj_data.get("achievements"),
            subject_slug=proj_data.get("subject_slug"),
        )
        db.add(project)

    # Add facts
    for fact_data in parsed.get("facts", []):
        fact = ResumeFact(
            resume_id=resume.id,
            category=fact_data.get("category", "experience"),
            fact_text=fact_data.get("text", ""),
            is_verified=False,
        )
        db.add(fact)

    await db.commit()
    await db.refresh(resume)

    # Load relationships
    res_full = await db.execute(
        select(Resume).where(Resume.id == resume.id)
    )
    r = res_full.scalar_one()

    skills_res = await db.execute(select(ResumeSkill).where(ResumeSkill.resume_id == r.id))
    projects_res = await db.execute(select(ResumeProject).where(ResumeProject.resume_id == r.id))
    facts_res = await db.execute(select(ResumeFact).where(ResumeFact.resume_id == r.id))

    return ResumeResponse(
        id=r.id,
        version=r.version,
        filename=r.filename,
        is_latest=r.is_latest,
        created_at=r.created_at,
        skills=[ResumeSkill(**{c.key: getattr(s, c.key) for c in s.__table__.columns}) for s in skills_res.scalars().all()],
        projects=[ResumeProject(**{c.key: getattr(p, c.key) for c in p.__table__.columns}) for p in projects_res.scalars().all()],
        facts=[ResumeFact(**{c.key: getattr(f, c.key) for c in f.__table__.columns}) for f in facts_res.scalars().all()],
    )


@router.get("/latest", response_model=ResumeResponse)
async def get_latest_resume(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id, Resume.is_latest == True)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")

    return await _build_resume_response(resume.id, db)


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return await _build_resume_response(resume_id, db)


@router.get("/{resume_id}/facts")
async def get_resume_facts(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.schemas.schemas import ResumeFactSchema
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Resume not found")

    facts_res = await db.execute(select(ResumeFact).where(ResumeFact.resume_id == resume_id))
    facts = facts_res.scalars().all()
    return [ResumeFactSchema.model_validate(f) for f in facts]


@router.patch("/{resume_id}/facts/{fact_id}")
async def update_resume_fact(
    resume_id: uuid.UUID,
    fact_id: uuid.UUID,
    payload: FactUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.schemas.schemas import ResumeFactSchema
    # Verify ownership
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Resume not found")

    fact_res = await db.execute(
        select(ResumeFact).where(ResumeFact.id == fact_id, ResumeFact.resume_id == resume_id)
    )
    fact = fact_res.scalar_one_or_none()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")

    if payload.fact_text is not None:
        fact.fact_text = payload.fact_text
    if payload.is_verified is not None:
        fact.is_verified = payload.is_verified

    await db.commit()
    await db.refresh(fact)
    return ResumeFactSchema.model_validate(fact)


async def _build_resume_response(resume_id: uuid.UUID, db: AsyncSession) -> ResumeResponse:
    from app.schemas.schemas import ResumeSkillSchema, ResumeProjectSchema, ResumeFactSchema

    r_res = await db.execute(select(Resume).where(Resume.id == resume_id))
    r = r_res.scalar_one()

    skills_res = await db.execute(select(ResumeSkill).where(ResumeSkill.resume_id == resume_id))
    projects_res = await db.execute(select(ResumeProject).where(ResumeProject.resume_id == resume_id))
    facts_res = await db.execute(select(ResumeFact).where(ResumeFact.resume_id == resume_id))

    return ResumeResponse(
        id=r.id,
        version=r.version,
        filename=r.filename,
        is_latest=r.is_latest,
        created_at=r.created_at,
        skills=[ResumeSkillSchema.model_validate(s) for s in skills_res.scalars().all()],
        projects=[ResumeProjectSchema.model_validate(p) for p in projects_res.scalars().all()],
        facts=[ResumeFactSchema.model_validate(f) for f in facts_res.scalars().all()],
    )
