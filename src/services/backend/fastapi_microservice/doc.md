# Features

Basic FastAPI service that has two pages:
> /upload_file_page - page to select file and upload it to the next page

> /answer - uploading file redirects user to this page, hardcoded answer is returned

# Set-up (Debian-based Linux)

	cd backend
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -m requirements.txt

# Run server locally

	uvicorn src.main::app
