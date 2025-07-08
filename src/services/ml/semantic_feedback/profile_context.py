"""Gateway for retrieving reference profile context from the database.

This module encapsulates **all** database access related to profiles so that
other parts of the service remain decoupled from persistence details. A single
instance is typically created per request via FastAPI dependency injection.
"""

from __future__ import annotations

from typing import Tuple
import asyncpg
import uuid


class ProfileContextGateway:
    """Retrieve profile description, section description and reference code."""

    def __init__(self, pg_pool: asyncpg.Pool):
        self._pg_pool = pg_pool

    async def get_section(
        self, profile_id: uuid.UUID, section_index: int
    ) -> Tuple[str, str, str]:
        """Return *(profile_desc, section_desc, reference_code)* for the section.

        Args:
            profile_id: UUID of the profile/case.
            section_index: Zero-based index of the section within the profile.

        Raises:
            ValueError: If the profile/section pair does not exist.

        Returns:
            tuple[str, str, str]: A tuple containing the profile description,
            section description, and reference code.
        """

        async with self._pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT p.description AS profile_desc,
                       ps.description AS section_desc,
                       ps.code AS section_code
                FROM profile_sections ps
                JOIN profiles p ON ps.profile_id = p.id
                WHERE ps.profile_id = $1 AND ps.section_id = $2
                """,
                profile_id,
                section_index,
            )

        if row is None:
            raise ValueError("Profile or section not found")

        return row["profile_desc"], row["section_desc"], row["section_code"]
