from jupyter_ai_magics.providers import BaseProvider
import os
from llm_custom_providers.adviser_llm import AdviserLLM
from llm_custom_providers.adviser_provider import AdviserProvider
from llm_custom_providers.chat_handler_patch import patch_chat_handlers
import jupyter_ai.config as _jai_config

# Получаем конфиг
c = get_config()

# Настройка провайдера
adviser_provider = AdviserProvider(
    model_id="adviser",
    model_kwargs=AdviserProvider.model_kwargs,
    api_keys={"adviser_api_url": os.environ.get("ADVISER_API_URL", "http://adviser:9353")},
)

# Регистрируем провайдер в Jupyter AI
c.JupyterAI.llm_providers = [adviser_provider]
c.AiExtension.llm_providers = [adviser_provider]
c.AiExtension.allowed_providers = ["adviser"]

# Включаем серверное расширение для обработки контекста
c.ServerApp.jpserver_extensions = {
    "llm_custom_providers": True
}

# Патчим функцию получения провайдеров
try:
    from jupyter_ai.model_providers import PROVIDER_CLASSES as _BUILTIN
    _ALL = {**_BUILTIN, "adviser": AdviserProvider}
    def _patched():
        return _ALL
    _jai_config.get_llm_provider_classes = _patched
except Exception:
    pass

# Загружаем плагины
c.JupyterAI.plugins = [
    "llm_custom_providers.adviser_plugin",
]

c.AiExtension.plugins = [
    "llm_custom_providers.adviser_plugin",
]

# Применяем патчи при загрузке конфига
patch_chat_handlers()