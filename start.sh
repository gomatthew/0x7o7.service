#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$BASE_DIR"

/root/.local/bin/uv run gunicorn -c deploy/gunicorn_conf.py main:app
