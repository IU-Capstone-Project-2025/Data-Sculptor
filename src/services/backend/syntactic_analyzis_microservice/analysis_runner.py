from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from importlib import util as import_util
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
SEMANTIC_FEEDBACK_LOCALISE_URL = os.getenv("SEMANTIC_FEEDBACK_LOCALISE_URL")
RE_VULTURE_TXT = re.compile(r"^(?P<path>.*?):(?P<line>\d+):\s*(?P<msg>.+)$")


def _dotted_module_name(path: Path) -> str:
    try:
        spec = import_util.spec_from_file_location(None, path)
        if spec and spec.name:
            return spec.name
    except Exception:
        pass

    return path.stem


def _safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _parse_vulture_output(path: Path, raw_stdout: str) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    mod_name = _dotted_module_name(path)

    for line in raw_stdout.splitlines():
        if not line.strip():
            continue
        m = RE_VULTURE_TXT.match(line)
        if not m:
            continue

        lineno = int(m["line"]) - 1
        msg = m["msg"]

        confidence = 80
        conf_match = re.search(r"(\d+)%\s*confidence\)?$", msg)
        if conf_match:
            confidence = int(conf_match.group(1))
            msg = re.sub(r"\s*\(\d+%\s*confidence\)$", "", msg).strip()

        sev = 2 if confidence >= 90 else 3
        diagnostics.append(
            {
                "tool": "vulture",
                "type": "warning" if sev == 2 else "information",
                "module": mod_name,
                "obj": "",
                "line": lineno,
                "column": 0,
                "endLine": lineno,
                "endColumn": 0,
                "message": msg,
                "symbol": "vulture-unused-code",
                "message-id": "vulture-unused",
                "severity": sev,
            }
        )
    return diagnostics


def run_all_linters(py_path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    py_path = Path(py_path).resolve()
    module_name = _dotted_module_name(py_path)

    sev_type = {1: "error", 2: "warning", 3: "information", 4: "hint"}
    pylint_sev = {"error": 1, "warning": 2, "refactor": 3, "convention": 3, "info": 4}

    diagnostics: list[dict[str, Any]] = []
    deferred: list[dict[str, str]] = []
    try:
        with tempfile.TemporaryDirectory() as outdir:
            proc = subprocess.run(
                ["ml_smell_detector", "analyze", "--output-dir", outdir, str(py_path)],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"ml_smell_detector failed: {proc.stderr.strip() or proc.stdout}"
                )

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
    except FileNotFoundError:
        print("ml_smell_detector not installed", file=sys.stderr)
    except Exception as exc:
        print(exc, file=sys.stderr)
    if deferred:
        try:
            payload = {
                "current_code": py_path.read_text(encoding="utf-8"),
                "warnings": deferred,
                "cell_code_offset": 0,
            }
            resp = requests.post(SEMANTIC_FEEDBACK_LOCALISE_URL, json=payload, timeout=60)
            resp.raise_for_status()
            for item in resp.json().get("localized_feedback", []):
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
        except Exception as exc:
            print(f"LLM localisation failed: {exc}", file=sys.stderr)
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

    try:
        proc = subprocess.run(
            ["pylint", str(py_path), "-f", "json", "--disable=R,C"],
            capture_output=True,
            text=True,
        )
        for issue in _safe_json_loads(proc.stdout) or []:
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
    except FileNotFoundError:
        print("pylint not installed", file=sys.stderr)

    try:
        proc = subprocess.run(
            ["vulture", "--json", "--min-confidence", "80", str(py_path)],
            capture_output=True,
            text=True,
        )
        if proc.returncode in (0, 3):
            items = _safe_json_loads(proc.stdout)
            if isinstance(items, list) and items:
                for item in items:
                    lineno = item["lineno"] - 1
                    confidence = int(item.get("confidence", 80))
                    sev = 2 if confidence >= 90 else 3
                    diagnostics.append(
                        {
                            "tool": "vulture",
                            "type": "warning" if sev == 2 else "information",
                            "module": module_name,
                            "obj": "",
                            "line": lineno,
                            "column": 0,
                            "endLine": lineno,
                            "endColumn": 0,
                            "message": item["message"],
                            "symbol": "vulture-unused-code",
                            "message-id": "vulture-unused",
                            "severity": sev,
                        }
                    )
            else:
                diagnostics.extend(_parse_vulture_output(py_path, proc.stdout))
        elif proc.returncode not in (1, 2):
            diagnostics.extend(_parse_vulture_output(py_path, proc.stdout))
    except FileNotFoundError:
        print("vulture not installed", file=sys.stderr)

    try:
        proc = subprocess.run(
            ["bandit", "--exit-zero", "-f", "json", "-q", str(py_path)],
            capture_output=True,
            text=True,
        )
        if proc.returncode in (0, 1, 2, 255):
            bandit_report = _safe_json_loads(proc.stdout)
            for issue in bandit_report.get("results", []):
                sev_map = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
                sev = sev_map.get(issue.get("issue_severity", "LOW"), 3)

                line0 = max(0, issue.get("line_number", 1) - 1)
                col0 = issue.get("col_offset", 0)
                diagnostics.append(
                    {
                        "tool": "bandit",
                        "type": sev_type.get(sev, "warning"),
                        "module": module_name,
                        "obj": "",
                        "line": line0,
                        "column": col0,
                        "endLine": line0,
                        "endColumn": col0,
                        "message": issue.get("issue_text", ""),
                        "symbol": issue.get("test_id", ""),
                        "message-id": issue.get("test_id", ""),
                        "severity": sev,
                    }
                )
    except FileNotFoundError:
        print("bandit not installed", file=sys.stderr)

    return diagnostics
