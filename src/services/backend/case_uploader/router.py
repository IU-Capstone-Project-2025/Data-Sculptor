"""API router for the Profile Uploader service."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi import Path as FastAPIPath  # name conflict with pathlib

from .schemas import HealthCheckResponse, UploadResponse
from .dependencies import get_case_uploader
from .profile_uploader import NotebookParseError
from .case_uploader import CaseUploader

router = APIRouter()
logger = logging.getLogger(__name__)

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


# ──────────────────────────────────────────────────────────────────────────────
# Variant 1 documentation: rely on inline descriptions & Pydantic models
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/upload_case/{name}",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a case",
    description=(
        "Upload a full educational/analytics case consisting of: 1) requirements.txt "
        "with Python dependencies, 2) a dataset file, 3) a profile notebook that "
        "describes and demonstrates the solution, 4) a template notebook for "
        "students.  The service validates inputs, builds a Docker image with "
        "repo2docker, stores artefacts in MinIO and records metadata in PostgreSQL.\n\n"
        "Returns JSON with the generated case_id on success."
    ),
    response_model=UploadResponse,
    tags=["Cases"],
)
async def upload_case(
    name: str = FastAPIPath(
        ..., description="Human-readable case name", examples={"example": {"value": "Titanic"}}
    ),
    requirements: UploadFile = File(
        ...,
        description="requirements.txt (only .txt is accepted)",
    ),
    dataset: UploadFile = File(
        ...,
        description="Dataset file (any format: CSV, JSON, Parquet, ZIP, etc.)",
    ),
    profile: UploadFile = File(
        ...,
        description=(
            "Profile notebook (.ipynb). First markdown cell → overall task; subsequent "
            "pairs of markdown (with ```json) + code cells describe sections. Must "
            "contain at least one complete pair."
        ),
    ),
    template: UploadFile = File(
        ..., description="Solution template notebook (.ipynb) shown to students",
    ),
    case_uploader: CaseUploader = Depends(get_case_uploader),
) -> dict[str, str]:
    """Upload a case and process it: build Docker image, store in MinIO, record in DB."""
    try:
        case_id = await case_uploader.upload_case(
            case_name=name,
            requirements=requirements,
            dataset=dataset,
            profile=profile,
            template=template,
        )
        return {"case_id": case_id}
    except ValueError as exc:
        logger.warning("Validation error: %s", str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except NotebookParseError as exc:
        logger.warning("Notebook parsing error: %s", str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error uploading case", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
