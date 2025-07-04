"""Feedback generation utilities unified into a single class.

This refactor merges previous standalone *generate_feedback* and
*generate_warnings* helpers into :class:`FeedbackGenerator`. The class uses
dependency-injected *llm_client* and :class:`ProfileContextGateway` instances
to keep responsibilities clearly separated and testable.
"""

from __future__ import annotations

import uuid
import logging

from langchain_core.runnables import Runnable

from prompts import COMBINED_FEEDBACK_PROMPT

from schemas import LocalizedWarning, Range, Position
from llm_schemas import CombinedFeedback

from profile_context import ProfileContextGateway

logger = logging.getLogger(__name__)


class FeedbackGenerator:
    """Generate non-localized and localized feedback for notebook code snippets.

    Parameters
    ----------
    llm_client : Runnable
        Initialised LLM client (LangChain runnable).
    profile_context : ProfileContextGateway
        Gateway responsible for fetching reference profile information.
    """

    def __init__(self, llm_client: Runnable, profile_context: ProfileContextGateway):
        self._llm = llm_client
        self._profiles = profile_context

    async def generate_feedback(
        self,
        user_code: str,
        profile_id: uuid.UUID,
        section_index: int,
        global_line_offset: int = 0,
    ) -> tuple[str, list[LocalizedWarning]]:
        """Generate both non-localized and localized feedback.

        The method performs **one** database query to retrieve the profile
        context and then delegates the actual LLM calls to internal helper
        methods that reuse this context.

        Args:
            user_code: Source code provided by the user (single cell).
            profile_id: UUID of the reference *profile* (ethalon notebook).
            section_index: Zero-based index of the section inside the profile.
            global_line_offset: Line offset applied to all diagnostics so they
                align with the full notebook (default 0).

        Returns:
            tuple[str, list[LocalizedWarning]]: A tuple containing the
            free-form, high-level feedback string and a list of
            `LocalizedWarning` objects suitable for LSP clients.
        """

        (
            profile_desc,
            section_desc,
            reference_code,
        ) = await self._profiles.get_section(profile_id, section_index)

        non_localized, localized = await self._generate_combined(
            user_code=user_code,
            profile_desc=profile_desc,
            section_desc=section_desc,
            reference_code=reference_code,
            line_offset=global_line_offset,
        )

***REMOVED*** non_localized, localized

    async def _generate_combined(
        self,
        *,
        user_code: str,
        profile_desc: str,
        section_desc: str,
        reference_code: str,
        line_offset: int = 0,
    ) -> tuple[str, list[LocalizedWarning]]:
        """Generate both conceptual and localised feedback in a *single* LLM call.

        The method leverages the new ``COMBINED_FEEDBACK_PROMPT`` together with
        a structured output model (:class:`CombinedFeedback`).  After obtaining
        the raw LLM response we convert the line-based warnings into
        :class:`LocalizedWarning` instances used by the public API.

        Args:
            user_code: The code snippet provided by the user.
            profile_desc: Full profile description.
            section_desc: Current section description.
            reference_code: Canonical reference implementation.
            line_offset: Zero-based line offset to align diagnostics with the
                full notebook.

        Returns:
            tuple[str, list[LocalizedWarning]]: High-level conceptual feedback
                (bullet-point string) and list of localised warnings.
        """

        # Annotate user code with line numbers for easier localisation.
        numbered_code = "\n".join(
            f"{idx + 1} | {line}" for idx, line in enumerate(user_code.splitlines())
        )

        structured_llm = self._llm.with_structured_output(CombinedFeedback)
        chain = COMBINED_FEEDBACK_PROMPT | structured_llm
        combo: CombinedFeedback = await chain.ainvoke(
            {
                "profile_desc": profile_desc,
                "section_desc": section_desc,
                "reference_code": reference_code,
                "user_code": numbered_code,
            }
        )

        # ── Build conceptual feedback string ────────────────────────────────
        conceptual_bullets = [f"- {item}" for item in combo.conceptual if item]
        conceptual_feedback = "\n".join(conceptual_bullets)

        # ── Convert WarningSpan objects to LocalizedWarning ────────────────
        lines = user_code.splitlines()
        max_line_index = len(lines)

        localized: list[LocalizedWarning] = []
        for span in combo.warnings:
            start_line = span.start_line
            end_line = span.end_line
            msg = span.message

            if (
                start_line < 1
                or end_line < start_line
                or end_line > max_line_index
                or not msg
            ):
                continue

            start_zero = line_offset + start_line - 1
            end_zero = line_offset + end_line - 1

            start_char = 0
            end_char = len(lines[end_line - 1])

            localized.append(
                LocalizedWarning(
                    range=Range(
                        start=Position(line=start_zero, character=start_char),
                        end=Position(line=end_zero, character=end_char),
                    ),
                    message=msg,
                )
            )

***REMOVED*** conceptual_feedback, localized
