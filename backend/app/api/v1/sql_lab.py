"""
SQL Lab — executes learner queries against a read-only sandbox schema.
Never touches the main application database.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import Optional
import uuid
import time
import psycopg2
from app.core.database import get_db
from app.core.config import settings
from app.core.deps import get_current_user
from app.models.models import User, SQLProblem, LearningActivity
from app.schemas.schemas import SQLProblemResponse, SQLExecuteRequest, SQLExecuteResponse

router = APIRouter(prefix="/sql", tags=["sql"])


@router.get("/problems")
async def get_sql_problems(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    difficulty: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(SQLProblem).where(SQLProblem.is_active == True)
    if difficulty:
        q = q.where(SQLProblem.difficulty == difficulty)
    if category:
        q = q.where(SQLProblem.category == category)

    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar() or 0

    q = q.order_by(SQLProblem.difficulty, SQLProblem.title).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    problems = result.scalars().all()

    return {
        "items": [SQLProblemResponse.model_validate(p) for p in problems],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("/execute", response_model=SQLExecuteResponse)
async def execute_sql(
    payload: SQLExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = payload.query.strip()

    # Safety: only allow SELECT statements
    if not _is_safe_query(query):
        raise HTTPException(
            status_code=400,
            detail="Only SELECT statements are allowed in the SQL Lab"
        )

    try:
        result = _execute_in_sandbox(query)

        # Log activity
        activity = LearningActivity(
            user_id=current_user.id,
            activity_type="sql_execute",
            metadata_json={"query_length": len(query)},
        )
        db.add(activity)
        await db.commit()

        return result

    except HTTPException:
        raise
    except Exception as e:
        return SQLExecuteResponse(
            columns=[],
            rows=[],
            row_count=0,
            execution_time_ms=0.0,
            error=str(e),
        )


def _is_safe_query(query: str) -> bool:
    """Ensure only SELECT statements pass through."""
    normalized = query.strip().upper()
    # Strip comments
    normalized = " ".join(line for line in normalized.splitlines() if not line.strip().startswith("--"))
    keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
    first_word = normalized.split()[0] if normalized.split() else ""
    return first_word == "SELECT" and not any(kw in normalized for kw in keywords)


def _execute_in_sandbox(query: str) -> SQLExecuteResponse:
    """Execute query against the sandbox database."""
    start = time.perf_counter()

    conn = psycopg2.connect(settings.SANDBOX_DATABASE_URL)
    try:
        # Read-only transaction
        conn.set_session(readonly=True, autocommit=False)
        cursor = conn.cursor()
        cursor.execute(f"SET search_path TO sandbox; SET statement_timeout = '10s'; {query}")

        rows = cursor.fetchmany(500)  # max 500 rows
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        elapsed = (time.perf_counter() - start) * 1000

        return SQLExecuteResponse(
            columns=columns,
            rows=[list(row) for row in rows],
            row_count=len(rows),
            execution_time_ms=round(elapsed, 2),
        )
    finally:
        conn.close()
