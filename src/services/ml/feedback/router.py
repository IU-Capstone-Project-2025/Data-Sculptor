"""Module for the API router of the feedback service.

This module defines the API endpoints for the feedback service,
including a health check and the notebook feedback submission endpoint.

Public API:
    - router: The FastAPI APIRouter instance.
"""

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    status,
    UploadFile,
)

from qwen import get_qwen_client
from notebook import JupyterNotebook
from prompt import FEEDBACK_PROMPT
from schemas import (
    FeedbackResponse,
    HealthCheckResponse,
)


router = APIRouter()


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
    summary="Get feedback on a Jupyter Notebook",
    tags=["Feedback"],
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

        formatted_code = "\\n---\\n".join(code_cells)

        chain = FEEDBACK_PROMPT | llm_client
        response = await chain.ainvoke({"code_cells": formatted_code})
        return FeedbackResponse(feedback=response.content)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feedback from LLM: {e}",
        ) from e
