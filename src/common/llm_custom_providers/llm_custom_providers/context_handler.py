"""Utilities and Tornado handler for exposing notebook context via the Jupyter
Server REST API.

The heavy lifting – extracting code cells – is intentionally written in a very
conservative manner so that it continues to work even if the notebook metadata
changes slightly across Jupyter versions.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import tornado.web
from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import ensure_async

__all__ = [
    "NotebookContextExtractor",
    "JupyterAIContextHandler",
    "setup_handlers",
]


class NotebookContextExtractor:
    """Static helpers for slicing & dicing notebook JSON."""

    MAX_CONTEXT_LENGTH: int = 10_000  # safeguard, characters
    MAX_CELLS: int = 50

    @staticmethod
    def _normalise_source(src: str | list[str]) -> str:
        if isinstance(src, list):
            src = "".join(src)
        return src

    @classmethod
    def extract_notebook_cells(
        cls,
        notebook_data: Dict[str, Any],
        *,
        max_length: Optional[int] = None,
        max_cells: Optional[int] = None,
    ) -> str:
        """Return a concatenation of all code cells with optional limits."""
        if not notebook_data or "cells" not in notebook_data:
            return ""

        max_length = max_length or cls.MAX_CONTEXT_LENGTH
        max_cells = max_cells or cls.MAX_CELLS

        collected: list[str] = []
        current_len = 0

        for cell in notebook_data.get("cells", [])[:max_cells]:
            if cell.get("cell_type") != "code":
                continue
            src = cls._normalise_source(cell.get("source", ""))
            if not src.strip():
                continue

            if current_len + len(src) > max_length:
                break

            collected.append(src)
            current_len += len(src)

        return "\n\n".join(collected)

    @classmethod
    def get_active_cell(
        cls,
        notebook_data: Dict[str, Any],
        *,
        cell_index: Optional[int] = None,
    ) -> str:
        """Return source code of the active cell (last runnable if index not given)."""
        if not notebook_data or "cells" not in notebook_data:
            return ""

        cells = notebook_data["cells"]

        if cell_index is None:
            # pick last code cell
            for cell in reversed(cells):
                if cell.get("cell_type") == "code":
                    return cls._normalise_source(cell.get("source", ""))
            return ""

        if 0 <= cell_index < len(cells):
            cell = cells[cell_index]
            if cell.get("cell_type") == "code":
                return cls._normalise_source(cell.get("source", ""))
        return ""


class JupyterAIContextHandler(APIHandler):
    """/api/ai/context?path=... -> JSON with current_code etc."""

    @tornado.web.authenticated
    async def get(self):  # type: ignore[override]
        notebook_path = self.get_query_argument("path", default="")
        if not notebook_path:
            self.set_status(400)
            self.finish(json.dumps({"error": "No notebook path provided"}))
            return

        try:
            cm = self.contents_manager  # type: ignore[attr-defined]
            notebook = await ensure_async(cm.get(notebook_path, content=True))
            if notebook.get("type") != "notebook":
                self.set_status(400)
                self.finish(json.dumps({"error": "Path does not point to a notebook"}))
                return

            extractor = NotebookContextExtractor()
            current_code = extractor.extract_notebook_cells(notebook["content"])
            context = {
                "current_code": current_code,
                "notebook_path": notebook_path,
                "notebook_name": notebook.get("name"),
            }
            self.finish(json.dumps(context))
        except Exception as exc:  # pragma: no cover – defensive
            self.set_status(500)
            self.finish(json.dumps({"error": str(exc)}))


def setup_handlers(web_app):  # noqa: D401 – imperative mood
    """Register the REST handler under the /api prefix."""
    host_pattern = ".*$"
    base_url = web_app.settings["base_url"]
    route = f"{base_url}api/ai/context"
    web_app.add_handlers(host_pattern, [(route, JupyterAIContextHandler)]) 