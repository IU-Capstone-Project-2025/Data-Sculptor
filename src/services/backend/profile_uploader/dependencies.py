"""FastAPI dependency factories for the Profile Uploader service."""

from __future__ import annotations

from fastapi import Request, Depends
from typing import Annotated
import asyncpg

from profile_uploader import ProfileUploader


def get_pg_pool(request: Request):
    """Return the shared *asyncpg* connection pool from the lifespan state."""

    return request.state.postgres_pool


def get_profile_service(
    pg_pool: Annotated[asyncpg.Pool, Depends(get_pg_pool)],
) -> ProfileUploader:
    """Create a *ProfileUploaderService* instance wired with *pg_pool*."""

    return ProfileUploader(pg_pool)
