#!/bin/sh

echo "export const API_ENDPOINT = '${LLM_VALIDATOR_URL}';" > /extensions/buttons/src/config.ts

exec "$@"