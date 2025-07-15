"""Semantic evaluation system for ML task assessment."""

from __future__ import annotations

import json
import os
***REMOVED***
import uuid
from pathlib import Path

import nbformat
from tqdm import tqdm

from evaluation_client import EvaluationClient
from settings import settings
from direct_feedback_client import DirectFeedbackClient, FeedbackRequest
import importlib.util

# Import local schemas module explicitly to avoid conflict with semantic feedback schemas
_schemas_path = Path(__file__).parent / "schemas.py"
_schemas_spec = importlib.util.spec_from_file_location("local_schemas", _schemas_path)
_local_schemas = importlib.util.module_from_spec(_schemas_spec)
_schemas_spec.loader.exec_module(_local_schemas)

TestCaseData = _local_schemas.TestCaseData
ParsedCaseData = _local_schemas.ParsedCaseData
ProfileSectionData = _local_schemas.ProfileSectionData
SolutionSectionData = _local_schemas.SolutionSectionData
EvaluationMetrics = _local_schemas.EvaluationMetrics
SectionIssuesData = _local_schemas.SectionIssuesData


class NotebookParseError(RuntimeError):
    """Raised when notebook structure does not match expectations."""


class SemanticEvaluator:
    """Semantic evaluation system for ML task assessment.

    This class handles parsing of folder structures containing profile
    and solution notebooks, evaluates them using OpenAI API, and produces
    metrics compatible with the existing metrics processing pipeline.
    """

    def __init__(self):
        """Initialize the semantic evaluator using global settings."""
        self.evaluation_client = EvaluationClient()
        self.direct_feedback_client = None  # Will be initialized with case data

    def calculate_metrics(
        self, raw_result, solution_section: SolutionSectionData
    ) -> EvaluationMetrics:
        """Calculate final metrics from raw LLM observations.

        Args:
            raw_result: Raw counts and classifications from LLM.
            solution_section: Solution data with required terms and problems.

        Returns:
            Dictionary with calculated metrics in required format.
        """
        # Get known totals from solution data
        total_required_issues = len(solution_section["problems_to_detect"])
        total_issues_mentioned = (
            raw_result.true_positives_issue_count
            + raw_result.false_positives_issues_count
        )

        # Calculate brief issue ratio
        brief_issue_ratio = (
            min(raw_result.brief_issues_count, total_issues_mentioned)
            / total_issues_mentioned
            if total_issues_mentioned > 0
            else 0
        )

        # Calculate precision and recall for issues
        precision = (
            min(raw_result.true_positives_issue_count, total_issues_mentioned)
            / total_issues_mentioned
            if total_issues_mentioned > 0
            else 0
        )

        recall = (
            min(raw_result.true_positives_issue_count, total_required_issues)
            / total_required_issues
            if total_required_issues > 0
            else 0
        )

        # Profile detail detection (1 = good, 0 = bad)
        no_case_profile_detail = "0" if raw_result.is_profile_detail_mentioned else "1"

        # Consequence language ratio
        consequence_language_ratio = (
            min(raw_result.consequence_language_issues_count, total_issues_mentioned)
            / total_issues_mentioned
            if total_issues_mentioned > 0
            else 0
        )

***REMOVED*** EvaluationMetrics(
            brief_issue_ratio=brief_issue_ratio,
            necessary_issues_precision=precision,
            necessary_issues_recall=recall,
            no_case_profile_detail=no_case_profile_detail,
            consequence_language_ratio=consequence_language_ratio,
        )

    def parse_folder_structure(self, path: str) -> list[TestCaseData]:
        """Parse folder structure with case-*/profile.ipynb and solution.ipynb.

        Args:
            path: Root path containing case directories (relative or absolute).

        Returns:
            List of dictionaries with case_id, profile_path, solution_path.

        Raises:
            FileNotFoundError: If required files are missing.
        """
        # AICODE-NOTE: Resolve the path to an absolute path to support relative paths like "./results"
        root_path = Path(path).expanduser().resolve()
        if not root_path.exists():
            raise FileNotFoundError(f"Path does not exist: {root_path}")

        cases = []
        try:
            case_dirs = [d for d in root_path.iterdir() if d.is_dir()]
        except Exception as exc:
            raise FileNotFoundError(
                f"Unable to list directories in {root_path}: {exc}"
            ) from exc

        if not case_dirs:
            raise FileNotFoundError(f"No case-* directories found in {root_path}")

        for case_dir in sorted(case_dirs):
            profile_path = case_dir / "profile.ipynb"
            solution_path = case_dir / "solution.ipynb"

            if not profile_path.exists():
                raise FileNotFoundError(f"Missing profile.ipynb in {case_dir}")
            if not solution_path.exists():
                raise FileNotFoundError(f"Missing solution.ipynb in {case_dir}")

            cases.append(
                TestCaseData(
                    case_name=case_dir.name,
                    profile_path=str(profile_path),
                    solution_path=str(solution_path),
                )
            )

