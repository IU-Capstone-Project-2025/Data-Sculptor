from __future__ import annotations

from fastapi import Request, Depends
from typing import Annotated
import asyncpg

from progress_tracker import ProgressTracker


def get_pg_pool(request: Request):
    return request.state.postgres_pool


def get_progress_tracker(pg_pool: Annotated[asyncpg.Pool, Depends(get_pg_pool)]) -> ProgressTracker:
    return ProgressTracker(pg_pool) 