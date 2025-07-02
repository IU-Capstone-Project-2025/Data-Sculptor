from jupyter_ai_magics.providers import BaseProvider
from typing import Any, Dict, ClassVar
from langchain.llms.base import LLM

from .adviser_llm import AdviserLLM


class AdviserProvider(AdviserLLM, BaseProvider):
    """Jupyter-AI provider that talks to the internal Adviser backend.

    This subclass wires our custom LangChain LLM into the provider interface and
    exposes an extra helper ``set_context`` so that chat handlers can inject the
    current notebook code right before generation.
    """

    id = "adviser"
    name = "Adviser"
    models = ["adviser"]
    model_id_key = "model_name"

    # Provider will remain hidden in the UI until the user sets this single
    # credential – we treat it as just a URL.
    required_credentials: ClassVar[list[str]] = ["adviser_api_url"]

    # default structure expected by the backend, can be mutated at runtime
    model_kwargs: ClassVar[dict[str, Any]] = {
        "chat_request": {
            "conversation_id": "",
            "user_id": "",
            "current_code": "",
            "current_non_localized_feedback": [],
            "current_localized_feedback": [],
            "message": "",
        }
    }

    # ------------------------------------------------------------------
    # public helpers ----------------------------------------------------
    # ------------------------------------------------------------------
    def set_context(self, context: Dict[str, Any]):
        """Inject notebook context (current code etc.) into the next request."""
        if context:
            chat_request: Dict[str, Any] = self.model_kwargs.setdefault("chat_request", {})
            chat_request.update({
                "current_code": context.get("current_code", ""),
                "conversation_id": context.get("conversation_id", chat_request.get("conversation_id")),
                "user_id": context.get("user_id", chat_request.get("user_id")),
            })

    # ------------------------------------------------------------------
    # interface implementation -----------------------------------------
    # ------------------------------------------------------------------
    def get_model(self, model_name: str, **kwargs) -> LLM:  # noqa: D401 (simple verb)
        """Return a fresh AdviserLLM instance pre-loaded with notebook context."""
        notebook_ctx: Dict[str, Any] = kwargs.get("notebook_context", {})
        llm = AdviserLLM(model_name=model_name)

        if notebook_ctx:
            # build a shallow copy so caller's dict doesn't get mutated
            base = self.model_kwargs["chat_request"].copy()
            base.update({
                "current_code": notebook_ctx.get("current_code", ""),
                "conversation_id": notebook_ctx.get("conversation_id", base["conversation_id"]),
                "user_id": notebook_ctx.get("user_id", base["user_id"]),
            })
            llm.model_kwargs = {"chat_request": base}
        return llm 
