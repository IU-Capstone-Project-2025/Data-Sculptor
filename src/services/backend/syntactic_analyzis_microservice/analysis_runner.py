import subprocess
import json
import tempfile
import os
from typing import List, Dict

def run_all_linters(py_path: str) -> List[Dict]:
    """
    Run ML smell detector and pylint on the given Python file,
    return diagnostics with uniform fields and approximate positions for ML smells.
    """
    diagnostics: List[Dict] = []
    module_name = os.path.splitext(os.path.basename(py_path))[0]

    # ---------- severity mappings ----------
    pylint_sev_map = {
        "error": 1,
        "warning": 2,
        "refactor": 3,
        "convention": 3,
        "info": 4,
    }
    ml_sev_map = {
        "Framework-Specific Smells": 2,
        "Hugging Face Smells":       2,
        "General ML Smells":         3,
    }
    sev_type_map = {1: "error", 2: "warning", 3: "information", 4: "hint"}

    # keywords for heuristics
    keywords_map = {
        "Framework-Specific Smells": ["Sequential("],
        "Hugging Face Smells":       ["transformers", "AutoModel"],
        "General ML Smells":         ["fit(", "predict("],
    }

    def find_position(path: str, keywords: List[str]) -> (int, int):
        """Search for any of the keywords in the source, return line/column or (0,0)."""
        try:
            with open(path, encoding="utf-8") as src:
                for idx, row in enumerate(src):
                    for kw in keywords:
                        if kw in row:
                    ***REMOVED*** idx, row.index(kw)
        except OSError:
            pass
***REMOVED*** 0, 0

    # ---------- 1. ML Smell Detector ----------
    with tempfile.TemporaryDirectory() as outdir:
        proc = subprocess.run(
            ["ml_smell_detector", "analyze", "--output-dir", outdir, py_path],
            capture_output=True, text=True
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ml_smell_detector failed: {proc.stderr.strip()}")

        report_path = os.path.join(outdir, "analysis_report.txt")
        if os.path.exists(report_path):
            current_cat = None
            for raw in open(report_path, encoding="utf-8"):
                line = raw.strip()
                if not line:
                    continue
                if line.endswith("Smells:"):
                    current_cat = line[:-1]
                elif line.startswith("- "):
                    smell = line[2:]
                    sev = ml_sev_map.get(current_cat, 3)
                    ltype = sev_type_map[sev]
                    kws = keywords_map.get(current_cat, [])
                    ln, col = find_position(py_path, kws) if kws else (0, 0)
                    diagnostics.append({
                        "tool":       "ml_smell_detector",
                        "type":       ltype,
                        "module":     module_name,
                        "obj":        "",
                        "line":       ln,
                        "column":     col,
                        "message":    smell,
                        "symbol":     current_cat or "",
                        "message-id": "",
                        "severity":   sev,
                    })

    # ---------- 2. Pylint ----------
    proc = subprocess.run(
        ["pylint", py_path, "-f", "json", "--disable=R,C"],
        capture_output=True, text=True
    )
    try:
        issues = json.loads(proc.stdout)
    except json.JSONDecodeError:
        issues = []

    for issue in issues:
        sev = pylint_sev_map.get(issue.get("type", ""), 3)
        diagnostics.append({
            "tool":       "pylint",
            "type":       sev_type_map[sev],
            "module":     issue.get("module", module_name),
            "obj":        issue.get("obj", ""),
            "line":       issue.get("line", 0) - 1,
            "column":     issue.get("column", 0),
            "message":    issue.get("message", ""),
            "symbol":     issue.get("symbol", ""),
            "message-id": issue.get("message-id", ""),
            "severity":   sev,
        })

    return diagnostics
