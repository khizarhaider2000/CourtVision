#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"

stop_pid_file() {
  local label="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    echo "$label not running."
    return
  fi

  local pid
  pid="$(cat "$pid_file")"

  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid"
    echo "$label stopped (pid $pid)."
  else
    echo "$label already stopped."
  fi

  rm -f "$pid_file"
}

stop_pid_file "Backend" "$RUN_DIR/backend.pid"
stop_pid_file "Frontend" "$RUN_DIR/frontend.pid"
