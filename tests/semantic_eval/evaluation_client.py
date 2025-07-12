"""Evaluation client for LLM-based semantic assessment."""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from llm_schemas import EvaluationRawResult
from settings import settings
from prompts import ROUTER_FEEDBACK_EVALUATION_PROMPT
from schemas import SolutionSectionData


class EvaluationClient:
    """Client for evaluating code sections using LLM with structured output.

    This class encapsulates all LLM-related functionality for semantic evaluation,
    including retry logic and structured output parsing.
    """

    def __init__(self):
        """Initialize the evaluation client using global settings."""
        self.llm = ChatOpenAI(
            api_key=settings.evaluator_llm_api_key,
            base_url=settings.evaluator_llm_base_url,
            model=settings.evaluator_llm_model,
            temperature=0,
        )

        # Create structured output chain
        self.structured_llm = self.llm.with_structured_output(EvaluationRawResult)

    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_fixed(settings.retry_delay),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def evaluate_section(
        self,
        task_description: str,
        profile_section_description: str,
        profile_section_code: str,
        solution_section: SolutionSectionData,
        feedback: str,
    ) -> EvaluationRawResult:
        """Evaluate a profile section using LLM with retry logic.

        Args:
            task_description: The overall task description.
            profile_section_description: Description from profile section.
            profile_section_code: Code from profile section.
            solution_section: Solution data with required terms and problems.
            router_feedback: Feedback from router service.

        Returns:
            Structured LLM evaluation result with raw counts and classifications.
        """
        # Format the prompt with provided arguments
        formatted_prompt = ROUTER_FEEDBACK_EVALUATION_PROMPT.format(
            task_description=task_description,
            profile_section_description=profile_section_description,
            profile_section_code=profile_section_code,
            required_ml_terms=solution_section["required_ml_terms"],
            problems_to_detect=solution_section["problems_to_detect"],
            solution_code=solution_section["code"],
            feedback=feedback,
        )
        return self.structured_llm.invoke(formatted_prompt)
