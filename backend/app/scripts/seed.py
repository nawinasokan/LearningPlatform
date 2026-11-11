"""
Seed script: loads the curated curriculum into the database.

Content lives in ``app/content/*`` (topics + Q&A, coding problems, SQL problems) and is
upserted by slug / question text, so re-running is safe and also *updates* answers.
Rows that are no longer part of the curated content (e.g. legacy filler rows) are
deactivated rather than deleted, so learner progress is never lost.

Run via: python -m app.scripts.seed
"""
import importlib
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.models.models import (
    Base, ContentCategory, Subject, Topic, LearningContent,
    Question, QuestionAnswer, ExplanationMode, DifficultyLevel,
    CodingProblem, CodingTestCase, SQLProblem, Diagram,
)

TOPIC_MODULES = ["python", "django_flask", "fastapi_backend", "sql_db", "ai_llm",
                 "git_linux", "infra_misc", "frontend_design"]

engine = create_engine(settings.SYNC_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def seed():
    print("🌱 Starting seed...")
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        _seed_categories(db)
        _seed_subjects(db)
        _sync_curated_topics(db)
        _seed_project_topics(db)
        _sync_coding_problems(db)
        _sync_sql_problems(db)
        _seed_diagrams(db)
        db.commit()
        print("✅ Seed complete!")
    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


def _get_or_create(db: Session, model, defaults=None, **kwargs):
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    params = {**kwargs, **(defaults or {})}
    instance = model(**params)
    db.add(instance)
    db.flush()
    return instance, True


def _seed_categories(db: Session):
    categories = [
        {"name": "Core Backend", "slug": "core-backend", "description": "Python, Django, FastAPI, Flask"},
        {"name": "Databases", "slug": "databases", "description": "SQL, PostgreSQL, MongoDB"},
        {"name": "AI & LLM", "slug": "ai-llm", "description": "LLMs, AI APIs, LangChain, RAG, agents"},
        {"name": "DevOps & Cloud", "slug": "devops-cloud", "description": "Git, Linux, Docker, AWS, GCP"},
        {"name": "Frontend", "slug": "frontend", "description": "JavaScript, React"},
        {"name": "System Design", "slug": "system-design", "description": "Architecture and design patterns"},
    ]
    for c in categories:
        _get_or_create(db, ContentCategory, slug=c["slug"], defaults={"name": c["name"], "description": c["description"]})
    db.flush()
    print(f"  ✓ Categories: {len(categories)}")


def _seed_subjects(db: Session):
    cat = {c.slug: c for c in db.query(ContentCategory).all()}
    subjects_data = [
        ("Python", "python", "🐍", "#3776ab", 1, "core-backend", "Python fundamentals through advanced — data model, OOP, generators, asyncio, GIL, performance"),
        ("AI & LLM", "ai-llm", "🤖", "#8e44ad", 1, "ai-llm", "LLM fundamentals, AI APIs, prompt engineering, embeddings, RAG, LangChain, LangGraph agents, MCP, evals, production GenAI"),
        ("Django", "django", "🎸", "#092e20", 1, "core-backend", "Django MVT, ORM, DRF, middleware, signals, caching, authentication, security"),
        ("FastAPI", "fastapi", "⚡", "#009688", 1, "core-backend", "FastAPI routing, Pydantic, dependency injection, async, JWT, SQLAlchemy"),
        ("Flask", "flask", "🫙", "#000000", 2, "core-backend", "Flask application lifecycle, blueprints, REST APIs, extensions, testing"),
        ("SQL & PostgreSQL", "sql-postgresql", "🐘", "#336791", 1, "databases", "SQL fundamentals through advanced PostgreSQL: joins, CTEs, window functions, indexing, query plans"),
        ("Database Engineering", "database-engineering", "🗄️", "#ff6b35", 2, "databases", "ACID, isolation levels, locking, normalization, NoSQL, replication, sharding, MongoDB"),
        ("Backend Engineering", "backend-engineering", "🔧", "#6c3483", 2, "core-backend", "REST design, auth, JWT, RBAC, pagination, rate limiting, security, observability"),
        ("Git", "git", "🌿", "#f05032", 2, "devops-cloud", "Git internals, branching, merge vs rebase, undoing mistakes, team workflows"),
        ("Linux", "linux", "🐧", "#fcc624", 2, "devops-cloud", "Linux filesystem, permissions, processes, shell, networking, troubleshooting"),
        ("Celery & Redis", "celery-redis", "📮", "#37b24d", 3, "core-backend", "Celery task queues, workers, brokers, Redis data structures, caching, locks"),
        ("Docker", "docker-linux", "🐋", "#0db7ed", 3, "devops-cloud", "Containers, images, Dockerfile, networking, volumes, Compose, security, orchestration basics"),
        ("AWS & GCP", "aws-gcp", "☁️", "#ff9900", 4, "devops-cloud", "IAM, EC2, S3, VPC, Lambda, queues, GCP equivalents, deployment patterns"),
        ("JavaScript & React", "js-react", "⚛️", "#61dafb", 4, "frontend", "JavaScript core, async, React hooks, rendering, state management"),
        ("System Design", "system-design", "🏛️", "#7209b7", 3, "system-design", "Scalability, load balancing, caching, sharding, queues and classic design problems"),
        ("Project Deep Dive", "project-deep-dive", "🏗️", "#e63946", 5, "core-backend", "Deep dives into the author's own projects: Audio Annotation, F1 QC Audit, Smart AI Assist"),
    ]
    for name, slug, icon, color, priority, cat_slug, desc in subjects_data:
        subj, created = _get_or_create(db, Subject, slug=slug, defaults={
            "name": name, "icon": icon, "color": color, "priority": priority,
            "category_id": cat[cat_slug].id, "description": desc})
        if not created:  # keep catalogue metadata in sync with this file
            subj.name, subj.icon, subj.color, subj.priority = name, icon, color, priority
            subj.category_id, subj.description, subj.is_active = cat[cat_slug].id, desc, True
    db.flush()
    print(f"  ✓ Subjects: {len(subjects_data)}")


def _load(name):
    try:
        return importlib.import_module(f"app.content.{name}")
    except ModuleNotFoundError as e:
        if e.name == f"app.content.{name}":
            print(f"  ! content module {name} missing — skipped")
            return None
        raise


def _sync_curated_topics(db: Session):
    topics_n = questions_n = 0
    for name in TOPIC_MODULES:
        mod = _load(name)
        if not mod:
            continue
        for subject_slug, topics in mod.TOPICS.items():
            subject = db.query(Subject).filter_by(slug=subject_slug).one()
            keep_topics = set()
            for t in topics:
                topic = db.query(Topic).filter_by(subject_id=subject.id, slug=t["slug"]).first()
                fields = dict(title=t["title"], description=t.get("description"), difficulty=DifficultyLevel(t["difficulty"]),
                              order_index=t["order_index"], estimated_minutes=t["estimated_minutes"], is_active=True)
                if topic:
                    for k, v in fields.items():
                        setattr(topic, k, v)
                else:
                    topic = Topic(subject_id=subject.id, slug=t["slug"], **fields)
                    db.add(topic)
                db.flush()
                keep_topics.add(topic.id)
                _sync_topic_content(db, topic, t["content"])
                q_n = _sync_questions(db, topic, t["questions"])
                topics_n += 1
                questions_n += q_n
            # Retire topics of this subject that are no longer in the curated set (e.g. legacy filler).
            for old in db.query(Topic).filter(Topic.subject_id == subject.id, Topic.is_active == True).all():  # noqa: E712
                if old.id not in keep_topics:
                    old.is_active = False
                    for q in db.query(Question).filter_by(topic_id=old.id).all():
                        q.is_active = False
    db.flush()
    print(f"  ✓ Curated topics: {topics_n}, questions: {questions_n}")


def _sync_topic_content(db: Session, topic: Topic, c: dict):
    row = db.query(LearningContent).filter_by(topic_id=topic.id).first() or LearningContent(topic_id=topic.id)
    row.definition = c.get("definition")
    row.easy_explanation = c.get("easy_explanation")
    row.analogy = c.get("analogy")
    row.technical_explanation = c.get("technical_explanation")
    row.code_example = c.get("code_example")
    row.code_language = c.get("code_language", "python")
    row.interview_answer = c.get("interview_answer")
    db.add(row)


def _sync_questions(db: Session, topic: Topic, questions: list) -> int:
    keep = set()
    for index, q in enumerate(questions, 1):
        row = db.query(Question).filter_by(topic_id=topic.id, question_text=q["text"]).first()
        if row:
            row.difficulty, row.order_index, row.is_active = DifficultyLevel(q["difficulty"]), index, True
        else:
            row = Question(topic_id=topic.id, question_text=q["text"], difficulty=DifficultyLevel(q["difficulty"]), order_index=index)
            db.add(row)
        db.flush()
        keep.add(row.id)
        existing = {a.mode: a for a in db.query(QuestionAnswer).filter_by(question_id=row.id).all()}
        for mode_name, text in q["answers"].items():
            mode = ExplanationMode(mode_name)
            if mode in existing:
                existing[mode].answer_text = text
            else:
                db.add(QuestionAnswer(question_id=row.id, mode=mode, answer_text=text))
    for old in db.query(Question).filter_by(topic_id=topic.id, is_active=True).all():
        if old.id not in keep:
            old.is_active = False
    return len(questions)


def _sync_coding_problems(db: Session):
    mod = _load("coding_problems")
    if not mod:
        return
    keep = set()
    for p in mod.PROBLEMS:
        row = db.query(CodingProblem).filter_by(slug=p["slug"]).first() or CodingProblem(slug=p["slug"])
        row.title, row.description = p["title"], p["description"]
        row.difficulty = DifficultyLevel(p["difficulty"])
        row.category, row.starter_code, row.solution_code = p.get("category"), p.get("starter_code"), p.get("solution_code")
        row.solution_explanation = p.get("explanation")
        row.time_complexity, row.space_complexity = p.get("time_complexity"), p.get("space_complexity")
        row.hints, row.examples, row.is_active = p.get("hints"), p.get("examples"), True
        db.add(row)
        db.flush()
        keep.add(row.slug)
        db.query(CodingTestCase).filter_by(problem_id=row.id).delete()
        for i, tc in enumerate(p["test_cases"]):
            db.add(CodingTestCase(problem_id=row.id, input_data=tc["input"], expected_output=tc["expected"],
                                  is_hidden=tc.get("hidden", False), order_index=i))
    for old in db.query(CodingProblem).filter(CodingProblem.is_active == True).all():  # noqa: E712
        if old.slug not in keep:
            old.is_active = False
    db.flush()
    print(f"  ✓ Coding problems: {len(mod.PROBLEMS)}")


def _sync_sql_problems(db: Session):
    mod = _load("sql_problems")
    if not mod:
        return
    keep = set()
    for p in mod.PROBLEMS:
        row = db.query(SQLProblem).filter_by(slug=p["slug"]).first() or SQLProblem(slug=p["slug"])
        row.title, row.description = p["title"], p["description"]
        row.difficulty = DifficultyLevel(p["difficulty"])
        row.category, row.dataset_name = p.get("category"), p.get("dataset_name")
        row.expected_query, row.hints, row.explanation = p["expected_query"], p.get("hints"), p.get("explanation")
        row.is_active = True
        db.add(row)
        keep.add(row.slug)
    db.flush()
    for old in db.query(SQLProblem).filter(SQLProblem.is_active == True).all():  # noqa: E712
        if old.slug not in keep:
            old.is_active = False
    db.flush()
    print(f"  ✓ SQL problems: {len(mod.PROBLEMS)}")


def _seed_project_topics(db: Session):
    """Project deep-dive topics (author's own projects). Upsert-by-slug, create-only."""
    total_topics = 0
    total_questions = 0

    proj_subj = db.query(Subject).filter_by(slug="project-deep-dive").first()
    proj_topics = [
        {
            "title": "F1 Enterprise QC Audit — Architecture",
            "slug": "f1-architecture",
            "difficulty": DifficultyLevel.expert,
            "order_index": 1,
            "estimated_minutes": 60,
            "description": "Deep dive into the F1 QC platform's modular Django architecture, service patterns, and request lifecycle",
            "questions": [
                {
                    "text": "Describe the architecture of the F1 QC Audit & Reporting Platform.",
                    "difficulty": DifficultyLevel.expert,
                    "answers": {
                        ExplanationMode.easy: "The F1 platform is a multi-module Django app. It has modules for Excel upload, data validation, audit workflows, and 8+ report engines. It handles 150M+ rows using PostgreSQL partitioning, Celery background tasks, and Redis caching.",
                        ExplanationMode.technical: "Modular Django application with: (1) Upload module — Excel ingestion with dynamic field mapping. (2) Audit module — multi-step QC workflow. (3) Reporting engine — 8+ configurable report types with Django ORM + raw SQL for performance. (4) Dashboard — real-time aggregations cached in Redis. PostgreSQL: partitioned tables by month, composite indexes. Celery: background batch processing, report generation. Redis: dashboard cache (60s TTL), task result storage.",
                        ExplanationMode.interview: "The F1 platform started as a simple audit tool and grew to handle 150M+ rows. Architecture decisions: (1) Modular Django apps — each domain (upload, audit, reporting, dashboard) is a separate Django app with its own models, views, services. (2) Service layer — business logic in service classes, not views. Views just call services and return JSON. (3) Repository pattern — database queries in separate repository functions, making them testable. (4) PostgreSQL partitioning by month for audit_records table — required for performance at this scale. (5) Celery tasks for all long-running operations — Excel processing (5-10 min for large files) runs as background task with progress tracking via Redis. (6) Redis caching for dashboard KPIs — heavy GROUP BY aggregations cached with 60-second TTL.",
                    },
                },
                {
                    "text": "How did you achieve 78x query performance improvement in the F1 platform?",
                    "difficulty": DifficultyLevel.expert,
                    "answers": {
                        ExplanationMode.easy: "Start by measuring with EXPLAIN ANALYZE. Add the right indexes (composite indexes for multi-column queries). Partition large tables by date. Move aggregations to PostgreSQL instead of Python. Cache expensive results. The sum of all these gives dramatic improvement.",
                        ExplanationMode.technical: "Step 1: Profile with django-debug-toolbar + EXPLAIN ANALYZE. Found: Seq Scans on 150M-row tables, N+1 for related records, Python-side aggregation loops. Fixes: (1) Composite indexes on (batch_id, status, created_at). (2) Table partitioning by month — query pruned 95% of partitions. (3) Moved GROUP BY aggregation to SQL from Python. (4) Used values().annotate(Count) instead of Python loops. (5) Pagination on all list endpoints. (6) Redis cache for static reports.",
                        ExplanationMode.interview: "The 78x improvement came from several compounding fixes measured with EXPLAIN ANALYZE: (1) Found a report query doing Seq Scan on a 150M-row table — added composite index on (audit_date, department_id, status): query time 45s → 8s. (2) Added monthly RANGE partitioning on audit_date — same query now prunes to relevant partition: 8s → 0.6s. (3) Moved Python-side aggregation (looping through QuerySet) to SQL GROUP BY with annotation — eliminates data transfer. (4) Composite indexes tailored to each report's WHERE clause. (5) EXPLAIN ANALYZE revealed stale statistics on one table — ANALYZE fixed row estimates and query plan. Combined: 45s → 0.58s = 77.6x improvement. Documented each change and its measurement.",
                    },
                },
                {
                    "text": "How did you implement the Excel processing pipeline in the F1 platform?",
                    "difficulty": DifficultyLevel.expert,
                    "answers": {
                        ExplanationMode.easy: "Excel files are uploaded, validated, then processed in chunks by Celery workers. Each chunk is validated row-by-row, duplicates are detected, and valid records are bulk-inserted. Progress is tracked in Redis so users can see real-time status.",
                        ExplanationMode.technical: "Pipeline: (1) File upload → save to S3/disk, return task_id. (2) Celery task receives file path. (3) openpyxl reads in read-only mode (memory-efficient streaming). (4) Process in chunks of 1000 rows. (5) Dynamic field mapping (column headers mapped to model fields via config). (6) Row validation (types, required fields, business rules). (7) Duplicate detection via Redis set of unique keys. (8) Bulk insert via Django bulk_create(batch_size=500). (9) Progress: `cache.set(f'task:{task_id}:progress', pct)`. (10) Error rows collected, available for download as Excel.",
                        ExplanationMode.interview: "5.2x throughput improvement came from: (1) Streaming Excel reading with openpyxl read_only=True — avoids loading entire file into memory. (2) Chunked processing (1000 rows/chunk) — consistent memory footprint. (3) Bulk insert replacing row-by-row inserts: `Model.objects.bulk_create(records, batch_size=500, ignore_conflicts=True)` — reduced DB round-trips from N to N/500. (4) Duplicate detection moved from DB query to Redis SET — `SADD processed:batch:{id} {unique_key}` is O(1) vs SQL query. (5) Background Celery processing with progress tracking means UI is non-blocking. (6) Transactions per chunk — if chunk fails, only that chunk rolls back. These combined gave 5.2x throughput improvement on 100K+ row Excel files.",
                    },
                },
            ],
        },
        {
            "title": "Audio Annotation & Transcription Platform",
            "slug": "audio-annotation",
            "difficulty": DifficultyLevel.advanced,
            "order_index": 2,
            "estimated_minutes": 45,
            "description": "Django-based audio annotation system with RBAC, workflows, and transcription pipeline",
            "questions": [
                {
                    "text": "How was RBAC (Role-Based Access Control) implemented in the Audio Annotation platform?",
                    "difficulty": DifficultyLevel.advanced,
                    "answers": {
                        ExplanationMode.easy: "RBAC gives each user a role (Admin, Annotator, Reviewer). Each role has specific permissions — Annotators can annotate tasks, Reviewers can approve, Admins manage everything. The code checks the user's role before allowing any action.",
                        ExplanationMode.technical: "Implementation: Django's built-in Group + Permission system extended with custom roles. Custom User model with role field. Custom permission backend checking role-based permissions. DRF custom permission classes: `IsAnnotator(BasePermission)`, `IsReviewer`. Task assignments stored in DB with user_id and role. Middleware checks role on every request. Workflow states enforced at view level.",
                        ExplanationMode.interview: "RBAC in the annotation platform used Django's Group/Permission system as the foundation with custom extensions. Roles: Admin (full access), Project Manager (create/assign tasks), Annotator (annotate assigned tasks), Reviewer (review and approve). Implementation: (1) Extended AbstractUser with role field. (2) Custom permission classes for DRF: check user.role and task assignment. (3) Object-level permissions — annotators can only access their assigned tasks. (4) Workflow enforcement — task can only move Pending → In Progress → Review → Approved in sequence, enforced at API level. (5) Audit log on every state transition. This reduced unauthorized access and eliminated manual permission checking scattered throughout the codebase.",
                    },
                },
                {
                    "text": "How did you reduce manual annotation effort by 50% in the Audio Annotation platform?",
                    "difficulty": DifficultyLevel.expert,
                    "answers": {
                        ExplanationMode.easy: "By using AI transcription as a starting point. Instead of annotators transcribing audio from scratch, the system pre-fills a transcription using AI, and annotators only correct errors. This cuts work in half.",
                        ExplanationMode.technical: "Workflow: (1) Audio uploaded → stored (S3/filesystem). (2) Background Celery task calls transcription API (Gemini). (3) Result stored as initial annotation with status 'ai_draft'. (4) Annotator reviews AI draft, corrects errors — typically 60-70% accurate for high-quality audio. (5) Reviewer approves. Auto-translation pipeline similarly pre-fills translations. Measured: average annotation time before: 8 min/file, after: 3-4 min/file.",
                        ExplanationMode.interview: "The 50% reduction came from AI-assisted pre-annotation: instead of annotators transcribing audio from scratch, the pipeline uses transcription API to generate an initial draft. Annotators shift from 'transcription' to 'review and correction' — much faster. Architecture: upload → Celery task → transcription API → store as ai_draft → notify annotator → annotator corrects → reviewer approves. Additional optimizations: keyboard shortcuts for common corrections, batch annotation workflow for similar audio, auto-advance to next file. For this platform, Gemini API was used as the transcription backend, but the annotation tool is API-agnostic by design.",
                    },
                },
            ],
        },
        {
            "title": "Smart AI Assist — Flask Architecture",
            "slug": "smart-ai-assist",
            "difficulty": DifficultyLevel.intermediate,
            "order_index": 3,
            "estimated_minutes": 35,
            "description": "Flask SPA architecture, caching strategy, response optimization, reusable prompt layer",
            "questions": [
                {
                    "text": "How was the reusable prompt-engineering layer designed in Smart AI Assist?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Instead of writing prompt instructions in every function, a central PromptBuilder class builds prompts based on content type (email, blog, summary). This avoids repeating instructions and ensures consistent, optimized prompts across all three features.",
                        ExplanationMode.technical: "PromptTemplate class with: content_type enum (email, blog, summary). build_prompt(user_input, **context) method returns formatted prompt string. Shared system instructions extracted once. Per-type templates with placeholders. Reduces token usage by eliminating duplicate instruction text across prompt variants. Factory pattern: PromptFactory.get_template(content_type).",
                        ExplanationMode.interview: "The reusable layer solved two problems: code duplication and token waste. Architecture: `PromptTemplate` base class with shared system instructions. Subclasses: `EmailPromptTemplate`, `BlogPromptTemplate`, `SummaryPromptTemplate`. Each defines only the content-specific portion. Factory returns appropriate template by type. Benefits: (1) System instructions appear once in each template object, not repeated in every request. (2) Adding a new content type adds one class, no changes elsewhere. (3) Token optimization: 25% reduction came from removing redundant instruction text that was copy-pasted across functions. (4) Consistent tone and format across content types.",
                    },
                },
                {
                    "text": "How did you achieve under 2-second response latency in Smart AI Assist?",
                    "difficulty": DifficultyLevel.intermediate,
                    "answers": {
                        ExplanationMode.easy: "Latency was reduced through: caching repeated requests (same input → cached response), async calls (non-blocking), optimized prompts (fewer tokens), and measuring each step to find bottlenecks.",
                        ExplanationMode.technical: "Techniques: (1) Response caching with Redis — key: hash(content_type + user_input). TTL: 5 minutes for similar requests. (2) Async HTTP calls with aiohttp/httpx for API requests. (3) Token reduction via prompt templates — fewer input tokens → faster API response. (4) Streaming responses for longer content — user sees output incrementally. (5) Latency measurement: timestamps at each step, logged for analysis.",
                        ExplanationMode.interview: "Target: <2 second P95 latency. Achieved through: (1) Response caching — identical or near-identical prompts cached in Redis (SHA256 hash key). First request: ~1.5s (API call), subsequent: <50ms cache hit. (2) Async HTTP calls — non-blocking API request while Flask returns promise to frontend. (3) Prompt optimization — shorter, more precise prompts reduced API processing time. (4) Frontend: streaming display — show tokens as they arrive rather than waiting for full response. (5) Measurement: Python time.perf_counter() around each API call, logged to identify slow prompts. Result: 95th percentile latency: 1.8s including network overhead.",
                    },
                },
            ],
        },
    ]

    for topic_data in proj_topics:
        topic, created = _get_or_create(db, Topic, slug=topic_data["slug"], defaults={
            "subject_id": proj_subj.id,
            "title": topic_data["title"],
            "difficulty": topic_data["difficulty"],
            "order_index": topic_data["order_index"],
            "estimated_minutes": topic_data["estimated_minutes"],
            "description": topic_data.get("description"),
        })
        total_topics += 1

        for q_data in topic_data.get("questions", []):
            q_obj, q_created = _get_or_create(db, Question,
                topic_id=topic.id,
                question_text=q_data["text"],
                defaults={"difficulty": q_data["difficulty"]}
            )
            total_questions += 1
            if q_created:
                for mode, answer_text in q_data["answers"].items():
                    db.add(QuestionAnswer(question_id=q_obj.id, mode=mode, answer_text=answer_text))

        db.flush()

    db.flush()

    db.flush()
    print(f"  ✓ Project deep-dive topics: {total_topics}, questions: {total_questions}")



