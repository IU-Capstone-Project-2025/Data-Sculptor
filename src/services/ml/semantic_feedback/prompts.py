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

LOCALIZE_WARNINGS_PROMPT = PromptTemplate.from_template(
    """
You are a rigorous static-analysis assistant. Your task is to **localise** a given set of high-level warnings inside a Python code snippet that is annotated with 1-based line numbers in the form `"<line_no> | <code>"`.

ASSUMPTIONS
- Each warning in the WARNINGS array **definitely** exists in the code at least once. But could exist in multiple places. Before claiming that warning exists in multiple places, make sure that it is really disting and not connected issues.
- Ignore any potential issue that is **not** listed in the input warnings.

YOUR TASK
1. Identify exactly **one** line range that best exemplifies each warning. Do
   not output more than one localisation object per warning, even if it appears
   multiple times.
2. Ensure that the chosen span contains explicit evidence of the issue (e.g.,
   the problematic identifier or pattern) and quote that evidence in your own
   reasoning before finalising.
3. Output exactly one localisation object **per warning** in the WARNINGS list—no
   more, no less.
4. For warnings that are difficult to localise to exact line, localise it to the place where it can cause the most harm.

CONSTRAINTS
- Emit a localisation object **only when you are 100 % certain** the code span violates the specified warning. If confidence <100 %, omit the span.
- Each input warning is definitely present in the code, so your output should contain at least one object for each warning in the input.
- Output localisation objects **only for warnings explicitly listed** in the WARNINGS section. **Never invent new warnings.**
- If the same warning appears multiple times, output one object per distinct, independent occurrence—not adjacent lines of the same issue.
- In output firstly provide the details of the original warning, then provide `message` of the warning that will be shown to the user.
- `messages` must contain focused and precise description of the issue. No vague descriptions are allowed.

STYLE GUIDE FOR "message"
- <= 150 characters.
- Sentence case, present tense.
- Include a *brief* reasoning explaining **why** the span violates the warning.
- Mention variable/function names that cause the issue.

Begin your analysis **after** reading the complete CODE and WARNINGS sections.

INPUT SECTIONS (delimited by triple dashes):
--- CODE ---
{code}

--- WARNINGS ---
{warnings}
"""
)
