"""
Улучшенная интеграция Adviser с Jupyter AI для автоматической передачи контекста.
Этот модуль обеспечивает более надежную передачу контекста notebook.
"""

from typing import Dict, Any, Optional, List
from jupyter_ai.chat_handlers.base import BaseChatHandler
from jupyter_ai.models import HumanChatMessage, AgentChatMessage
from jupyter_ai_magics.providers import BaseProvider
from langchain.schema import BaseMessage, HumanMessage, AIMessage
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class AdviserChatHandler(BaseChatHandler):
    """
    Специализированный обработчик чата для Adviser с поддержкой контекста notebook.
    """
    
    id = "adviser"
    name = "Adviser Assistant"
    help = "AI assistant with full notebook context"
    routing_type = "llm"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._context_cache = {}
        
    async def get_notebook_context(self, notebook_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает контекст текущего notebook.
        """
        try:
            # Пытаемся получить путь к notebook из разных источников
            if not notebook_path:
                # Из последнего сообщения
                if hasattr(self, '_last_notebook_path'):
                    notebook_path = self._last_notebook_path
                # Из конфигурации
                elif hasattr(self, 'config') and hasattr(self.config, 'notebook_path'):
                    notebook_path = self.config.notebook_path
            
            if not notebook_path:
                logger.warning("No notebook path available for context extraction")
                return {"current_code": ""}
            
            # Проверяем кеш
            cache_key = f"{notebook_path}:{self._get_notebook_mtime(notebook_path)}"
            if cache_key in self._context_cache:
                return self._context_cache[cache_key]
            
            # Получаем содержимое notebook
            if hasattr(self, 'contents_manager'):
                notebook = await self.contents_manager.get(notebook_path, content=True)
                
                if notebook['type'] == 'notebook':
                    context = self._extract_notebook_context(notebook['content'])
                    context['notebook_path'] = notebook_path
                    context['notebook_name'] = notebook['name']
                    
                    # Кешируем результат
                    self._context_cache[cache_key] = context
                    
                    # Ограничиваем размер кеша
                    if len(self._context_cache) > 10:
                        oldest_key = list(self._context_cache.keys())[0]
                        del self._context_cache[oldest_key]
                    
                    return context
            
            return {"current_code": ""}
            
        except Exception as e:
            logger.error(f"Failed to get notebook context: {e}")
            return {"current_code": ""}
    
    def _extract_notebook_context(self, notebook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает контекст из данных notebook.
        """
        from .context_handler import NotebookContextExtractor
        extractor = NotebookContextExtractor()
        
        # Извлекаем код
        current_code = extractor.extract_notebook_cells(notebook_data)
        
        # Можно добавить дополнительную информацию
        context = {
            "current_code": current_code,
            "cell_count": len(notebook_data.get('cells', [])),
            "language": notebook_data.get('metadata', {}).get('language_info', {}).get('name', 'python')
        }
        
        return context
    
    def _get_notebook_mtime(self, notebook_path: str) -> float:
        """
        Получает время модификации notebook для кеширования.
        """
        try:
            if hasattr(self, 'contents_manager'):
                model = self.contents_manager.get(notebook_path, content=False)
                return model.get('last_modified', 0)
        except:
            return 0
    
    async def process_message(self, message: HumanChatMessage):
        """
        Обрабатывает сообщение с автоматическим добавлением контекста.
        """
        try:
            # Сохраняем путь к notebook из метаданных
            if message.metadata and 'notebook_path' in message.metadata:
                self._last_notebook_path = message.metadata['notebook_path']
            
            # Получаем контекст
            context = await self.get_notebook_context()
            
            # Подготавливаем LLM с контекстом
            if hasattr(self, 'llm') and self.llm:
                # Для Adviser провайдера
                if hasattr(self.llm, '__class__') and 'Adviser' in self.llm.__class__.__name__:
                    if not hasattr(self.llm, 'model_kwargs'):
                        self.llm.model_kwargs = {}
                    
                    if 'chat_request' not in self.llm.model_kwargs:
                        self.llm.model_kwargs['chat_request'] = {}
                    
                    # Обновляем контекст
                    self.llm.model_kwargs['chat_request'].update({
                        'current_code': context.get('current_code', ''),
                        'message': message.body,
                        'conversation_id': getattr(self, 'conversation_id', None) or message.id,
                        'user_id': getattr(self, 'user_id', None) or 'jupyter-user'
                    })
                    
                    logger.info(f"Updated Adviser context with {len(context.get('current_code', ''))} chars of code")
            
            # Генерируем ответ
            response = await self.llm.agenerate([message.body])
            response_text = response.generations[0][0].text
            
            # Отправляем ответ
            self.reply(response_text, message)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.reply(f"Error: {str(e)}", message)


class ContextAwareAdviserProvider(BaseProvider):
    """
    Провайдер с улучшенной поддержкой контекста.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._context = {}
    
    def set_context(self, context: Dict[str, Any]):
        """Устанавливает контекст для следующего вызова."""
        self._context = context
    
    async def agenerate(self, messages: List[BaseMessage], **kwargs) -> Any:
        """Генерация с учетом контекста."""
        # Добавляем контекст в kwargs
        if self._context:
            if 'chat_request' not in kwargs:
                kwargs['chat_request'] = {}
            kwargs['chat_request'].update(self._context)
        
        # Вызываем базовый метод
        return await super().agenerate(messages, **kwargs)


# Регистрация обработчика
def register_adviser_handler(chat_handlers: Dict[str, Any]):
    """
    Регистрирует Adviser chat handler.
    """
    chat_handlers['adviser'] = AdviserChatHandler