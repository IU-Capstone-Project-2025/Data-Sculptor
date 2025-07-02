"""
Инициализация расширения для Jupyter AI с поддержкой контекста notebook.
"""

from .adviser_provider import AdviserProvider
from .chat_handler_patch import patch_chat_handlers
from .context_handler import setup_handlers


def _jupyter_server_extension_points():
    """
    Точки входа для расширения Jupyter Server.
    """
    return [{
        "module": "llm_custom_providers"
    }]


def _load_jupyter_server_extension(server_app):
    """
    Загрузка расширения при старте Jupyter Server.
    """
    # Регистрируем HTTP handlers для API контекста
    setup_handlers(server_app.web_app)
    
    # Применяем патчи к chat handlers
    patch_chat_handlers()
    
    server_app.log.info("Adviser extension with notebook context support loaded")


# Для обратной совместимости
load_jupyter_server_extension = _load_jupyter_server_extension