"""API router for the Profile Uploader service."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status

from schemas import HealthCheckResponse, UploadResponse
from dependencies import get_profile_service
from profile_uploader import ProfileUploader, NotebookParseError

router = APIRouter()
logger = logging.getLogger(__name__)

# Load OpenAPI spec relative to this file regardless of CWD
OPENAPI_SPEC_UPLOAD = yaml.safe_load(
    (Path(__file__).parent / "docs" / "openapi" / "upload.yaml").read_text()
)


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check",
    tags=["Health"],
)
async def health_check() -> HealthCheckResponse:
    """Simple liveness probe used by orchestration systems."""

    return HealthCheckResponse(status="ok")


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload profile notebook",
    tags=["Profiles"],
    openapi_extra=OPENAPI_SPEC_UPLOAD,
)
async def upload_profile(
    profile_file: UploadFile = File(..., description="Notebook file (.ipynb)"),
    service: ProfileUploader = Depends(get_profile_service),
) -> UploadResponse:
    """Persist a notebook profile and return the generated *profile_id*."""

    if not profile_file.filename.endswith(".ipynb"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="profile_file must be a .ipynb notebook",
        )

    content = await profile_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    try:
        profile_id = await service.store_profile(content)
    except NotebookParseError as parse_err:
        logger.error("Invalid notebook uploaded", exc_info=True)
        raise HTTPException(status_code=400, detail=str(parse_err)) from parse_err
    except Exception as exc:
        logger.error("Unexpected error while storing profile", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return UploadResponse(profile_id=profile_id)
