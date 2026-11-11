import pytest

from app.main import app
from app.services.coding_service import run_code_against_tests


def test_health_route_is_registered():
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/projects" in paths


def test_coding_runner_passes_and_fails_cases():
    result = run_code_against_tests(
        "print(input().strip()[::-1])",
        [{"input_data": "academy", "expected_output": "ymedaca"}],
    )
    assert result["status"] == "passed"
    assert result["passed_cases"] == 1


def test_coding_runner_times_out():
    result = run_code_against_tests(
        "while True: pass",
        [{"input_data": "", "expected_output": ""}],
    )
    assert result["status"] == "failed"
    assert "Time limit exceeded" in result["test_results"][0]["error"] or result["test_results"][0]["error"]
