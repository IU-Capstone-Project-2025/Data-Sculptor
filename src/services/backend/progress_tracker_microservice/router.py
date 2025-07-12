from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from schemas import (
    HealthCheckResponse,
    SaveProgressRequest,
    SaveProgressResponse,
    RestoreProgressResponse,
)
from dependencies import get_progress_tracker
from progress_tracker import ProgressTracker

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check() -> HealthCheckResponse:  # pragma: no cover
    return HealthCheckResponse(status="ok")


@router.post(
    "/progress",
    response_model=SaveProgressResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Progress"],
)
async def save_progress(
    payload: SaveProgressRequest,
    service: ProgressTracker = Depends(get_progress_tracker),
) -> SaveProgressResponse:
    await service.save_progress(payload.session_id, payload.progress, payload.feedback)
    return SaveProgressResponse(status="saved")


@router.get("/progress/{session_id}", response_model=RestoreProgressResponse, tags=["Progress"])
async def get_progress(
    session_id: UUID,
    service: ProgressTracker = Depends(get_progress_tracker),
) -> RestoreProgressResponse:
    record = await service.get_progress(session_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No progress found for session {session_id}")
    return RestoreProgressResponse(session_id=session_id, **record)


@router.post("/session/close", response_model=SaveProgressResponse, tags=["Session"])
async def session_closed(
    payload: SaveProgressRequest,
    service: ProgressTracker = Depends(get_progress_tracker),
) -> SaveProgressResponse:
    await service.save_progress(payload.session_id, payload.progress, payload.feedback)
    return SaveProgressResponse(status="saved")


@router.get("/session/open/{session_id}", response_model=RestoreProgressResponse, tags=["Session"])
async def session_open(
    session_id: UUID,
    service: ProgressTracker = Depends(get_progress_tracker),
) -> RestoreProgressResponse:
    record = await service.get_progress(session_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No progress found for session {session_id}")
    return RestoreProgressResponse(session_id=session_id, **record) 