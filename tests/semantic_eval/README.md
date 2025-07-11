# Semantic Evaluation System

A comprehensive system for evaluating semantic feedback on ML tasks using OpenRouter, designed to assess the quality of solutions and profiles in Jupyter notebooks.

## Overview

The semantic evaluation system analyzes pairs of Jupyter notebooks:
- **Profile notebooks**: Contain task descriptions and requirements
- **Solution notebooks**: Contain solutions and dynamic evaluation criteria

## Prerequisites

- Python 3.11+
- OpenAI API key (via OpenRouter)
- Access to the semantic feedback service

## Usage

### Environment Variables

The system uses the following configuration (all optional except `OPENAI_API_KEY`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | **Required** | Your OpenAI API key for OpenRouter |
| `OPENAI_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI API base URL |
| `MODEL_NAME` | `deepseek/deepseek-chat-v3-0324:free` | Model for evaluation |
| `TEMPERATURE` | `0.1` | Model temperature (0.0-2.0) |
| `MAX_TOKENS` | `1000` | Maximum tokens per response |
| `DEFAULT_OUTPUT_DIR` | `results` | Default output directory |
| `SEMANTIC_FEEDBACK_BASE_URL` | `http://localhost:8000` | Semantic feedback service URL |
| `MAX_RETRIES` | `3` | Maximum API request retries |
| `RETRY_DELAY` | `1.0` | Delay between retries (seconds) |



### Startup

1. Install dependencies
```bash
pip install -r requirements.txt
```

2. Run the evaluation
```bash
python evaluate.py --input_dir ./test_cases --output_dir ./results
```

### Command Line Arguments

- `--input_dir`: Path to folder containing case directories with profile.ipynb and solution.ipynb
- `--output_dir`: Directory to store JSON results (default: "results")


## Output

The system generates JSON files with detailed metrics:

```json
{
  "case_id": "test_case_1",
  "accuracy": 0.85,
  "completeness": 0.90,
  "clarity": 0.80,
  "overall_quality": 0.85,
  "detailed_feedback": "...",
  "timestamp": "2024-01-01T12:00:00Z"
}
```