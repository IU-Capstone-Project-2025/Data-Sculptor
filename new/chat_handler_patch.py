"""
Патч для Jupyter AI chat handler для автоматической передачи контекста notebook.
Этот модуль перехватывает сообщения чата и добавляет контекст notebook.
"""

from jupyter_ai.chat_handlers.base import BaseChatHandler
from jupyter_ai.models import HumanChatMessage
from typing import Dict, Any, Optional
import asyncio
from functools import wraps


def inject_notebook_context(original_process_message):
    """
    Декоратор для инъекции контекста notebook в сообщения чата.
    """
    @wraps(original_process_message)
    async def wrapped_process_message(self, message: HumanChatMessage):
        # Получаем контекст notebook
        context = await get_current_notebook_context(self)
        
        # Если у нас есть провайдер Adviser, передаем ему контекст
        if hasattr(self, 'llm') and hasattr(self.llm, 'model_kwargs'):
            if not hasattr(self.llm, 'model_kwargs'):
                self.llm.model_kwargs = {}
            
            if 'chat_request' not in self.llm.model_kwargs:
                self.llm.model_kwargs['chat_request'] = {}
            
            # Обновляем current_code в chat_request
            self.llm.model_kwargs['chat_request']['current_code'] = context.get('current_code', '')
            
            # Можно также передать дополнительную информацию
            if context.get('notebook_path'):
                self.llm.model_kwargs['chat_request']['notebook_path'] = context['notebook_path']
        
        # Вызываем оригинальный метод
        return await original_process_message(message)
    
    return wrapped_process_message


async def get_current_notebook_context(chat_handler) -> Dict[str, Any]:
    """
    Получает контекст текущего notebook через Jupyter Server API.
    """
    try:
        # Получаем текущий notebook из контекста чата
        # Это зависит от того, как Jupyter AI хранит информацию о текущем notebook
        
        # Вариант 1: Если есть доступ к contents manager
        if hasattr(chat_handler, 'contents_manager'):
            # Здесь нужно знать путь к текущему notebook
            # Это может быть сохранено в сессии или передано в сообщении
            notebook_path = getattr(chat_handler, 'current_notebook_path', None)
            
            if notebook_path:
                notebook = await chat_handler.contents_manager.get(notebook_path, content=True)
                if notebook['type'] == 'notebook':
                    from .context_handler import NotebookContextExtractor
                    extractor = NotebookContextExtractor()
                    current_code = extractor.extract_notebook_cells(notebook['content'])
                    return {
                        'current_code': current_code,
                        'notebook_path': notebook_path
                    }
        
        # Вариант 2: Если notebook передается в сообщении
        # (это нужно будет реализовать на стороне frontend)
        
        return {'current_code': ''}
        
    except Exception as e:
        # В случае ошибки возвращаем пустой контекст
        return {'current_code': ''}


def patch_chat_handlers():
    """
    Применяет патч ко всем chat handlers в Jupyter AI.
    """
    try:
        from jupyter_ai.chat_handlers import DefaultChatHandler, AskChatHandler
        
        # Патчим DefaultChatHandler
        if hasattr(DefaultChatHandler, 'process_message'):
            DefaultChatHandler.process_message = inject_notebook_context(
                DefaultChatHandler.process_message
            )
        
        # Патчим AskChatHandler если нужно
        if hasattr(AskChatHandler, 'process_message'):
            AskChatHandler.process_message = inject_notebook_context(
                AskChatHandler.process_message
            )
            
    except ImportError:
        pass