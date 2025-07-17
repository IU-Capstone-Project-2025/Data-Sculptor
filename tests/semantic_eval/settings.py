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
    evaluator_llm_api_key: str = Field(..., description="OpenAI API key for OpenRouter")
    evaluator_llm_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="Base URL for OpenAI API (OpenRouter endpoint)",
    )
    evaluator_llm_model: str = Field(
        default="deepseek/deepseek-chat-v3-0324:free",
        description="Model name to use for evaluation",
    )

    # Local Qwen Client Configuration
    local_llm_base_url: str = Field(
        default="http://10.100.30.239:9362/v1",
        description="Base URL for local LLM service",
    )
    local_llm_api_key: str = Field(
        default="vllml", description="API key for local LLM authentication"
    )
    local_llm_model: str = Field(
        default="Qwen/Qwen3-30B-A3B",
        description="Model name for local LLM",
    )
    local_enable_thinking: bool = Field(
        default=True, description="Enable thinking mode for local LLM"
    )

    # File Paths
    default_output_dir: str = Field(
        default="results", description="Default output directory for results"
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
        protected_namespaces=(
            "settings_",
        ),  # AICODE-NOTE: Avoid conflict with 'model_' protected namespace
    )


settings = SemanticEvalSettings()
