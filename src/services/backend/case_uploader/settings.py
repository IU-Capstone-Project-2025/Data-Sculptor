"""Configuration settings for the Profile Uploader micro-service.

This module exposes a *singleton* `settings` instance that encapsulates
all environment-driven configuration required by the service.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load variables from a local .env file *before* instantiating `Settings`.
load_dotenv()


class Settings(BaseSettings):
    """Application configuration pulled from the environment.

    Attributes:
        postgres_dsn: PostgreSQL connection string.
        case_upload_service_host: Host/interface to bind the HTTP server to.
        case_upload_service_port: TCP port exposed by the HTTP server.
        case_upload_service_n_workers: Number of *uvicorn* workers to spawn.
    """

    # required
    profile_postgres_dsn: str

    # MinIO settings
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "cases"

    # optional with sane defaults
    case_upload_service_host: str = "127.0.0.1"
    case_upload_service_port: int = 8001
    case_upload_service_n_workers: int = 1

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


# Single shared settings instance
settings = Settings()
