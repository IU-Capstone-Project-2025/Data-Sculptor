import os
***REMOVED***quests
from typing import Any, List
from langchain.llms.base import LLM
from langchain.schema import Generation, LLMResult
import uuid


class AdviserLLM(LLM):
    model_name: str = "adviser"

    @property
    def _llm_type(self) -> str:
***REMOVED*** self.model_name

    def _call(
        self,
        prompt: str,
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> str:  # sync вариант
        chat_request = kwargs.get("chat_request")
        if chat_request is None:
            chat_request = {}

        # --- Patch missing / empty fields to satisfy API validation ---
        patched = {
            "conversation_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "message": prompt,
            "current_code": "print('placeholder')",
            "cell_code_offset": 0,
            "current_non_localized_feedback": "No feedback",
            "current_localized_feedback": [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 0, "character": 0},
                    },
                    "severity": 2,
                    "code": "custom-warning",
                    "source": "Data Sculptor",
                    "message": "placeholder warning",
                }
            ],
            "use_deep_analysis": False,
        }

        # merge user-supplied dict (if any) over defaults, then fill blanks
        patched.update({k: v for k, v in chat_request.items() if v not in (None, "", [], {})})

        chat_request = patched

        url = os.getenv("ADVISER_API_URL", "http://adviser:9353/api/v1/chat")
        resp = requests.post(url, json=chat_request, timeout=60)
        resp.raise_for_status()
        data = resp.json()
***REMOVED*** data.get("message", str(data))

    def generate(
        self, prompts: List[str], **kwargs: Any
    ) -> LLMResult:  # async-безопасность
        text = self._call(prompts[0], **kwargs)
***REMOVED*** LLMResult(generations=[[Generation(text=text)]])
