# main.py

import json
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import nbformat
from nbconvert import PythonExporter

from analysis_runner import run_all_linters, LspDiagnostic

# --- Logging setup ---
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- FastAPI app and exception handler ---
app = FastAPI(title="Notebook Static Analysis", debug=True)

@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error during analysis", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# --- Response model ---
class DiagnosticsResponse(BaseModel):
    diagnostics: list[LspDiagnostic]

# --- Notebook analysis endpoint ---
@app.post("/analyze", response_model=DiagnosticsResponse)
async def analyze_notebook(nb_file: UploadFile = File(...)):
    # 1. Read raw notebook JSON
    raw = (await nb_file.read()).decode("utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in notebook: {e}")

    # 2. Auto-inject required v4 code-cell fields and normalize source
    for cell in data.get("cells", []):
        cell_type = cell.get("cell_type")
        if cell_type == "code":
            cell.setdefault("execution_count", None)
            cell.setdefault("outputs", [])
        # Ensure source is a string (nbformat allows list of lines)
        src = cell.get("source")
        if isinstance(src, list):
            cell["source"] = "".join(src)

    # 3. Convert to NotebookNode
    try:
        nb = nbformat.from_dict(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Notebook validation failed: {e}")

    # 4. Export to .py source
    exporter = PythonExporter()
    try:
        source, _ = exporter.from_notebook_node(nb)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert notebook to Python: {e}")

    # 5. Write source to a temp file and run linters
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(source)
        py_path = tmp.name

    # 6. Run all linters in parallel
    try:
        diagnostics = await run_all_linters(py_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Linting failed: {e}")

    return JSONResponse({"diagnostics": diagnostics})
