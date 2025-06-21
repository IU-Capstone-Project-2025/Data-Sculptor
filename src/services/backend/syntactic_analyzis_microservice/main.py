import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from analysis_runner import run_all_linters

app = FastAPI(title="Static Analysis Service")


class DiagnosticsResponse(BaseModel):
    diagnostics: list[dict]


@app.post("/analyze", response_model=DiagnosticsResponse)
async def analyze_code(code_file: UploadFile = File(...)):
    """
    Accepts a single .py file, runs configured linters on it, and returns diagnostics.
    """
    filename = code_file.filename or ""
    # 1) Only .py files supported
    if not filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only .py files are supported")

    # 2) Read and decode file contents
    data = await code_file.read()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text")

    # 3) Write to a temporary .py file
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(text)
        tmp_path = tmp.name

    # 4) Run linters on the temp file
    try:
        diagnostics = run_all_linters(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Linting failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # 5) Return the collected diagnostics
    return JSONResponse({"diagnostics": diagnostics})
