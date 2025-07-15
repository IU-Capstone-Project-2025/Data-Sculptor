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
    apt-get install -y nodejs netcat && \
    node -v && npm -v && \
    npm install -g npm@latest

RUN apt-get update && apt-get install -y \
    curl ca-certificates gnupg lsb-release

# Add Docker repo (for Ubuntu!)
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list

RUN apt-get update && apt-get install -y docker-ce-cli

# custom providers
COPY src/common/llm_custom_providers /llm_custom_providers
RUN pip install /llm_custom_providers

# jupyterhub service source
COPY src/services/backend/jupyter_hub/ /srv/jupyterhub_build/
WORKDIR /srv/jupyterhub_build

# multi-user set up
RUN pip install jupyterhub dockerspawner oauthenticator

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir "jupyterlab>=4.2" "jupyter-ai[all]" "oauthenticator" "dockerspawner" && \
    jupyter server extension enable jupyter_ai --sys-prefix

# jupyterlab extensions
COPY src/services/backend/jupyter_hub/extensions/ /extensions/

ARG FEEDBACK_SERVICE_URL
RUN echo "export const API_ENDPOINT = '${FEEDBACK_SERVICE_URL}';" > /extensions/buttons/src/config.ts

RUN cd /extensions/buttons && npm install && npm run build && jupyter labextension install --minimize=False .

# # real time analysisconfiguration #WARNING: Now it is Fast api service

# runtime configuration
WORKDIR /srv/jupyterhub

RUN mkdir -p /etc/jupyter/jupyter_server_config.d
RUN mkdir -p /lsp
COPY src/services/backend/lsp_server/lsp.py /lsp/lsp.py
# RUN mkdir -p /logs
# WORKDIR /lsp
# RUN /lsp/custom_linters/setup.sh


#WARNING: THIS 2 lines should always be the last!!
WORKDIR /srv/jupyterhub
CMD ["jupyterhub"]
