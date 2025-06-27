from __future__ import annotations

import ast
import json
import os
***REMOVED***
import subprocess
import tempfile
***REMOVED***quests

SEMANTIC_FEEDBACK_LOCALISE_URL = os.getenv("LOCALIZE_MLSCENT_URL")


def find_position(py_path: str, smell: str, keywords: list[str]) -> tuple[int, int]:
    if keywords:
        try:
            with open(py_path, encoding="utf-8") as src_file:
                for idx, row in enumerate(src_file):
                    for kw in keywords:
                        if kw in row:
                    ***REMOVED*** idx, row.index(kw)
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
                ***REMOVED*** node.lineno - 1, node.col_offset
            except Exception:
                pass

    return 0, 0


def run_all_linters(py_path: str) -> list[dict]:
    diagnostics: list[dict] = []
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

    warnings_for_localization: list[
        dict[str, str]
    ] = []  # warnings missing explicit location

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

                    framework = "Not specified"
                    fix = "Not specified"
                    benefit = "Not specified"

                    line_no, col_no = 0, 0

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

                        # --- Location parsing ---
                        m_line = re.match(r"Location:\s*Line\s+(\d+)", ex, re.I)
                        if m_line:
                            line_no = int(m_line.group(1)) - 1
                            col_no = 0
                            continue

                        m_tuple = re.match(
                            r"Location:\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)", ex
                        )
                        if m_tuple:
                            line_no = int(m_tuple.group(1)) - 1
                            col_no = int(m_tuple.group(2))
                            continue

                    # If still unknown – attempt heuristic search
                    if line_no == 0 and col_no == 0:
                        kw_list = keywords_map.get(current_cat or "", [])
                        line_no, col_no = find_position(py_path, title, kw_list)

                    if line_no == 0:
                        # No reliable location → defer to semantic-feedback service
                        warnings_for_localization.append(
                            {
                                "description": title,
                                "framework": framework,
                                "fix": fix,
                                "benefit": benefit,
                            }
                        )
                        # Skip adding diagnostic for now; will add after LLM localisation
                        continue

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

    if warnings_for_localization:
        print(warnings_for_localization)
        try:
            code_str = open(py_path, "r", encoding="utf-8").read()
            payload = {
                "current_code": code_str,
                "warnings": warnings_for_localization,
                "cell_code_offset": 0,
            }

            resp = requests.post(
                SEMANTIC_FEEDBACK_LOCALISE_URL, json=payload, timeout=60
            )
            if resp.ok:
                data = resp.json()
                for item in data.get("localized_feedback", []):
                    rng = item.get("range", {})
                    start = rng.get("start", {})

                    sev = item.get("severity", 2)
                    diagnostics.append(
                        {
                            "tool": "ml_smell_detector_localised",
                            "type": sev_type_map.get(sev, "warning"),
                            "module": module_name,
                            "obj": "",
                            "line": start.get("line", 0),
                            "column": start.get("character", 0),
                            "message": item.get("message", ""),
                            "symbol": "LLM-localised",
                            "message-id": "",
                            "severity": sev,
                        }
                    )
            else:
                # Fallback: append diagnostics without location
                for w in warnings_for_localization:
                    diagnostics.append(
                        {
                            "tool": "ml_smell_detector",
                            "type": "warning",
                            "module": module_name,
                            "obj": "",
                            "line": 0,
                            "column": 0,
                            "message": w["description"],
                            "symbol": "LLM-localisation-failed",
                            "message-id": "",
                            "severity": 2,
                        }
                    )
        except Exception:
            # Ensure localisation failures don't break primary linter flow
            for w in warnings_for_localization:
                diagnostics.append(
                    {
                        "tool": "ml_smell_detector",
                        "type": "warning",
                        "module": module_name,
                        "obj": "",
                        "line": 0,
                        "column": 0,
                        "message": w["description"],
                        "symbol": "LLM-localisation-error",
                        "message-id": "",
                        "severity": 2,
                    }
                )

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
