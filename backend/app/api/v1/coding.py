from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
import uuid
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import (
    User, CodingProblem, CodingTestCase, CodingSubmission, SubmissionStatus, LearningActivity
)
from app.schemas.schemas import (
    CodingProblemResponse, CodeRunRequest, CodeSubmitRequest,
    CodeRunResponse, SubmissionResponse, TestResultSchema
)
from app.services.coding_service import run_code_against_tests
from datetime import datetime, timezone

router = APIRouter(prefix="/coding", tags=["coding"])


@router.get("/problems")
async def get_coding_problems(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    difficulty: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(CodingProblem).where(CodingProblem.is_active == True)
    if difficulty:
        q = q.where(CodingProblem.difficulty == difficulty)
    if category:
        q = q.where(CodingProblem.category == category)

    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar() or 0

    q = q.order_by(CodingProblem.difficulty, CodingProblem.title)
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    problems = result.scalars().all()

    # Check which are solved
    p_ids = [p.id for p in problems]
    solved_res = await db.execute(
        select(CodingSubmission.problem_id).where(
            CodingSubmission.user_id == current_user.id,
            CodingSubmission.problem_id.in_(p_ids),
            CodingSubmission.status == SubmissionStatus.passed,
        )
    )
    solved_ids = {r for r in solved_res.scalars()}

    items = [
        CodingProblemResponse(
            id=p.id,
            title=p.title,
            slug=p.slug,
            description=p.description,
            difficulty=p.difficulty,
            category=p.category,
            starter_code=p.starter_code,
            hints=p.hints,
            time_complexity=p.time_complexity,
            space_complexity=p.space_complexity,
            constraints=p.constraints,
            examples=p.examples,
            is_solved=p.id in solved_ids,
        )
        for p in problems
    ]

    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size}


@router.post("/run", response_model=CodeRunResponse)
async def run_code(
    payload: CodeRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get visible test cases
    result = await db.execute(
        select(CodingTestCase).where(
            CodingTestCase.problem_id == payload.problem_id,
            CodingTestCase.is_hidden == False,
        ).order_by(CodingTestCase.order_index)
    )
    test_cases = result.scalars().all()

    if not test_cases:
        raise HTTPException(status_code=404, detail="No test cases found for this problem")

    tc_data = [
        {"input_data": tc.input_data, "expected_output": tc.expected_output}
        for tc in test_cases
    ]

    exec_result = run_code_against_tests(payload.code, tc_data)

    return CodeRunResponse(
        status=exec_result["status"],
        test_results=[TestResultSchema(**r) for r in exec_result["test_results"]],
        passed_cases=exec_result["passed_cases"],
        total_cases=exec_result["total_cases"],
        runtime_ms=exec_result.get("runtime_ms"),
        error=None,
    )


@router.post("/submit", response_model=SubmissionResponse)
async def submit_code(
    payload: CodeSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get ALL test cases (including hidden)
    result = await db.execute(
        select(CodingTestCase).where(
            CodingTestCase.problem_id == payload.problem_id,
        ).order_by(CodingTestCase.order_index)
    )
    test_cases = result.scalars().all()

    if not test_cases:
        raise HTTPException(status_code=404, detail="No test cases found")

    tc_data = [
        {"input_data": tc.input_data, "expected_output": tc.expected_output}
        for tc in test_cases
    ]

    exec_result = run_code_against_tests(payload.code, tc_data)

    status = SubmissionStatus.passed if exec_result["status"] == "passed" else SubmissionStatus.failed

    submission = CodingSubmission(
        user_id=current_user.id,
        problem_id=payload.problem_id,
        code=payload.code,
        status=status,
        test_results=exec_result["test_results"],
        runtime_ms=exec_result.get("runtime_ms"),
        passed_cases=exec_result["passed_cases"],
        total_cases=exec_result["total_cases"],
    )
    db.add(submission)

    # Log activity
    activity = LearningActivity(
        user_id=current_user.id,
        activity_type="coding_submit",
        metadata_json={"problem_id": str(payload.problem_id), "status": status.value},
    )
    db.add(activity)

    await db.commit()
    await db.refresh(submission)
    return submission


@router.get("/submissions")
async def get_submissions(
    problem_id: Optional[uuid.UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(CodingSubmission).where(CodingSubmission.user_id == current_user.id)
    if problem_id:
        q = q.where(CodingSubmission.problem_id == problem_id)
    q = q.order_by(CodingSubmission.created_at.desc())

    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar() or 0

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    submissions = result.scalars().all()

    return {
        "items": [SubmissionResponse.model_validate(s) for s in submissions],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/problems/{problem_id}/solution")
async def coding_solution(
    problem_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    problem = (await db.execute(select(CodingProblem).where(CodingProblem.id == problem_id))).scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return {
        "solution_code": problem.solution_code, "explanation": problem.solution_explanation,
        "time_complexity": problem.time_complexity, "space_complexity": problem.space_complexity,
    }
