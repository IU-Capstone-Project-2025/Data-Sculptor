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
    Depends,
)
import logging
from openai import BadRequestError
import uuid

from feedback_generator import FeedbackGenerator
from warning_localizer import localize_warnings
from schemas import (
    FeedbackResponse,
    HealthCheckResponse,
    FeedbackRequest,
    MLScentLocalizationRequest,
    MLScentLocalizationResponse,
)
from dependencies import get_feedback_generator, get_llm_client

router = APIRouter()
logger = logging.getLogger(__name__)

OPENAPI_SPEC_FEEDBACK = yaml.safe_load(
    (Path(__file__).parent / "docs" / "openapi" / "feedback.yaml").read_text()
)

OPENAPI_SPEC_LOCALIZE = yaml.safe_load(
    (Path(__file__).parent / "docs" / "openapi" / "localize_mlscent.yaml").read_text()
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
    generator: FeedbackGenerator = Depends(get_feedback_generator),
) -> FeedbackResponse:
    """Generate feedback for a code snippet supplied by the client."""

    try:
        if not body.current_code.strip():
            raise HTTPException(
                status_code=400, detail="current_code must not be empty."
            )

        non_localized_feedback, localized_feedback = await generator.generate_feedback(
            user_code=body.current_code,
            profile_id=body.profile_index,
            section_index=body.section_index,
            global_line_offset=body.cell_code_offset,
        )

***REMOVED*** FeedbackResponse(
            non_localized_feedback=non_localized_feedback,
            localized_feedback=localized_feedback,
        )

    except ValueError:
        logger.error(
            f"Profile {body.profile_index} or section {body.section_index} not found"
        )
        raise HTTPException(
            status_code=404,
            detail=f"Profile {body.profile_index} or section {body.section_index} not found",
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


@router.post(
    "/localize_mlscent",
    response_model=MLScentLocalizationResponse,
    summary="Localise high-level warnings into code positions",
    tags=["Localization"],
    openapi_extra=OPENAPI_SPEC_LOCALIZE,
)
async def localize_mlscent(
    body: MLScentLocalizationRequest = Body(...),
    llm_client=Depends(get_llm_client),
) -> MLScentLocalizationResponse:
    """Localise a list of high-level warnings to specific lines of the given code.

    The request body must contain:
        - current_code: The code snippet to analyse.
        - warnings: A list of warnings to be localised.
    """

    try:
        if not body.current_code.strip():
            raise HTTPException(
                status_code=400, detail="current_code must not be empty."
            )
        if not body.warnings:
            raise HTTPException(
                status_code=400, detail="warnings list must not be empty."
            )

        localized_feedback = await localize_warnings(
            llm_client=llm_client,
            code=body.current_code,
            warnings=body.warnings,
            global_line_offset=body.cell_code_offset or 0,
        )

***REMOVED*** MLScentLocalizationResponse(localized_feedback=localized_feedback)

    except BadRequestError as openai_error:
        logger.error("LLM request error", exc_info=True)
        error_body = json.loads(openai_error.response.text)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM request error: {error_body['message']}",
        ) from openai_error

    except Exception as e:
        logger.error("Unexpected error", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to localise warnings: {e}")
