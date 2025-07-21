"""API router for the adviser chat service."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException, Body, Depends, status
from openai import BadRequestError

from schemas import HealthCheckResponse, ChatRequest, ChatResponse
from dependencies import get_chat_service, get_llm_client

router = APIRouter()
logger = logging.getLogger(__name__)

# load ./docs/openapi/chat.yaml relative to this file regardless of cwd
OPENAPI_SPEC_CHAT = yaml.safe_load(
    (Path(__file__).parent / "docs" / "openapi" / "chat.yaml").read_text()
)


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check endpoint",
    tags=["Health"],
)
async def health_check() -> HealthCheckResponse:
    """Simple liveness probe used by orchestration systems."""
    return HealthCheckResponse(status="ok")


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with the LLM",
    tags=["Chat"],
    openapi_extra=OPENAPI_SPEC_CHAT,
)
async def chat(
    body: ChatRequest = Body(...),
    llm_client=Depends(get_llm_client),
    service=Depends(get_chat_service),
) -> ChatResponse:
    """Return an assistant reply based on user code and conversation history."""

    if not body.current_code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current_code must not be empty.",
        )
    try:
        reply: str = await service.generate_response(
            llm_client=llm_client,
            conversation_id=body.conversation_id,
            user_id=body.user_id,
            code=body.current_code,
            non_localized_feedback=body.current_non_localized_feedback,
            localized_feedback=body.current_localized_feedback,
            message=body.message,
        )
        return ChatResponse(message=reply)
    except BadRequestError as openai_error:
        logger.error("LLM request error", exc_info=True)
        error_body = json.loads(openai_error.response.text)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM request error: {error_body['message']}",
        ) from openai_error
    except Exception as exc:
        logger.error("Unexpected error", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
