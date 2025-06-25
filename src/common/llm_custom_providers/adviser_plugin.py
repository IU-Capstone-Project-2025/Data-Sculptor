from .adviser_llm import AdviserLLM

def _jupyter_ai_plugin(extension):
    """Register adviser provider during Jupyter AI startup."""
    extension.provider_registry.register("adviser", lambda _: AdviserLLM()) 
