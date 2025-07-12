"""Input validation for the Case Uploader service.

This module provides validation for uploaded files including file extension
checks and profile notebook structure validation.
"""

from __future__ import annotations

import logging
from pathlib import Path

import nbformat
from fastapi import UploadFile

logger = logging.getLogger(__name__)


class FileValidator:
    """Validates uploaded files for the case uploader service.
    
    Validates file extensions and profile notebook structure before
    expensive operations like Docker image building.
    """

    ALLOWED_PROFILE_EXTENSIONS = {".ipynb"}
    ALLOWED_TEMPLATE_EXTENSIONS = {".ipynb"}
    ALLOWED_REQUIREMENTS_EXTENSIONS = {".txt"}
    # Dataset can be any file type

    def validate_file_extensions(
        self,
        requirements: UploadFile,
        dataset: UploadFile,
        profile: UploadFile,
        template: UploadFile,
    ) -> None:
        """Validate file extensions for all uploaded files.
        
        Args:
            requirements: Requirements file (must be .txt)
            dataset: Dataset file (any extension allowed)
            profile: Profile notebook (must be .ipynb)
            template: Template notebook (must be .ipynb)
            
        Raises:
            ValueError: If any file has invalid extension
        """
        validations = [
            (requirements, self.ALLOWED_REQUIREMENTS_EXTENSIONS, "requirements"),
            (profile, self.ALLOWED_PROFILE_EXTENSIONS, "profile"),
            (template, self.ALLOWED_TEMPLATE_EXTENSIONS, "template"),
        ]
        
        for file_obj, allowed_extensions, file_type in validations:
            if not file_obj.filename:
                raise ValueError(f"{file_type} file must have a filename")
                
            file_ext = Path(file_obj.filename).suffix.lower()
            if file_ext not in allowed_extensions:
                allowed_str = ", ".join(sorted(allowed_extensions))
                raise ValueError(
                    f"{file_type} file must have extension {allowed_str}, got '{file_ext}'"
                )

    async def validate_and_cache_profile(self, profile: UploadFile) -> bytes:
        """Validate profile notebook structure and return cached content.
        
        This method reads the profile once, validates its structure,
        and returns the content for later use to avoid multiple reads.
        
        Args:
            profile: Profile notebook file
            
        Returns:
            bytes: Raw notebook content that passed validation
            
        Raises:
            ValueError: If notebook structure is invalid
            OSError: If failed to read profile file
        """
        try:
            profile_content = await profile.read()
            await profile.seek(0)  # Reset file pointer for potential later reads
        except Exception as exc:
            raise OSError("Failed to read profile file") from exc
        
        self._validate_profile_structure(profile_content)
***REMOVED*** profile_content

    def _validate_profile_structure(self, profile_content: bytes) -> None:
        """Validate the structure of a profile notebook.
        
        Uses the same validation logic as ProfileUploader._parse_notebook
        but only checks structure without extracting content.
        
        Args:
            profile_content: Raw notebook bytes
            
        Raises:
            ValueError: If notebook structure is invalid
        """
        try:
            nb = nbformat.reads(profile_content.decode(), as_version=4)
        except Exception as exc:
            raise ValueError("Unable to read notebook file") from exc

        cells = nb.get("cells", [])
        if not cells:
            raise ValueError("Profile notebook contains no cells")

        if cells[0].get("cell_type") != "markdown":
            raise ValueError("Profile notebook must start with a markdown description")

        # Find the first cell with ```json after the profile description
        idx = 1
        json_section_found = False
        while idx < len(cells):
            cell = cells[idx]
            if cell.get("cell_type") == "markdown" and "```json" in cell.get("source", ""):
                json_section_found = True
                break
            idx += 1

        if not json_section_found:
            logger.warning("No ```json sections found in profile notebook")
            raise ValueError("No section found in profile notebook")

        # Validate that we have at least one complete description/code pair
        sections_found = 0
        while idx < len(cells) - 1:
            desc_cell = cells[idx]

            # Skip cells that don't contain ```json
            if desc_cell.get("cell_type") != "markdown" or "```json" not in desc_cell.get("source", ""):
                idx += 1
                continue

            next_idx = idx + 1
            if next_idx >= len(cells):
                break  # No cell following the description

            code_cell = cells[next_idx]

            # Description with ```json must be followed by code cell
            if code_cell.get("cell_type") != "code":
                logger.error(
                    "Description cell at %d not followed by code cell; skipping", idx
                )
                raise ValueError("Profile notebook contains incomplete section. Each section must have a description and code cell.")

            sections_found += 1
            idx += 2  # Move past the processed code cell

        if sections_found == 0 and json_section_found:
            raise ValueError(
                "No valid description/code section pairs found after profile description"
            )

        logger.debug("Profile notebook validation passed with %d sections", sections_found)