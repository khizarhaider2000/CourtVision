#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"

mkdir -p "$RUN_DIR"

is_running() {
  local pid="$1"
  kill -0 "$pid" >/dev/null 2>&1
}

cleanup_stale_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" ]] && is_running "$pid"; then
      return 0
    fi
    rm -f "$pid_file"
  fi
  return 1
}

start_backend() {
  if cleanup_stale_pid "$BACKEND_PID_FILE"; then
    echo "Backend already running on http://127.0.0.1:8000 (pid $(cat "$BACKEND_PID_FILE"))."
    return
  fi

  nohup bash -lc "
    cd \"$ROOT_DIR\"
    source .venv/bin/activate
    exec uvicorn api.main:app --host 127.0.0.1 --port 8000
  " >"$BACKEND_LOG" 2>&1 &

  echo $! >"$BACKEND_PID_FILE"
  echo "Backend started: http://127.0.0.1:8000"
}

start_frontend() {
  if cleanup_stale_pid "$FRONTEND_PID_FILE"; then
    echo "Frontend already running on http://127.0.0.1:5173 (pid $(cat "$FRONTEND_PID_FILE"))."
    return
  fi

  nohup bash -lc "
    cd \"$ROOT_DIR\"
    exec npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
  " >"$FRONTEND_LOG" 2>&1 &

  echo $! >"$FRONTEND_PID_FILE"
  echo "Frontend started: http://127.0.0.1:5173"
}

start_backend
start_frontend

echo
echo "Logs:"
echo "  backend  $BACKEND_LOG"
echo "  frontend $FRONTEND_LOG"
echo
echo "Open:"
echo "  http://127.0.0.1:5173"
echo "  http://127.0.0.1:8000/docs"
