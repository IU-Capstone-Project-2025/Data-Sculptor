from pylsp import hookimpl
import subprocess
import json
import logging
import os
import tempfile
# Настройка логирования в ~/logs.txt
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

log_file_path = os.path.expanduser("~/logs.txt")
if not log.handlers:
    file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)


@hookimpl
def pylsp_lint(document):
    diagnostics = []

    log.debug(f"[pylsp-bandit] Запуск анализа через Bandit...{document.path}")

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
        tmp.write(document.source)
        tmp_path = tmp.name

    try:
        results = subprocess.run(
            ["bandit", "-f", "json", "-q", tmp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except Exception as e:
        log.error(f"[pylsp-bandit] Ошибка выполнения Bandit: {e}")
***REMOVED*** []
    finally:
        os.unlink(tmp_path)

    try:
        data = json.loads(results.stdout)
    except json.JSONDecodeError as e:
        log.error(f"[pylsp-bandit] Ошибка разбора JSON-вывода Bandit: {e}")
***REMOVED*** []

    for item in data.get("results", []):
        char_start = item.get("col_offset", 0)
        char_end = item.get("end_col_offset", 0)
        message = (
            f"{item['issue_text']} "
            f"(Severity: {item['issue_severity']}, Confidence: {item['issue_confidence']})"
        )
        log.debug(
            f"[pylsp-bandit] Найдена проблема: {message} "
            f"(line {item['line_range'][0]})"
        )
        diagnostics.append(
            {
                "source": "bandit",
                "range": {
                    "start": {
                        "line": item["line_range"][0] - 1,
                        "character": char_start,
                    },
                    "end": {
                        "line": item["line_range"][-1] - 1,
                        "character": char_end,
                    },
                },
                "message": message,
                "severity": 2,
            }
        )

    log.debug(f"[pylsp-bandit] Возвращено {len(diagnostics)} диагностик.")
    return diagnostics
