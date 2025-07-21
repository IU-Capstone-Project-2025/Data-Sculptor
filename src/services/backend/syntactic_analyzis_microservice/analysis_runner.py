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
    
    # Read file content for better range calculation
    try:
        with open(py_path, "r", encoding="utf-8") as f:
            file_lines = f.readlines()
    except Exception:
        file_lines = []
    
    for issue in issues:
        sev = pylint_sev.get(issue.get("type", ""), 3)
        line0 = max(0, issue.get("line", 1) - 1)
        col0 = issue.get("column", 0)
        
        # Calculate better end position based on the actual content
        end_line = line0
        end_col = col0 + 1  # Default fallback
        
        if line0 < len(file_lines):
            line_content = file_lines[line0].rstrip('\n\r')
            message = issue.get("message", "").lower()
            symbol = issue.get("symbol", "").lower()
            
            # Try to find a better end position
            if col0 < len(line_content):
                end_pos = col0
                
                # Method 1: Context-specific improvements first (more accurate)
                if "import" in message or "unused-import" in symbol:
                    # For import issues, try to find the module name in the message
                    import_name_match = re.search(r"'([^']+)'", message)
                    if import_name_match:
                        import_name = import_name_match.group(1)
                        # Find the import name in the line
                        name_pos = line_content.find(import_name)
                        if name_pos >= 0:
                            end_pos = name_pos + len(import_name)
                        else:
                            # Fallback: mark from "import" keyword
                            import_pos = line_content.find('import')
                            if import_pos >= 0:
                                end_pos = import_pos
                                while end_pos < len(line_content) and line_content[end_pos] not in ' \t\n':
                                    end_pos += 1
                                # Skip whitespace
                                while end_pos < len(line_content) and line_content[end_pos] in ' \t':
                                    end_pos += 1
                                # Mark the module name
                                while end_pos < len(line_content) and (line_content[end_pos].isalnum() or line_content[end_pos] in '_.'):
                                    end_pos += 1
                
                elif "undefined" in message or "name" in message:
                    # For undefined variable/name issues, extract the variable name from the message
                    var_name_match = re.search(r"'([^']+)'", message)
                    if var_name_match:
                        var_name = var_name_match.group(1)
                        # Find the variable name in the line
                        var_pos = line_content.find(var_name, col0)
                        if var_pos >= 0:
                            end_pos = var_pos + len(var_name)
                        else:
                            # Fallback: mark identifier at col0
                            end_pos = col0
                            while end_pos < len(line_content) and (line_content[end_pos].isalnum() or line_content[end_pos] in '_'):
                                end_pos += 1
                    else:
                        # Fallback: mark identifier at col0
                        end_pos = col0
                        while end_pos < len(line_content) and (line_content[end_pos].isalnum() or line_content[end_pos] in '_'):
                            end_pos += 1
                
                elif "unused variable" in message:
                    # For unused variable issues, extract the variable name from the message
                    var_name_match = re.search(r"'([^']+)'", message)
                    if var_name_match:
                        var_name = var_name_match.group(1)
                        # Find the variable name in the line
                        var_pos = line_content.find(var_name)
                        if var_pos >= 0:
                            end_pos = var_pos + len(var_name)
                        else:
                            # Fallback: mark whole line for long variable names
                            end_pos = len(line_content.strip())
                    else:
                        # Fallback: mark a larger portion of the line
                        end_pos = min(col0 + 20, len(line_content.strip()))
                
                elif "function" in message or "method" in message:
                    # For function/method issues, mark until parenthesis or whitespace
                    end_pos = col0
                    while end_pos < len(line_content) and line_content[end_pos] not in '( \t':
                        end_pos += 1
                
                else:
                    # Method 2: Generic identifier/word boundary detection
                    if col0 < len(line_content):
                        # If starting with quote, find string boundaries
                        if line_content[col0] in ['"', "'"]:
                            quote = line_content[col0]
                            end_pos = col0 + 1
                            while end_pos < len(line_content) and line_content[end_pos] != quote:
                                if line_content[end_pos] == '\\':  # Skip escaped characters
                                    end_pos += 1
                                end_pos += 1
                            if end_pos < len(line_content):  # Include closing quote
                                end_pos += 1
                        else:
                            # Mark identifier/word
                            while end_pos < len(line_content) and (line_content[end_pos].isalnum() or line_content[end_pos] in '_'):
                                end_pos += 1
                            # If we didn't find anything significant, mark at least a few characters
                            if end_pos <= col0:
                                end_pos = min(col0 + 5, len(line_content))
                
                # Ensure we mark at least one character and don't exceed line length
                end_col = max(col0 + 1, min(end_pos, len(line_content)))
        
        diagnostics.append(
            {
                "tool": "pylint",
                "type": sev_type[sev],
                "module": issue.get("module", module_name),
                "obj": issue.get("obj", ""),
                "line": line0,
                "column": col0,
                "endLine": end_line,
                "endColumn": end_col,
                "message": issue.get("message", ""),
                "symbol": issue.get("symbol", ""),
                "message-id": issue.get("message-id", ""),
                "severity": sev,
            }
        )

    # -------------------------- mypy --------------------------------
    proc = subprocess.run(
        ["mypy", py_path, "--show-column-numbers", "--no-error-summary"],
        capture_output=True,
        text=True,
    )
    
    # Parse mypy output (format: filename:line:column: error_type: message)
    for line in proc.stdout.splitlines():
        if ":" in line and py_path in line:
            parts = line.split(":", 4)
            if len(parts) >= 4:
                try:
                    line_num = int(parts[1]) - 1  # Convert to 0-based
                    col_num = int(parts[2]) if parts[2].isdigit() else 0
                    error_type = parts[3].strip()
                    message = parts[4].strip() if len(parts) > 4 else ""
                    
                    # Determine severity based on error type
                    sev = 1 if error_type == "error" else 2  # error or warning
                    
                    # Calculate better end position for mypy errors
                    end_line = line_num
                    end_col = col_num + 1  # Default fallback
                    
                    if line_num < len(file_lines):
                        line_content = file_lines[line_num].rstrip('\n\r')
                        
                        if col_num < len(line_content):
                            # For mypy, try to find the full identifier or type annotation
                            end_pos = col_num
                            
                            # Type annotation errors - mark the whole type
                            if "type" in message.lower() or "annotation" in message.lower():
                                # Look for type annotations like : int, -> str, etc.
                                if col_num > 0 and line_content[col_num-1:col_num+1] in [':', '-']:
                                    # Skip whitespace after : or ->
                                    while end_pos < len(line_content) and line_content[end_pos].isspace():
                                        end_pos += 1
                                    # Mark the type name
                                    while end_pos < len(line_content) and (line_content[end_pos].isalnum() or line_content[end_pos] in '_.[]'):
                                        end_pos += 1
                                else:
                                    # Mark identifier
                                    while end_pos < len(line_content) and (line_content[end_pos].isalnum() or line_content[end_pos] in '_'):
                                        end_pos += 1
                            else:
                                # Default: mark identifier
                                while end_pos < len(line_content) and (line_content[end_pos].isalnum() or line_content[end_pos] in '_'):
                                    end_pos += 1
                            
                            end_col = max(col_num + 1, min(end_pos, len(line_content)))
                    
                    diagnostics.append(
                        {
                            "tool": "mypy",
                            "type": sev_type.get(sev, "warning"),
                            "module": module_name,
                            "obj": "",
                            "line": line_num,
                            "column": col_num,
                            "endLine": end_line,
                            "endColumn": end_col,
                            "message": message,
                            "symbol": "mypy",
                            "message-id": error_type,
                            "severity": sev,
                        }
                    )
                except (ValueError, IndexError):
                    continue

    # -------------------------- flake8 ------------------------------
    proc = subprocess.run(
        ["flake8", py_path, "--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s"],
        capture_output=True,
        text=True,
    )
    
    # Parse flake8 output (format: filename:line:column:code:message)
    for line in proc.stdout.splitlines():
        if ":" in line and py_path in line:
            parts = line.split(":", 4)
            if len(parts) >= 4:
                try:
                    line_num = int(parts[1]) - 1  # Convert to 0-based
                    col_num = int(parts[2]) - 1 if parts[2].isdigit() else 0  # flake8 uses 1-based columns
                    code = parts[3].strip()
                    message = parts[4].strip() if len(parts) > 4 else ""
                    
                    # All flake8 issues are warnings
                    sev = 2
                    
                    # Calculate better end position for flake8 errors
                    end_line = line_num
                    end_col = col_num + 1  # Default fallback
                    
                    if line_num < len(file_lines):
                        line_content = file_lines[line_num].rstrip('\n\r')
                        
                        if col_num < len(line_content):
                            end_pos = col_num
                            
                            # Line length errors - mark the whole excess
                            if "line too long" in message.lower():
                                end_col = len(line_content)
                            # Import errors - mark the import statement
                            elif code.startswith('F4') or "import" in message.lower():
                                # Look for import keyword and module name
                                import_match = re.search(r'import\s+([a-zA-Z0-9_.]+)', line_content[col_num:])
                                if import_match:
                                    end_pos = col_num + import_match.end()
                                else:
                                    # Mark identifier
                                    while end_pos < len(line_content) and (line_content[end_pos].isalnum() or line_content[end_pos] in '_.'):
                                        end_pos += 1
                            else:
                                # Default: mark identifier or symbol
                                while end_pos < len(line_content) and (line_content[end_pos].isalnum() or line_content[end_pos] in '_'):
                                    end_pos += 1
                            
                            end_col = max(col_num + 1, min(end_pos, len(line_content)))
                    
                    diagnostics.append(
                        {
                            "tool": "flake8",
                            "type": sev_type.get(sev, "warning"),
                            "module": module_name,
                            "obj": "",
                            "line": line_num,
                            "column": col_num,
                            "endLine": end_line,
                            "endColumn": end_col,
                            "message": message,
                            "symbol": code,
                            "message-id": code,
                            "severity": sev,
                        }
                    )
                except (ValueError, IndexError):
                    continue

    return diagnostics
