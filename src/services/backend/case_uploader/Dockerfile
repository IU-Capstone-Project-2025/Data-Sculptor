FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Docker and repo2docker
RUN apt-get update && apt-get install -y \
    docker.io \
    curl \
    && rm -rf /var/lib/apt/lists/*

# install deps for this micro-service
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install jupyter-repo2docker

# copy the service source code
COPY . /app/case_uploader

# ensure shared is on PYTHONPATH
ENV PYTHONPATH="/app:${PYTHONPATH}"

# set working dir to service package
WORKDIR /app/case_uploader

# Run debug script first, then start the service
CMD ["sh", "-c", "python api.py"] 