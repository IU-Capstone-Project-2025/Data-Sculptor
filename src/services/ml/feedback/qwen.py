"""Module for Qwen LLM integration in the feedback service.

This module provides functionality to interact with the Qwen LLM through LangChain,
enabling AI-powered feedback generation. It handles client initialization and
configuration with support for thinking capabilities.

Public API:
    - get_qwen_client: Creates and configures a Qwen LLM client with optional
      thinking capabilities for feedback generation.
"""

from langchain_core.runnables import Runnable
from langchain_qwq import ChatQwQ


from settings import settings


def get_qwen_client(
    enable_thinking: bool = False, thinking_budget: int = 1000, **kwargs
) -> Runnable:
    """Creates and configures a Qwen LLM client for the feedback service.

    This function initializes a ChatQwQ model with specified thinking capabilities
    and returns it as a LangChain runnable. The model is configured using settings
    from the feedback service configuration.

    Args:
        enable_thinking: Whether to enable thinking.
        thinking_budget: The budget for thinking.

    Returns:
        Runnable: A configured LangChain runnable instance of the Qwen LLM client.
    """
    llm = ChatQwQ(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model_kwargs={
            "extra_body": {
                "chat_template_kwargs": {
                    "enable_thinking": enable_thinking,
                    "thinking_budget": thinking_budget,
                }
            }
        },
        **kwargs,
    )
    return llm
