from jupyter_ai_magics.providers import BaseProvider
import os
from llm_custom_providers.adviser_llm import AdviserLLM
import jupyter_ai.config as _jai_config

class AdviserProvider(BaseProvider):
    id = "adviser"
    name = "Adviser"
    model_id_key = "model_name"
    models = ["adviser"]

    # default kwargs structure; can be overridden by client
    model_kwargs = {
        "chat_request": {
            "conversation_id": "00000000-0000-0000-0000-000000000000",
            "user_id": "00000000-0000-0000-0000-000000000000",
            "current_code": "",
            "current_non_localized_feedback": [],
            "current_localized_feedback": [],
            "message": ""
        }
    }

    def get_model(self, model_name: str, **kwargs):
        return AdviserLLM()

# add to classic traitlets config so Jupyter AI UI lists it
c = get_config()

c.JupyterAI.llm_providers = [
    AdviserProvider(
        model_id="adviser",
        model_kwargs=AdviserProvider.model_kwargs,
        api_keys={"adviser_api_url": os.environ.get("ADVISER_API_URL", "http://adviser:9353")},
    )
]

c.AiExtension.llm_providers = [
    AdviserProvider(
        model_id="adviser",
        model_kwargs=AdviserProvider.model_kwargs,
        api_keys={"adviser_api_url": os.environ.get("ADVISER_API_URL", "http://adviser:9353")},
    )
]

# patch get_llm_provider_classes so that extensions relying on it also see provider
try:
    from jupyter_ai.model_providers import PROVIDER_CLASSES as _BUILTIN
    _ALL = {**_BUILTIN, "adviser": AdviserProvider}
    def _patched():
        return _ALL
    _jai_config.get_llm_provider_classes = _patched
except Exception:
    pass
# tell Jupyter-AI to load our plugin on start-up
c.JupyterAI.plugins = [
    "llm_custom_providers.adviser_plugin",
]

c.AiExtension.plugins = [
    "llm_custom_providers.adviser_plugin",
]
c.AiExtension.allowed_providers = ["adviser"]
