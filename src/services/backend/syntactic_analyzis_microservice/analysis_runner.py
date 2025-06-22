# analysis_runner.py
import subprocess, json
from typing import List, Dict


def _run(cmd: list[str]) -> list[dict]:
    """Run cmd, parse JSON stdout (или stderr)."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = proc.stdout.strip() or proc.stderr.strip()
    try:
        return json.loads(out) if out else []
    except json.JSONDecodeError:
        print(f"[lint] JSON parse error. Raw output:\n{out}")
        return []


def run_all_linters(py_path: str) -> List[Dict]:
    diagnostics: list[dict] = []

    linters = {
        "pylint": ["pylint", "--output-format=json", py_path],
        "ml_smell_detector": ["ml_smell_detector", "--output=json", py_path],
    }

    for cmd in linters.values():
        diagnostics += _run(cmd)

    return diagnostics
