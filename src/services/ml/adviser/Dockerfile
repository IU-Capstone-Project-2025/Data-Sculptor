FROM python:3.11-slim

WORKDIR /app

# install deps for this micro-service
COPY adviser/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# copy shared utilities
COPY shared_ml/shared_ml /app/shared_ml

# copy the service source code
COPY adviser /app

# ensure shared is on PYTHONPATH (optional when /app is already in sys.path)
ENV PYTHONPATH="/app:${PYTHONPATH}"

# set working dir to service package
WORKDIR /app/adviser

CMD ["python", "api.py"]

