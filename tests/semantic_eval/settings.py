"""Configuration management for semantic evaluation using Pydantic Settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class SemanticEvalSettings(BaseSettings):
    """Configuration for semantic evaluation system.

    This class handles all configuration parameters including API keys,
    model settings, and evaluation parameters. Values can be set via
    environment variables or .env files.
    """

    # API Configuration
    openai_api_key: str = Field(..., description="OpenAI API key for OpenRouter")
    openai_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="Base URL for OpenAI API (OpenRouter endpoint)",
    )

    # Model Configuration
    model_name: str = Field(
        default="deepseek/deepseek-chat-v3-0324:free",
        description="Model name to use for evaluation",
    )
    temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="Temperature for model responses"
    )
    max_tokens: int = Field(
        default=1000, gt=0, description="Maximum tokens for model responses"
    )

    # File Paths
    default_output_dir: str = Field(
        default="results", description="Default output directory for results"
    )

    # Semantic Feedback Service Configuration
    semantic_feedback_base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for the semantic feedback service",
    )

    # Retry Configuration
    max_retries: int = Field(
        default=3, ge=0, description="Maximum number of API request retries"
    )
    retry_delay: float = Field(
        default=1.0, ge=0.0, description="Delay between retries in seconds"
    )
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=("settings_",),  # AICODE-NOTE: Avoid conflict with 'model_' protected namespace
    )


settings = SemanticEvalSettings()
