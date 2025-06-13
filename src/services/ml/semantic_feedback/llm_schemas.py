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