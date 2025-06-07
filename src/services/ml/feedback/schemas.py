"""Module for defining API schemas for the feedback service.

This module contains Pydantic models used for request and response
data validation in the FastAPI application.

Public API:
    - HealthCheckResponse: Schema for the health check endpoint.
    - FeedbackResponse: Schema for the feedback endpoint response.
"""

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Response model for the health check endpoint."""

    status: str = Field(..., example="ok")


class FeedbackResponse(BaseModel):
    """Response model for the feedback endpoint."""

    feedback: str = Field(
        ...,
        example="The notebook provides a good starting point for analysis.",
    )
