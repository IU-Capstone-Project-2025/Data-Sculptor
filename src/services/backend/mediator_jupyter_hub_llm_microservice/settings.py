from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Specifies application configuration.

    Reads configuration from environment variables.
    Dotenv file is supported.

    Attributes:
        feedback_service_url (str): The host for the feedback service.
    """

    feedback_service_url: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()