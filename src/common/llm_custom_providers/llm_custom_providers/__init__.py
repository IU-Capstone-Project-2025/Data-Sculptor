"""Top-level package for custom Jupyter-AI providers and extensions."""

from .adviser_provider import AdviserProvider  # re-export for convenience
from .chat_handler_patch import patch_chat_handlers
from .context_handler import setup_handlers

__all__ = [
    "AdviserProvider",
    "patch_chat_handlers",
]


def _jupyter_server_extension_points():
    """Entry-point for classic server extension loading."""
    return [{"module": "llm_custom_providers"}]


def _load_jupyter_server_extension(server_app):  # noqa: D401 – imperative
    """Register REST handlers and monkey-patch chat once the server starts."""
    setup_handlers(server_app.web_app)
    patch_chat_handlers()
    server_app.log.info("Adviser extension with notebook context support loaded")


# Alias used by older versions of Jupyter Server
load_jupyter_server_extension = _load_jupyter_server_extension


def _jupyter_nbextension_paths():
    """Provide classic Notebook extension metadata for automatic installation."""
    return [
        {
            "section": "notebook",
            # Directory relative to this __init__.py containing JS assets
            "src": "static",
            # Directory name within nbextensions after install
            "dest": "jupyter_ai_context",
            # `require` module path, used by the notebook frontend
            "require": "jupyter_ai_context/frontend_extension",
        }
    ]
