import subprocess
import json
import tempfile
import os
from typing import List, Dict


def run_all_linters(py_path: str) -> List[Dict]:
    """
    Run ML smell detector and pylint on the given Python file and return diagnostics.
    """
    diagnostics: List[Dict] = []

    # ---------- 1. ML Smell Detector ----------
    with tempfile.TemporaryDirectory() as outdir:
        cmd = [
            "ml_smell_detector",
            "analyze",
            "--output-dir",
            outdir,
            py_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"ml_smell_detector failed: {proc.stderr.strip()}")

        report_path = os.path.join(outdir, "analysis_report.txt")
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.endswith("Smells:"):
                    current_section = line.replace(":", "")
                elif line.startswith("-"):
                    smell_name = line[2:]
                    diagnostics.append({
                        "tool": "ml_smell_detector",
                        "category": current_section,
                        "message": smell_name,
                    })
                elif line.startswith("  ") and current_section:
                    # Sub-key:value pair
                    parts = line.strip().split(":", 1)
                    if len(parts) == 2 and diagnostics:
                        diagnostics[-1][parts[0].strip()] = parts[1].strip()

    # ---------- 2. Pylint ----------
    pylint_cmd = [
        "pylint",
        py_path,
        "-f", "json",
        "--disable=R,C",  # optionally suppress Refactor/Convention noise
    ]
    proc = subprocess.run(pylint_cmd, capture_output=True, text=True)

    # Log output for debug
    print("PYLINT STDOUT:\n", proc.stdout)
    print("PYLINT STDERR:\n", proc.stderr)

    try:
        pylint_issues = json.loads(proc.stdout)
        for issue in pylint_issues:
            diagnostics.append({
                "tool": "pylint",
                "type": issue.get("type"),
                "module": issue.get("module"),
                "obj": issue.get("obj"),
                "line": issue.get("line"),
                "column": issue.get("column"),
                "message": issue.get("message"),
                "symbol": issue.get("symbol"),
                "message-id": issue.get("message-id"),
            })
    except json.JSONDecodeError:
        print("Pylint output is not valid JSON or empty. Skipping.")

    return diagnostics
