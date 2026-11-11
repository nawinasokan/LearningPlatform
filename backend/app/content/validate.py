"""Schema + quality checks for curated content. Used by tests and by authors:

    cd backend && python -m app.content.validate            # all modules
    cd backend && python -m app.content.validate python     # one module
"""
import importlib
import re
import sys

TOPIC_MODULES = [
    "python", "django_flask", "fastapi_backend", "sql_db", "ai_llm", "git_linux",
    "infra_misc", "frontend_design",
]
DIFFS = {"beginner", "practical", "intermediate", "advanced", "expert"}
MODES = ("easy", "technical", "interview")

# Phrases that betray generated filler / template text.
BANNED = [
    r"interview practice \d+", r"practice problem \d+", r"\blorem\b", r"\bplaceholder\b",
    r"\bTODO\b", r"\bTBD\b", r"your answer here", r"foundations of .* are the concepts",
    r"explain the concept and a production tradeoff", r"demo content", r"sample answer",
    r"In the F1\b", r"in the F1\b", r"Audio Annotation platform", r"my Celery setup",
]
MIN_LEN = {"easy": 120, "technical": 250, "interview": 450}


def check_topics(name, topics_by_subject, errors):
    for subj, topics in topics_by_subject.items():
        slugs = set()
        for t in topics:
            where = f"{name}:{subj}:{t.get('slug')}"
            for k in ("title", "slug", "difficulty", "order_index", "estimated_minutes", "description", "content", "questions"):
                if k not in t:
                    errors.append(f"{where} missing {k}")
            if t.get("slug") in slugs:
                errors.append(f"{where} duplicate topic slug")
            slugs.add(t.get("slug"))
            if t.get("difficulty") not in DIFFS:
                errors.append(f"{where} bad difficulty {t.get('difficulty')}")
            c = t.get("content") or {}
            for k in ("definition", "easy_explanation", "technical_explanation", "interview_answer"):
                if len(c.get(k, "")) < 80:
                    errors.append(f"{where} content.{k} missing/too short")
            qs = t.get("questions") or []
            if len(qs) < 3:
                errors.append(f"{where} needs >=3 questions, has {len(qs)}")
            texts = set()
            for q in qs:
                qw = f"{where}:{q.get('text', '')[:50]!r}"
                if not q.get("text", "").strip().endswith("?") and not q.get("text", "").lower().startswith(("write", "design", "implement", "given", "compare", "explain", "walk", "list", "describe", "diagnose", "debug")):
                    errors.append(f"{qw} question text should be a real question")
                if q.get("text") in texts:
                    errors.append(f"{qw} duplicate question")
                texts.add(q.get("text"))
                if q.get("difficulty") not in DIFFS:
                    errors.append(f"{qw} bad difficulty")
                ans = q.get("answers") or {}
                for m in MODES:
                    a = ans.get(m, "")
                    if len(a) < MIN_LEN[m]:
                        errors.append(f"{qw} answers.{m} too short ({len(a)}<{MIN_LEN[m]})")
            blob = repr(t)
            for pat in BANNED:
                if re.search(pat, blob):
                    errors.append(f"{where} contains banned phrase /{pat}/")


def main(argv):
    errors, counts = [], {}
    names = argv or TOPIC_MODULES
    for name in names:
        try:
            mod = importlib.import_module(f"app.content.{name}")
        except ModuleNotFoundError as e:
            if e.name == f"app.content.{name}":
                print(f"(skip {name}: not written yet)")
                continue
            raise
        check_topics(name, mod.TOPICS, errors)
        for subj, topics in mod.TOPICS.items():
            counts[subj] = (len(topics), sum(len(t["questions"]) for t in topics))
    for s, (t, q) in sorted(counts.items()):
        print(f"{s:24s} topics={t:3d} questions={q:4d}")
    for e in errors[:80]:
        print("ERROR", e)
    print(f"{len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
