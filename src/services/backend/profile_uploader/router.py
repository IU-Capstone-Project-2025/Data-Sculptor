"""API router for the Profile Uploader service."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi import Path as FastAPIPath  # name conflict with pathlib
from typing import Optional

from schemas import HealthCheckResponse, UploadResponse
from dependencies import get_profile_service, get_case_uploader
from profile_uploader import ProfileUploader, NotebookParseError
from case_uploader import CaseUploader

router = APIRouter()
logger = logging.getLogger(__name__)

# Load OpenAPI spec relative to this file regardless of CWD
try:
    OPENAPI_SPEC_UPLOAD = yaml.safe_load(
        (Path(__file__).parent / "docs" / "openapi" / "upload.yaml").read_text()
    )
except Exception as e:
    logger.warning(f"Could not load OpenAPI spec: {e}")
    OPENAPI_SPEC_UPLOAD = {}


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
    "/upload_case/{name}",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a case with requirements, dataset, profile, and template",
    tags=["Cases"],
)
async def upload_case(
    name: str = FastAPIPath(..., description="Case name"),
    requirements: UploadFile = File(..., description="requirements.txt file"),
    dataset: UploadFile = File(..., description="Dataset file"),
    profile: UploadFile = File(..., description="Profile notebook file (.ipynb)"),
    template: UploadFile = File(..., description="Solution template file"),
    case_uploader: CaseUploader = Depends(get_case_uploader),
) -> dict:
    """Upload a case and process it: build Docker image, store in MinIO, record in DB."""
    try:
        # Ensure MinIO bucket exists
        await case_uploader.ensure_minio_bucket_exists()

        case_id = await case_uploader.upload_case(
            case_name=name,
            requirements=requirements,
            dataset=dataset,
            profile=profile,
            template=template,
        )
        return {"status_code": 201, "case_id": case_id}
    except Exception as exc:
        logger.error("Error uploading case", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
