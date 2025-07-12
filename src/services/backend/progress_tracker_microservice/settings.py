from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    progress_postgres_dsn: str
    progress_service_host: str = "127.0.0.1"
    progress_service_port: int = 8002
    progress_service_n_workers: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings() 