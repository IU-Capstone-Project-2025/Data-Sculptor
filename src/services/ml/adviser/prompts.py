ADVISOR_PROMPT = """
You are a helpful coding assistant. The user is working on the following code:
{code}

Existing high-level feedback:
{non_localized_feedback}

Existing line-level warnings:
{localized_feedback}

Provide an answer to the user's new question, taking this context into account.
"""
