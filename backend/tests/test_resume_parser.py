from app.services.resume_parser import _extract_facts, _extract_projects, _extract_skills

SAMPLE = """Jane Doe
Skills: Python, Django, PostgreSQL, Redis, class3 notes
Audio Annotation Platform
Built with Django and PostgreSQL.
Reduced manual effort by 50%
Best Project Award (2024)
"""


def test_skills_use_whole_word_matching_and_no_injection():
    names = {s["name"].lower() for s in _extract_skills(SAMPLE)}
    assert {"python", "django", "redis"} <= names
    assert "s3" not in names


def test_projects_and_facts_come_only_from_the_text():
    projects = _extract_projects(SAMPLE)
    assert [p["title"] for p in projects] == ["Audio Annotation Platform"]
    assert projects[0]["achievements"]["list"] == ["Reduced manual effort by 50%"]
    assert any("50%" in f["text"] for f in _extract_facts(SAMPLE))


def test_unrelated_text_yields_nothing():
    text = "Just a grocery list: eggs, milk"
    assert _extract_projects(text) == [] and _extract_facts(text) == [] and _extract_skills(text) == []
