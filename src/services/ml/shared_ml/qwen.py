"""Module for Qwen LLM integration shared between ML microservices.

This module provides functionality to interact with the Qwen LLM through LangChain.
"""

from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI


__all__ = [
    "get_qwen_client",
]


def get_qwen_client(
    llm_base_url: str,
    llm_api_key: str,
    llm_model: str,
    enable_thinking: bool = False,
    thinking_budget: int = 1000,
    **kwargs,
) -> Runnable:
    """Create and configure a Qwen LLM client.
    
    Args:
        llm_base_url: Base URL of the LLM service.
        llm_api_key: API key for authentication.
        llm_model: Model identifier.
        enable_thinking: Whether to enable thinking mode.
        thinking_budget: Token budget for thinking mode.
    """

    llm = ChatOpenAI(
        model=llm_model,
        api_key=llm_api_key,
        base_url=llm_base_url,
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