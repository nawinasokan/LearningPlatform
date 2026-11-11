import os

from app.api.v1.sql_lab import _is_safe_query
from app.services.coding_service import run_code_against_tests


def _run(code, stdin=""):
    return run_code_against_tests(code, [{"input_data": stdin, "expected_output": ""}])["test_results"][0]


def test_runner_does_not_expose_environment_secrets(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "top-secret-value")
    out = _run("import os\nprint(os.environ.get('SECRET_KEY'))")
    assert "top-secret-value" not in (out["actual_output"] or "")
    assert out["actual_output"] == "None"


def test_runner_blocks_network_and_subprocess():
    out = _run("import socket\nsocket.socket()")
    assert out["passed"] is False and "disabled" in (out["error"] or "")
    out = _run("import os\nos.system('echo hi')")
    assert "disabled" in (out["error"] or "")


def test_runner_supports_stdin_and_future_imports():
    out = run_code_against_tests("from __future__ import annotations\nprint(input()[::-1])", [{"input_data": "abc", "expected_output": "cba"}])
    assert out["status"] == "passed"


def test_runner_cwd_is_empty_throwaway_dir():
    out = _run("import os\nprint(sorted(os.listdir('.')))")
    assert "solution.py" in out["actual_output"] and ".env" not in out["actual_output"]


def test_sql_guard_accepts_read_only_queries():
    for q in ["select 1", "SELECT * FROM employees;", "with a as (select 1) select * from a",
              "explain select 1", "select 'drop table x' as note", "select 1 -- ; drop table x"]:
        assert _is_safe_query(q), q


def test_sql_guard_rejects_dangerous_queries():
    for q in ["select 1; select 2", "drop table employees", "select pg_read_file('/etc/passwd')",
              "select * into t from employees", "explain analyze select 1", "select set_config('a','b',false)",
              "select $$x$$", "update employees set salary=0", "", "  ;  "]:
        assert not _is_safe_query(q), q
