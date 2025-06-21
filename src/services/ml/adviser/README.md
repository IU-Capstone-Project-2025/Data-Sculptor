## Adviser Chat Service

This directory houses a FastAPI micro-service that transforms user questions plus
notebook context into assistant replies via a Qwen-based LLM.

## Usage
To run the service outside Docker:
1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Install local packages (for `shared_ml` imports):
```bash
cd ../
pip install -e ./shared_ml
```

## `.env` Example
Create a `.env` file in the service root containing:

```bash
# Required: Qwen LLM configuration
llm_base_url="<your_qwen_llm_base_url>"
llm_api_key="<your_qwen_llm_api_key>"
llm_model="<your_qwen_llm_model_name>"
tokenizer_model="<huggingface_tokenizer_name>"

# Optional: Service configuration
chat_service_host="127.0.0.1"
chat_service_port=8000
chat_service_n_workers=1

# Back-end stores
redis_url="redis://localhost:6379/0"
postgres_dsn="postgresql://app:app@localhost:5432/chatdb"
```
