import os
import requests
from typing import Any, List, Dict
from langchain.llms.base import LLM
from langchain.schema import Generation, LLMResult
import uuid


class AdviserLLM(LLM):
    """LLM wrapper for the internal Adviser REST API with optional notebook context support."""

    model_name: str = "adviser"
    # arbitrary kwargs fed straight to the API payload on each call (mutable)
    model_kwargs: Dict[str, Any] = {}

    @property
    def _llm_type(self) -> str:
        return self.model_name

    def _patch_base_request(self, prompt: str) -> Dict[str, Any]:
        """Return a fully-populated request dict with sane defaults.

        The Adviser backend validates the incoming JSON very strictly so we need
        to fill in every required field even if the caller omitted them.
        """
        base_request = {
            "conversation_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "message": prompt,
            "current_code": "print('placeholder')",  # overwritten if context provided
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
        return base_request

    def _merge_request(self, prompt: str, chat_request: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user-supplied chat_request on top of defaults, skipping blanks."""
        patched = self._patch_base_request(prompt)
        # remove any keys not accepted by backend schema
        allowed_keys = {
            "conversation_id",
            "user_id",
            "message",
            "current_code",
            "cell_code_offset",
            "current_non_localized_feedback",
            "current_localized_feedback",
            "use_deep_analysis",
        }
        chat_request = {k: v for k, v in chat_request.items() if k in allowed_keys}
        for key, value in chat_request.items():
            if key in ("conversation_id", "user_id"):
                try:
                    # accept only valid version-4 UUIDs
                    uuid_obj = uuid.UUID(str(value), version=4)
                    value = str(uuid_obj)
                except (ValueError, TypeError):
                    # ignore invalid placeholders like all-zero UUID
                    continue

            if value not in (None, "", [], {}):
                patched[key] = value
        return patched

    # ---------------------------------------------------------------------
    # synchronous call implementation (Jupyter-AI currently calls sync LLMs)
    # ---------------------------------------------------------------------
    def _call(
        self,
        prompt: str,
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> str:
        # precedence: explicit kwargs -> self.model_kwargs
        chat_request: Dict[str, Any] = kwargs.get("chat_request", self.model_kwargs.get("chat_request", {}))
        payload = self._merge_request(prompt, chat_request)

        url = os.getenv("ADVISER_API_URL", "http://adviser:9353/api/v1/chat")
        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", str(data))
        except requests.HTTPError as http_err:
            try:
                error_detail = http_err.response.json()
            except Exception:
                error_detail = http_err.response.text if http_err.response else str(http_err)
            return f"Error calling Adviser API: {http_err} | Details: {error_detail}"
        except requests.RequestException as exc:
            # return string so that LangChain doesn't crash upstream
            return f"Error calling Adviser API: {str(exc)}"

    # ------------------------------------------------------------------
    # batch generation – required by LangChain interface but Adviser only
    # supports one prompt at a time, so we proxy sequentially.
    # ------------------------------------------------------------------
    def generate(self, prompts: List[str], **kwargs: Any) -> LLMResult:
        generations = []
        for p in prompts:
            text = self._call(p, **kwargs)
            generations.append([Generation(text=text)])
        return LLMResult(generations=generations)
