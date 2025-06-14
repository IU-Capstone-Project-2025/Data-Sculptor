# analysis_runner.py

import asyncio
import json
import re
import traceback
from typing import Tuple

from pydantic import BaseModel, Field

# --- LSP Diagnostic Models ---
class Position(BaseModel):
    line: int
    character: int

class Range(BaseModel):
    start: Position
    end: Position

class LspDiagnostic(BaseModel):
    range: Range
    severity: int = Field(..., ge=1, le=4)  # 1=Error, 2=Warning, 3=Info, 4=Hint
    code: str
    source: str
    message: str

async def _run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    """
    Execute an external command and capture stdout/stderr.
    On failure to even start the process, logs the exception and
    returns (–1, "", "<ExceptionType>: <message>").
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as e:
        # Логируем короткое сообщение и полную трассировку
        print("Ошибка запуска команды %r: %s"%( cmd, e))
        print("Полная трассировка:\n%s"% traceback.format_exc())
        # Возвращаем информацию об ошибке в stderr
        return -1, "", f"{type(e).__name__}: {e}"

    # Если процесс успешно запущен — подождём вывода
    out, err = await proc.communicate()
    return proc.returncode, out.decode(errors="ignore"), err.decode(errors="ignore")

# --- Parsing Functions ---
def _parse_pylint(json_output: str) -> list[LspDiagnostic]:
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError:
        return []
    diags: list[LspDiagnostic] = []
    for item in data:
        diags.append(LspDiagnostic(
            range=Range(
                start=Position(line=item.get("line", 1) - 1, character=item.get("column", 1) - 1),
                end=Position(line=item.get("line", 1) - 1, character=item.get("column", 1))
            ),
            severity=1 if item.get("type") == "error" else 2,
            code=item.get("message-id", "pylint"),
            source="pylint",
            message=item.get("message", "")
        ))
    return diags


def _parse_mypy(json_output: str) -> list[LspDiagnostic]:
    try:
        parsed = json.loads(json_output)
    except json.JSONDecodeError:
        return []
    diags: list[LspDiagnostic] = []
    for item in parsed.get("errors", []):
        diags.append(LspDiagnostic(
            range=Range(
                start=Position(line=item.get("line", 1) - 1, character=item.get("column", 1) - 1),
                end=Position(line=item.get("line", 1) - 1, character=item.get("column", 1))
            ),
            severity=1 if item.get("severity", "error") == "error" else 2,
            code=item.get("code", "mypy"),
            source="mypy",
            message=item.get("message", "")
        ))
    return diags


def _parse_dodgy(text: str) -> list[LspDiagnostic]:
    pattern = re.compile(r"^(.*?):(\d+):(\d+):\s+\[([EW]\d+)\]\s+(.*)$", re.M)
    diags: list[LspDiagnostic] = []
    for m in pattern.finditer(text):
        _, line, col, code, msg = m.groups()
        diags.append(LspDiagnostic(
            range=Range(
                start=Position(line=int(line) - 1, character=int(col) - 1),
                end=Position(line=int(line) - 1, character=int(col))
            ),
            severity=2,
            code=code,
            source="dodgy",
            message=msg
        ))
    return diags


def _parse_pydocstyle(json_output: str) -> list[LspDiagnostic]:
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError:
        return []
    diags: list[LspDiagnostic] = []
    for path, issues in data.items():
        for item in issues:
            diags.append(LspDiagnostic(
                range=Range(
                    start=Position(line=item.get("line", 1) - 1, character=item.get("column", 1) - 1),
                    end=Position(line=item.get("line", 1) - 1, character=item.get("column", 1))
                ),
                severity=3,
                code=item.get("code", "D???"),
                source="pydocstyle",
                message=item.get("message", "")
            ))
    return diags


def _parse_vulture(text: str) -> list[LspDiagnostic]:
    pattern = re.compile(r"^(.*?):(\d+): (.*?) \(confidence: [\d\.]+\)$", re.M)
    diags: list[LspDiagnostic] = []
    for m in pattern.finditer(text):
        _, line, msg = m.groups()
        diags.append(LspDiagnostic(
            range=Range(
                start=Position(line=int(line) - 1, character=0),
                end=Position(line=int(line) - 1, character=0)
            ),
            severity=3,
            code="VULTURE",
            source="vulture",
            message=msg
        ))
    return diags


async def run_all_linters(py_path: str) -> list[dict]:
    cmds = {
        "pylint": ["pylint", "--output-format=json", py_path],
        "mypy":   ["mypy", "--hide-error-context", "--no-color-output",
                   "--error-summary", "--show-error-codes", "--json-output", py_path],
        "dodgy":  ["dodgy", py_path],
        "pydocstyle": ["pydocstyle", "--format=json", py_path],
        "vulture": ["vulture", "--min-confidence", "50", py_path],
    }

    tasks = {name: asyncio.create_task(_run_cmd(cmd)) for name, cmd in cmds.items()}
    results: dict[str, str] = {}
    for name, task in tasks.items():
        code, out, err = await task
        # Prefer stdout, fallback to stderr
        results[name] = out.strip() if out.strip() else err.strip()

    diagnostics: list[LspDiagnostic] = []
    # Safely parse each linter
    diagnostics += _parse_pylint(results.get("pylint", ""))
    diagnostics += _parse_mypy(results.get("mypy", ""))
    diagnostics += _parse_dodgy(results.get("dodgy", ""))
    diagnostics += _parse_pydocstyle(results.get("pydocstyle", ""))
    diagnostics += _parse_vulture(results.get("vulture", ""))

    # Return plain dicts
    return [diag.dict() for diag in diagnostics]
