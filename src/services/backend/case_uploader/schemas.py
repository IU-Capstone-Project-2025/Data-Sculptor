"""Pydantic data models for the Profile Uploader service."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response schema returned after a successful profile upload."""

    case_id: str = Field(
        ...,
        description="Identifier of the persisted case.",
        examples={"example": {"value": "5ca16dbe-4abe-4f75-956f-2e2d9cb04e24"}},
    )


class HealthCheckResponse(BaseModel):
    """Schema used by the liveness probe endpoint."""

    status: str = Field(..., example="ok")


class Section(BaseModel):
    """Section schema."""

    description: str = Field(..., description="Description of the section.")
    code: str = Field(..., description="Code of the section.")
