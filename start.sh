#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$BASE_DIR"

gunicorn -c deploy/gunicorn_conf.py main:app
