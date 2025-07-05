"""Centralised prompt templates for the semantic-feedback service.

This module houses *all* LangChain `PromptTemplate` instances used across the
service so that they are defined in one place and can be imported elsewhere.
"""

from langchain_core.prompts import PromptTemplate

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
- <= 120 characters.
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

COMBINED_FEEDBACK_PROMPT = PromptTemplate.from_template(
    """
You are an **ML-oriented static-analysis assistant**. Your task is to analyse USER CODE for the current SECTION in the context of the overall PROFILE and a canonical REFERENCE CODE for this section.

──────────────────────── CONTEXT INPUTS ──────────────────────────────
1. PROFILE DESCRIPTION – multi-step overview of the whole problem.  
2. SECTION DESCRIPTION – **single** step under review (assume earlier steps work).  
3. REFERENCE CODE – canonical implementation for this step.  
4. USER CODE – learner code annotated as "<n> | <code>".

──────────────────────── DEFINITIONS ─────────────────────────────────
Localised issue  – Confined to **one function/method body** or a very small, contiguous block inside it (typically ≤ 5 lines).  
Conceptual issue – Relates to **global design or ML methodology** and therefore spans multiple units (functions, classes, modules, or the entire pipeline). Typical conceptual categories:
  • Algorithm selection / complexity  
  • End-to-end data-processing strategy (splitting, scaling, augmentation)  
  • Evaluation-metric misuse or leakage  
  • Security & privacy risks (model or data)  
  • Performance, scalability or maintainability concerns  
Such issues CANNOT be pinned to a single narrow span; they require coordinated changes across the codebase.

──────────────────────── GUIDELINES & CONSTRAINTS ────────────────────
1. **No duplication** – conceptual list MUST NOT reiterate any warning.
   Before you emit the final JSON, compare each conceptual sentence with the warnings: if they share *any* core noun phrase (e.g. "test data", "duplicate", "eval"), discard the conceptual sentence.
2. **No line numbers** or code pointers inside conceptual messages.
3. Use **established ML terminology**; avoid verbose prose.
4. Express every message in terms of **consequences** (effects, risks); never prescribe concrete fixes.
5. **Ignore syntax errors, lint, or formatting errors**; focus exclusively on semantic / logical / ML-specific issues.
6. Do **not** mention identifiers from PROFILE or REFERENCE code; user-code names are allowed.
7. Raise an issue **only if behaviour violates SECTION requirements or introduces risk**; alternative but correct approaches are valid.
8. REFERENCE CODE is canonical – if a flaw also exists there, assume intentional and skip.
9. If no items for a bucket, return an empty array for that field.

──────────────────────── STRICT ISSUE CLASSIFICATION ────────────────
For every detected problem:  
• If it can be fully demonstrated **within one function/method or its immediate block** (usually ≤ 5 contiguous lines) → add ONE object to `warnings`.  
• If understanding or fixing it requires touching **whole functions/classes or cross-cutting logic** → add ONE sentence to `conceptual`.  
Never place the same root issue in both buckets.

──────────────────────── PROHIBITED / ACCEPTED EXAMPLES ─────────────
Bad ❌  "Load test.csv instead of slicing train data (line 8) to avoid leakage"  
Good ✅ "Test set derived from training data causes data leakage and invalid evaluation"

Bad ❌  "You forgot to impute missing values"  
Good ✅ "NaN values can enter training set, degrading model performance"

──────────────────────── INPUT BLOCKS ───────────────────────────────
--- PROFILE DESCRIPTION ---
{profile_desc}

--- SECTION DESCRIPTION ---
{section_desc}

--- REFERENCE CODE (ethalon) ---
{reference_code}

--- USER CODE (numbered) ---
{user_code}
"""
)
