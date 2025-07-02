"""
Monkey-patch default Jupyter-AI chat handlers so that they transparently inject
current notebook code into every Adviser request.

The actual extraction logic lives in ``context_handler.NotebookContextExtractor``.
This module merely wires the pieces together at runtime.
"""

from functools import wraps
from typing import Any, Dict

from jupyter_ai.models import HumanChatMessage

from .context_handler import NotebookContextExtractor

import uuid


async def _get_current_notebook_context(handler) -> Dict[str, Any]:
    """Attempt to extract notebook context using Jupyter Server contents API."""
    # NOTE: The internal structure of Jupyter-AI chat handlers is not formally
    # documented, so we rely on a few heuristics here.
    notebook_path: str | None = (
        getattr(handler, "current_notebook_path", None)
        or getattr(handler, "notebook_path", None)
    )
    if not notebook_path:
        return {"current_code": ""}

    try:
        if hasattr(handler, "contents_manager"):
            notebook = await handler.contents_manager.get(notebook_path, content=True)  # type: ignore[attr-defined]
            if notebook.get("type") == "notebook":
                extractor = NotebookContextExtractor()
                return {
                    "current_code": extractor.extract_notebook_cells(notebook["content"]),
                    "notebook_path": notebook_path,
                }
    except Exception:
        # swallow all exceptions – context extraction must never break chat
        pass

    return {"current_code": ""}


def _inject_notebook_context(original):
    """Wrapper that augments the chat handler's ``process_message`` method."""

    @wraps(original)
    async def _wrapped(self, message: HumanChatMessage):  # type: ignore[override]
        # ------------------------------------------------------------------
        # 1. Extract metadata sent from the Jupyter front-end (if any)
        # ------------------------------------------------------------------
        metadata: Dict[str, Any] = {}
        if hasattr(message, "metadata") and isinstance(message.metadata, dict):
            metadata = message.metadata  # type: ignore[assignment]

        nb_ctx: Dict[str, Any] = metadata.get("notebook_context", {}) if isinstance(metadata.get("notebook_context"), dict) else {}

        # pull both path & code from the nested structure (they may be empty)
        md_path: str | None = nb_ctx.get("notebook_path")
        md_code: str | None = nb_ctx.get("current_code")

        # ------------------------------------------------------------------
        # 2. Build the initial context dict
        # ------------------------------------------------------------------
        context: Dict[str, Any] = {}

        if md_path:
            context["notebook_path"] = md_path

        if md_code is not None:
            # include empty strings as a deliberate signal to clear stale code
            context["current_code"] = md_code

        # ------------------------------------------------------------------
        # 3. Fallback – fetch notebook via contents API when we only have path
        # ------------------------------------------------------------------
        if "current_code" not in context:
            nb_path = context.get("notebook_path") or metadata.get("notebook_path")
            if nb_path and hasattr(self, "contents_manager"):
                try:
                    notebook = await self.contents_manager.get(nb_path, content=True)  # type: ignore[attr-defined]
                    if notebook.get("type") == "notebook":
                        extractor = NotebookContextExtractor()
                        context["current_code"] = extractor.extract_notebook_cells(notebook["content"])
                except Exception:
                    pass

        # ------------------------------------------------------------------
        # 4. As a last resort try to infer the active notebook from the handler
        # ------------------------------------------------------------------
        if "current_code" not in context:
            inferred_ctx = await _get_current_notebook_context(self)
            context.update(inferred_ctx)

        # If the underlying LLM/provider is our Adviser, patch its kwargs.
        if hasattr(self, "llm") and hasattr(self.llm, "model_kwargs"):
            # Build a **fresh** chat_request for every user message to avoid
            # accidental leakage of previous metadata such as localized
            # feedback or cell offsets.
            base_req: Dict[str, Any] = {
                "conversation_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),
                "current_code": context.get("current_code", ""),
                "cell_code_offset": 0,
                "current_non_localized_feedback": [],
                "current_localized_feedback": [],
                # ``use_deep_analysis`` intentionally omitted – the backend
                # will use its default unless explicitly requested by the UI.
            }

            self.llm.model_kwargs["chat_request"] = base_req  # type: ignore[attr-defined]

            # reference for notebook-switch detector below
            chat_req = self.llm.model_kwargs["chat_request"]

        # Detect potential notebook switch early, but postpone updating
        # ``_last_notebook_path`` until we have actually refreshed the code to
        # avoid the race where the subsequent refresh branch sees the same
        # path and skips re-extraction.
        new_path = context.get("notebook_path") or metadata.get("notebook_path") or md_path
        switched = new_path and getattr(self, "_last_notebook_path", None) != new_path

        if "chat_req" in locals() and switched:
            # start a brand-new conversation/user context; the actual path will
            # be committed after we successfully refresh the code further down
            chat_req["conversation_id"] = str(uuid.uuid4())
            chat_req["user_id"] = str(uuid.uuid4())

        # ------------------------------------------------------------------
        # 5. Handle notebook switch – refresh code if path changed
        # ------------------------------------------------------------------
        last_path = getattr(self, "_last_notebook_path", None)
        new_path = context.get("notebook_path")
        if new_path and new_path != last_path:
            # Try to fetch fresh code from contents_manager even if we already
            # received `current_code` from the front-end: that string might be
            # stale when the chat panel was opened from a different notebook.
            if hasattr(self, "contents_manager"):
                try:
                    nb = await self.contents_manager.get(new_path, content=True)  # type: ignore[attr-defined]
                    if nb.get("type") == "notebook":
                        extractor = NotebookContextExtractor()
                        context["current_code"] = extractor.extract_notebook_cells(nb["content"])
                except Exception:
                    # if anything goes wrong just clear the code to be safe
                    context["current_code"] = ""

            # persist the path so we can detect further switches
            self._last_notebook_path = new_path

        # also ensure the freshly extracted code propagates to chat_request
        if "chat_req" in locals():
            chat_req["current_code"] = context.get("current_code", "")

        # ------------------------------------------------------------------
        # 0. Preemptively inject context into provider-level defaults so that
        #    *any* upcoming AdviserLLM instance receives fresh code.
        # ------------------------------------------------------------------
        try:
            from .adviser_provider import AdviserProvider

            # Work on a copy to avoid mutating the shared template too much – we
            # only replace fields that are guaranteed to exist in the schema.
            if context.get("current_code") is not None:
                AdviserProvider.model_kwargs["chat_request"]["current_code"] = context["current_code"]
            # always randomise conversation to prevent mixing messages between files
            AdviserProvider.model_kwargs["chat_request"]["conversation_id"] = str(uuid.uuid4())
            AdviserProvider.model_kwargs["chat_request"]["user_id"] = str(uuid.uuid4())
        except Exception:
            # Provider not importable? Skip – the downstream logic will still run
            pass

        return await original(self, message)

    return _wrapped


def patch_chat_handlers():
    """Apply patches to all built-in Jupyter-AI chat handlers."""
    try:
        from jupyter_ai.chat_handlers import DefaultChatHandler, AskChatHandler

        if hasattr(DefaultChatHandler, "process_message"):
            DefaultChatHandler.process_message = _inject_notebook_context(  # type: ignore[assignment]
                DefaultChatHandler.process_message
            )

        if hasattr(AskChatHandler, "process_message"):
            AskChatHandler.process_message = _inject_notebook_context(  # type: ignore[assignment]
                AskChatHandler.process_message
            )
    except ImportError:
        # Jupyter-AI may not be installed in every environment (e.g. during unit tests)
        pass 