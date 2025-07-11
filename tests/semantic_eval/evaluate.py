"""
Evaluate semantic feedback using OpenAI API and output JSON metrics
suitable for the metrics_processing.py script.

Usage
-----
# New folder structure mode:
python evaluate_feedback.py --cases_path ./test_cases --output_dir ./results
"""

import argparse
import sys

from semantic_evaluator import SemanticEvaluator, NotebookParseError


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate semantic feedback using OpenAI API."
    )

    # New folder structure mode
    parser.add_argument(
        "--input_dir",
        help="Path to folder containing case-*/profile.ipynb and solution.ipynb",
    )

    # Common arguments
    parser.add_argument(
        "--output_dir", default="results", help="Directory to store JSON results"
    )

    args = parser.parse_args()

    try:
        # Initialize evaluator
        evaluator = SemanticEvaluator()

        evaluator.evaluate(args.input_dir, args.output_dir)

    except NotebookParseError as exc:
        print(f"Error parsing notebook: {exc}")
        sys.exit(1)
    except FileNotFoundError as exc:
        print(f"File not found: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"Error during evaluation: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
