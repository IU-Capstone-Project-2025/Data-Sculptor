"""HTTP client for calling the semantic feedback router."""

from __future__ import annotations
from schemas import FeedbackRequest, RouterFeedbackResponse, LocalizedFeedbackItem
from settings import settings
import requests


class SemanticFeedbackClient:
    """HTTP client for the semantic feedback service."""

    def __init__(self):
        """Initialize the client.

        Args:
            base_url: Base URL of the semantic feedback service.
            timeout: Request timeout in seconds.
        """
        self.base_url = settings.semantic_feedback_base_url.rstrip("/")

    def get_feedback(self, request: FeedbackRequest) -> RouterFeedbackResponse:
        """Get feedback from the semantic feedback service.

        Args:
            request: The feedback request.

        Returns:
            RouterFeedbackResponse with the service response.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        # url = f"{self.base_url}/feedback"

        # try:
        #     response = requests.post(url, json=request.model_dump(), timeout=30)
        #     response.raise_for_status()
        #     return RouterFeedbackResponse.model_validate(response.json())
        # except requests.HTTPError as exc:
        #     raise exc

        mock_feedback: list[str] = []
        mock_localized: list[LocalizedFeedbackItem] = [
            LocalizedFeedbackItem(
                range={
                    "start": {"line": 9, "character": 0},
                    "end": {"line": 9, "character": 15},
                },
                severity=2,
                code="custom-warning",
                source="Data Sculptor",
                message="Test set is derived from train set. This can lead to data leakage.",
            ),
            LocalizedFeedbackItem(
                range={
                    "start": {"line": 19, "character": 0},
                    "end": {"line": 19, "character": 20},
                },
                severity=2,
                code="custom-warning",
                source="Data Sculptor",
                message="Using last duplicate rows can lead to losing information. Instead you have to change keep=\"last\" to keep=\"first\"",
            ),
        ]
        return RouterFeedbackResponse(
            non_localized_feedback=mock_feedback, localized_feedback=mock_localized
        )
