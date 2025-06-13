"""Module for the API router of the feedback service.

This module defines the API endpoints for the feedback service,
including a health check and the notebook feedback submission endpoint.

Public API:
    - router: The FastAPI APIRouter instance.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from openai import BadRequestError

from notebook import JupyterNotebook
from feedback_generator import generate_feedback
from warnings_generator import generate_warnings
from qwen import get_qwen_client
from settings import settings
from schemas import FeedbackResponse, HealthCheckResponse

router = APIRouter()

OPENAPI_SPEC_FEEDBACK = yaml.safe_load(
    Path(settings.open_api_folder).joinpath("feedback.yaml").read_text()
)

@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check endpoint",
    tags=["Health"],
    openapi_extra=OPENAPI_SPEC_FEEDBACK,
)
async def health_check() -> HealthCheckResponse:
    """Performs a health check of the service."""
    return HealthCheckResponse(status="ok")


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Submit a Jupyter Notebook for automated code feedback",
    tags=["Feedback"],
    openapi_extra=OPENAPI_SPEC_FEEDBACK,
)
async def get_feedback(
    file: UploadFile = File(...),
    target_cell_id: int = Form(-1),
    use_deep_analysis: bool = Form(False),
) -> FeedbackResponse:
    """Receives a Jupyter notebook, extracts code, and returns general LLM feedback."""
    try:
        if not file.filename or not file.filename.endswith(".ipynb"):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .ipynb file.")
        
        llm_client = get_qwen_client(enable_thinking=use_deep_analysis)

        notebook = JupyterNotebook(await file.read())
        code_cells = notebook.get_code_cells()
        if not code_cells:
            raise HTTPException(status_code=400, detail="The notebook does not contain any code cells.")

        formatted_code = "\n".join(code_cells)
        
        non_localized_feedback = await generate_feedback(formatted_code, llm_client=llm_client)
        
        if target_cell_id == -1:
            warn_code, global_offset = formatted_code, 0
        else:
            warn_code, global_offset = notebook.get_code_cell_with_offset(target_cell_id)

        localized_feedback = await generate_warnings(
            warn_code,
            global_line_offset=global_offset,
            llm_client=llm_client,
        )

        return FeedbackResponse(
            non_localized_feedback=non_localized_feedback,
            localized_feedback=localized_feedback,
        )
    except IndexError:
        raise HTTPException(status_code=400, detail="Invalid target cell index")
    except BadRequestError as openai_error:
        error_body = json.loads(openai_error.response.text)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM request error: {error_body['message']}",
        ) from openai_error

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feedback: {e}")
