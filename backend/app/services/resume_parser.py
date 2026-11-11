"""
Deterministic resume parser for PDF and DOCX files.
Extracts text using PyPDF2 / python-docx, then uses
keyword matching to identify skills, projects, and facts.
No external AI API is called.
"""
import re
import os
from typing import Dict, List, Any

# Skill keyword → category mapping
SKILL_CATEGORIES = {
    # Python
    "python": ("Python", "python"),
    "django": ("Django", "django"),
    "fastapi": ("FastAPI", "fastapi"),
    "flask": ("Flask", "flask"),
    "celery": ("Celery & Redis", "celery-redis"),
    "redis": ("Celery & Redis", "celery-redis"),
    # DB
    "postgresql": ("Databases", "sql-postgresql"),
    "postgres": ("Databases", "sql-postgresql"),
    "mysql": ("Databases", "database-engineering"),
    "mongodb": ("Databases", "database-engineering"),
    "sqlite": ("Databases", "database-engineering"),
    "sqlalchemy": ("Python", "fastapi"),
    # DevOps
    "docker": ("DevOps", "docker-linux"),
    "aws": ("Cloud", "aws-gcp"),
    "ec2": ("Cloud", "aws-gcp"),
    "s3": ("Cloud", "aws-gcp"),
    "gcp": ("Cloud", "aws-gcp"),
    "linux": ("DevOps", "docker-linux"),
    "nginx": ("DevOps", "docker-linux"),
    "git": ("Tools", None),
    "github": ("Tools", None),
    # Frontend
    "javascript": ("Frontend", "js-react"),
    "react": ("Frontend", "js-react"),
    "bootstrap": ("Frontend", "js-react"),
    "html": ("Frontend", None),
    "css": ("Frontend", None),
    # Backend
    "rest api": ("Backend", "backend-engineering"),
    "jwt": ("Backend", "backend-engineering"),
    "oauth": ("Backend", "backend-engineering"),
}

# Project headings are detected from the uploaded text only (nothing is injected).
PROJECT_TITLE_RE = re.compile(
    r"^\s*[-•*]?\s*([A-Z][A-Za-z0-9&/ ,'\-]{3,80}(?:Platform|Application|App|System|Assist|Portal|Tool|Engine|Dashboard))\s*(?:[:\-–—|(].*)?$"
)
# A line is a "fact" when it states a measurable result or a credential.
METRIC_RE = re.compile(r"(\d+(?:\.\d+)?\s*(?:%|x\b|[KMB]\+|\+|ms\b|seconds?\b|rows?\b|users?\b|records?\b))", re.I)
EDUCATION_RE = re.compile(r"\b(bachelor|master|b\.?e\.?|b\.?tech|m\.?tech|b\.?sc|m\.?sc|mba|cgpa|gpa|university|college)\b", re.I)
AWARD_RE = re.compile(r"\b(award|winner|rank(?:ed)?|scholarship|certified|certification)\b", re.I)
EXPERIENCE_RE = re.compile(r"\b(developer|engineer|intern|analyst|consultant|architect|lead)\b.{0,80}\b(?:19|20)\d{2}\b", re.I)


def parse_resume(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Extract structured information from a resume file.
    Returns dict with keys: raw_text, skills, projects, facts.
    """
    raw_text = _extract_text(file_path, filename)
    skills = _extract_skills(raw_text)
    projects = _extract_projects(raw_text)
    facts = _extract_facts(raw_text)

    return {
        "raw_text": raw_text,
        "skills": skills,
        "projects": projects,
        "facts": facts,
    }


def _extract_text(file_path: str, filename: str) -> str:
    """Extract plain text from PDF or DOCX."""
    if filename.lower().endswith(".pdf"):
        return _extract_pdf(file_path)
    elif filename.lower().endswith(".docx"):
        return _extract_docx(file_path)
    return ""


def _extract_pdf(file_path: str) -> str:
    try:
        import PyPDF2
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        return f"[PDF extraction error: {e}]"


def _extract_docx(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs)
    except Exception as e:
        return f"[DOCX extraction error: {e}]"


def _lines(text: str) -> List[str]:
    return [re.sub(r"\s+", " ", ln).strip(" \t•*-–") for ln in text.splitlines() if ln.strip()]


def _skill_hits(text: str) -> Dict[str, Dict]:
    """Whole-word keyword matches (so 's3' never matches inside 'class3')."""
    found: Dict[str, Dict] = {}
    for keyword, (category, subject_slug) in SKILL_CATEGORIES.items():
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(keyword) + r"(?![A-Za-z0-9])", text, re.I):
            found[keyword] = {
                "name": keyword.upper() if len(keyword) <= 4 else keyword.title(),
                "category": category,
                "proficiency": None,  # a resume cannot prove proficiency; the learner edits this
                "subject_slug": subject_slug,
            }
    return found


def _extract_skills(text: str) -> List[Dict]:
    """Match known technology keywords that actually appear in the resume text."""
    return list(_skill_hits(text).values())


def _extract_projects(text: str) -> List[Dict]:
    """Detect project headings in the text and collect the bullet lines under each."""
    lines = _lines(text)
    projects: List[Dict] = []
    for i, line in enumerate(lines):
        m = PROJECT_TITLE_RE.match(line)
        if not m:
            continue
        block: List[str] = []
        for nxt in lines[i + 1:i + 9]:
            if PROJECT_TITLE_RE.match(nxt):
                break
            block.append(nxt)
        block_text = " ".join(block)
        hits = _skill_hits(block_text)
        slug = next((h["subject_slug"] for h in hits.values() if h["subject_slug"]), None)
        projects.append({
            "title": m.group(1).strip(),
            "description": " ".join(block[:3]) or None,
            "technologies": {"list": [h["name"] for h in hits.values()]},
            "achievements": {"list": [b for b in block if METRIC_RE.search(b)]},
            "subject_slug": slug,
        })
    return projects


def _extract_facts(text: str) -> List[Dict]:
    """Extract measurable achievements and credentials stated in the resume text."""
    facts: List[Dict] = []
    seen = set()
    for line in _lines(text):
        if len(line) < 12 or len(line) > 400:
            continue
        if EDUCATION_RE.search(line):
            category = "education"
        elif AWARD_RE.search(line):
            category = "award"
        elif METRIC_RE.search(line):
            category = "achievement"
        elif EXPERIENCE_RE.search(line):
            category = "experience"
        else:
            continue
        if line.lower() not in seen:
            seen.add(line.lower())
            facts.append({"category": category, "text": line})
    return facts
