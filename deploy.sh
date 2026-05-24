#!/bin/bash
set -e

LOCAL_PATH="/Users/0x7o7/workspace/0x7o7.service.v1/"
REMOTE_PATH="/root/project/0x7o7.service"
SERVER="root@server"

echo "🚀 Sync backend project..."

rsync -avz --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.DS_Store' \
  --exclude 'docs' \
  --exclude 'log' \
  "$LOCAL_PATH" "$SERVER:$REMOTE_PATH/"

echo "📦 Install dependencies & restart service..."

ssh "$SERVER" "
set -e
cd $REMOTE_PATH
pwd
/root/.local/bin/uv sync
/bin/bash ./shutdown.sh || true
/bin/bash ./start.sh
"

echo "✅ Backend deploy success!"