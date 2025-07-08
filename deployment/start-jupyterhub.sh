#!/usr/bin/env bash
set -eo pipefail

# -----------------------------------------------------------------------------
# start-jupyterhub.sh
# Usage: ./start-jupyterhub.sh <deployment-env-file>
#
#   e.g. ./start-jupyterhub.sh dev.env
#
#   - Sources deployment/<arg> and resources/config/jupyterhub/.env
#   - Chowns /home/developer
#   - Loops to auto-restart JupyterHub on crash
#   - Logs to logs/jupyterhub.log
# -----------------------------------------------------------------------------

# locate script dir
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# check args
if [[ $# -ne 1 ]]; then
	echo "Usage: $0 <deployment-env-filename>    (e.g. dev.env)" >&2
  exit 1
fi

ENV_FILENAME="$1"
ENV_DEPLOY="$SCRIPT_DIR/$ENV_FILENAME"
ENV_JH="$(dirname "$SCRIPT_DIR")/resources/config/jupyterhub/.env"
LAB_EXTENSIONS="$(dirname "$SCRIPT_DIR")/src/services/backend/jupyter_hub/extensions"

for F in "$ENV_DEPLOY" "$ENV_JH"; do
  if [[ ! -f "$F" ]]; then
    echo "ERROR: env file not found: $F" >&2
    exit 2
  fi
done

# export all variables
set -o allexport
source "$ENV_DEPLOY"
source "$ENV_JH"
set +o allexport

# export urls
export ADVISER_API_URL="http://${HOST_IP}:${ADVISER_PORT_EXTERNAL}/api/v1/chat"
export LLM_VALIDATOR_URL="http://${HOST_IP}:${MEDIATOR_PORT_EXTERNAL}"
export URL_STATIC_ANALYZER="http://${HOST_IP}:${ANALYZER_PORT_EXTERNAL}"
export URL_LSP_SERVER="http://${HOST_IP}:${LSP_PORT_EXTERNAL}"

#installing extensions
cd "$LAB_EXTENSIONS"
echo "export const API_ENDPOINT = '${FEEDBACK_PORT_EXTERNAL}';" > ./buttons/src/config.ts
cd ./buttons
npm install && npm run build && jupyter labextension install --minimize=False .
jupyter lab build
#TODO: сделать установку lsp сервера

# prepare logging
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/jupyterhub.log"

# ensure permissions
#chown -R developer:developer /home/developer/notebooks

echo "[$(date)] Launching JupyterHub on 0.0.0.0:${JUPYTER_PORT_EXTERNAL}"
while true; do
  jupyterhub \
    --config="$(dirname "$SCRIPT_DIR")/resources/config/jupyterhub/jupyterhub_config.py" \
    --ip=0.0.0.0 \
    --port="${JUPYTER_PORT_EXTERNAL}" \
    2>&1 | tee -a "$LOG_FILE"
  EXIT_CODE=${PIPESTATUS[0]}
  echo "[$(date)] JupyterHub exited (code $EXIT_CODE). Restarting in 5s..." | tee -a "$LOG_FILE"
  sleep 5
done
