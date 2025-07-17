#!/usr/bin/env bash
set -euo pipefail

# ensure Postgres bin dir is on PATH
export PATH="/usr/lib/postgresql/$(ls /usr/lib/postgresql)/bin:$PATH"

# env vars come from docker-compose env_file
: "${KEYCLOAK_DB_NAME:?}"
: "${KEYCLOAK_DB_USER:?}"
: "${KEYCLOAK_DB_PASSWORD:?}"
: "${KEYCLOAK_DB_PORT:?}"
: "${KEYCLOAK_ADMIN_USER:?}"
: "${KEYCLOAK_ADMIN_PASSWORD:?}"

PGDATA=/var/lib/postgresql/data

chown -R postgres:postgres "${PGDATA}"

# 1) Initialize Postgres if empty
if [ ! -s "${PGDATA}/PG_VERSION" ]; then
  echo ">>> Initializing Postgres DB…"
  su postgres -c "initdb -D ${PGDATA}"
  # start Postgres to create user/db
  su postgres -c "pg_ctl -D ${PGDATA} -o \"-c listen_addresses='localhost'\" -w start"

  cat <<EOF | su postgres -c "psql -v ON_ERROR_STOP=1 --username=postgres"
CREATE USER "${KEYCLOAK_DB_USER}" WITH PASSWORD '${KEYCLOAK_DB_PASSWORD}';
CREATE DATABASE "${KEYCLOAK_DB_NAME}" OWNER "${KEYCLOAK_DB_USER}";
EOF


  su postgres -c "pg_ctl -D ${PGDATA} -m fast -w stop"
  echo ">>> Postgres init complete."
fi

# 2) Launch Postgres in background
echo ">>> Starting Postgres…"
su postgres -c "pg_ctl -D ${PGDATA} -o \"-c listen_addresses='localhost'\" -w start"

# wait until it's accepting connections
until pg_isready -h localhost -p "${KEYCLOAK_DB_PORT}"; do
  echo "Waiting on Postgres…"
  sleep 1
done

# 3) Export Keycloak DB URL
export KC_DB=postgres
export KC_DB_URL_HOST=localhost
export KC_DB_URL_PORT="${KEYCLOAK_DB_PORT}"
export KC_DB_USERNAME="${KEYCLOAK_DB_USER}"
export KC_DB_PASSWORD="${KEYCLOAK_DB_PASSWORD}"
export KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN_USER}"
export KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD}"

# 4) Start Keycloak in dev mode (binds 0.0.0.0)
echo ">>> Starting Keycloak…"
exec /opt/keycloak/bin/kc.sh start-dev

