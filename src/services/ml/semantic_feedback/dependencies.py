from typing import Annotated

from fastapi import Body, Request
from fastapi import Depends

from shared_ml.qwen import get_qwen_client
from settings import settings

from profile_context import ProfileContextGateway
from feedback_generator import FeedbackGenerator


def get_llm_client(body: Annotated[dict, Body(...)]):
    """Return a configured Qwen LLM client for this request."""
    return get_qwen_client(
        llm_base_url=settings.llm_base_url,
        llm_api_key=settings.llm_api_key,
        llm_model=settings.llm_model,
        enable_thinking=body["use_deep_analysis"],
        temperature=0.0,
    )


# Database pool dependency
def get_pg_pool(request: Request):
    """Return the shared *asyncpg* connection pool from the lifespan state."""

    return request.state.postgres_pool


# Dependency returning a ProfileContextGateway
def get_profile_context(pg_pool=Depends(get_pg_pool)) -> ProfileContextGateway:  # type: ignore
    return ProfileContextGateway(pg_pool)


# Dependency returning a FeedbackGenerator instance
def get_feedback_generator(
    llm_client=Depends(get_llm_client),
    profile_ctx: ProfileContextGateway = Depends(get_profile_context),
):
    return FeedbackGenerator(llm_client=llm_client, profile_context=profile_ctx)
