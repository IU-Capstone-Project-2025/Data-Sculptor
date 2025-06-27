"""Utility for localising high-level warnings into LSP-style diagnostics.

This module transforms a list of abstract warning messages into concrete, line-
level diagnostics for a given code snippet. It relies on the same Qwen LLM used
in the service but enforces a rigorous JSON schema to reduce hallucinations.
"""

from __future__ import annotations


import logging
from langchain_core.runnables import Runnable

from prompts import LOCALIZE_WARNINGS_PROMPT
from schemas import LocalizedWarning, Range, Position
from schemas import MLScentWarningItem
from llm_schemas import MLScentWarningList, MLScentWarningSpan

logger = logging.getLogger(__name__)


async def localize_warnings(
    llm_client: Runnable,
    code: str,
    warnings: list[MLScentWarningItem],
    global_line_offset: int = 0,
) -> list[LocalizedWarning]:
    """Localise non-specific warnings to line ranges within *code*.

    Args:
        llm_client: The LangChain `Runnable` that executes the LLM call.
        code: The source code snippet to analyse.
        warnings: A list of warning strings produced by earlier analysis.
        global_line_offset: Offset applied to line numbers so they map to the
            full notebook (zero-based).

    Returns:
        A list of `LocalizedWarning` objects suitable for LSP clients.
    """

    if not warnings:
        return []

    numbered_code = "\n".join(
        f"{idx + 1} | {line}" for idx, line in enumerate(code.splitlines())
    )
    warnings_block = "\n".join(
        f"{idx + 1}. {w.get_llm_description()}" for idx, w in enumerate(warnings)
    )
    structured_llm = llm_client.with_structured_output(MLScentWarningList)
    chain = LOCALIZE_WARNINGS_PROMPT | structured_llm

    try:
        warnings_obj: MLScentWarningList = await chain.ainvoke(
            {"code": numbered_code, "warnings": warnings_block}
        )
        warnings_list: list[MLScentWarningSpan] = warnings_obj.warnings
    except Exception:
        logger.warning("Error occurred while localising warnings", exc_info=True)
        warnings_list = []

    lines = code.splitlines()
    max_line_index = len(lines)

    localized: list[LocalizedWarning] = []
    for item in warnings_list:
        start_line = item.start_line
        end_line = item.end_line
        msg = item.message

        # Validate basic invariants
        if (
            start_line < 1
            or end_line < start_line
            or end_line > max_line_index
            or not msg
        ):
            continue

        start_zero = global_line_offset + start_line - 1
        end_zero = global_line_offset + end_line - 1

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
