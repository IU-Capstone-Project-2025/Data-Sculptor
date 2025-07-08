FROM python:3.11-slim

WORKDIR /app

# install deps for this micro-service
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# copy the service source code
COPY . /app/profile_uploader

# ensure shared is on PYTHONPATH
ENV PYTHONPATH="/app:${PYTHONPATH}"

# set working dir to service package
WORKDIR /app/profile_uploader

CMD ["python", "api.py"] 