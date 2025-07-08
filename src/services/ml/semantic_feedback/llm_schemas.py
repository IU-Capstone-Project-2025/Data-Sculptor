"""Pydantic models describing the structured JSON formats we expect from the LLM.

Keeping these definitions in a dedicated module avoids circular imports and
makes it simple to reuse the same schema in multiple generator utilities.
"""

from pydantic import BaseModel, Field


class WarningSpan(BaseModel):
    """A span of lines flagged by the LLM.

    Attributes
    ----------
    start_line : int
        1-based line number where the problematic span begins.
    end_line : int
        1-based line number where the span ends (inclusive).
    message : str
        Short description of the issue (≤120 characters recommended).
    """

    start_line: int = Field(..., description="1-based start line")
    end_line: int = Field(..., description="1-based end line (inclusive)")
    message: str = Field(..., description="Short description of the issue")


class WarningList(BaseModel):
    """Top-level array wrapper so `with_structured_output` accepts one schema."""

    warnings: list[WarningSpan]


class MLScentWarningSpan(BaseModel):
    """Schema describing one localised warning with rationale.

    This model is used exclusively as the *structured output* schema for the
    localisation LLM call. Compared to :class:`WarningSpan`, it contains an
    additional ``rationale`` field that holds the model's explanation of why
    the code span violates the warning.
    """

    start_line: int = Field(..., description="1-based start line of the span")
    end_line: int = Field(..., description="1-based end line (inclusive)")
    description: str = Field(..., description="Warning description.")
    framework: str = Field(..., description="Associated ML/DS framework.")
    fix: str = Field(..., description="Suggested fix for the warning.")
    benefit: str = Field(..., description="Benefit gained by applying the fix.")
    message: str = Field(..., description="Short warning text for end-users")


class MLScentWarningList(BaseModel):
    """Wrapper so LangChain can enforce a JSON array of localised warnings."""

    warnings: list[MLScentWarningSpan]


class CombinedFeedback(BaseModel):
    """Structured output containing both localized and conceptual feedback.

    The ``warnings`` field mirrors :class:`WarningSpan` objects and is intended
    for precise, line-based diagnostics. The ``conceptual`` field holds high-
    level, non-localized issues that apply to the broader code context or
    algorithmic design. Keeping both buckets in one schema allows us to obtain
    the full feedback in a *single* LLM call.
    """

    warnings: list[WarningSpan] = Field(
        default_factory=list,
        description="List of line-scoped warnings (localized).",
    )
    conceptual: list[str] = Field(
        default_factory=list,
        description="List of high-level, non-localized conceptual issues.",
    )
