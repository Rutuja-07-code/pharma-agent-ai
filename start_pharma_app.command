#!/bin/zsh
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/tmp/pharma_agent_ai.log"
APP_PORT="${APP_PORT:-8003}"
APP_URL="http://127.0.0.1:${APP_PORT}"

# Optional tracing config (set real values in your shell/profile).
export LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY:-}"
export LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY:-}"
export LANGFUSE_BASE_URL="${LANGFUSE_BASE_URL:-https://cloud.langfuse.com}"
export LANGFUSE_HOST="${LANGFUSE_HOST:-https://cloud.langfuse.com}"

# Autonomous reminder defaults.
export WHATSAPP_REMINDER_ENABLED="${WHATSAPP_REMINDER_ENABLED:-true}"
export REMINDER_SCHEDULE_HOUR="${REMINDER_SCHEDULE_HOUR:-9}"
export REMINDER_SCHEDULE_MINUTE="${REMINDER_SCHEDULE_MINUTE:-0}"
export REMINDER_RUN_ON_STARTUP="${REMINDER_RUN_ON_STARTUP:-false}"

if lsof -iTCP:${APP_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Pharma app is already running on port ${APP_PORT}."
else
  cd "$REPO_DIR/backend/app"

  if [ -f "$REPO_DIR/.venv/bin/activate" ]; then
    source "$REPO_DIR/.venv/bin/activate"
  fi

  nohup uvicorn main:app --reload --host 127.0.0.1 --port "${APP_PORT}" > "$LOG_FILE" 2>&1 &
  sleep 2
  echo "Started backend. Logs: $LOG_FILE"
fi

open "$APP_URL"
echo "Opened $APP_URL"
