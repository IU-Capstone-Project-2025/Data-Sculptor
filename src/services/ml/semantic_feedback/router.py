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
from prompt import FEEDBACK_PROMPT
from qwen import get_qwen_client
from schemas import FeedbackResponse, HealthCheckResponse
from settings import settings

router = APIRouter()

OPENAPI_SPEC_FEEDBACK = yaml.safe_load(
    Path(settings.open_api_folder).joinpath("feedback.yaml").read_text()
)

@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check endpoint",
    tags=["Health"],
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
    use_deep_analysis: bool = Form(False),
) -> FeedbackResponse:
    """Receives a Jupyter notebook, extracts code, and returns general LLM feedback."""
    if not file.filename or not file.filename.endswith(".ipynb"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload a .ipynb file.",
        )

    try:
        llm_client = get_qwen_client(enable_thinking=use_deep_analysis)

        content = await file.read()
        notebook = JupyterNotebook(content)
        code_cells = notebook.get_code_cells()

        if not code_cells:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The notebook does not contain any code cells.",
            )

        formatted_code = "\n---\n".join(code_cells)

        chain = FEEDBACK_PROMPT | llm_client
        response = await chain.ainvoke({"code_cells": formatted_code})
***REMOVED*** FeedbackResponse(feedback=response.content)

    except BadRequestError as openai_error:
        error_body = json.loads(openai_error.response.text)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM request error: {error_body['message']}",
        ) from openai_error

    except Exception as e:
        # Fallback for all other unexpected errors.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feedback: {e}",
        ) from e
