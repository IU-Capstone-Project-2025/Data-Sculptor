import os
from llm_custom_providers.adviser_provider import AdviserProvider
from jupyter_ai.model_providers import OpenAIProvider
from llm_custom_providers.chat_handler_patch import patch_chat_handlers
import jupyter_ai.config as _jai_config

c = get_config()


adviser_provider = AdviserProvider(
    model_id="adviser",
    model_kwargs=AdviserProvider.model_kwargs,
    api_keys={
        "adviser_api_url": os.environ.get(
            "ADVISER_API_URL", "http://adviser-service:9353/api/v1/chat"
        )
    },
)


c.AiExtension.allowed_providers = ["adviser"]

try:
    from jupyter_ai.model_providers import PROVIDER_CLASSES as _BUILTIN

    _ALL = {**_BUILTIN, "adviser": AdviserProvider}

    def _patched():
        return _ALL

    _jai_config.get_llm_provider_classes = _patched
except Exception:
    pass

c.ServerApp.jpserver_extensions = {
    "llm_custom_providers": True,
}

patch_chat_handlers()

c.JupyterAI.plugins = [
    "llm_custom_providers.adviser_plugin",
]

c.AiExtension.plugins = [
    "llm_custom_providers.adviser_plugin",
]
