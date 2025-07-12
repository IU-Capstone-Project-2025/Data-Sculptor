"""FastAPI dependency factories for the Profile Uploader service."""

from __future__ import annotations

from fastapi import Request, Depends
from typing import Annotated
import asyncpg
from minio import Minio

from profile_uploader import ProfileUploader
from case_uploader import CaseUploader
from settings import settings


def get_pg_pool(request: Request):
    """Return the shared *asyncpg* connection pool from the lifespan state."""

    return request.state.postgres_pool


def get_minio_client() -> Minio:
    """Create MinIO client instance."""
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False  # Set to True if using HTTPS
    )


def get_profile_service(
    pg_pool: Annotated[asyncpg.Pool, Depends(get_pg_pool)],
) -> ProfileUploader:
    """Create a *ProfileUploaderService* instance wired with *pg_pool*."""

    return ProfileUploader(pg_pool)


def get_case_uploader(
    pg_pool: Annotated[asyncpg.Pool, Depends(get_pg_pool)],
    minio_client: Annotated[Minio, Depends(get_minio_client)],
    profile_uploader: Annotated[ProfileUploader, Depends(get_profile_service)],
) -> CaseUploader:
    """Create a *CaseUploader* instance wired with *pg_pool*, *minio_client*, and *profile_uploader*."""

    return CaseUploader(pg_pool, minio_client, profile_uploader)
