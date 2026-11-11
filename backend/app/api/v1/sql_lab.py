"""
SQL Lab — executes learner queries against a read-only sandbox schema.
Never touches the main application database.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import Optional
import re
import uuid
import time
import psycopg2
from app.core.database import get_db
from app.core.config import settings
from app.core.deps import get_current_user
from app.models.models import User, SQLProblem, LearningActivity
from app.schemas.schemas import SQLProblemResponse, SQLExecuteRequest, SQLExecuteResponse
from decimal import Decimal

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


def _strip_literals_and_comments(query: str) -> str:
    """Remove comments and quoted text so structural checks see only SQL syntax."""
    out, i, n = [], 0, len(query)
    while i < n:
        two = query[i:i + 2]
        if two == "--":
            j = query.find("\n", i)
            i = n if j == -1 else j
        elif two == "/*":
            j = query.find("*/", i + 2)
            i = n if j == -1 else j + 2
            out.append(" ")
        elif query[i] in ("'", '"'):
            quote = query[i]
            i += 1
            while i < n:
                if query[i] == quote:
                    if query[i + 1:i + 2] == quote:  # doubled quote escape
                        i += 2
                        continue
                    break
                i += 1
            i += 1
            out.append(" ")
        elif query[i] == "$" and re.match(r"\$[A-Za-z_]*\$", query[i:]):
            raise ValueError("Dollar-quoted strings are not allowed in the SQL Lab")
        else:
            out.append(query[i])
            i += 1
    return "".join(out)


_ALLOWED_FIRST = {"SELECT", "WITH", "EXPLAIN", "VALUES", "TABLE"}
_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE|COPY|DO|CALL|SET|RESET|"
    r"LOCK|VACUUM|ANALYZE|REINDEX|CLUSTER|REFRESH|LISTEN|NOTIFY|PREPARE|EXECUTE|DISCARD|"
    r"COMMIT|ROLLBACK|BEGIN|SAVEPOINT|INTO|PG_[A-Z_]+|LO_[A-Z_]+|DBLINK[A-Z_]*|CURRENT_SETTING|SET_CONFIG)\b",
    re.IGNORECASE,
)


def _is_safe_query(query: str) -> bool:
    """Structural guard: one read-only statement. The DB role is the real security boundary."""
    try:
        cleaned = _strip_literals_and_comments(query).strip()
    except ValueError:
        return False
    cleaned = cleaned.rstrip(";").strip()
    if not cleaned or ";" in cleaned:
        return False
    first = cleaned.split(None, 1)[0].upper()
    if first not in _ALLOWED_FIRST:
        return False
    # EXPLAIN ANALYZE would execute the statement; plain EXPLAIN is fine.
    if first == "EXPLAIN" and re.search(r"\bANALYZE\b", cleaned, re.IGNORECASE):
        return False
    body = re.sub(r"^EXPLAIN\b", "", cleaned, flags=re.IGNORECASE)
    return not _FORBIDDEN.search(body)


def _execute_in_sandbox(query: str) -> SQLExecuteResponse:
    """Execute one query against the sandbox DB as a restricted read-only role."""
    start = time.perf_counter()
    conn = psycopg2.connect(settings.SANDBOX_DATABASE_URL, options="-c statement_timeout=5000 -c search_path=sandbox")
    try:
        conn.set_session(readonly=True, autocommit=False)
        cursor = conn.cursor()
        cursor.execute(query.strip().rstrip(";"))
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
        conn.rollback()
        conn.close()


def _normalise(value):
    if isinstance(value, Decimal):
        return round(float(value), 2)
    if isinstance(value, float):
        return round(value, 2)
    return None if value is None else str(value) if not isinstance(value, (int, str, bool)) else value


def _is_ordered(sql: str) -> bool:
    """Heuristic: the reference query sorts at its top level (ORDER BY after the last closing paren)."""
    cleaned = _strip_literals_and_comments(sql).lower()
    tail = cleaned[cleaned.rfind(")") + 1:]
    return "order by" in tail


def _rows(result):
    return [tuple(_normalise(c) for c in row) for row in result.rows]


@router.post("/check")
async def check_sql(
    payload: SQLExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run the learner's query and the reference query; compare result sets (values, not column aliases)."""
    if payload.problem_id is None:
        raise HTTPException(status_code=400, detail="problem_id is required")
    problem = (await db.execute(select(SQLProblem).where(SQLProblem.id == payload.problem_id))).scalar_one_or_none()
    if not problem or not problem.expected_query:
        raise HTTPException(status_code=404, detail="This problem has no reference solution")
    query = payload.query.strip()
    if not _is_safe_query(query):
        raise HTTPException(status_code=400, detail="Only a single read-only SELECT statement is allowed")
    try:
        mine = _execute_in_sandbox(query)
    except Exception as exc:  # syntax errors etc. are feedback, not server errors
        return {"correct": False, "message": f"Your query failed: {str(exc).splitlines()[0]}"}
    expected = _execute_in_sandbox(problem.expected_query)

    mine_rows, expected_rows = _rows(mine), _rows(expected)
    ordered = _is_ordered(problem.expected_query)
    if len(mine.columns) != len(expected.columns):
        msg = f"Expected {len(expected.columns)} column(s) but your query returned {len(mine.columns)}."
        correct = False
    elif len(mine_rows) != len(expected_rows):
        msg = f"Expected {len(expected_rows)} row(s) but your query returned {len(mine_rows)}."
        correct = False
    else:
        key = lambda r: tuple((v is None, str(v)) for v in r)  # noqa: E731
        a, b = (mine_rows, expected_rows) if ordered else (sorted(mine_rows, key=key), sorted(expected_rows, key=key))
        correct = a == b
        msg = "Correct — your result matches the reference solution." if correct else (
            "Right shape, but some values differ" + (" (row order matters for this problem)." if ordered else "."))
    return {"correct": correct, "message": msg, "expected_row_count": len(expected_rows), "row_count": len(mine_rows)}


@router.get("/problems/{problem_id}/solution")
async def sql_solution(
    problem_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    problem = (await db.execute(select(SQLProblem).where(SQLProblem.id == problem_id))).scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return {"query": problem.expected_query, "explanation": problem.explanation}
