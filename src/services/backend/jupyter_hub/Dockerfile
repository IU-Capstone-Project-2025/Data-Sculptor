FROM jupyterhub/jupyterhub:latest

RUN useradd -m developer

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt
