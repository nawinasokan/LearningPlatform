"""Quality gates for the curated curriculum (no filler, runnable solutions, safe SQL)."""
import importlib

import pytest

from app.content import validate
from app.content.validate import TOPIC_MODULES, check_topics
from app.services.coding_service import run_code_against_tests


def _mod(name):
    try:
        return importlib.import_module(f"app.content.{name}")
    except ModuleNotFoundError as exc:
        if exc.name == f"app.content.{name}":
            pytest.skip(f"{name} not written")
        raise


@pytest.mark.parametrize("name", TOPIC_MODULES)
def test_topic_modules_are_complete_and_real(name):
    errors = []
    check_topics(name, _mod(name).TOPICS, errors)
    assert not errors, "\n".join(errors[:20])


def test_new_subjects_are_covered():
    slugs = set()
    for name in TOPIC_MODULES:
        slugs |= set(_mod(name).TOPICS)
    assert {"ai-llm", "git", "linux"} <= slugs


def test_coding_problem_reference_solutions_pass_all_tests():
    problems = _mod("coding_problems").PROBLEMS
    assert len(problems) >= 50
    assert len({p["slug"] for p in problems}) == len(problems)
    for p in problems:
        assert sum(t.get("hidden", False) for t in p["test_cases"]) >= 1, p["slug"]
        tests = [{"input_data": t["input"], "expected_output": t["expected"]} for t in p["test_cases"]]
        result = run_code_against_tests(p["solution_code"], tests)
        assert result["status"] == "passed", (p["slug"], result["test_results"])
        assert p.get("explanation"), p["slug"]


def test_sql_problems_have_safe_reference_queries():
    from app.api.v1.sql_lab import _is_safe_query
    problems = _mod("sql_problems").PROBLEMS
    assert len(problems) >= 45
    assert len({p["slug"] for p in problems}) == len(problems)
    for p in problems:
        assert _is_safe_query(p["expected_query"]), p["slug"]
        assert p.get("explanation") and p.get("hints"), p["slug"]
