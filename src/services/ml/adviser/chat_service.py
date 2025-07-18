"""Chat-service helper that builds prompts, maintains history and calls the LLM."""

from tokenizers import Tokenizer
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from memory_manager import MemoryManager
from settings import settings
from prompts import ADVISOR_PROMPT
from pydantic import UUID4
from langchain_core.runnables import Runnable
from openai import BadRequestError
from tenacity import retry, retry_if_exception_type, stop_after_attempt


class ChatService:
    """Generate assistant replies using a stateless workflow.

    All conversational state is delegated to `MemoryManager` so this
    class focuses exclusively on prompt construction, token budgeting
    and LLM invocation.
    """

    def __init__(self, memory_manager: MemoryManager, tokenizer: Tokenizer):
        self._memory: MemoryManager = memory_manager
        self._tokenizer = tokenizer

    def _count_tokens(self, text: str) -> int:
        """Return the amount of tokens a *text* occupies.

        Args:
            text: Arbitrary plain-text string.

        Returns:
            int: Number of tokens according to the provided tokenizer.
        """
        return len(self._tokenizer.encode(text).ids)

    async def generate_response(
        self,
        llm_client: Runnable,
        conversation_id: UUID4,
        user_id: UUID4,
        code: str,
        non_localized_feedback: list[str],
        localized_feedback: list[str],
        message: str,
    ) -> str:
        """Produce an assistant reply for the current user *message*.

        The function
        1. Builds the full prompt (system + history + user message).
        2. Invokes the LLM asynchronously.
        3. Persists the new user/assistant messages.

        Args:
            llm_client: A LangChain Runnable that wraps the LLM.
            conversation_id: Identifier of the ongoing conversation.
            user_id: Identifier of the user that owns the conversation.
            code: Current code cell/snippet the user is working on.
            non_localized_feedback: High-level feedback strings that are
                not bound to a specific code location.
            localized_feedback: Structured warnings tied to code ranges.
            message: The natural-language question from the user.

        Returns:
            str: The assistant reply generated by the LLM.
        """
        lf_text = "\n".join(
            warning.get_llm_description() for warning in localized_feedback
        )

        system_msg = SystemMessage(
            content=ADVISOR_PROMPT.format(
                code=code,
                non_localized_feedback=non_localized_feedback,
                localized_feedback=lf_text,
            )
        )
        tokens_user = self._count_tokens(message)
        tokens_system = self._count_tokens(system_msg.content)

        reserved = tokens_system + settings.reserved_answer_tokens + tokens_user

        available_for_history = max(settings.token_limit - reserved, 0)

        # initial history limited by budget
        history = await self._memory.get_history(conversation_id, available_for_history)

        # build a nested callable so tenacity can retry it automatically
        @retry(
            retry=retry_if_exception_type(BadRequestError),
            stop=stop_after_attempt(3),
            reraise=True,
            before_sleep=lambda _: history.pop(0) if history else None,
        )
        async def _invoke():
            msgs = (
                [system_msg]
                + [
                    (HumanMessage if m["role"] == "user" else AIMessage)(
                        content=m["content"]
                    )
                    for m in history
                ]
                + [HumanMessage(content=message)]
            )
            return await llm_client.ainvoke(msgs)

        response = await _invoke()

        tokens_ai = response.usage_metadata["output_tokens"]

        await self._memory.save_messages(
            conversation_id,
            user_id,
            [
                ("user", message, tokens_user),
                ("assistant", response.content, tokens_ai),
            ],
        )

        updated = history + [
            dict(role="user", content=message, token_count=tokens_user),
            dict(role="assistant", content=response.content, token_count=tokens_ai),
        ]

        await self._memory.save_history(conversation_id, updated)

        return response.content
