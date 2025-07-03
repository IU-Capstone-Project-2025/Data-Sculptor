"""Feedback generation utilities unified into a single class.

This refactor merges previous standalone *generate_feedback* and
*generate_warnings* helpers into :class:`FeedbackGenerator`. The class uses
dependency-injected *llm_client* and :class:`ProfileContextGateway` instances
to keep responsibilities clearly separated and testable.
"""

from __future__ import annotations

import uuid
import logging
from typing import List

from langchain_core.runnables import Runnable

from prompts import FEEDBACK_WITH_PROFILE_PROMPT, WARNINGS_WITH_PROFILE_PROMPT

from schemas import LocalizedWarning, Range, Position
from llm_schemas import WarningList

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
    ) -> tuple[str, List[LocalizedWarning]]:
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

        non_localized = await self._generate_non_localized(
            user_code=user_code,
            profile_desc=profile_desc,
            section_desc=section_desc,
            reference_code=reference_code,
        )

        localized = await self._generate_localized(
            user_code=user_code,
            profile_desc=profile_desc,
            section_desc=section_desc,
            reference_code=reference_code,
            line_offset=global_line_offset,
        )

        return non_localized, localized

    async def _generate_non_localized(
        self,
        *,
        user_code: str,
        profile_desc: str,
        section_desc: str,
        reference_code: str,
    ) -> str:
        """Generate high-level textual feedback.

        Args:
            user_code: User-submitted code snippet.
            profile_desc: Full description of the profile/task.
            section_desc: Description of the specific section.
            reference_code: Reference implementation for the section.

        Returns:
            str: A narrative feedback paragraph.
        """

        chain = FEEDBACK_WITH_PROFILE_PROMPT | self._llm

        response = await chain.ainvoke(
            {
                "profile_desc": profile_desc,
                "section_desc": section_desc,
                "reference_code": reference_code,
                "user_code": user_code,
            }
        )

        return getattr(response, "content", str(response))

    async def _generate_localized(
        self,
        *,
        user_code: str,
        profile_desc: str,
        section_desc: str,
        reference_code: str,
        line_offset: int = 0,
    ) -> List[LocalizedWarning]:
        """Generate LSP-compatible diagnostics.

        Args:
            user_code: User-submitted code snippet.
            profile_desc: Description of the profile.
            section_desc: Description of the section.
            reference_code: Reference implementation.
            line_offset: Global zero-based line offset.

        Returns:
            list[LocalizedWarning]: List of warnings with precise ranges.
        """

        numbered_code = "\n".join(
            f"{idx + 1} | {line}" for idx, line in enumerate(user_code.splitlines())
        )

        structured_llm = self._llm.with_structured_output(WarningList)
        chain = WARNINGS_WITH_PROFILE_PROMPT | structured_llm

        try:
            warnings_obj: WarningList = await chain.ainvoke(
                {
                    "profile_desc": profile_desc,
                    "section_desc": section_desc,
                    "reference_code": reference_code,
                    "user_code": numbered_code,
                }
            )
            warnings_list = warnings_obj.warnings
        except Exception:
            logger.warning("Error occurred while generating warnings", exc_info=True)
            warnings_list = []

        lines = user_code.splitlines()
        max_line_index = len(lines)

        localized: list[LocalizedWarning] = []
        for item in warnings_list:
            start_line = item.start_line
            end_line = item.end_line
            msg = item.message

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

        return localized
