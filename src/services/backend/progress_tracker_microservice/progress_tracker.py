from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


class ProgressTracker:
    def __init__(self, pg_pool: asyncpg.Pool):
        self._pg_pool = pg_pool

    async def save_progress(
        self,
        session_id: UUID,
        progress: Dict[str, Any],
        feedback: Optional[Dict[str, Any]] = None,
    ) -> None:
        async with self._pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO progress_records(session_id, progress, feedback, updated_at)
                VALUES ($1, $2::jsonb, $3::jsonb, now())
                ON CONFLICT (session_id)
                DO UPDATE SET
                  progress = EXCLUDED.progress,
                  feedback = EXCLUDED.feedback,
                  updated_at = now()
                """,
                session_id,
                json.dumps(progress),
                json.dumps(feedback or {}),
            )

    async def get_progress(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        async with self._pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT progress, feedback FROM progress_records WHERE session_id = $1",
                session_id,
            )
        if row is None:
            return None
        return {"progress": row["progress"], "feedback": row["feedback"]} 