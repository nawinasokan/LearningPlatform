from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID
from app.models.models import DifficultyLevel, ExplanationMode, SubmissionStatus, RevisionStatus


# ─── Auth ───────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    full_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Resume ─────────────────────────────────────────────────
class ResumeSkillSchema(BaseModel):
    id: UUID
    skill_name: str
    category: Optional[str]
    proficiency: Optional[str]
    subject_slug: Optional[str]

    model_config = {"from_attributes": True}


class ResumeProjectSchema(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    technologies: Optional[Dict[str, Any]]
    achievements: Optional[Dict[str, Any]]
    subject_slug: Optional[str]

    model_config = {"from_attributes": True}


class ResumeFactSchema(BaseModel):
    id: UUID
    category: str
    fact_text: str
    is_verified: bool

    model_config = {"from_attributes": True}


class ResumeResponse(BaseModel):
    id: UUID
    version: int
    filename: str
    is_latest: bool
    created_at: datetime
    skills: List[ResumeSkillSchema] = []
    projects: List[ResumeProjectSchema] = []
    facts: List[ResumeFactSchema] = []

    model_config = {"from_attributes": True}


class ResumeSkillInput(BaseModel):
    skill_name: str = Field(min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=100)
    proficiency: Optional[str] = Field(default=None, max_length=50)
    subject_slug: Optional[str] = Field(default=None, max_length=100)


class ResumeProjectInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    technologies: Optional[Dict[str, Any]] = None
    achievements: Optional[Dict[str, Any]] = None
    subject_slug: Optional[str] = Field(default=None, max_length=100)


class NewFactInput(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    fact_text: str = Field(min_length=1, max_length=2000)


class ResumeUpdateRequest(BaseModel):
    skills: Optional[List[ResumeSkillInput]] = None
    projects: Optional[List[ResumeProjectInput]] = None
    new_facts: Optional[List[NewFactInput]] = None


class FactUpdateRequest(BaseModel):
    fact_text: Optional[str] = None
    is_verified: Optional[bool] = None


# ─── Subjects & Topics ──────────────────────────────────────
class SubjectResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    priority: int
    topic_count: int = 0
    progress_percentage: float = 0.0

    model_config = {"from_attributes": True}


class TopicResponse(BaseModel):
    id: UUID
    subject_id: UUID
    title: str
    slug: str
    description: Optional[str]
    difficulty: DifficultyLevel
    order_index: int
    estimated_minutes: int
    is_completed: bool = False
    completion_percentage: float = 0.0

    model_config = {"from_attributes": True}


class LearningContentResponse(BaseModel):
    id: UUID
    definition: Optional[str]
    easy_explanation: Optional[str]
    analogy: Optional[str]
    technical_explanation: Optional[str]
    internal_working: Optional[str]
    code_example: Optional[str]
    code_language: Optional[str]
    step_by_step: Optional[List[Any]]
    use_cases: Optional[List[Any]]
    common_mistakes: Optional[List[Any]]
    interview_answer: Optional[str]
    follow_up_questions: Optional[List[str]]
    practice_exercises: Optional[List[Any]]
    revision_notes: Optional[str]

    model_config = {"from_attributes": True}


class TopicDetailResponse(TopicResponse):
    content: Optional[LearningContentResponse] = None
    question_count: int = 0


# ─── Questions ──────────────────────────────────────────────
class QuestionAnswerSchema(BaseModel):
    id: UUID
    mode: ExplanationMode
    answer_text: str
    code_example: Optional[str]
    key_points: Optional[List[str]]

    model_config = {"from_attributes": True}


class QuestionResponse(BaseModel):
    id: UUID
    topic_id: UUID
    question_text: str
    difficulty: DifficultyLevel
    order_index: int
    is_completed: bool = False
    is_bookmarked: bool = False

    model_config = {"from_attributes": True}


class QuestionDetailResponse(QuestionResponse):
    answers: List[QuestionAnswerSchema] = []


class CompleteQuestionRequest(BaseModel):
    mode_viewed: Optional[ExplanationMode] = None
    self_rating: Optional[int] = Field(None, ge=1, le=5)


# ─── Coding ─────────────────────────────────────────────────
class CodingProblemResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str
    difficulty: DifficultyLevel
    category: Optional[str]
    starter_code: Optional[str]
    hints: Optional[List[str]]
    time_complexity: Optional[str]
    space_complexity: Optional[str]
    constraints: Optional[str]
    examples: Optional[List[Any]]
    is_solved: bool = False

    model_config = {"from_attributes": True}


class CodeRunRequest(BaseModel):
    code: str
    problem_id: UUID


class CodeSubmitRequest(BaseModel):
    code: str
    problem_id: UUID


class TestResultSchema(BaseModel):
    test_case_index: int
    passed: bool
    input_data: Optional[str]
    expected_output: str
    actual_output: Optional[str]
    error: Optional[str]
    runtime_ms: Optional[float]


class CodeRunResponse(BaseModel):
    status: str
    test_results: List[TestResultSchema]
    passed_cases: int
    total_cases: int
    runtime_ms: Optional[float]
    error: Optional[str]


class SubmissionResponse(BaseModel):
    id: UUID
    problem_id: UUID
    status: SubmissionStatus
    passed_cases: int
    total_cases: int
    runtime_ms: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── SQL Lab ────────────────────────────────────────────────
class SQLProblemResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str
    difficulty: DifficultyLevel
    category: Optional[str]
    dataset_name: Optional[str]
    hints: Optional[List[str]]

    model_config = {"from_attributes": True}


class SQLExecuteRequest(BaseModel):
    query: str
    problem_id: Optional[UUID] = None


class SQLExecuteResponse(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time_ms: float
    error: Optional[str] = None


# ─── Diagrams ───────────────────────────────────────────────
class DiagramResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    description: Optional[str]
    mermaid_source: str
    explanation: Optional[str]
    step_by_step: Optional[List[Any]]
    subject_slug: Optional[str]

    model_config = {"from_attributes": True}


# ─── Analytics ──────────────────────────────────────────────
class SubjectProgressSchema(BaseModel):
    subject_id: UUID
    subject_name: str
    slug: str
    color: Optional[str]
    total_topics: int
    completed_topics: int
    progress_percentage: float
    questions_completed: int
    total_questions: int


class DashboardResponse(BaseModel):
    overall_progress: float
    total_topics: int
    completed_topics: int
    questions_completed: int
    total_questions: int
    coding_solved: int
    sql_completed: int
    streak_days: int
    subjects: List[SubjectProgressSchema]
    weak_topics: List[TopicResponse]
    recently_studied: List[TopicResponse]
    due_for_revision: int


class ActivityHistorySchema(BaseModel):
    date: str
    activities: int
    minutes: int


# ─── Revision ───────────────────────────────────────────────
class RevisionItemResponse(BaseModel):
    id: UUID
    topic_id: UUID
    topic_title: str
    subject_name: str
    due_date: datetime
    interval_days: int
    repetitions: int

    model_config = {"from_attributes": True}


class CompleteRevisionRequest(BaseModel):
    self_rating: int = Field(ge=1, le=5)


# ─── Bookmarks ──────────────────────────────────────────────
class BookmarkResponse(BaseModel):
    id: UUID
    question_id: UUID
    question_text: str
    topic_title: str
    subject_name: str
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AddBookmarkRequest(BaseModel):
    question_id: UUID
    notes: Optional[str] = None


# ─── Pagination ─────────────────────────────────────────────
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
