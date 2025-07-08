"""Shared ML utilities package.

This package exposes common utilities such as `get_qwen_client` for other microservices.
"""

from .qwen import get_qwen_client

__all__: list[str] = ["get_qwen_client"] 