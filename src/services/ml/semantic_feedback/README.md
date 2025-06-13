## ML Feedback Service

This directory contains a FastAPI microservice designed to provide AI-powered feedback on Jupyter Notebooks.

## `.env` Example

Create a `.env` file in the service's root directory with the following variables.

```bash
# Required: Qwen LLM Configuration
llm_base_url="<your_qwen_llm_base_url>"
llm_api_key="<your_qwen_llm_api_key>"
llm_model="<your_qwen_llm_model_name>"

# Optional: Service Configuration
feedback_service_host="127.0.0.1"
feedback_service_port=8000
feedback_service_n_workers=1
open_api_folder="./docs/openapi"
```