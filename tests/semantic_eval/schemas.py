from __future__ import annotations

import uuid
from typing import Any, Literal, TypedDict
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    """Request model for the semantic feedback API.

    Args:
        current_code: The code currently being analyzed.
        section_index: The index of the section in the notebook.
        case_id: The UUID of the case.
        cell_code_offset: The code offset within the cell (default 0).
        use_deep_analysis: Whether to use deep analysis (default True).
    """

    current_code: str
    section_index: int
    case_id: uuid.UUID
    cell_code_offset: int = 0
    use_deep_analysis: bool = True


class FeedbackResponse(BaseModel):
    """Complete router feedback response structure with validation."""

    non_localized_feedback: str = Field(
        default="", description="List of non-localized feedback messages"
    )
    localized_feedback: list[dict] = Field(
        default_factory=list,
        description="List of localized feedback items with range and message data",
    )

    def get_description_for_llm(self) -> str:
        """Get description for LLM."""
***REMOVED*** "-\n".join(self.non_localized_feedback) + "-\n".join(
            [warning["message"] for warning in self.localized_feedback]
        )


# TypedDict definitions for heterogeneous data structures


class TestCaseData(TypedDict):
    """Structure for parsed test case information."""

    profile_path: str
    solution_path: str


class ProfileSectionData(TypedDict):
    """Structure for profile notebook sections."""

    description: str
    code: str


class SolutionSectionData(TypedDict):
    """Structure for solution notebook sections with ML evaluation data."""

    json_data: dict[str, Any]
    code: str
    required_ml_terms: list[str]
    problems_to_detect: list[str]


class LocalizedFeedbackItem(TypedDict):
    """Structure for individual localized feedback items."""

    range: dict[str, Any]
    severity: int
    code: str
    source: str
    message: str


class EvaluationResult(TypedDict):
    """Structure for evaluation results compatible with metrics processing."""

    router_feedback: dict[str, Any]


class AcceptanceCriteriaData(TypedDict):
    """Structure for acceptance criteria in evaluation results."""

    sections_evaluated: str


class QualityAttributesData(TypedDict):
    """Structure for quality attributes in evaluation results."""

    ml_term_ratio: float
    necessary_issues_precision: float
    necessary_issues_recall: float
    no_case_profile_detail: str
    consequence_language_ratio: float


class RouterFeedbackData(TypedDict):
    """Structure for router feedback section in results."""

    acceptance_criteria: AcceptanceCriteriaData
    quality_attributes: QualityAttributesData | dict[str, str]  # dict for error cases


class EvaluationMetrics(TypedDict):
    """Calculated metrics from raw LLM observations."""

    ml_term_ratio: float
    necessary_issues_precision: float
    necessary_issues_recall: float
    no_case_profile_detail: int  # 0 if profile details mentioned, 1 if not mentioned
    consequence_language_ratio: float


class AggregatedMetrics(TypedDict):
    """Aggregated metrics from multiple sections."""

    ml_term_ratio: float
    necessary_issues_precision: float
    necessary_issues_recall: float
    no_case_profile_detail: Literal["1", "0"]
    consequence_language_ratio: float


class ParsedCaseData(TypedDict):
    """Structure for parsed case data."""

    task_desc: str
    profile_sections: list[ProfileSectionData]
    solution_sections: list[SolutionSectionData]
