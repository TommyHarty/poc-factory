#!/usr/bin/env bash
# Start the POC Factory application

set -e

echo "Starting POC Factory..."

# Load .env if present
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

LOG_LEVEL_LOWER=$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')

exec uvicorn app.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --log-level "${LOG_LEVEL_LOWER}"
