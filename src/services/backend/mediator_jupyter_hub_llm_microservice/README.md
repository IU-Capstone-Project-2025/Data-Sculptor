# Features

Basic FastAPI service:
> /mdAnswer - post query, get string - return hardcoded md file

# Set-up (Debian-based Linux)

	cd backend
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -m requirements.txt

# Run server locally

	uvicorn src.main::app
