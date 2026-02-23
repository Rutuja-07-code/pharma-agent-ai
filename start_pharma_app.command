#!/bin/zsh
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/tmp/pharma_agent_ai.log"
APP_URL="http://127.0.0.1:8000"

if lsof -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Pharma app is already running on port 8000."
else
  cd "$REPO_DIR/backend/app"

  if [ -f "$REPO_DIR/.venv/bin/activate" ]; then
    source "$REPO_DIR/.venv/bin/activate"
  fi

  nohup uvicorn main:app --reload --host 127.0.0.1 --port 8000 > "$LOG_FILE" 2>&1 &
  sleep 2
  echo "Started backend. Logs: $LOG_FILE"
fi

open "$APP_URL"
echo "Opened $APP_URL"
