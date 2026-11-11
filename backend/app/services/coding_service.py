"""
Sandboxed Python code execution service.
Runs user code in an isolated subprocess with strict timeouts
and resource limits. Never executes inside the FastAPI process.
"""
import subprocess
import sys
import tempfile
import os
import time
import uuid
import json
import resource
from typing import List, Dict, Any, Optional


TIMEOUT_SECONDS = 10
MAX_OUTPUT_BYTES = 50_000  # 50KB
MAX_MEMORY_BYTES = 256 * 1024 * 1024


def _limit_resources() -> None:
    """Apply Linux process limits before starting untrusted exercise code."""
    resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT_SECONDS, TIMEOUT_SECONDS + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))


def run_code_against_tests(
    code: str,
    test_cases: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Execute user code against test cases.
    Returns dict with test_results, passed_cases, total_cases, runtime_ms.
    """
    results = []
    total_runtime = 0.0

    for i, tc in enumerate(test_cases):
        result = _run_single_test(code, tc, i)
        results.append(result)
        if result.get("runtime_ms"):
            total_runtime += result["runtime_ms"]

    passed = sum(1 for r in results if r["passed"])

    return {
        "test_results": results,
        "passed_cases": passed,
        "total_cases": len(test_cases),
        "runtime_ms": round(total_runtime, 2),
        "status": "passed" if passed == len(test_cases) else "failed",
    }


def _run_single_test(
    code: str,
    test_case: Dict[str, Any],
    index: int,
) -> Dict[str, Any]:
    """Run code against a single test case in a subprocess."""
    input_data = test_case.get("input_data", "")
    expected_output = str(test_case.get("expected_output", "")).strip()

    # Provide test input before evaluating the learner's script. Starter code
    # commonly reads stdin at module level after defining its function.
    runner_code = f"""
import sys
import io
sys.stdin = io.StringIO({repr(input_data)})

# User code
{code}
"""

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        prefix="interview_academy_",
    ) as tmp:
        tmp.write(runner_code)
        tmp_path = tmp.name

    try:
        start = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            preexec_fn=_limit_resources,
            # Resource limits via env
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        elapsed = (time.perf_counter() - start) * 1000

        actual_output = proc.stdout.strip()
        stderr = proc.stderr.strip()

        if len(actual_output) > MAX_OUTPUT_BYTES:
            actual_output = actual_output[:MAX_OUTPUT_BYTES] + "\n[Output truncated]"

        passed = (proc.returncode == 0) and (actual_output == expected_output)

        return {
            "test_case_index": index,
            "passed": passed,
            "input_data": input_data,
            "expected_output": expected_output,
            "actual_output": actual_output,
            "error": stderr if proc.returncode != 0 else None,
            "runtime_ms": round(elapsed, 2),
        }

    except subprocess.TimeoutExpired:
        return {
            "test_case_index": index,
            "passed": False,
            "input_data": input_data,
            "expected_output": expected_output,
            "actual_output": None,
            "error": f"Time limit exceeded ({TIMEOUT_SECONDS}s)",
            "runtime_ms": TIMEOUT_SECONDS * 1000,
        }
    except Exception as e:
        return {
            "test_case_index": index,
            "passed": False,
            "input_data": input_data,
            "expected_output": expected_output,
            "actual_output": None,
            "error": str(e),
            "runtime_ms": None,
        }
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
