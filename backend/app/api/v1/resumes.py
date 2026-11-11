from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List
import uuid
import os
import shutil
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.models import User, Resume, ResumeSkill, ResumeProject, ResumeFact
from app.schemas.schemas import ResumeResponse, FactUpdateRequest, ResumeUpdateRequest
from app.services.resume_parser import parse_resume

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    original_name = os.path.basename((file.filename or "").replace("\\", "/"))
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    data = await file.read(settings.MAX_UPLOAD_SIZE + 1)
    if len(data) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE // (1024 * 1024)} MB limit")
    magic_ok = data.startswith(b"%PDF") if ext == ".pdf" else data.startswith(b"PK")
    if not magic_ok:
        raise HTTPException(status_code=400, detail="File content does not match its extension")

    # Store under a server-generated name; the client filename is only kept as a label.
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{current_user.id}_{uuid.uuid4().hex}{ext}")
    with open(file_path, "wb") as f:
        f.write(data)
    file.filename = original_name[:255]

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


@router.patch("/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: uuid.UUID,
    payload: ResumeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit parsed data. Lists, when provided, replace the stored skills/projects;
    `new_facts` appends manually documented facts (unverified until confirmed)."""
    result = await db.execute(select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Resume not found")

    if payload.skills is not None:
        await db.execute(delete(ResumeSkill).where(ResumeSkill.resume_id == resume_id))
        for item in payload.skills:
            db.add(ResumeSkill(resume_id=resume_id, **item.model_dump()))
    if payload.projects is not None:
        await db.execute(delete(ResumeProject).where(ResumeProject.resume_id == resume_id))
        for item in payload.projects:
            db.add(ResumeProject(resume_id=resume_id, **item.model_dump()))
    for fact in payload.new_facts or []:
        db.add(ResumeFact(resume_id=resume_id, category=fact.category, fact_text=fact.fact_text, is_verified=False))
    await db.commit()
    return await _build_resume_response(resume_id, db)


@router.delete("/{resume_id}/facts/{fact_id}", status_code=204)
async def delete_resume_fact(
    resume_id: uuid.UUID,
    fact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    owned = await db.execute(select(Resume.id).where(Resume.id == resume_id, Resume.user_id == current_user.id))
    if not owned.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Resume not found")
    await db.execute(delete(ResumeFact).where(ResumeFact.id == fact_id, ResumeFact.resume_id == resume_id))
    await db.commit()


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