***REMOVED*** cases

    def parse_profile_notebook(
        self, notebook_path: str
    ) -> tuple[str, list[ProfileSectionData]]:
        """Parse profile notebook following the profile uploader pattern.

        Expected structure:
        - First markdown cell: task description
        - First cell with ```json: start of sections
        - Alternating markdown (with ```json) and code cells

        Args:
            notebook_path: Path to the profile notebook.

        Returns:
            TaskDescription: The task description.
            List[Tuple[str, str]]: A list of (section_description, section_code) tuples.

        Raises:
            NotebookParseError: If notebook structure is invalid.
        """
        try:
            with open(notebook_path, "r", encoding="utf-8") as f:
                nb = nbformat.read(f, as_version=4)
        except Exception as exc:
            raise NotebookParseError(
                f"Unable to read notebook file: {notebook_path}"
            ) from exc

        cells = nb.get("cells", [])
        if not cells:
            raise NotebookParseError(f"Notebook contains no cells: {notebook_path}")

        if cells[0].get("cell_type") != "markdown":
            raise NotebookParseError(f"First cell must be markdown: {notebook_path}")

        task_description = cells[0].get("source", "").strip()
        sections = []

        # Find first cell with ```json after the task description
        idx = 1
        while idx < len(cells):
            cell = cells[idx]
            if cell.get("cell_type") == "markdown" and "```json" in cell.get(
                "source", ""
            ):
                break
            idx += 1

        # Parse (markdown with ```json, code) pairs
        while idx < len(cells) - 1:
            desc_cell = cells[idx]

            if desc_cell.get(
                "cell_type"
            ) != "markdown" or "```json" not in desc_cell.get("source", ""):
                idx += 1
                continue

            next_idx = idx + 1
            if next_idx >= len(cells):
                break

            code_cell = cells[next_idx]
            if code_cell.get("cell_type") != "code":
                idx += 1
                continue

            section_desc = desc_cell.get("source", "").strip()
            section_code = code_cell.get("source", "").strip()
            sections.append(
                ProfileSectionData(description=section_desc, code=section_code)
            )

            idx += 2

        if not sections:
            raise NotebookParseError(f"No sections found in profile: {notebook_path}")

***REMOVED*** task_description, sections

    def parse_solution_notebook(self, notebook_path: str) -> list[SolutionSectionData]:
        """Parse solution notebook with JSON metadata and code.

        Expected structure:
        - Alternating markdown cells (with JSON) and code cells
        - JSON format: {"problems_to_detect": [...]}

        Args:
            notebook_path: Path to the solution notebook.

        Returns:
            List of dictionaries with parsed JSON data and code.

        Raises:
            NotebookParseError: If notebook structure is invalid.
        """
        try:
            with open(notebook_path, "r", encoding="utf-8") as f:
                nb = nbformat.read(f, as_version=4)
        except Exception as exc:
            raise NotebookParseError(
                f"Unable to read notebook file: {notebook_path}"
            ) from exc

        cells = nb.get("cells", [])
        sections = []

        idx = 0
        while idx < len(cells) - 1:
            json_cell = cells[idx]

            if json_cell.get("cell_type") != "markdown":
                idx += 1
                continue

            json_source = json_cell.get("source", "").strip()

            # Extract JSON from markdown cell
            try:
                # Try to parse as direct JSON
                json_data = json.loads(json_source)
            except json.JSONDecodeError:
                # Try to extract JSON from code block
                json_match = re.search(
                    r"```json\s*(\{.*?\})\s*```", json_source, re.DOTALL
                )
                if json_match:
                    try:
                        json_data = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        idx += 1
                        continue
                else:
                    idx += 1
                    continue

            # Get corresponding code cell
            code_idx = idx + 1
            if code_idx >= len(cells):
                break

            code_cell = cells[code_idx]
            if code_cell.get("cell_type") != "code":
                idx += 1
                continue

            code_content = code_cell.get("source", "").strip()

            sections.append(
                SolutionSectionData(
                    json_data=json_data,
                    code=code_content,
                    problems_to_detect=json_data.get("problems_to_detect", []),
                )
            )

            idx += 2

        if not sections:
            raise NotebookParseError(f"No sections found in solution: {notebook_path}")

