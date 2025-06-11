Basic FastAPI service:

> POST /getMdAnswer - takes .ipynb file, returns .md file  

# Set-up (Debian-based Linux)

	cd backend
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -m requirements.txt

# Run server locally
```bash
uvicorn service::app
```

# `.env` Example

Create a `.env` file in the service's root directory with the following variables.

```bash
# Required: Feedback Service Configuration
feedback_service_url="<your_feedback_service_url>"
```
