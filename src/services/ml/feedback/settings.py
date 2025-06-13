"""Module for loading and validating application configuration.

This module defines a Pydantic Settings class to manage configuration
variables for the FastAPI application. It loads settings from environment
variables and a .env file.

Public API:
    - settings: The application settings object.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Specifies application configuration.

    Reads configuration from environment variables.
    Dotenv file is supported.

    Attributes:
        llm_base_url (str): The base URL of the LLM server.
        llm_api_key (str): The API key for the LLM server.
        llm_model (str): The model name to use for the LLM.
        feedback_service_host (str): The host for the feedback service.
        feedback_service_port (int): The port for the feedback service.
        feedback_service_n_workers (int): The number of workers for the feedback service.
    """

    llm_base_url: str
    llm_api_key: str
    llm_model: str
    feedback_service_host: str = "127.0.0.1"
    feedback_service_port: int = 8000
    feedback_service_n_workers: int = 1
    
    open_api_folder: str = "./docs/openapi/"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()