FROM jupyterhub/jupyterhub:latest

RUN useradd -m developer

COPY . .


RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /etc/jupyter/jupyter_server_config.d
