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

The system uses the following configuration (all optional except `EVALUATOR_LLM_API_KEY`):

#### Evaluator LLM Configuration (OpenRouter)
| Variable | Default | Description |
|----------|---------|-------------|
| `EVALUATOR_LLM_API_KEY` | **Required** | OpenAI API key for OpenRouter evaluation |
| `EVALUATOR_LLM_BASE_URL` | `https://openrouter.ai/api/v1` | Base URL for OpenAI API (OpenRouter endpoint) |
| `EVALUATOR_LLM_MODEL` | `deepseek/deepseek-chat-v3-0324:free` | Model name to use for evaluation |

#### Local LLM Configuration (Qwen)
| Variable | Default | Description |
|----------|---------|-------------|
| `LOCAL_LLM_BASE_URL` | `http://10.100.30.239:9362/v1` | Base URL for local LLM service |
| `LOCAL_LLM_API_KEY` | `vllml` | API key for local LLM authentication |
| `LOCAL_LLM_MODEL` | `Qwen/Qwen3-30B-A3B` | Model name for local LLM |
| `LOCAL_ENABLE_THINKING` | `True` | Enable thinking mode for local LLM (boolean) |

#### General Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_OUTPUT_DIR` | `results` | Default output directory for results |
| `MAX_RETRIES` | `3` | Maximum number of API request retries (≥0) |
| `RETRY_DELAY` | `1.0` | Delay between retries in seconds (≥0.0) |



### Startup

1. Put testcases in `./test_cases` in the following format:
```
test_cases/
├── case_1/
│   ├── profile.ipynb
│   └── solution.ipynb
```

2. Run the evaluation
```bash
./evaluate.sh ./test_cases ./results
```