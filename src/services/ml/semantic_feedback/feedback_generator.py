"""Utility for producing general, non-localized feedback for a notebook.

Isolated into its own module so it can be reused independently of the API
router (e.g. batch processing scripts) and keeps `router.py` clean.
"""

from __future__ import annotations

from langchain_core.runnables import Runnable

from prompts import FEEDBACK_PROMPT

__all__ = [
    "generate_feedback",
]


async def generate_feedback(
    llm_client: Runnable,
    code: str,
) -> str:
    """Return high-level feedback on an ordered sequence of notebook code cells.

    Args:
        code_cells: iterable of raw source strings from each code cell.
        llm_client: optional pre-initialised Qwen client to reuse the same
            connection across multiple generator calls.

    Returns
    -------
    str
        Free-form text feedback provided by the LLM.
    """

    chain = FEEDBACK_PROMPT | llm_client
    response = await chain.ainvoke({"code": code})

    # LangChain responses often expose `.content`; fall back to str(response)
    return getattr(response, "content", str(response))
