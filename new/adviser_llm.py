import os
import requests
from typing import Any, List, Dict, Optional
from langchain.llms.base import LLM
from langchain.schema import Generation, LLMResult
import uuid


class AdviserLLM(LLM):
    model_name: str = "adviser"
    model_kwargs: Dict[str, Any] = {}
    
    @property
    def _llm_type(self) -> str:
        return self.model_name
    
    def _call(
        self,
        prompt: str,
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> str:
        """Вызов API с передачей контекста notebook."""
        # Получаем chat_request из kwargs или model_kwargs
        chat_request = kwargs.get("chat_request", self.model_kwargs.get("chat_request", {}))
        
        # Базовые значения для обязательных полей
        base_request = {
            "conversation_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "message": prompt,
            "current_code": "",  # Будет заполнено из контекста
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
        
        # Объединяем базовые значения с переданными
        final_request = {**base_request}
        
        # Обновляем только непустые значения из chat_request
        for key, value in chat_request.items():
            if value not in (None, "", [], {}):
                final_request[key] = value
        
        # Обновляем message на текущий prompt
        final_request["message"] = prompt
        
        # Отправляем запрос
        url = os.getenv("ADVISER_API_URL", "http://adviser:9353/api/v1/chat")
        
        try:
            resp = requests.post(url, json=final_request, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", str(data))
        except requests.RequestException as e:
            return f"Error calling Adviser API: {str(e)}"
    
    def generate(
        self, prompts: List[str], **kwargs: Any
    ) -> LLMResult:
        """Генерация ответов для списка промптов."""
        generations = []
        for prompt in prompts:
            text = self._call(prompt, **kwargs)
            generations.append([Generation(text=text)])
        return LLMResult(generations=generations)