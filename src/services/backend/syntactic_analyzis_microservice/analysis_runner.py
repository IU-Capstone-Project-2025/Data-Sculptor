from __future__ import annotations
import json, os, re, subprocess, sys, tempfile
from importlib import util as import_util
from pathlib import Path
from typing import Any
import requests
from dotenv import load_dotenv

load_dotenv()
SEMANTIC_FEEDBACK_LOCALISE_URL = os.getenv("SEMANTIC_FEEDBACK_LOCALISE_URL")
SEV_TYPE = {1: "error", 2: "warning", 3: "information", 4: "hint"}
PYLINT_SEV = {"error": 1, "warning": 2, "refactor": 3, "convention": 3, "info": 4}
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


def _ruff_project_root(start: Path) -> Path:
    root = start
    while root != root.parent:
        if (root / "ruff.toml").exists():
            return root
        root = root.parent
    return start.parent


def run_all_linters(py_path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    py_path = Path(py_path).resolve()
    module_name = _dotted_module_name(py_path)
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
                raise RuntimeError(proc.stderr.strip() or proc.stdout)
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
                        while i < len(lines) and not lines[i].startswith("- ") and lines[i].strip():
                            extras.append(lines[i].strip())
                            i += 1
                        framework, fix, benefit = "Not specified", "Not specified", "Not specified"
                        for ex in extras:
                            if ex.startswith("Framework:"):
                                framework = ex.split(":", 1)[1].strip() or framework
                            elif ex.startswith("How to fix:"):
                                fix = ex.split(":", 1)[1].strip() or fix
                            elif ex.startswith("Benefits:"):
                                benefit = ex.split(":", 1)[1].strip() or benefit
                        deferred.append({"description": title, "framework": framework, "fix": fix, "benefit": benefit})
                    else:
                        i += 1
    except FileNotFoundError:
        print("ml_smell_detector not installed", file=sys.stderr)
    except Exception as exc:
        print(exc, file=sys.stderr)

    if deferred:
        try:
            payload = {"current_code": py_path.read_text(encoding="utf-8"), "warnings": deferred, "cell_code_offset": 0}
            resp = requests.post(SEMANTIC_FEEDBACK_LOCALISE_URL, json=payload, timeout=60)
            resp.raise_for_status()
            for item in resp.json().get("localized_feedback", []):
                rng = item["range"]
                start, end = rng["start"], rng["end"]
                sev = item.get("severity", 2)
                diagnostics.append(
                    {
                        "tool": "ml_smell_detector",
                        "type": SEV_TYPE.get(sev, "warning"),
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
        proc = subprocess.run(["pylint", str(py_path), "-f", "json", "--disable=R,C"], capture_output=True, text=True)
        for issue in _safe_json_loads(proc.stdout) or []:
            sev = PYLINT_SEV.get(issue.get("type", ""), 3)
            line0 = max(0, issue.get("line", 1) - 1)
            col0 = issue.get("column", 0)
            diagnostics.append(
                {
                    "tool": "pylint",
                    "type": SEV_TYPE[sev],
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
        proc = subprocess.run(["vulture", "--json", str(py_path)], capture_output=True, text=True)
        if proc.returncode in (0, 3):
            items = _safe_json_loads(proc.stdout)
            if isinstance(items, list) and items:
                for it in items:
                    msg = f"{it['type']}: {it['name']}"
                    conf = int(it.get("confidence", 80))
                    sev = 2 if conf >= 90 else 3
                    diagnostics.append(
                        {
                            "tool": "vulture",
                            "type": SEV_TYPE[sev],
                            "module": module_name,
                            "obj": "",
                            "line": it["lineno"] - 1,
                            "column": 0,
                            "endLine": it["lineno"] - 1,
                            "endColumn": 0,
                            "message": msg,
                            "symbol": "vulture-unused-code",
                            "message-id": "vulture-unused",
                            "severity": sev,
                        }
                    )
            else:
                for line in proc.stdout.splitlines():
                    m = RE_VULTURE_TXT.match(line)
                    if not m:
                        continue
                    lineno = int(m["line"]) - 1
                    msg_full = m["msg"]
                    conf = 80
                    mc = re.search(r"(\d+)%\s*confidence\)?$", msg_full)
                    if mc:
                        conf = int(mc.group(1))
                        msg_full = re.sub(r"\s*\(\d+%\s*confidence\)$", "", msg_full).strip()
                    sev = 2 if conf >= 90 else 3
                    diagnostics.append(
                        {
                            "tool": "vulture",
                            "type": SEV_TYPE[sev],
                            "module": module_name,
                            "obj": "",
                            "line": lineno,
                            "column": 0,
                            "endLine": lineno,
                            "endColumn": 0,
                            "message": msg_full,
                            "symbol": "vulture-unused-code",
                            "message-id": "vulture-unused",
                            "severity": sev,
                        }
                    )
        else:
            print("vulture failed:", proc.stderr or proc.stdout, file=sys.stderr)
    except FileNotFoundError:
        print("vulture not installed", file=sys.stderr)

    try:
        root = _ruff_project_root(py_path.parent)
        proc = subprocess.run(
            ["ruff", "check", "--format", "json", str(py_path)],
            capture_output=True,
            text=True,
            cwd=root,
        )
        if proc.returncode in (0, 1):
            for item in _safe_json_loads(proc.stdout) or []:
                loc = item["location"]
                line0 = loc["row"] - 1
                col0 = loc["column"] - 1
                diagnostics.append(
                    {
                        "tool": "ruff",
                        "type": "warning",
                        "module": module_name,
                        "obj": "",
                        "line": line0,
                        "column": col0,
                        "endLine": line0,
                        "endColumn": col0,
                        "message": item["message"],
                        "symbol": item["code"],
                        "message-id": item["code"],
                        "severity": 2,
                    }
                )
    except FileNotFoundError:
        print("ruff not installed", file=sys.stderr)

    try:
        proc = subprocess.run(["bandit", "--exit-zero", "-f", "json", "-q", str(py_path)], capture_output=True, text=True)
        if proc.returncode in (0, 1, 2, 255):
            bandit_report = _safe_json_loads(proc.stdout)
            for issue in bandit_report.get("results", []):
                sev = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(issue.get("issue_severity", "LOW"), 3)
                line0 = max(0, issue.get("line_number", 1) - 1)
                col0 = issue.get("col_offset", 0)
                diagnostics.append(
                    {
                        "tool": "bandit",
                        "type": SEV_TYPE.get(sev, "warning"),
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
