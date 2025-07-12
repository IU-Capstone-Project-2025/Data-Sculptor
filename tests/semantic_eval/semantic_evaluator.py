"""Semantic evaluation system for ML task assessment."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

import nbformat
from tqdm import tqdm

from evaluation_client import EvaluationClient
from settings import settings
from router_client import SemanticFeedbackClient
from schemas import (
    FeedbackRequest,
    TestCaseData,
    ProfileSectionData,
    SolutionSectionData,
    EvaluationMetrics,
    AggregatedMetrics,
)


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
        self.router_client = SemanticFeedbackClient()

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
        total_required_terms = len(solution_section["required_ml_terms"])
        total_required_issues = len(solution_section["problems_to_detect"])
        total_issues_mentioned = raw_result.true_positives + raw_result.false_positives

        # Calculate ML term ratio
        ml_term_ratio = (
            raw_result.ml_terms_found / total_required_terms
            if total_required_terms > 0
            else 0
        )

        # Calculate precision and recall for issues
        precision = (
            raw_result.true_positives
            / (raw_result.true_positives + raw_result.false_positives)
            if (raw_result.true_positives + raw_result.false_positives) > 0
            else 0
        )

        recall = (
            raw_result.true_positives / total_required_issues
            if total_required_issues > 0
            else 0
        )

        # Profile detail detection (1 = good, 0 = bad)
        no_case_profile_detail = 0 if raw_result.mentions_profile_details else 1

        # Consequence language ratio
        consequence_language_ratio = (
            raw_result.consequence_language_issues / total_issues_mentioned
            if total_issues_mentioned > 0
            else 0
        )

        return EvaluationMetrics(
            ml_term_ratio=ml_term_ratio,
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
                {
                    "case_id": case_dir.name,
                    "profile_path": str(profile_path),
                    "solution_path": str(solution_path),
                }
            )

        return cases

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

        return task_description, sections

    def parse_solution_notebook(self, notebook_path: str) -> list[SolutionSectionData]:
        """Parse solution notebook with JSON metadata and code.

        Expected structure:
        - Alternating markdown cells (with JSON) and code cells
        - JSON format: {"required_ml_terms": [...], "problems_to_detect": [...]}

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
                    required_ml_terms=json_data.get("required_ml_terms", []),
                    problems_to_detect=json_data.get("problems_to_detect", []),
                )
            )

            idx += 2

        if not sections:
            raise NotebookParseError(f"No sections found in solution: {notebook_path}")

        return sections

    def evaluate_section(
        self,
        task_description: str,
        profile_section: ProfileSectionData,
        solution_section: SolutionSectionData,
        profile_id: uuid.UUID,
        section_index: int,
    ) -> EvaluationMetrics:
        """Evaluate a profile section against a solution section via router feedback.

        Args:
            task_description: The overall task description.
            profile_section: Tuple of (description, code) from profile.
            solution_section: Dictionary with solution data.
            profile_id: UUID for the profile (generated from case name).
            section_index: Index of the section being evaluated.

        Returns:
            Dictionary with calculated evaluation metrics.
        """
        profile_desc = profile_section["description"]
        profile_code = profile_section["code"]

        # Get feedback from router
        router_response = self.router_client.get_feedback(
            FeedbackRequest(
                current_code=solution_section["code"],
                section_index=section_index,
                profile_index=profile_id,
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
            router_feedback=router_response.get_description_for_llm(),
        )

        # Calculate final metrics from raw observations
        calculated_metrics = self.calculate_metrics(raw_result, solution_section)

        return calculated_metrics

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

        results = {}

        for test_case in tqdm(test_cases, desc="Evaluating test cases"):
            case_id = test_case["case_id"]

            try:
                # Parse notebooks
                task_desc, profile_sections = self.parse_profile_notebook(
                    test_case["profile_path"]
                )
                solution_sections = self.parse_solution_notebook(
                    test_case["solution_path"]
                )

                # Generate profile ID from case name
                # AICODE-TODO: Replace with id received from profile uploader
                profile_id = uuid.uuid5(uuid.NAMESPACE_DNS, case_id)

                # Evaluate each section pair
                section_results = []
                min_sections = min(len(profile_sections), len(solution_sections))

                for i in range(min_sections):
                    section_result = self.evaluate_section(
                        task_desc,
                        profile_sections[i],
                        solution_sections[i],
                        profile_id,
                        i,
                    )
                    section_results.append(section_result)

                # Aggregate results for this case
                if section_results:
                    aggregated = self._aggregate_section_results(section_results)
                    results[case_id] = {
                        "router_feedback": {
                            "acceptance_criteria": {
                                "sections_evaluated": "Yes"
                                if section_results
                                else "No",
                            },
                            "quality_attributes": aggregated,
                        }
                    }

            except Exception as exc:
                print(f"Error evaluating {case_id}: {exc}")
                results[case_id] = {
                    "router_feedback": {
                        "acceptance_criteria": {"sections_evaluated": "No"},
                        "quality_attributes": {"error": str(exc)},
                    }
                }

        # Save results
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "evaluation_results.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"Evaluation complete. Results saved to: {output_path}")

    def _aggregate_section_results(
        self, section_results: list[EvaluationMetrics]
    ) -> AggregatedMetrics:
        """Aggregate results from multiple sections.

        Args:
            section_results: List of calculated metrics dictionaries.

        Returns:
            Aggregated metrics dictionary in required format.
        """
        if not section_results:
            return AggregatedMetrics(
                ml_term_ratio=0.0,
                necessary_issues_precision=0.0,
                necessary_issues_recall=0.0,
                no_case_profile_detail="0",
                consequence_language_ratio=0.0,
            )

        # Parse percentage values and calculate averages
        ml_term_ratios = []
        precisions = []
        recalls = []
        profile_details = []
        consequence_ratios = []

        for result in section_results:
            ml_term_ratios.append(result["ml_term_ratio"])
            precisions.append(result["necessary_issues_precision"])
            recalls.append(result["necessary_issues_recall"])
            profile_details.append(result["no_case_profile_detail"])
            consequence_ratios.append(result["consequence_language_ratio"])

        # Calculate aggregated metrics
        avg_ml_term_ratio = (
            sum(ml_term_ratios) / len(ml_term_ratios) if ml_term_ratios else 0.0
        )
        avg_precision = sum(precisions) / len(precisions) if precisions else 0.0
        avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
        min_profile_detail = str(min(profile_details)) if profile_details else "0"
        avg_consequence_ratio = (
            sum(consequence_ratios) / len(consequence_ratios)
            if consequence_ratios
            else 0.0
        )

        return AggregatedMetrics(
            ml_term_ratio=avg_ml_term_ratio,
            necessary_issues_precision=avg_precision,
            necessary_issues_recall=avg_recall,
            no_case_profile_detail=min_profile_detail,
            consequence_language_ratio=avg_consequence_ratio,
        )
