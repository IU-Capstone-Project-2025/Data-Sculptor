from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
SEMANTIC_FEEDBACK_LOCALISE_URL = os.getenv("SEMANTIC_FEEDBACK_LOCALISE_URL")


def find_position(py_path: str, smell: str, keywords: list[str]) -> tuple[int, int]:
    if keywords:
        with open(py_path, encoding="utf-8") as src:
            for idx, row in enumerate(src):
                for kw in keywords:
                    if kw in row:
                        return idx, row.index(kw)

    m = re.search(r"[-+]?[0-9]+(?:\.[0-9]+)?", smell)
    if m:
        try:
            literal = float(m.group())
        except ValueError:
            literal = None
        if literal is not None:
            tree = ast.parse(Path(py_path).read_text(encoding="utf-8"), py_path)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, (int, float))
                    and node.value == literal
                ):
                    return node.lineno - 1, node.col_offset
    return 0, 0


def run_all_linters(py_path: str) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    module_name = os.path.splitext(os.path.basename(py_path))[0]

    pylint_sev = {"error": 1, "warning": 2, "refactor": 3, "convention": 3, "info": 4}
    sev_type = {1: "error", 2: "warning", 3: "information", 4: "hint"}
    deferred: list[dict[str, str]] = []

    # --------------------- ml_smell_detector ------------------------
    with tempfile.TemporaryDirectory() as outdir:
        proc = subprocess.run(
            ["ml_smell_detector", "analyze", "--output-dir", outdir, py_path],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ml_smell_detector failed: {proc.stderr.strip()}")

        report = Path(outdir, "analysis_report.txt")
        if report.exists():
            lines = report.read_text(encoding="utf-8").splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.endswith("Smells:"):
                    i += 1
                    continue
                if line.startswith("- "):
                    title = line[2:].strip()
                    extras: list[str] = []
                    i += 1
                    while (
                        i < len(lines)
                        and not lines[i].startswith("- ")
                        and lines[i].strip()
                    ):
                        extras.append(lines[i].strip())
                        i += 1

                    framework, fix, benefit = (
                        "Not specified",
                        "Not specified",
                        "Not specified",
                    )
                    for ex in extras:
                        if ex.startswith("Framework:"):
                            framework = ex.split(":", 1)[1].strip() or framework
                            continue
                        if ex.startswith("How to fix:"):
                            fix = ex.split(":", 1)[1].strip() or fix
                            continue
                        if ex.startswith("Benefits:"):
                            benefit = ex.split(":", 1)[1].strip() or benefit
                            continue

                    # Always delegate localisation of the smell to the LLM service, disregarding
                    # any explicit or implicit location hints found in the report.
                    deferred.append(
                        {
                            "description": title,
                            "framework": framework,
                            "fix": fix,
                            "benefit": benefit,
                        }
                    )
                else:
                    i += 1

    # ------------- deferred localisation via LLM --------------------
    if deferred:
        try:
            payload = {
                "current_code": Path(py_path).read_text(encoding="utf-8"),
                "warnings": deferred,
                "cell_code_offset": 0,
            }
            data = requests.post(
                SEMANTIC_FEEDBACK_LOCALISE_URL, json=payload, timeout=60
            ).json()
            for item in data.get("localized_feedback", []):
                rng = item["range"]
                start, end = rng["start"], rng["end"]
                sev = item.get("severity", 2)
                diagnostics.append(
                    {
                        "tool": "ml_smell_detector",
                        "type": sev_type.get(sev, "warning"),
                        "module": module_name,
                        "obj": "",
                        "line": start["line"],
                        "column": start["character"],
                        "endLine": end["line"],
                        "endColumn": end["character"],
                        "message": item.get("message", ""),
                        "symbol": "LLM-localised",
                        "message-id": "",
                        "severity": sev,
                        "range": rng,
                    }
                )
        except Exception:
            for w in deferred:
                diagnostics.append(
                    {
                        "tool": "ml_smell_detector",
                        "type": "warning",
                        "module": module_name,
                        "obj": "",
                        "line": 0,
                        "column": 0,
                        "endLine": 0,
                        "endColumn": 0,
                        "message": w["description"],
                        "symbol": "LLM-localisation-error",
                        "message-id": "",
                        "severity": 2,
                    }
                )

    # -------------------------- pylint ------------------------------
    proc = subprocess.run(
        ["pylint", py_path, "-f", "json", "--disable=R,C"],
        capture_output=True,
        text=True,
    )
    try:
        issues = json.loads(proc.stdout)
    except json.JSONDecodeError:
        issues = []
    for issue in issues:
        sev = pylint_sev.get(issue.get("type", ""), 3)
        line0 = max(0, issue.get("line", 1) - 1)
        col0 = issue.get("column", 0)
        diagnostics.append(
            {
                "tool": "pylint",
                "type": sev_type[sev],
                "module": issue.get("module", module_name),
                "obj": issue.get("obj", ""),
                "line": line0,
                "column": col0,
                "endLine": line0,
                "endColumn": col0 + 1,
                "message": issue.get("message", ""),
                "symbol": issue.get("symbol", ""),
                "message-id": issue.get("message-id", ""),
                "severity": sev,
            }
        )

    return diagnostics
