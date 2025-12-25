#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$BASE_DIR/log/gunicorn.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "Gunicorn pid file not found: $PID_FILE"
  exit 1
fi

PID=$(cat "$PID_FILE")
echo "Stopping Gunicorn (PID: $PID)..."

kill -TERM "$PID" 2>/dev/null || true
sleep 2

if ps -p "$PID" > /dev/null 2>&1; then
  echo "Force killing Gunicorn..."
  kill -9 "$PID" || true
else
  echo "Gunicorn stopped."
fi

rm -f "$PID_FILE"
