"""Pydantic schemas for structured evaluation output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationRawResult(BaseModel):
    """Raw observations from LLM evaluation - no calculations."""

    ml_terms_found: int = Field(
        ge=0, description="Count of required ML terms found in router feedback"
    )
    true_positives: int = Field(
        ge=0, description="Count of required issues correctly identified by router"
    )
    false_positives: int = Field(
        ge=0,
        description="Count of issues mentioned by router that are NOT in problems_to_detect",
    )
    false_negatives: int = Field(
        ge=0, description="Count of required issues missed by router"
    )
    mentions_profile_details: bool = Field(
        description="Whether router feedback mentions case profile details (variable names, code fragments)"
    )
    consequence_language_issues: int = Field(
        ge=0,
        description="Count of issues described using consequence language rather than solution suggestions",
    )
