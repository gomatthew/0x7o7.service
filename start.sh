#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$BASE_DIR"

API_ENV_FILE="${API_ENV_FILE:-/etc/0x7o7/api.env}"
if [ -f "$API_ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$API_ENV_FILE"
  set +a
fi

# `uv run` can sanitize the inherited environment when it launches an
# already-synced project.  This service receives production secrets through
# API_ENV_FILE, so execute the pinned virtualenv binary directly and preserve
# the exported environment for the worker process.
exec "$BASE_DIR/.venv/bin/gunicorn" -c deploy/gunicorn_conf.py main:app
