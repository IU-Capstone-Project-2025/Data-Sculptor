FROM python:3.11-slim

WORKDIR /app

# install deps for this micro-service
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# copy the service source code
COPY . /app/progress_tracker_microservice

# ensure shared is on PYTHONPATH
ENV PYTHONPATH="/app:${PYTHONPATH}"

# set working dir to service package
WORKDIR /app/progress_tracker_microservice

CMD ["python", "api.py"] 