***REMOVED*** sections

    def evaluate_section(
        self,
        task_description: str,
        profile_section: ProfileSectionData,
        solution_section: SolutionSectionData,
        case_id: uuid.UUID,
        section_index: int,
    ) -> tuple[EvaluationMetrics, SectionIssuesData]:
        """Evaluate a profile section against a solution section via semantic feedback pipeline.

        Args:
            task_description: The overall task description.
            profile_section: Tuple of (description, code) from profile.
            solution_section: Dictionary with solution data.
            profile_id: UUID for the profile (generated from case name).
            section_index: Index of the section being evaluated.

        Returns:
            Tuple of (calculated evaluation metrics, raw issues data).
        """
        profile_desc = profile_section["description"]
        profile_code = profile_section["code"]

        # Get feedback from direct feedback client
        feedback_response = self.direct_feedback_client.get_feedback(
            FeedbackRequest(
                current_code=solution_section["code"],
                section_index=section_index,
                case_id=case_id,
                cell_code_offset=0,
                use_deep_analysis=True,
            )
        )

        # Get raw LLM observations
        raw_result = self.evaluation_client.evaluate_section(
            task_description=task_description,
            profile_section_description=profile_desc,
            profile_section_code=profile_code,
            solution_section=solution_section,
            feedback=feedback_response.get_description_for_llm(),
        )

        # Calculate final metrics from raw observations
        calculated_metrics = self.calculate_metrics(raw_result, solution_section)

        # Extract raw issues data
        issues_data = SectionIssuesData(
            long_issues_found=raw_result.long_issues_found,
            false_positives_issues=raw_result.false_positives_issues,
            false_negatives_issues=raw_result.false_negatives_issues,
            profile_detail_mentioned=raw_result.profile_detail_mentioned,
            non_consequence_language_issues=raw_result.non_consequence_language_issues,
            feedback_text=feedback_response.get_description_for_llm(),
        )

***REMOVED*** calculated_metrics, issues_data

    def evaluate(self, cases_path: str, output_dir: str | None = None) -> None:
        """Evaluate all cases in a folder structure.

        Args:
            cases_path: Path to folder containing case directories.
            output_dir: Output directory for results.
            stage: Pipeline stage name for metrics.
        """
        output_dir = output_dir or settings.default_output_dir

        test_cases = self.parse_folder_structure(cases_path)
        print(f"Found {len(test_cases)} test cases to evaluate")

        # Parse all cases first to initialize DirectFeedbackClient
        parsed_cases = {}

        for test_case in test_cases:
            try:
                # Parse notebooks
                task_desc, profile_sections = self.parse_profile_notebook(
                    test_case["profile_path"]
                )
                solution_sections = self.parse_solution_notebook(
                    test_case["solution_path"]
                )

                # Store parsed data for evaluation
                parsed_cases[test_case["case_name"]] = ParsedCaseData(
                    case_id=uuid.uuid4(),  # Generate case ID
                    task_desc=task_desc,
                    profile_sections=profile_sections,
                    solution_sections=solution_sections,
                )

            except Exception as exc:
                print(f"Error parsing {test_case['case_name']}: {exc} skipping")

        # Initialize DirectFeedbackClient with all cases data
        self.direct_feedback_client = DirectFeedbackClient(parsed_cases)

        results = {}
        issues_results = {}

        for case_name, case_data in tqdm(
            parsed_cases.items(), desc="Evaluating test cases"
        ):
            try:
                # Evaluate each section pair
                min_sections = min(
                    len(case_data["profile_sections"]),
                    len(case_data["solution_sections"]),
                )

                for i in range(min_sections):
                    section_result, issues_data = self.evaluate_section(
                        case_data["task_desc"],
                        case_data["profile_sections"][i],
                        case_data["solution_sections"][i],
                        case_data["case_id"],
                        i,
                    )
                    
                    # Store results for this section with section index in key
                    section_key = f"{case_name}_section_{i}"
                    results[section_key] = {
                        "semantic_feedback": {
                            "acceptance_criteria": {
                                "sections_evaluated": "Yes",
                            },
                            "quality_attributes": section_result,
                        }
                    }

                    # Store issues data for this section
                    issues_results[section_key] = issues_data

            except Exception as exc:
                print(f"Error evaluating {case_name}: {exc}")
                # Store error for the case (without section index since we don't know which section failed)
                results[case_name] = {
                    "semantic_feedback": {
                        "acceptance_criteria": {"sections_evaluated": "No"},
                        "quality_attributes": {"error": str(exc)},
                    }
                }

        # Save results
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "evaluation_results.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        # Save issues data
        issues_output_path = os.path.join(output_dir, "evaluation_issues.json")
        with open(issues_output_path, "w", encoding="utf-8") as f:
            json.dump(issues_results, f, ensure_ascii=False, indent=2)

        print(f"Evaluation complete. Results saved to: {output_path}")
        print(f"Issues data saved to: {issues_output_path}")

