"""Direct feedback client for semantic evaluation without API calls.

This script imports and uses the FeedbackGenerator from the main codebase
while also accessing local test utilities.

IMPORTANT: Importing this module will shadow all local models with names:
    - prompts
    - schemas
    - llm_schemas
    - profile_context
    - feedback_generator
If you need to use local models with such names, import them with importlib.
"""

from __future__ import annotations

import asyncio
import importlib.util
import uuid
from pathlib import Path

from settings import settings
from schemas import ParsedCaseData, FeedbackRequest, FeedbackResponse

# Import qwen client function
project_root = Path(__file__).parent.parent.parent
qwen_path = (
    project_root / "src" / "services" / "ml" / "shared_ml" / "shared_ml" / "qwen.py"
)
qwen_spec = importlib.util.spec_from_file_location("qwen", qwen_path)
qwen_module = importlib.util.module_from_spec(qwen_spec)
qwen_spec.loader.exec_module(qwen_module)
get_qwen_client = qwen_module.get_qwen_client


def import_semantic_feedback_modules():
    """Import semantic feedback modules using importlib with proper dependency resolution."""
    import sys

    project_root = Path(__file__).parent.parent.parent
    semantic_feedback_dir = (
        project_root / "src" / "services" / "ml" / "semantic_feedback"
    )

    # Import dependencies first in the correct order
    module_dependencies = [
        "prompts",
        "schemas",
        "llm_schemas",
        "profile_context",
        "feedback_generator",
    ]

    modules = {}

    for module_name in module_dependencies:
        module_path = semantic_feedback_dir / f"{module_name}.py"
        if not module_path.exists():
            continue

        spec = importlib.util.spec_from_file_location(
            f"semantic_feedback_{module_name}", module_path
        )
        module = importlib.util.module_from_spec(spec)

        # Add previously loaded modules to sys.modules so they can be imported
        for prev_name, prev_module in modules.items():
            sys.modules[prev_name] = prev_module

        try:
            spec.loader.exec_module(module)
            modules[module_name] = module
        except ImportError as e:
            print(f"Warning: Could not import {module_name}: {e}")
            continue

    return modules


# Import semantic feedback modules using importlib (non-local)
semantic_modules = import_semantic_feedback_modules()
FeedbackGenerator = semantic_modules["feedback_generator"].FeedbackGenerator


class MockProfileContextGateway:
    """Mock ProfileContextGateway that returns profile data from evaluation input for all cases."""

    def __init__(self, cases_data: dict[str, ParsedCaseData]):
        """Initialize with all cases data.

        Args:
            cases_data: Dictionary mapping case_id to case data with structure:
                {
                    "case_id": {
                        "task_description": str,
                        "profile_sections": list[ProfileSectionData],
                        "case_uuid": uuid.UUID
                    }
                }
        """
        self.cases_data = cases_data

    async def get_section(
        self, case_id: uuid.UUID, section_index: int
    ) -> tuple[str, str, str]:
        """Return profile and section data for the specified case and section.

        Args:
            case_id: UUID of the case.
            section_index: Zero-based index of the section within the profile.

        Returns:
            A tuple containing the profile description, section description,
            and reference code.

        Raises:
            ValueError: If the case/section pair does not exist.
        """
        case_data = self.cases_data[str(case_id)]
        section = case_data["profile_sections"][section_index]
***REMOVED*** (case_data["task_desc"], section["description"], section["code"])


class DirectFeedbackClient:
    """Direct feedback client that calls FeedbackGenerator without API overhead."""

    def __init__(self, parsed_cases: dict[str, ParsedCaseData]):
        """Initialize the direct feedback client.

        Args:
            cases_data: Dictionary mapping case_id to case data with all profile information.
        """
        # Initialize LLM client using qwen client with LOCAL settings
        self.llm = get_qwen_client(
            llm_base_url=settings.local_llm_base_url,
            llm_api_key=settings.local_llm_api_key,
            llm_model=settings.local_llm_model,
            enable_thinking=settings.local_enable_thinking,
            temperature=0,
        )

        # Create mock profile context gateway
        self.profile_context = MockProfileContextGateway(parsed_cases)

        # Create feedback generator
        self.feedback_generator = FeedbackGenerator(
            llm_client=self.llm, profile_context=self.profile_context
        )

    def get_feedback(self, request: FeedbackRequest) -> FeedbackResponse:
        """Generate feedback for a code snippet.

        Args:
            request: The feedback request with code and metadata.

        Returns:
            FeedbackResponse with generated feedback.
        """
        # Run the async feedback generation in a synchronous context

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            non_localized_feedback, localized_feedback = loop.run_until_complete(
                self.feedback_generator.generate_feedback(
                    user_code=request.current_code,
                    case_id=request.case_id,
                    section_index=request.section_index,
                    global_line_offset=request.cell_code_offset,
                )
            )

    ***REMOVED*** FeedbackResponse(
                non_localized_feedback=non_localized_feedback,
                localized_feedback=[
                    warning.model_dump() for warning in localized_feedback
                ],
            )

        finally:
            loop.close()
