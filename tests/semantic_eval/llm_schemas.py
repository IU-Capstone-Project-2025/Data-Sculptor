"""Pydantic schemas for structured evaluation output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationRawResult(BaseModel):
    """Raw observations from LLM evaluation - no calculations."""

    # Observability
    long_issues_found: list[str] = Field(
        description="List of issues mentioned in feedback that are described verbosely rather than concisely"
    )
    false_positives_issues: list[str] = Field(
        description="List of issues mentioned in feedback that are NOT in problems_to_detect"
    )
    false_negatives_issues: list[str] = Field(
        description="List of issues mentioned in problems_to_detect that feedback failed to mention"
    )
    profile_detail_mentioned: list[str] = Field(
        description="List of code details mentioned in feedback like variable/function/class names, code fragments"
    )
    non_consequence_language_issues: list[str] = Field(
        description="List of issues mentioned in feedback that are not described using consequence language rather than solution suggestions"
    )

    # Metrics
    brief_issues_count: int = Field(
        ge=0,
        description="Count of issues described concisely with appropriate ML terminology",
    )
    true_positives_issue_count: int = Field(
        ge=0, description="Count of required issues correctly identified by feedback"
    )
    false_positives_issues_count: int = Field(
        ge=0,
        description="Count of issues mentioned in feedback that are NOT in problems_to_detect",
    )
    is_profile_detail_mentioned: bool = Field(
        description="Whether feedback mentions code details like variable/function/class names or code fragments"
    )
    consequence_language_issues_count: int = Field(
        ge=0,
        description="Count of issues described using consequence language rather than solution suggestions",
    )
