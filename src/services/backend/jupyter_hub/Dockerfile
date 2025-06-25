FROM jupyterhub/jupyterhub:latest

RUN useradd -m developer
RUN chown -R developer:developer /home/developer && chmod u+rwx /home/developer

RUN apt-get update && apt-get install -y curl build-essential && apt-get purge -y nodejs npm libnode* && rm -rf /usr/lib/node_modules /etc/apt/sources.list.d/nodesource.list && apt-get autoremove -y
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs && node -v && npm -v && npm install -g npm@latest

COPY src/common/llm_custom_providers /llm_custom_providers
RUN pip install /llm_custom_providers

COPY src/services/backend/jupyter_hub/ /srv/jupyterhub_build/
WORKDIR /srv/jupyterhub_build

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir "jupyterlab>=4.2" "jupyter-ai[all]" && \
    jupyter server extension enable jupyter_ai --sys-prefix

COPY src/services/backend/jupyter_hub/extensions/ /extensions/
WORKDIR /extensions/validate-button
RUN npm install && npm run build && jupyter labextension install .

WORKDIR /srv/jupyterhub
RUN mkdir -p /etc/jupyter/jupyter_server_config.d
