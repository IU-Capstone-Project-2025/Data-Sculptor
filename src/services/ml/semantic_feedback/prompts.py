"""Centralised prompt templates for the semantic-feedback service.

This module houses *all* LangChain `PromptTemplate` instances used across the
service so that they are defined in one place and can be imported elsewhere.
"""

from langchain_core.prompts import PromptTemplate

FEEDBACK_PROMPT = PromptTemplate.from_template(
    """
You are an expert code reviewer.
You are tasked with providing feedback on the code from a Jupyter Notebook.
The user has submitted a notebook, and your job is to provide feedback on the code cells.

Please provide a high-level summary of the notebook's purpose, followed by
specific, constructive feedback on the code. Focus on code quality, logic,
potential bugs, and areas for improvement. Be clear and concise.

Here is the content of the code cells from the notebook, in order:

{code}
"""
)

WARNINGS_PROMPT = PromptTemplate.from_template(
    """
You are an automated code quality assistant. The user will send you a code
snippet from a Jupyter notebook annotated with 1-based line numbers like
"1 | <code>".

Your task: Identify semantic or logical issues (not syntax errors) and
return an array of warnings in JSON format. Each warning must have these
fields:
  - "start_line": 1-based line number where the problematic span begins.
  - "end_line":   1-based line number where the span ends (inclusive). Use the same
    value as "start_line" for single-line issues.
  - "message":     A short (≤120 chars) description of the issue.

If there are no issues, return an empty JSON list `[]`.

If line doesn't contain any issues, don't report anything about this line.
Include only the lines that contain semantic or logical issues.

Return *only* valid JSON. Do not wrap it in markdown or prose.

Snippet:
{code}
"""
) 