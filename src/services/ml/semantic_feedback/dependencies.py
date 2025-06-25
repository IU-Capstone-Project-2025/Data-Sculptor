from typing import Annotated

from fastapi import Body

from shared_ml.qwen import get_qwen_client
from schemas import FeedbackRequest
from settings import settings


def get_llm_client(body: Annotated[FeedbackRequest, Body(...)]):
    """Return a configured Qwen LLM client for this request."""
    return get_qwen_client(
        llm_base_url=settings.llm_base_url,
        llm_api_key=settings.llm_api_key,
        llm_model=settings.llm_model,
        enable_thinking=body.use_deep_analysis,
    ) 