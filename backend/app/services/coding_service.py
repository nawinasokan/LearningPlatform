"""
Sandboxed Python code execution service.
Runs user code in an isolated subprocess with strict timeouts
and resource limits. Never executes inside the FastAPI process.
"""
import shutil
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
    os.setsid()
    resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT_SECONDS, TIMEOUT_SECONDS + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


# Runs inside the child interpreter. Best-effort guards (not a security boundary
# on their own - the boundary is the scrubbed environment, throwaway cwd and
# resource limits): block network sockets and process spawning.
_WRAPPER = r"""
import sys, io, runpy, socket, os, builtins
sys.stdin = io.StringIO(open('input.txt').read())
def _blocked(*a, **k):
    raise PermissionError('Network and process access are disabled in the sandbox')
socket.socket = _blocked
socket.create_connection = _blocked
socket.getaddrinfo = _blocked
for _n in ('system', 'popen', 'fork', 'forkpty', 'execv', 'execve', 'execvp', 'spawnl', 'spawnv', 'kill'):
    if hasattr(os, _n):
        setattr(os, _n, _blocked)
runpy.run_path('solution.py', run_name='__main__')
"""


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

    # Each run gets an empty throwaway directory as its cwd and a minimal
    # environment, so learner code cannot see the API's secrets or files.
    workdir = tempfile.mkdtemp(prefix="interview_academy_")
    with open(os.path.join(workdir, "solution.py"), "w") as fh:
        fh.write(code)
    with open(os.path.join(workdir, "input.txt"), "w") as fh:
        fh.write(str(input_data))
    tmp_path = workdir

    try:
        start = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, "-I", "-c", _WRAPPER],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=workdir,
            stdin=subprocess.DEVNULL,
            preexec_fn=_limit_resources,
            env={"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"},
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
        shutil.rmtree(workdir, ignore_errors=True)
