from jupyter_ai_magics.providers import BaseProvider
from .adviser_llm import AdviserLLM
from typing import Any, Dict, Optional
from langchain.llms.base import LLM
from typing import ClassVar
import json

class AdviserProvider(AdviserLLM, BaseProvider):
    id = "adviser"
    name = "Adviser"
    models = ["adviser"]
    model_id_key = "model_name"
    
    # URL требуется для отображения в UI
    required_credentials: ClassVar[list[str]] = ["adviser_api_url"]
    
    # Базовая структура kwargs
    model_kwargs: ClassVar[dict[str, Any]] = {
        "chat_request": {
            "conversation_id": "",
            "user_id": "",
            "current_code": "",
            "current_non_localized_feedback": [],
            "current_localized_feedback": [],
            "message": ""
        }
    }
    
    def get_model(self, model_name: str, **kwargs) -> LLM:
        """Создает экземпляр модели с передачей контекста notebook."""
        # Получаем контекст notebook из kwargs, если он передан
        notebook_context = kwargs.get("notebook_context", {})
        
        # Создаем экземпляр LLM
        llm = AdviserLLM(model_name=model_name)
        
        # Передаем контекст в model_kwargs
        if notebook_context:
            llm.model_kwargs = {
                "chat_request": {
                    **self.model_kwargs["chat_request"],
                    "current_code": notebook_context.get("current_code", ""),
                    "conversation_id": notebook_context.get("conversation_id", 
                                                           self.model_kwargs["chat_request"]["conversation_id"]),
                    "user_id": notebook_context.get("user_id", 
                                                   self.model_kwargs["chat_request"]["user_id"])
                }
            }
        
        return llm