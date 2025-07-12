"""FastAPI dependency factories for the Profile Uploader service."""

from __future__ import annotations

from fastapi import Request, Depends
from typing import Annotated
import asyncpg
from minio import Minio

from profile_uploader import ProfileUploader
from case_uploader import CaseUploader
from validation import FileValidator
from settings import settings


async def get_pg_connection(request: Request):
    """Return a transactional database connection from the shared pool.

    Creates a connection with an active transaction that will be automatically
    committed on success or rolled back on error.
    """
    pool = request.state.postgres_pool
    async with pool.acquire() as conn:
        yield conn


def get_minio_client() -> Minio:
    """Create MinIO client instance."""
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,  # Set to True if using HTTPS
    )


def get_profile_service(
    conn: Annotated[asyncpg.Connection, Depends(get_pg_connection)],
) -> ProfileUploader:
    """Create a *ProfileUploader* instance wired with a transactional connection."""

    return ProfileUploader(conn)


def get_file_validator() -> FileValidator:
    """Create a *FileValidator* instance."""
    return FileValidator()


def get_case_uploader(
    conn: Annotated[asyncpg.Connection, Depends(get_pg_connection)],
    minio_client: Annotated[Minio, Depends(get_minio_client)],
    case_uploader: Annotated[ProfileUploader, Depends(get_profile_service)],
    validator: Annotated[FileValidator, Depends(get_file_validator)],
) -> CaseUploader:
    """Create a *CaseUploader* instance wired with a transactional connection, *minio_client*, and *case_uploader*."""

    return CaseUploader(conn, minio_client, case_uploader, validator)
