from __future__ import annotations

"""High-level utility to produce LSP-style warnings for notebook code.

It relies on the same Qwen LLM used for general feedback but forces a very
strict JSON schema to minimise hallucinated ranges. Only the *line* number is
provided by the model – character offsets are post-filled (`0` .. len(line)).
"""

from prompts import WARNINGS_PROMPT

from schemas import LocalizedWarning, Range, Position

from langchain_core.runnables import Runnable

from llm_schemas import WarningList

import logging

logger = logging.getLogger(__name__)

async def generate_warnings(
    llm_client: Runnable,
    code: str,
    global_line_offset: int = 0,
) -> list[LocalizedWarning]:
    """Generate LSP warnings for a piece of code.

    Args:
        code: The code snippet to analyse.
        global_line_offset: Offset applied to line numbers so they map to the
            full notebook (zero-based).
        llm_client: Optional pre-initialised LLM client.

    Returns:
        List[LocalizedWarning] objects. Always within document bounds.
    """

    numbered_code = "\n".join(f"{idx + 1} | {line}" for idx, line in enumerate(code.splitlines()))

    structured_llm = llm_client.with_structured_output(WarningList)
    chain = WARNINGS_PROMPT | structured_llm

    try:
        warnings_obj: WarningList = await chain.ainvoke({"code": numbered_code})
        warnings_list = warnings_obj.warnings
    except Exception:
        logger.warning("Error happened while generating warnings", exc_info=True)
        warnings_list = []

    lines = code.splitlines()
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

        start_zero = global_line_offset + start_line - 1
        end_zero = global_line_offset + end_line - 1

        # Determine character positions
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