def _seed_diagrams(db: Session):
    diagrams = [
        {
            "title": "Django MVT Request Lifecycle",
            "slug": "django-mvt-lifecycle",
            "subject_slug": "django",
            "description": "Complete flow of an HTTP request through Django's MVT architecture",
            "explanation": "This diagram shows how a Django request flows from the browser through WSGI/ASGI, URL dispatcher, middleware layers, view, ORM, and back as an HTTP response.",
            "mermaid_source": """sequenceDiagram
    participant Browser
    participant Nginx
    participant Gunicorn
    participant Middleware
    participant URLDispatcher
    participant View
    participant ORM
    participant Database
    participant Template

    Browser->>Nginx: HTTP Request
    Nginx->>Gunicorn: Forward Request
    Gunicorn->>Middleware: Process Request
    Note over Middleware: SecurityMiddleware<br/>SessionMiddleware<br/>AuthenticationMiddleware<br/>CSRFMiddleware
    Middleware->>URLDispatcher: Processed Request
    URLDispatcher->>View: Route to View Function
    View->>ORM: QuerySet Operations
    ORM->>Database: SQL Query
    Database-->>ORM: Query Results
    ORM-->>View: Python Objects
    View->>Template: Render Context
    Template-->>View: HTML String
    View-->>Middleware: HttpResponse
    Middleware-->>Gunicorn: Final Response
    Gunicorn-->>Nginx: Response
    Nginx-->>Browser: HTTP Response""",
            "step_by_step": [
                "Browser sends HTTP request to Nginx (web server)",
                "Nginx forwards to Gunicorn (WSGI server) or Uvicorn (ASGI)",
                "Django creates HttpRequest object",
                "Request passes through MIDDLEWARE stack top-to-bottom (security, session, auth, CSRF)",
                "URL dispatcher matches URL pattern to view function",
                "View executes business logic, calls ORM",
                "ORM generates SQL and queries PostgreSQL",
                "Results returned as Python model instances",
                "View renders template with context OR serializes to JSON (DRF)",
                "Response passes through middleware bottom-to-top",
                "Response sent back to browser"
            ],
        },
        {
            "title": "FastAPI Dependency Injection",
            "slug": "fastapi-dependency-injection",
            "subject_slug": "fastapi",
            "description": "How FastAPI resolves and injects dependencies",
            "explanation": "FastAPI builds a dependency graph at startup and resolves dependencies in the correct order for each request.",
            "mermaid_source": """graph TD
    Request[HTTP Request] --> Router[FastAPI Router]
    Router --> DI[Dependency Injection Engine]
    
    DI --> DB[get_db\nyield AsyncSession]
    DI --> Auth[get_current_user\ndecode JWT token]
    DI --> Pagination[pagination_params\npage + page_size]
    
    Auth --> DB
    
    DB --> Session[(PostgreSQL\nAsync Session)]
    Auth --> JWT[JWT Decode\n+ User Query]
    JWT --> Session
    
    DI --> View[View Function\nreceives injected deps]
    DB --> View
    Auth --> View
    Pagination --> View
    
    View --> Response[JSON Response\nPydantic Serialized]
    
    DB --> Cleanup[Session Close\nyield cleanup]
    
    style DB fill:#009688,color:#fff
    style Auth fill:#ff5722,color:#fff
    style View fill:#3f51b5,color:#fff""",
            "step_by_step": [
                "Request arrives at FastAPI router",
                "FastAPI analyzes function signature for Depends()",
                "Builds dependency graph — resolves sub-dependencies first",
                "get_db generator: creates AsyncSession, yields to view, closes after",
                "get_current_user: extracts Bearer token, decodes JWT, queries User from DB",
                "All resolved dependencies injected as function parameters",
                "View function executes with all deps available",
                "Generator dependencies (yield) run cleanup after response"
            ],
        },
        {
            "title": "Celery Worker Architecture",
            "slug": "celery-worker-architecture",
            "subject_slug": "celery-redis",
            "description": "Celery's distributed task queue architecture with Redis broker",
            "explanation": "Tasks flow from your Django/FastAPI application through the Redis broker to Celery workers, with results stored back in Redis.",
            "mermaid_source": """flowchart LR
    App[Django/FastAPI App\nProducer] -->|task.delay| Redis[(Redis Broker\nTask Queue)]
    
    Redis -->|consume| W1[Celery Worker 1]
    Redis -->|consume| W2[Celery Worker 2]  
    Redis -->|consume| W3[Celery Worker 3]
    
    W1 -->|result| Backend[(Redis/DB\nResult Backend)]
    W2 -->|result| Backend
    W3 -->|result| Backend
    
    App -->|AsyncResult.get| Backend
    
    Beat[Celery Beat\nScheduler] -->|periodic tasks| Redis
    
    subgraph Workers
        W1
        W2
        W3
    end
    
    subgraph Queues
        HQ[high_priority queue]
        DQ[default queue]
        LQ[low_priority queue]
    end
    
    Redis --- HQ
    Redis --- DQ
    Redis --- LQ
    
    style Redis fill:#cc0000,color:#fff
    style Beat fill:#37b24d,color:#fff""",
            "step_by_step": [
                "App calls task.delay() or task.apply_async() — serializes task to JSON",
                "Task message published to Redis broker queue",
                "Celery workers poll their assigned queues",
                "Worker picks up task, deserializes, executes",
                "On success: result stored in Result Backend",
                "On failure: retried up to max_retries with exponential backoff",
                "Celery Beat sends periodic tasks on schedule",
                "App can poll task status with AsyncResult(task_id).state"
            ],
        },
        {
            "title": "SQL Index B-Tree Structure",
            "slug": "sql-btree-index",
            "subject_slug": "sql-postgresql",
            "description": "How PostgreSQL B-Tree indexes work internally",
            "explanation": "B-Tree indexes maintain sorted data in a tree structure, allowing O(log n) lookups instead of O(n) table scans.",
            "mermaid_source": """graph TD
    Root["Root Node\n[50]"] --> L1["Internal Node\n[25]"]
    Root --> L2["Internal Node\n[75]"]
    
    L1 --> LL["Leaf: 10, 15, 20"]
    L1 --> LR["Leaf: 30, 35, 40, 45"]
    
    L2 --> RL["Leaf: 55, 60, 65"]
    L2 --> RR["Leaf: 80, 85, 90, 95"]
    
    LL -->|next leaf| LR
    LR -->|next leaf| RL
    RL -->|next leaf| RR
    
    Note1["B-Tree Properties:\n- Always balanced\n- O(log n) lookup\n- Supports range scans\n- Leaves linked for sequential read"]
    
    style Root fill:#336791,color:#fff
    style L1 fill:#336791,color:#fff
    style L2 fill:#336791,color:#fff
    style LL fill:#4caf50,color:#fff
    style LR fill:#4caf50,color:#fff
    style RL fill:#4caf50,color:#fff
    style RR fill:#4caf50,color:#fff""",
            "step_by_step": [
                "Index stores column values in sorted B-Tree structure",
                "Root node contains pivot values directing search",
                "Internal nodes guide traversal — O(log n) steps to reach leaf",
                "Leaf nodes contain actual values + pointer to table row (ctid/heap pointer)",
                "Leaves are doubly linked — enables efficient range scans",
                "Query WHERE salary > 50000: traverse to 50000 in O(log n), then scan leaves sequentially",
                "Index Only Scan: if SELECT columns are all in index, never touches heap",
                "Composite index: sort by first column, then second within first"
            ],
        },
        {
            "title": "Python GIL & Threading Model",
            "slug": "python-gil-threading",
            "subject_slug": "python",
            "description": "How Python's GIL affects threading and when to use threads vs processes vs asyncio",
            "explanation": "The GIL prevents true parallel CPU execution in threads but releases during I/O, making threads useful for I/O-bound tasks.",
            "mermaid_source": """flowchart TD
    Task{Task Type?} -->|CPU-bound\nimage processing\nML computations| MP[multiprocessing\nSeparate processes\nNo GIL limitation\nTrue parallelism]
    
    Task -->|I/O-bound\nDB queries\nHTTP calls\nFile I/O| Choice{Concurrency\nStyle?}
    
    Choice -->|Multiple tasks\nAsync framework| AIO[asyncio\nSingle thread\nEvent loop\nFastAPI/Django async]
    
    Choice -->|Background tasks\nThread pool| THR[threading\nGIL releases on I/O\nGood for I/O waits]
    
    Choice -->|Background jobs\nDistributed| CEL[Celery\nSeparate processes\nRedis broker]
    
    MP --> PP[(Process Pool\nPython processes\neach with own GIL)]
    AIO --> EL[(Event Loop\nawait releases\ncontrol to loop)]
    THR --> GIL[(GIL released\nduring I/O\nSystem calls)]
    
    style Task fill:#3776ab,color:#fff
    style MP fill:#ff5722,color:#fff
    style AIO fill:#009688,color:#fff
    style CEL fill:#37b24d,color:#fff""",
            "step_by_step": [
                "GIL = mutex allowing only one thread to run Python bytecode at a time",
                "GIL is released during I/O operations (network, disk) and C extensions",
                "Threading: useful for I/O-bound tasks — threads can interleave during I/O waits",
                "Threading: NOT useful for CPU-bound tasks — GIL prevents parallel execution",
                "multiprocessing: each process has its own GIL — true CPU parallelism",
                "asyncio: single thread, cooperative multitasking — best for many concurrent I/O operations",
                "Celery: separate worker processes — bypasses GIL, handles distributed workloads",
                "Python 3.13+: experimental free-threading (no-GIL) mode available"
            ],
        },
        {
            "title": "F1 QC Audit — Excel Processing Pipeline",
            "slug": "f1-excel-pipeline",
            "subject_slug": "project-deep-dive",
            "description": "How the F1 platform processes large Excel files with Celery and PostgreSQL",
            "explanation": "The 5.2x throughput improvement came from streaming reads, chunked processing, Redis deduplication, and bulk database inserts.",
            "mermaid_source": """flowchart TD
    Upload[Excel Upload\nDjango View] -->|Save file| Storage[File Storage\nS3/Filesystem]
    Upload -->|task.delay| CeleryTask[Celery Task\nBackground Worker]
    Upload -->|Return| Response[Immediate Response\ntask_id to frontend]
    
    Storage --> CeleryTask
    CeleryTask --> ReadOnly[openpyxl\nread_only=True\nStreaming Mode]
    ReadOnly --> Headers[Parse Headers\nDynamic Field Mapping]
    Headers --> ChunkLoop[Process Chunks\n1000 rows/chunk]
    
    ChunkLoop --> Validate[Row Validation\nTypes + Business Rules]
    Validate -->|Valid| DedupCheck[Redis Dedup Check\nSADD unique_key]
    Validate -->|Invalid| ErrorLog[Collect Error Rows]
    
    DedupCheck -->|New record| BulkInsert[bulk_create\nbatch_size=500]
    DedupCheck -->|Duplicate| Skip[Skip + Log]
    
    BulkInsert --> Progress[Update Progress\ncache.set progress %]
    Progress --> ChunkLoop
    
    ChunkLoop -->|Done| Complete[Task Complete\nSend notification]
    ErrorLog --> ErrorFile[Error Report\nDownloadable Excel]
    
    style Upload fill:#2196F3,color:#fff
    style CeleryTask fill:#37b24d,color:#fff
    style BulkInsert fill:#ff5722,color:#fff
    style DedupCheck fill:#cc0000,color:#fff""",
            "step_by_step": [
                "User uploads Excel file — Django view saves to storage and triggers Celery task",
                "User receives immediate response with task_id — no waiting",
                "Celery worker opens file in streaming mode (openpyxl read_only=True) — no memory spike",
                "Headers parsed and mapped to model fields via dynamic field mapping config",
                "Process 1000 rows at a time — constant memory footprint",
                "Each row validated for types, required fields, business rules",
                "Valid rows checked for duplicates using Redis SADD (O(1) vs SQL query)",
                "Non-duplicate rows collected in batch, then bulk_create with 500 batch_size",
                "Progress updated in Redis after each chunk — frontend polls for status",
                "Error rows collected throughout, exported as Excel at end"
            ],
        },
        {
            "title": "RAG Pipeline: Ingest to Answer",
            "slug": "rag-pipeline",
            "subject_slug": "ai-llm",
            "description": "End-to-end retrieval-augmented generation: offline indexing and online question answering",
            "explanation": "RAG keeps the model frozen and gives it relevant, current context at question time. Quality depends mostly on chunking and retrieval, not on the generator.",
            "mermaid_source": """flowchart LR
    subgraph Offline[Indexing - offline]
        D[Documents] --> C[Chunk + clean]
        C --> E1[Embedding model]
        E1 --> V[(Vector DB + metadata)]
    end
    subgraph Online[Answering - per request]
        Q[User question] --> RW[Query rewrite]
        RW --> E2[Embedding model]
        E2 --> S[Top-k similarity search]
        V --> S
        S --> RR[Re-rank + filter]
        RR --> P[Prompt = instructions + context + question]
        P --> L[LLM]
        L --> A[Answer with citations]
    end""",
            "step_by_step": [
                "Load documents and split them into chunks (size/overlap tuned per content type)",
                "Embed every chunk with the same model that will embed queries; store vectors with metadata",
                "At query time rewrite/expand the question, embed it and run a top-k nearest-neighbour search",
                "Optionally combine with BM25 (hybrid) and re-rank candidates with a cross-encoder",
                "Build the prompt: system instructions, retrieved chunks, the user question",
                "The LLM answers only from the supplied context and cites the sources",
                "Evaluate retrieval (recall@k) and generation (faithfulness) separately"
            ],
        },
        {
            "title": "LangGraph Agent Loop (Tool Calling)",
            "slug": "langgraph-agent-loop",
            "subject_slug": "ai-llm",
            "description": "How an LLM agent alternates between reasoning and tool calls until it can answer",
            "explanation": "An agent is an LLM in a loop with tools and state. The graph decides after every model turn whether to run tools or finish; step limits and checkpoints keep it safe and resumable.",
            "mermaid_source": """flowchart TD
    S([START]) --> M[agent node: call LLM with messages + tool schemas]
    M --> R{tool_calls in response?}
    R -- yes --> T[tools node: run each tool, append ToolMessage]
    T --> M
    R -- no --> E([END: final answer])
    M -. checkpoint .-> CP[(Checkpointer: thread state)]
    T -. interrupt .-> H[Human approval]""",
            "step_by_step": [
                "State holds the message list (with a reducer that appends)",
                "The agent node sends messages and tool schemas to the model",
                "If the model returns tool calls, the conditional edge routes to the tools node",
                "The tools node executes the calls and appends results as tool messages",
                "Control returns to the agent node; the loop ends when no tool call is returned",
                "A recursion/step limit prevents infinite loops; a checkpointer persists state per thread",
                "Risky tools can pause the graph for human approval via an interrupt"
            ],
        },
        {
            "title": "Git: Working Tree, Index and Repository",
            "slug": "git-three-areas",
            "subject_slug": "git",
            "description": "Where changes live as they move through add, commit, push and pull",
            "explanation": "Git tracks content in three local areas plus remotes. Most confusing commands (reset, restore, stash) are just moves between these areas.",
            "mermaid_source": """flowchart LR
    WT[Working tree] -- git add --> IDX[Index / staging area]
    IDX -- git commit --> LOCAL[Local repository]
    LOCAL -- git push --> REMOTE[(Remote origin)]
    REMOTE -- git fetch --> LOCAL
    LOCAL -- git checkout / switch / restore --> WT
    REMOTE -- git pull = fetch + merge or rebase --> WT""",
            "step_by_step": [
                "Edit files in the working tree",
                "git add copies the chosen changes into the index (the next commit snapshot)",
                "git commit stores the snapshot as a commit object and moves the current branch pointer",
                "git push uploads commits and updates the remote branch if it is a fast-forward",
                "git fetch downloads remote commits without touching your files; git pull then integrates them",
                "git restore --staged unstages; git restore discards working-tree edits; git reset moves the branch"
            ],
        },
    ]

    count = 0
    for d_data in diagrams:
        _get_or_create(db, Diagram, slug=d_data["slug"], defaults={
            "title": d_data["title"],
            "subject_slug": d_data.get("subject_slug"),
            "description": d_data.get("description"),
            "mermaid_source": d_data["mermaid_source"],
            "explanation": d_data.get("explanation"),
            "step_by_step": d_data.get("step_by_step"),
        })
        count += 1

    db.flush()
    print(f"  ✓ Diagrams: {count}")


if __name__ == "__main__":
    seed()
