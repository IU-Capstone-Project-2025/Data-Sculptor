# Features

Basic FastAPI service:

> POST /getMdAnswer - takes .ipynb file, returns .md file  

# Set-up (Debian-based Linux)

	cd backend
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -m requirements.txt

# Run server locally

	uvicorn service::app
