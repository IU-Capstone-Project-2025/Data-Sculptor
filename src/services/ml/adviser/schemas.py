"""Pydantic models for the adviser chat service."""

from pydantic import BaseModel, Field, UUID4
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

    def to_langchain(self) -> BaseMessage:
        if self.role == "system":
            return SystemMessage(content=self.content)
        if self.role == "assistant":
            return AIMessage(content=self.content)
        return HumanMessage(content=self.content)

    @staticmethod
    def to_langchain_list(messages: list["Message"]) -> list[BaseMessage]:  # noqa: D401
        return [m.to_langchain() for m in messages]


class Position(BaseModel):
    line: int = Field(..., ge=0, description="Zero-based line index.")
    character: int = Field(0, description="Zero-based character offset.")


class Range(BaseModel):
    start: Position
    end: Position


class LocalizedWarning(BaseModel):
    range: Range
    severity: Literal[2] = 2
    code: Literal["custom-warning"] = "custom-warning"
    source: Literal["Data Sculptor"] = "Data Sculptor"
    message: str

    def get_llm_description(self) -> str:
        """Return a concise textual description suitable for LLM input."""
        start = (
            self.range.start.line + 1
        )  # convert zero-based to one-based for readability
        end = self.range.end.line + 1
        if start == end:
            line_part = f"Line {start}"
        else:
            line_part = f"Lines {start}-{end}"
        return f"{line_part}: {self.message}"


class ChatResponse(BaseModel):
    message: str = Field(..., description="Response message.")


class ChatRequest(BaseModel):
    conversation_id: UUID4 = Field(..., description="Conversation identifier, UUID.")
    user_id: UUID4 = Field(..., description="User identifier, UUID or similar.")
    message: str = Field(..., description="User's current message/question.")
    current_code: str = Field(..., description="Code snippet to analyse.")
    cell_code_offset: int = Field(
        0, ge=0, description="Global line offset inside the notebook."
    )
    current_non_localized_feedback: str = Field(
        "", description="Existing high-level feedback for the code."
    )
    current_localized_feedback: list[LocalizedWarning] = Field(
        default_factory=list, description="Existing line-localized warnings."
    )
    use_deep_analysis: bool = Field(
        False, description="Whether to use deep analysis for the response."
    )


class HealthCheckResponse(BaseModel):
    status: str = Field(..., example="ok")
