"""Jupyter-AI plugin entry-point used to register the Adviser provider.

Listed in traitlets config under ``c.JupyterAI.plugins``.
"""

from .adviser_provider import AdviserProvider


def _jupyter_ai_plugin(extension):  # noqa: D401 present – plugin hook
    """Called by Jupyter-AI during start-up to register custom providers."""
    extension.provider_registry.register("adviser", lambda _: AdviserProvider()) 