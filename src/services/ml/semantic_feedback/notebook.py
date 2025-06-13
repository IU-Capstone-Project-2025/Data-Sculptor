"""Module for parsing and handling Jupyter notebooks.

This module provides a class to represent a Jupyter notebook and
extract its content, such as code, markdown, and output cells.

Public API:
    - JupyterNotebook: A class to parse and access notebook content.
    - NotebookCell: A TypedDict representing a single cell.
"""

import json
from typing import Any, Dict, List, Literal
from dataclasses import dataclass


@dataclass
class NotebookCell:
    """Represents a single cell in a Jupyter notebook."""

    cell_type: Literal["code", "markdown"]
    source: List[str]
    metadata: Dict[str, Any]
    outputs: List[Dict[str, Any]]


class JupyterNotebook:
    """Parses and provides access to the content of a Jupyter notebook.

    Args:
        content (bytes): The byte content of the .ipynb file.

    Attributes:
        data (Dict[str, Any]): The parsed JSON data of the notebook.
    """

    def __init__(self, content: bytes):
        """Initializes the JupyterNotebook with the content of a .ipynb file.

        Args:
            content: The byte content of the notebook file.

        Raises:
            ValueError: If the content is not valid JSON.
        """
        try:
            self.data: Dict[str, Any] = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError("Invalid notebook format: Not a valid JSON file.") from e

    @property
    def cells(self) -> list[NotebookCell]:
        """Returns all cells from the notebook.

        Returns:
            A list of all cells.
        """
        return self.data.get("cells", [])

    def get_code_cells(self) -> list[str]:
        """Extracts the source code from all code cells.

        Returns:
            A list of strings, where each string is the content
            of a code cell.
        """
        return [
            "".join(cell["source"])
            for cell in self.cells
            if cell.get("cell_type") == "code"
        ]

    def get_code_cells_with_outputs(self) -> list[tuple[str, list[str]]]:
        """Extracts the source code and outputs from all code cells.

        Returns:
            A list of tuples, where each tuple contains:
                - The source code of a code cell as a string
                - A list of output strings from the cell (stream and error outputs only)
        """
        result = []
        for cell in self.cells:
            if cell.get("cell_type") != "code":
                continue

            source = "".join(cell["source"])
            outputs = []

            for output in cell.get("outputs", []):
                if output.get("output_type") == "stream":
                    outputs.append("".join(output.get("text", [])))
                elif output.get("output_type") == "error":
                    outputs.append("".join(output.get("traceback", [])))

            result.append((source, outputs))

        return result

    def get_markdown_cells(self) -> list[str]:
        """Extracts the content from all markdown cells.

        Returns:
            A list of strings, where each string is the content
            of a markdown cell.
        """
        return [
            "".join(cell["source"])
            for cell in self.cells
            if cell.get("cell_type") == "markdown"
        ]
