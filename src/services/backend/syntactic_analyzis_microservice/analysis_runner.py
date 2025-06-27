from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import tempfile
from typing import Dict, List, Tuple


def find_position(py_path: str, smell: str, keywords: List[str]) -> Tuple[int, int]:
    if keywords:
        try:
            with open(py_path, encoding="utf-8") as src_file:
                for idx, row in enumerate(src_file):
                    for kw in keywords:
                        if kw in row:
                            return idx, row.index(kw)
        except OSError:
            pass

    num_match = re.search(r"[-+]?[0-9]+(?:\.[0-9]+)?", smell)
    if num_match:
        try:
            literal = float(num_match.group())
        except ValueError:
            literal = None

        if literal is not None:
            try:
                tree = ast.parse(open(py_path, encoding="utf-8").read(), py_path)
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.Constant)
                        and isinstance(node.value, (int, float))
                        and node.value == literal
                    ):
                        return node.lineno - 1, node.col_offset
            except Exception:
                pass

    return 0, 0

def run_all_linters(py_path: str) -> List[Dict]:
    diagnostics: List[Dict] = []
    module_name = os.path.splitext(os.path.basename(py_path))[0]

    pylint_sev_map = {
        "error": 1,
        "warning": 2,
        "refactor": 3,
        "convention": 3,
        "info": 4,
    }
    ml_sev_map = {
        "Framework-Specific Smells": 2,
        "Hugging Face Smells": 2,
        "General ML Smells": 3,
    }
    sev_type_map = {1: "error", 2: "warning", 3: "information", 4: "hint"}

    keywords_map = {
        "Framework-Specific Smells": ["Sequential("],
        "Hugging Face Smells": ["transformers", "AutoModel"],
        "General ML Smells": [],
    }

    with tempfile.TemporaryDirectory() as outdir:
        proc = subprocess.run(
            ["ml_smell_detector", "analyze", "--output-dir", outdir, py_path],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ml_smell_detector failed: {proc.stderr.strip()}")

        report_path = os.path.join(outdir, "analysis_report.txt")
        if os.path.exists(report_path):
            lines = [ln.rstrip("\n") for ln in open(report_path, encoding="utf-8")]

            current_cat: str | None = None
            i = 0
            while i < len(lines):
                line = lines[i].strip()

                if line.endswith("Smells:"):
                    current_cat = line[:-1]
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

                    line_no, col_no = 0, 0
                    for idx_ex, ex in enumerate(extras):
                        m_line = re.match(r"Location:\s*Line\s+(\d+)", ex, re.I)
                        if m_line:
                            line_no = int(m_line.group(1)) - 1
                            del extras[idx_ex]
                            break
                        m_tuple = re.match(r"Location:\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", ex)
                        if m_tuple:
                            line_no = int(m_tuple.group(1)) - 1
                            col_no = int(m_tuple.group(2))
                            del extras[idx_ex]
                            break

                    if line_no == 0 and col_no == 0:
                        kw_list = keywords_map.get(current_cat or "", [])
                        line_no, col_no = find_position(py_path, title, kw_list)

                    message_text = "\n".join([title] + extras)

                    sev = ml_sev_map.get(current_cat, 3)
                    diagnostics.append(
                        {
                            "tool": "ml_smell_detector",
                            "type": sev_type_map[sev],
                            "module": module_name,
                            "obj": "",
                            "line": line_no,
                            "column": col_no,
                            "message": message_text,
                            "symbol": current_cat or "",
                            "message-id": "",
                            "severity": sev,
                        }
                    )
                else:
                    i += 1

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
        sev = pylint_sev_map.get(issue.get("type", ""), 3)
        diagnostics.append(
            {
                "tool": "pylint",
                "type": sev_type_map[sev],
                "module": issue.get("module", module_name),
                "obj": issue.get("obj", ""),
                "line": max(0, issue.get("line", 1) - 1),
                "column": issue.get("column", 0),
                "message": issue.get("message", ""),
                "symbol": issue.get("symbol", ""),
                "message-id": issue.get("message-id", ""),
                "severity": sev,
            }
        )

    return diagnostics
