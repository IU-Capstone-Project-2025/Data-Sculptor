"""Pydantic data models for the Profile Uploader service."""

from __future__ import annotations

from pydantic import BaseModel, Field, UUID4


class UploadResponse(BaseModel):
    """Response schema returned after a successful profile upload."""

    profile_id: UUID4 = Field(..., description="Identifier of the persisted profile.")


class HealthCheckResponse(BaseModel):
    """Schema used by the liveness probe endpoint."""

    status: str = Field(..., example="ok")


class Section(BaseModel):
    """Section schema."""

    description: str = Field(..., description="Description of the section.")
    code: str = Field(..., description="Code of the section.")
