"""FastAPI dependency factories used by the adviser service.

These helpers are responsible for wiring together shared runtime
objects (Redis, Postgres, tokenizer, LLM client) so that they can be
injected into request handlers via FastAPI's dependency mechanism.
"""

from fastapi import Request
from chat_service import ChatService

from typing import Annotated
from fastapi import Body, Depends

from schemas import ChatRequest
from settings import settings
from shared_ml.qwen import get_qwen_client
from tokenizers import Tokenizer
from memory_manager import MemoryManager


def get_memory_manager(request: Request) -> MemoryManager:
    """Return a `MemoryManager` built from objects placed in *request.state*.

    Args:
        request: Incoming FastAPI request whose lifespan middleware has
            populated `state.redis_pool` and `state.postgres_pool`.

    Returns:
        MemoryManager: Wrapper around Redis and Postgres that handles
        conversation history.
    """
    return MemoryManager(request.state.redis_pool, request.state.postgres_pool)


def get_tokenizer(request: Request) -> Tokenizer:
    """Retrieve the shared tokenizer instance from *request.state*.

    Args:
        request: Current request object.

    Returns:
        Tokenizer: Tokenizer compatible with the configured LLM.
    """
    return request.state.tokenizer


def get_chat_service(
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    tokenizer: Annotated[Tokenizer, Depends(get_tokenizer)],
) -> ChatService:
    """Create a `ChatService` with injected dependencies.

    Args:
        memory_manager: Memory manager instance provided by dependency injection.
        tokenizer: Tokenizer instance shared across requests.

    Returns:
        ChatService: Ready-to-use service layer.
    """
    return ChatService(memory_manager, tokenizer)


def get_llm_client(
    body: Annotated[ChatRequest, Body(...)],
):
    """Instantiate and configure the Qwen LLM client.

    The choice to enable the *thinking* (a.k.a. chain-of-thought) mode is
    derived from the request body field *use_deep_analysis*.

    Args:
        body: Parsed request payload.

    Returns:
        Runnable: LangChain runnable wrapping the remote model.
    """
    return get_qwen_client(
        llm_base_url=settings.llm_base_url,
        llm_api_key=settings.llm_api_key,
        llm_model=settings.llm_model,
        enable_thinking=body.use_deep_analysis,
    )
