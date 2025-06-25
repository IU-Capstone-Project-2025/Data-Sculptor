from jupyter_ai_magics.providers import BaseProvider
from .adviser_llm import AdviserLLM
from typing import Any
from langchain.llms.base import LLM
from typing import ClassVar

class AdviserProvider(AdviserLLM, BaseProvider):
    id = "adviser"
    name = "Adviser"
    models = ["adviser"]
    model_id_key = "model_name"

    # Jupyter AI hides providers from the UI until all credentials listed
    # here are configured by the user.  We need exactly one URL, which the
    # backend reads from environment or Settings panel.
    required_credentials: ClassVar[list[str]] = ["adviser_api_url"]

    # default kwargs structure; can be overridden by client
    model_kwargs: ClassVar[dict[str, Any]] = {
        "chat_request": {
            "conversation_id": "00000000-0000-0000-0000-000000000000",
            "user_id": "00000000-0000-0000-0000-000000000000",
            "current_code": "",
            "current_non_localized_feedback": [],
            "current_localized_feedback": [],
            "message": ""
        }
    } 
