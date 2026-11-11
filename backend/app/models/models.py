"""
All SQLAlchemy ORM models for Interview Academy.
25 tables as per the architecture specification.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Text, Boolean, Integer, Float, DateTime, ForeignKey,
    UniqueConstraint, Index, Enum as SAEnum, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core.database import Base

import enum


def now_utc():
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class DifficultyLevel(str, enum.Enum):
    beginner = "beginner"
    practical = "practical"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class ExplanationMode(str, enum.Enum):
    easy = "easy"
    technical = "technical"
    interview = "interview"


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    passed = "passed"
    failed = "failed"
    error = "error"


class RevisionStatus(str, enum.Enum):
    due = "due"
    completed = "completed"
    skipped = "skipped"


# ─────────────────────────────────────────────
# 1. users
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relationships
    resumes: Mapped[List["Resume"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    learning_progress: Mapped[List["LearningProgress"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    user_answers: Mapped[List["UserAnswer"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    bookmarks: Mapped[List["QuestionBookmark"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    daily_plans: Mapped[List["DailyPlan"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    revision_schedules: Mapped[List["RevisionSchedule"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    activities: Mapped[List["LearningActivity"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    coding_submissions: Mapped[List["CodingSubmission"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# 2. resumes
# ─────────────────────────────────────────────
class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped["User"] = relationship(back_populates="resumes")
    skills: Mapped[List["ResumeSkill"]] = relationship(back_populates="resume", cascade="all, delete-orphan")
    projects: Mapped[List["ResumeProject"]] = relationship(back_populates="resume", cascade="all, delete-orphan")
    facts: Mapped[List["ResumeFact"]] = relationship(back_populates="resume", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# 3. resume_skills
# ─────────────────────────────────────────────
class ResumeSkill(Base):
    __tablename__ = "resume_skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    proficiency: Mapped[Optional[str]] = mapped_column(String(50))
    subject_slug: Mapped[Optional[str]] = mapped_column(String(100))  # maps to subjects.slug
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    resume: Mapped["Resume"] = relationship(back_populates="skills")


# ─────────────────────────────────────────────
# 4. resume_projects
# ─────────────────────────────────────────────
class ResumeProject(Base):
    __tablename__ = "resume_projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    technologies: Mapped[Optional[dict]] = mapped_column(JSONB)
    achievements: Mapped[Optional[dict]] = mapped_column(JSONB)
    subject_slug: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    resume: Mapped["Resume"] = relationship(back_populates="projects")


# ─────────────────────────────────────────────
# 5. resume_facts
# ─────────────────────────────────────────────
class ResumeFact(Base):
    __tablename__ = "resume_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    fact_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    resume: Mapped["Resume"] = relationship(back_populates="facts")


# ─────────────────────────────────────────────
# 6. content_categories
# ─────────────────────────────────────────────
class ContentCategory(Base):
    __tablename__ = "content_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    subjects: Mapped[List["Subject"]] = relationship(back_populates="category")


# ─────────────────────────────────────────────
# 7. subjects
# ─────────────────────────────────────────────
class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("content_categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[Optional[str]] = mapped_column(String(50))
    color: Mapped[Optional[str]] = mapped_column(String(20))
    priority: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    category: Mapped[Optional["ContentCategory"]] = relationship(back_populates="subjects")
    topics: Mapped[List["Topic"]] = relationship(back_populates="subject", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_subjects_slug", "slug"),)


# ─────────────────────────────────────────────
# 8. topics
# ─────────────────────────────────────────────
class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    difficulty: Mapped[DifficultyLevel] = mapped_column(SAEnum(DifficultyLevel), default=DifficultyLevel.beginner)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    subject: Mapped["Subject"] = relationship(back_populates="topics")
    subtopics: Mapped[List["Subtopic"]] = relationship(back_populates="topic", cascade="all, delete-orphan")
    content: Mapped[List["LearningContent"]] = relationship(back_populates="topic", cascade="all, delete-orphan")
    questions: Mapped[List["Question"]] = relationship(back_populates="topic")
    prerequisites_as_topic: Mapped[List["TopicPrerequisite"]] = relationship(
        "TopicPrerequisite", foreign_keys="TopicPrerequisite.topic_id", back_populates="topic"
    )
    prerequisites_as_prereq: Mapped[List["TopicPrerequisite"]] = relationship(
        "TopicPrerequisite", foreign_keys="TopicPrerequisite.prerequisite_id", back_populates="prerequisite"
    )
    learning_progress: Mapped[List["LearningProgress"]] = relationship(back_populates="topic")
    revision_schedules: Mapped[List["RevisionSchedule"]] = relationship(back_populates="topic")

    __table_args__ = (
        UniqueConstraint("subject_id", "slug", name="uq_topic_subject_slug"),
        Index("idx_topics_subject_id", "subject_id"),
    )


# ─────────────────────────────────────────────
# 9. subtopics
# ─────────────────────────────────────────────
class Subtopic(Base):
    __tablename__ = "subtopics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    topic: Mapped["Topic"] = relationship(back_populates="subtopics")
    content: Mapped[List["LearningContent"]] = relationship(back_populates="subtopic")


# ─────────────────────────────────────────────
# 10. topic_prerequisites
# ─────────────────────────────────────────────
class TopicPrerequisite(Base):
    __tablename__ = "topic_prerequisites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    prerequisite_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    topic: Mapped["Topic"] = relationship("Topic", foreign_keys=[topic_id], back_populates="prerequisites_as_topic")
    prerequisite: Mapped["Topic"] = relationship("Topic", foreign_keys=[prerequisite_id], back_populates="prerequisites_as_prereq")

    __table_args__ = (
        UniqueConstraint("topic_id", "prerequisite_id", name="uq_topic_prereq"),
    )


# ─────────────────────────────────────────────
# 11. learning_content
# ─────────────────────────────────────────────
class LearningContent(Base):
    __tablename__ = "learning_content"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    subtopic_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("subtopics.id", ondelete="SET NULL"), nullable=True)
    # Content stored as structured JSONB
    definition: Mapped[Optional[str]] = mapped_column(Text)
    easy_explanation: Mapped[Optional[str]] = mapped_column(Text)
    analogy: Mapped[Optional[str]] = mapped_column(Text)
    technical_explanation: Mapped[Optional[str]] = mapped_column(Text)
    internal_working: Mapped[Optional[str]] = mapped_column(Text)
    code_example: Mapped[Optional[str]] = mapped_column(Text)
    code_language: Mapped[Optional[str]] = mapped_column(String(50), default="python")
    step_by_step: Mapped[Optional[dict]] = mapped_column(JSONB)  # list of steps
    use_cases: Mapped[Optional[dict]] = mapped_column(JSONB)
    common_mistakes: Mapped[Optional[dict]] = mapped_column(JSONB)
    interview_answer: Mapped[Optional[str]] = mapped_column(Text)
    follow_up_questions: Mapped[Optional[dict]] = mapped_column(JSONB)
    practice_exercises: Mapped[Optional[dict]] = mapped_column(JSONB)
    revision_notes: Mapped[Optional[str]] = mapped_column(Text)
    diagram_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("diagrams.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    topic: Mapped["Topic"] = relationship(back_populates="content")
    subtopic: Mapped[Optional["Subtopic"]] = relationship(back_populates="content")


# ─────────────────────────────────────────────
# 12. diagrams
# ─────────────────────────────────────────────
class Diagram(Base):
    __tablename__ = "diagrams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    mermaid_source: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    step_by_step: Mapped[Optional[dict]] = mapped_column(JSONB)
    subject_slug: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


# ─────────────────────────────────────────────
# 13. question_tags
# ─────────────────────────────────────────────
class QuestionTag(Base):
    __tablename__ = "question_tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    tag_mappings: Mapped[List["QuestionTagMapping"]] = relationship(back_populates="tag")


# ─────────────────────────────────────────────
# 14. questions
# ─────────────────────────────────────────────
class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[DifficultyLevel] = mapped_column(SAEnum(DifficultyLevel), default=DifficultyLevel.intermediate)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    topic: Mapped["Topic"] = relationship(back_populates="questions")
    answers: Mapped[List["QuestionAnswer"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    tag_mappings: Mapped[List["QuestionTagMapping"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    user_answers: Mapped[List["UserAnswer"]] = relationship(back_populates="question")
    bookmarks: Mapped[List["QuestionBookmark"]] = relationship(back_populates="question", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_questions_topic_id", "topic_id"),)


# ─────────────────────────────────────────────
# 15. question_answers
# ─────────────────────────────────────────────
class QuestionAnswer(Base):
    __tablename__ = "question_answers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    mode: Mapped[ExplanationMode] = mapped_column(SAEnum(ExplanationMode), nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    code_example: Mapped[Optional[str]] = mapped_column(Text)
    key_points: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    question: Mapped["Question"] = relationship(back_populates="answers")

    __table_args__ = (
        UniqueConstraint("question_id", "mode", name="uq_question_mode"),
    )


# ─────────────────────────────────────────────
# 16. question_tag_mappings
# ─────────────────────────────────────────────
class QuestionTagMapping(Base):
    __tablename__ = "question_tag_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("question_tags.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    question: Mapped["Question"] = relationship(back_populates="tag_mappings")
    tag: Mapped["QuestionTag"] = relationship(back_populates="tag_mappings")

    __table_args__ = (
        UniqueConstraint("question_id", "tag_id", name="uq_question_tag"),
    )


# ─────────────────────────────────────────────
# 17. coding_problems
# ─────────────────────────────────────────────
class CodingProblem(Base):
    __tablename__ = "coding_problems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("topics.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[DifficultyLevel] = mapped_column(SAEnum(DifficultyLevel), default=DifficultyLevel.intermediate)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    starter_code: Mapped[Optional[str]] = mapped_column(Text)
    solution_code: Mapped[Optional[str]] = mapped_column(Text)
    solution_explanation: Mapped[Optional[str]] = mapped_column(Text)
    optimized_solution: Mapped[Optional[str]] = mapped_column(Text)
    hints: Mapped[Optional[dict]] = mapped_column(JSONB)
    time_complexity: Mapped[Optional[str]] = mapped_column(String(100))
    space_complexity: Mapped[Optional[str]] = mapped_column(String(100))
    constraints: Mapped[Optional[str]] = mapped_column(Text)
    examples: Mapped[Optional[dict]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    test_cases: Mapped[List["CodingTestCase"]] = relationship(back_populates="problem", cascade="all, delete-orphan")
    submissions: Mapped[List["CodingSubmission"]] = relationship(back_populates="problem")


# ─────────────────────────────────────────────
# 18. coding_test_cases
# ─────────────────────────────────────────────
class CodingTestCase(Base):
    __tablename__ = "coding_test_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=False, index=True)
    input_data: Mapped[Optional[str]] = mapped_column(Text)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    problem: Mapped["CodingProblem"] = relationship(back_populates="test_cases")


# ─────────────────────────────────────────────
# 19. coding_submissions
# ─────────────────────────────────────────────
class CodingSubmission(Base):
    __tablename__ = "coding_submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    problem_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(SAEnum(SubmissionStatus), default=SubmissionStatus.pending)
    test_results: Mapped[Optional[dict]] = mapped_column(JSONB)
    runtime_ms: Mapped[Optional[float]] = mapped_column(Float)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0)
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped["User"] = relationship(back_populates="coding_submissions")
    problem: Mapped["CodingProblem"] = relationship(back_populates="submissions")


# ─────────────────────────────────────────────
# 20. sql_problems
# ─────────────────────────────────────────────
class SQLProblem(Base):
    __tablename__ = "sql_problems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[DifficultyLevel] = mapped_column(SAEnum(DifficultyLevel), default=DifficultyLevel.intermediate)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    dataset_name: Mapped[Optional[str]] = mapped_column(String(100))
    expected_query: Mapped[Optional[str]] = mapped_column(Text)
    hints: Mapped[Optional[dict]] = mapped_column(JSONB)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


# ─────────────────────────────────────────────
# 21. learning_progress
# ─────────────────────────────────────────────
class LearningProgress(Base):
    __tablename__ = "learning_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    is_started: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completion_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    questions_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    time_spent_minutes: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user: Mapped["User"] = relationship(back_populates="learning_progress")
    topic: Mapped["Topic"] = relationship(back_populates="learning_progress")

    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_user_topic_progress"),
        Index("idx_learning_progress_user", "user_id"),
    )


# ─────────────────────────────────────────────
# 22. user_answers
# ─────────────────────────────────────────────
class UserAnswer(Base):
    __tablename__ = "user_answers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    mode_viewed: Mapped[Optional[ExplanationMode]] = mapped_column(SAEnum(ExplanationMode))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    self_rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user: Mapped["User"] = relationship(back_populates="user_answers")
    question: Mapped["Question"] = relationship(back_populates="user_answers")

    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_question"),
    )


# ─────────────────────────────────────────────
# 23. question_bookmarks
# ─────────────────────────────────────────────
class QuestionBookmark(Base):
    __tablename__ = "question_bookmarks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped["User"] = relationship(back_populates="bookmarks")
    question: Mapped["Question"] = relationship(back_populates="bookmarks")

    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_bookmark"),
    )


# ─────────────────────────────────────────────
# 24. flashcards
# ─────────────────────────────────────────────
class Flashcard(Base):
    __tablename__ = "flashcards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


# ─────────────────────────────────────────────
# 25. revision_schedules (SM-2 spaced repetition)
# ─────────────────────────────────────────────
class RevisionSchedule(Base):
    __tablename__ = "revision_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    easiness_factor: Mapped[float] = mapped_column(Float, default=2.5)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[RevisionStatus] = mapped_column(SAEnum(RevisionStatus), default=RevisionStatus.due)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user: Mapped["User"] = relationship(back_populates="revision_schedules")
    topic: Mapped["Topic"] = relationship(back_populates="revision_schedules")

    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_user_topic_revision"),
        Index("idx_revision_due_date", "due_date"),
    )


# ─────────────────────────────────────────────
# 26. daily_plans
# ─────────────────────────────────────────────
class DailyPlan(Base):
    __tablename__ = "daily_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    topics: Mapped[Optional[dict]] = mapped_column(JSONB)  # list of topic ids + types
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped["User"] = relationship(back_populates="daily_plans")

    __table_args__ = (
        UniqueConstraint("user_id", "plan_date", name="uq_user_daily_plan"),
    )


# ─────────────────────────────────────────────
# 27. learning_activities  (time-series log)
# ─────────────────────────────────────────────
class LearningActivity(Base):
    __tablename__ = "learning_activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # topic_view, question_complete, coding_submit, sql_execute
    subject_slug: Mapped[Optional[str]] = mapped_column(String(100))
    topic_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    # ``metadata`` is reserved by SQLAlchemy's Declarative API; keep the DB
    # column name while exposing a safe Python attribute.
    metadata_json: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)

    user: Mapped["User"] = relationship(back_populates="activities")

    __table_args__ = (
        Index("idx_activities_user_date", "user_id", "created_at"),
    )
