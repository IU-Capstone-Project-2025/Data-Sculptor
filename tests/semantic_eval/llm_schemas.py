"""Pydantic schemas for structured evaluation output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationRawResult(BaseModel):
    """Raw observations from LLM evaluation - no calculations."""

    # Observability
    false_positives_issues: list[str] = Field(
        description="List of issues mentioned by router that are NOT in problems_to_detect"
    )
    false_negatives_issues: list[str] = Field(
        description="List of issues mentioned in problems_to_detect that router feedback failed to mention"
    )
    non_consequence_language_issues: list[str] = Field(
        description="List of issues mentioned by router that are not described using consequence language rather than solution suggestions"
    )

    # Metrics
    ml_terms_found_count: int = Field(
        ge=0, description="Count of required ML terms found in router feedback"
    )
    true_positives_issue_count: int = Field(
        ge=0, description="Count of required issues correctly identified by router"
    )
    false_positives_issues_count: int = Field(
        ge=0,
        description="Count of issues mentioned by router that are NOT in problems_to_detect",
    )
    is_profile_detail_mentioned: bool = Field(
        description="Whether router feedback mentions case profile details (variable names, code fragments)"
    )
    consequence_language_issues_count: int = Field(
        ge=0,
        description="Count of issues described using consequence language rather than solution suggestions",
    )
