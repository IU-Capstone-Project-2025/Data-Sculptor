# main.py
import tempfile
from pathlib import Path

import nbformat
from nbconvert import PythonExporter
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from analysis_runner import run_all_linters

app = FastAPI(title="Static Analysis Service")


class DiagnosticsResponse(BaseModel):
    diagnostics: list[dict]


def _ipynb_to_py(raw_bytes: bytes) -> str:
    """Convert raw .ipynb bytes to python code string."""
    try:
        nb_node = nbformat.reads(raw_bytes.decode("utf-8"), as_version=4)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid notebook: {exc}") from exc

    exporter = PythonExporter()
    py_code, _ = exporter.from_notebook_node(nb_node)
    return py_code


@app.post("/analyze", response_model=DiagnosticsResponse)
async def analyze(code_file: UploadFile = File(...)):
    ext = (code_file.filename or "").lower()

    raw = await code_file.read()
    if ext.endswith(".py"):
        py_source = raw.decode("utf-8", errors="ignore")
    elif ext.endswith(".ipynb"):
        py_source = _ipynb_to_py(raw)
    else:
        raise HTTPException(status_code=400, detail="Only .py or .ipynb accepted")

    # write temp .py
    with tempfile.NamedTemporaryFile(
        suffix=".py", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        tmp.write(py_source)
        tmp_path = tmp.name

    try:
        diagnostics = run_all_linters(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return JSONResponse({"diagnostics": diagnostics})
