# main.py
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .analysis_runner import run_all_linters

from fastapi.middleware.cors import CORSMiddleware

class DiagnosticsResponse(BaseModel):
    """Ответ с диагностическими сообщениями от линтеров."""

    diagnostics: list[dict] = Field(
        ..., description="Список LSP-совместимых диагностик, собранных всеми линтерами",
        examples=[
            [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 5},
                    },
                    "severity": 2,
                    "message": "Unused import os",
                    "source": "pylsp_vulture",
                }
            ]
        ],
    )

app = FastAPI(
    title="Syntactic Analysis Service",
    version="1.0.0",
    description=(
        "Микросервис запускает набор статических линтеров (ruff, bandit, vulture и др.) "
        "для uploaded Python-файла и возвращает объединённый список диагностик в формате LSP."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # Allow cookies and authorization headers
    allow_methods=["*"],     # Allow all HTTP methods (GET, POST, PUT, etc.)
    allow_headers=["*"],     # Allow all headers
)

@app.post(
    "/analyze",
    response_model=DiagnosticsResponse,
    summary="Запустить синтаксический анализ кода",
    description="Принимает Python-файл, прогоняет несколько линтеров и возвращает список диагностик.",
    tags=["Analysis"],
)
async def analyze_code(
    code_file: UploadFile = File(..., description="Файл с Python-кодом (.py) для проверки"),
):
    # if not code_file.filename.endswith(".py"):
    #     raise HTTPException(status_code=400, detail="Only .py files are supported")

    content = (await code_file.read()).decode("utf-8", errors="ignore")

    with tempfile.NamedTemporaryFile(suffix=".py", delete=False,
                                     mode="w", encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # run_all_linters синхронный → завернём в пул, чтобы не блокировать event-loop
        diagnostics = await run_in_threadpool(run_all_linters, tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # ⚠️ НИЧЕГО НЕ УРЕЗАЕМ – отдаём как есть
    return JSONResponse({"diagnostics": diagnostics})
