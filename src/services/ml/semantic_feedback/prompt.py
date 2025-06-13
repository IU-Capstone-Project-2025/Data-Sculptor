"""Module for storing and formatting the LLM prompt.

This module contains the prompt template used to generate feedback
for Jupyter notebooks.

Public API:
    - FEEDBACK_PROMPT_TEMPLATE: The LangChain prompt template.
"""

from langchain_core.prompts import PromptTemplate

FEEDBACK_PROMPT = PromptTemplate.from_template("""
You are an expert code reviewer.
You are tasked with providing feedback on the code from a Jupyter Notebook.
The user has submitted a notebook, and your job is to provide feedback on the code cells.

Please provide a high-level summary of the notebook's purpose, followed by
specific, constructive feedback on the code. Focus on code quality, logic,
potential bugs, and areas for improvement. Be clear and concise.

Here is the content of the code cells from the notebook, in order:

{code_cells}
""")
