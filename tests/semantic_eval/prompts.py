"""Evaluation prompts for semantic feedback assessment."""

from __future__ import annotations


ROUTER_FEEDBACK_EVALUATION_PROMPT = """You are an expert evaluator of AI-generated feedback for machine learning coding tasks.

Your task is to analyze router feedback and provide specific counts and classifications. Do NOT calculate ratios or percentages - only count what you observe.

TASK DESCRIPTION:
{task_description}

PROFILE SECTION (Reference):
Description: {profile_section_description}
Code: {profile_section_code}

SOLUTION SECTION (Evaluation Target):
Required ML Terms: {required_ml_terms}
Problems to Detect: {problems_to_detect}
Solution Code: {solution_code}

ROUTER FEEDBACK TO EVALUATE:
{router_feedback}

Please analyze the ROUTER FEEDBACK and provide these counts/classifications:

1. ML TERMS: Count how many of the required ML terms from the list above are mentioned in the router feedback.

2. ISSUE DETECTION: For each issue mentioned in the router feedback, classify it as:
   - TRUE POSITIVE: Issue is correctly identified AND is in the "Problems to Detect" list
   - FALSE POSITIVE: Issue is mentioned but NOT in the "Problems to Detect" list  
   - FALSE NEGATIVE: Required issue from "Problems to Detect" list that router feedback failed to mention

3. PROFILE DETAILS: Check if router feedback mentions ANY specific details from the PROFILE SECTION code such as:
   - Variable names (e.g., "df", "model", "X_train")
   - Code structure details (e.g., "the for loop", "the if statement")
   - Implementation specifics from profile code
   Answer: True if ANY profile details are mentioned, False if none are mentioned.

4. CONSEQUENCE LANGUAGE: For each issue mentioned in router feedback, classify the language as:
   - CONSEQUENCE-FOCUSED: Describes problems, impacts, or what could go wrong
   - SOLUTION-FOCUSED: Suggests fixes, implementations, or specific code changes
   Count only the consequence-focused issues.

Provide only the raw counts and classifications - no calculations."""