FROM jupyterhub/jupyterhub:latest

RUN useradd -m developer

# Remove old built-in npm
RUN apt-get update && apt-get install -y curl build-essential
RUN apt-get purge -y nodejs npm libnode* && \
    rm -rf /usr/lib/node_modules /etc/apt/sources.list.d/nodesource.list && \
    apt-get autoremove -y

# Install new npm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# If written in vice versa, nothing works lol
RUN node -v && npm -v
RUN npm install -g npm@latest

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY extensions/ /extensions/

ARG LLM_VALIDATOR_URL
RUN echo "export const API_ENDPOINT = '${LLM_VALIDATOR_URL}';" > /extensions/buttons/src/config.ts

# Load extension to Jupyter
RUN cd /extensions/buttons && \
    npm install && \
    npm run build && \
    jupyter labextension install .

COPY . .

WORKDIR /srv/jupyterhub

RUN mkdir -p /etc/jupyter/jupyter_server_config.d
