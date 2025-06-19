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
    HTTPException,
    status,
    Body,
)
import logging
from openai import BadRequestError

from feedback_generator import generate_feedback
from warnings_generator import generate_warnings
from shared_ml.qwen import get_qwen_client
from settings import settings
from schemas import FeedbackResponse, HealthCheckResponse, FeedbackRequest

router = APIRouter()
logger = logging.getLogger(__name__)

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
    summary="Submit code for automated feedback",
    tags=["Feedback"],
    openapi_extra=OPENAPI_SPEC_FEEDBACK,
)
async def get_feedback(
    body: FeedbackRequest = Body(...),
) -> FeedbackResponse:
    """Generate feedback for a code snippet supplied by the client.

    The request body must contain:
        - current_code: The code snippet to analyse.
        - cell_code_offset: Global line offset applied to generated warnings.
    """

    try:
        if not body.current_code.strip():
            raise HTTPException(
                status_code=400, detail="current_code must not be empty."
            )

        llm_client = get_qwen_client(
            llm_base_url=settings.llm_base_url,
            llm_api_key=settings.llm_api_key,
            llm_model=settings.llm_model,
            enable_thinking=body.use_deep_analysis,
        )

        non_localized_feedback = await generate_feedback(
            llm_client=llm_client,
            code=body.current_code,
        )

        localized_feedback = await generate_warnings(
            llm_client=llm_client,
            code=body.current_code,
            global_line_offset=body.cell_code_offset,
        )

        return FeedbackResponse(
            non_localized_feedback=non_localized_feedback,
            localized_feedback=localized_feedback,
        )

    except BadRequestError as openai_error:
        logger.error("LLM request error", exc_info=True)
        error_body = json.loads(openai_error.response.text)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM request error: {error_body['message']}",
        ) from openai_error

    except Exception as e:
        logger.error("Unexpected error", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get feedback: {e}")
