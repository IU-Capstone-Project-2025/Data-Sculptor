# main.py
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from analysis_runner import run_all_linters

class DiagnosticsResponse(BaseModel):
    diagnostics: list[dict]

app = FastAPI()
@app.post("/analyze", response_model=DiagnosticsResponse)
async def analyze_code(code_file: UploadFile = File(...)):
    """Принимает .py-файл, прогоняет линтеры, возвращает LSP-diagnostics."""
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
