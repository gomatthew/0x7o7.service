#!/usr/bin/env bash
set -euo pipefail

LOCAL_PATH="$(cd "$(dirname "$0")" && pwd)"
REMOTE_PATH="/root/project/0x7o7.service"
SERVER="root@server2"
RELEASE_ID="$(date +%Y%m%d-%H%M%S)"
BACKUP_PATH="/root/project/backend-backups/$RELEASE_ID"

ssh "$SERVER" bash -s -- "$REMOTE_PATH" "$BACKUP_PATH" <<'REMOTE'
set -euo pipefail
project_path="$1"
backup_path="$2"
mkdir -p "$backup_path"
cd "$project_path"
tar --exclude='__pycache__' -czf "$backup_path/code.tgz" src deploy scripts tests main.py requirements.txt pyproject.toml uv.lock start.sh shutdown.sh deploy.sh
cp /etc/systemd/system/0x7o7-api.service "$backup_path/previous-unit.service"
REMOTE

rsync -az --delete --exclude '__pycache__' --exclude '*.pyc' --exclude 'local_settings.py' "$LOCAL_PATH/src/" "$SERVER:$REMOTE_PATH/src/"
for directory in deploy scripts tests; do
  rsync -az --exclude '__pycache__' --exclude '*.pyc' "$LOCAL_PATH/$directory/" "$SERVER:$REMOTE_PATH/$directory/"
done
rsync -az "$LOCAL_PATH/main.py" "$LOCAL_PATH/requirements.txt" "$LOCAL_PATH/pyproject.toml" "$LOCAL_PATH/uv.lock" "$LOCAL_PATH/start.sh" "$LOCAL_PATH/shutdown.sh" "$LOCAL_PATH/deploy.sh" "$SERVER:$REMOTE_PATH/"

ssh "$SERVER" bash -s -- "$REMOTE_PATH" "$BACKUP_PATH" <<'REMOTE'
set -euo pipefail
project_path="$1"
backup_path="$2"
cd "$project_path"
restarted=0
rollback() {
  status="$?"
  trap - ERR
  echo "Deployment failed; restoring code from $backup_path"
  tar -xzf "$backup_path/code.tgz" -C "$project_path"
  /root/.local/bin/uv sync --frozen
  if [ "$restarted" -eq 1 ]; then
    systemctl restart 0x7o7-api.service
  fi
  exit "$status"
}
trap rollback ERR
/root/.local/bin/uv sync --frozen
set -a
. /etc/0x7o7/api.env
set +a
.venv/bin/python -c 'from src.server import create_app; from src.server.ai.document_workflow_service import document_workflow; assert create_app(); assert document_workflow'
pidfile="$(.venv/bin/python -c 'from src.configs import get_setting; import os; print(os.path.join(get_setting().LOG_PATH, "gunicorn.pid"))')"
install -m 644 deploy/0x7o7-api.service /etc/systemd/system/0x7o7-api.service
systemctl daemon-reload
if ! systemctl is-active --quiet 0x7o7-api.service && [ -f "$pidfile" ]; then
  old_pid="$(cat "$pidfile")"
  if kill -0 "$old_pid" 2>/dev/null; then
    test "$(readlink -f "/proc/$old_pid/cwd")" = "$project_path"
    test "$(cat "/proc/$old_pid/comm")" = gunicorn
    kill -TERM "$old_pid"
    for attempt in $(seq 1 30); do
      if ! kill -0 "$old_pid" 2>/dev/null || [ "$(ps -p "$old_pid" -o stat= | cut -c1)" = Z ]; then break; fi
      sleep 1
    done
  fi
fi
restarted=1
systemctl enable 0x7o7-api.service
systemctl restart 0x7o7-api.service
for attempt in $(seq 1 30); do
  if .venv/bin/python -c 'import json, os, urllib.request; url="http://"+os.environ.get("APP_HOST", "127.0.0.1")+":"+os.environ.get("APP_PORT", "8000")+"/health/ready"; result=json.load(urllib.request.urlopen(url,timeout=3)); assert result["status"] == "ready"' 2>/dev/null; then
    systemctl is-active --quiet 0x7o7-api.service
    trap - ERR
    echo "Backend ready. Backup: $backup_path"
    exit 0
  fi
  sleep 1
 done
false
REMOTE
