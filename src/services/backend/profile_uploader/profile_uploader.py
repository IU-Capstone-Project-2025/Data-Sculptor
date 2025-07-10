"""Business logic for persisting uploaded profile notebooks.

The *ProfileUploaderService* takes the raw bytes of a Jupyter notebook
(`.ipynb`) file, extracts the overall task description plus individual
sections and writes them into PostgreSQL tables::

    profiles(id UUID PRIMARY KEY,
             description TEXT NOT NULL,
             created_at TIMESTAMP DEFAULT now())

    profile_sections(id UUID PRIMARY KEY,
                     profile_id UUID NOT NULL REFERENCES profiles(id),
                     section_order INT NOT NULL,
                     description TEXT NOT NULL,
                     code TEXT NOT NULL,
                     created_at TIMESTAMP DEFAULT now())

The tables are expected to be created externally (e.g. via migrations).
"""

from __future__ import annotations

import uuid
import logging
import tempfile
import shutil
from fastapi import UploadFile
import subprocess

import asyncpg
import nbformat

from schemas import Section

logger = logging.getLogger(__name__)


class NotebookParseError(RuntimeError):
    """Raised when the notebook structure does not match expectations."""


class ProfileUploader:
    """Parse and persist Jupyter notebook *profiles*.

    Args:
        pg_pool: Asyncpg connection pool used for database access.
    """

    def __init__(self, pg_pool: asyncpg.Pool):
        self._pg_pool = pg_pool

    async def store_profile(self, ipynb_bytes: bytes) -> uuid.UUID:
        """Extract notebook content and write a new profile to Postgres.

        Args:
            ipynb_bytes: Raw contents of the uploaded `.ipynb` file.

        Returns:
            uuid.UUID: The generated *profile_id*.

        Raises:
            NotebookParseError: If the notebook does not conform to the expected
                `description + (markdown, code)*` pattern.
            asyncpg.PostgresError: If the database write fails.
        """
        profile_id = uuid.uuid4()
        description, sections = self._parse_notebook(ipynb_bytes)

        logger.debug("Storing profile %s with %d sections", profile_id, len(sections))

        await self._insert_into_db(profile_id, description, sections)
***REMOVED*** profile_id

    def _parse_notebook(self, raw: bytes) -> tuple[str, list[Section]]:
        """Return the notebook description plus its sections.

        The expected structure is::
            0. Markdown cell – *task description*
            1. Markdown cell – *section description*
            2. Code cell      – *section code*
            3. Markdown cell – *section description*
            4. Code cell      – *section code*
            ...

        Args:
            raw: Raw notebook file bytes.

        Returns:
            tuple[str, list[Section]]: Overall description and an ordered list
            of (section_description, code) pairs.

        Raises:
            NotebookParseError: If the notebook format is invalid.
        """
        try:
            nb = nbformat.reads(raw.decode(), as_version=4)
        except Exception as exc:
            raise NotebookParseError("Unable to read notebook file") from exc

        cells = nb.get("cells", [])
        if not cells:
            raise NotebookParseError("Notebook contains no cells")

        if cells[0].get("cell_type") != "markdown":
            raise NotebookParseError("First cell must be a markdown description")

        description: str = cells[0].get("source", "").strip()
        sections: list[Section] = []

        # locate the *first* cell with ```json after the profile description
        idx = 1
        while idx < len(cells):
            cell = cells[idx]
            if (cell.get("cell_type") == "markdown" and 
                "```json" in cell.get("source", "")):
                break
            idx += 1

        # iterate over remaining cells to collect (description, code) pairs
        while idx < len(cells) - 1:
            desc_cell = cells[idx]

            # if the current cell doesn't contain ```json, advance to next and continue search
            if (desc_cell.get("cell_type") != "markdown" or 
                "```json" not in desc_cell.get("source", "")):
                idx += 1
                continue

            next_idx = idx + 1
            if next_idx >= len(cells):
                break  # no cell following the description -> incomplete pair

            code_cell = cells[next_idx]

            # pair must be markdown with ```json followed immediately by code
            if code_cell.get("cell_type") != "code":
                logger.warning(
                    "Description cell at %d not followed by code cell; skipping", idx
                )
                idx += 1
                continue

            sec_desc = desc_cell.get("source", "").strip()
            sec_code = code_cell.get("source", "")
            sections.append((sec_desc, sec_code))

            idx += 2  # advance past the processed code cell

        if not sections:
            raise NotebookParseError(
                "No description/code section pairs found after profile description"
            )

***REMOVED*** description, sections

    async def _insert_into_db(
        self, profile_id: uuid.UUID, description: str, sections: list[Section]
    ) -> None:
        """Insert *profile* and its *sections* within a single transaction."""
        async with self._pg_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO profiles(id, description, created_at)
                    VALUES($1, $2, now())
                    """,
                    profile_id,
                    description,
                )

                await conn.executemany(
                    """
                    INSERT INTO profile_sections(profile_id, section_id, description, code, created_at)
                    VALUES($1, $2, $3, $4, now())
                    """,
                    [
                        (
                            profile_id,
                            section_id,
                            sec_desc,
                            sec_code,
                        )
                        for section_id, (sec_desc, sec_code) in enumerate(sections)
                    ],
                )
