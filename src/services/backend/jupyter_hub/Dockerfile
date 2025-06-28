FROM jupyterhub/jupyterhub:latest

# create non-root user
RUN useradd -m developer && \
    chown -R developer:developer /home/developer && \
    chmod u+rwx /home/developer

# install build deps and node
RUN apt-get update && \
    apt-get install -y curl build-essential && \
    apt-get purge -y nodejs npm libnode* && \
    rm -rf /usr/lib/node_modules /etc/apt/sources.list.d/nodesource.list && \
    apt-get autoremove -y && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    node -v && npm -v && \
    npm install -g npm@latest

# custom providers
COPY src/common/llm_custom_providers /llm_custom_providers
RUN pip install /llm_custom_providers

# jupyterhub service source
COPY src/services/backend/jupyter_hub/ /srv/jupyterhub_build/
WORKDIR /srv/jupyterhub_build

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir "jupyterlab>=4.2" "jupyter-ai[all]" && \
    jupyter server extension enable jupyter_ai --sys-prefix

# jupyterlab extensions
COPY src/services/backend/jupyter_hub/extensions/ /extensions/

ARG LLM_VALIDATOR_URL
RUN echo "export const API_ENDPOINT = '${LLM_VALIDATOR_URL}';" > /extensions/buttons/src/config.ts

RUN cd /extensions/buttons && npm install && npm run build && jupyter labextension install --minimize=False .

# runtime configuration
WORKDIR /srv/jupyterhub
RUN mkdir -p /etc/jupyter/jupyter_server_config.d

CMD ["jupyterhub"]
