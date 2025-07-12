from __future__ import annotations

from uuid import UUID
from typing import Any, Dict, Optional

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    status: str


class SaveProgressRequest(BaseModel):
    session_id: UUID
    progress: Dict[str, Any]
    feedback: Optional[Dict[str, Any]] = None


class SaveProgressResponse(BaseModel):
    status: str


class RestoreProgressResponse(BaseModel):
    session_id: UUID
    progress: Dict[str, Any]
    feedback: Optional[Dict[str, Any]] = None 