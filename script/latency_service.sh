#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

COMMAND="${1:-}"
HOST="${LATENCY_SERVICE_HOST:-127.0.0.1}"
PORT="${LATENCY_SERVICE_PORT:-8099}"
SERVICE_URL="${LATENCY_SERVICE_URL:-http://${HOST}:${PORT}}"
PID_FILE="${LATENCY_SERVICE_PID_FILE:-${REPO_ROOT}/.latency_service.pid}"
LOG_FILE="${LATENCY_SERVICE_LOG:-${REPO_ROOT}/.latency_service.log}"
STARTUP_JSON="${LATENCY_SERVICE_STARTUP_JSON:-${REPO_ROOT}/.latency_service_startup.json}"
START_TIMEOUT="${LATENCY_SERVICE_START_TIMEOUT:-300}"

now_epoch() {
  python3 - <<'PY'
import time
print(time.time())
PY
}

write_startup_json() {
  python3 - "$STARTUP_JSON" "$SERVICE_URL" "$LOG_FILE" "$1" "$2" "$3" <<'PY'
import json
import sys
from pathlib import Path

output_path = Path(sys.argv[1])
startup_ready_seconds = None
if len(sys.argv) > 6 and sys.argv[6] not in {"", "null", "None"}:
    startup_ready_seconds = float(sys.argv[6])
payload = {
    "service_url": sys.argv[2],
    "log_file": sys.argv[3],
    "pid": int(sys.argv[4]),
    "startup_wall_seconds": float(sys.argv[5]),
    "startup_ready_seconds": startup_ready_seconds,
}
output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

ensure_parent_dirs() {
  mkdir -p "$(dirname "$PID_FILE")"
  mkdir -p "$(dirname "$LOG_FILE")"
  mkdir -p "$(dirname "$STARTUP_JSON")"
}

service_pid() {
  if [[ -f "$PID_FILE" ]]; then
    cat "$PID_FILE"
  fi
}

listener_pid() {
  lsof -tiTCP:"$PORT" -sTCP:LISTEN -n -P 2>/dev/null | head -n 1
}

is_running() {
  local pid
  pid="$(service_pid || true)"
  if [[ -z "${pid}" ]]; then
    return 1
  fi
  kill -0 "$pid" 2>/dev/null
}

start_service() {
  ensure_parent_dirs
  if is_running; then
    echo "Latency service already running at ${SERVICE_URL}" >&2
    return 0
  fi

  : > "$LOG_FILE"
  local started_at launcher_pid
  started_at="$(now_epoch)"
  launcher_pid="$(
    cd "$REPO_ROOT"
    nohup uv run python -m ragent.api.benchmark_service --host "$HOST" --port "$PORT" >>"$LOG_FILE" 2>&1 &
    echo $!
  )"

  local deadline=$((SECONDS + START_TIMEOUT))
  local health_json=""
  until health_json="$(curl --noproxy '*' -fsS "${SERVICE_URL}/health" 2>/dev/null)"; do
    if [[ -n "$launcher_pid" ]] && ! kill -0 "$launcher_pid" 2>/dev/null; then
      if [[ -z "$(listener_pid)" ]]; then
        echo "Latency service exited before becoming ready. See ${LOG_FILE}" >&2
        return 1
      fi
    fi
    if (( SECONDS >= deadline )); then
      if [[ -n "$launcher_pid" ]]; then
        kill "$launcher_pid" 2>/dev/null || true
      fi
      echo "Timed out waiting for latency service health endpoint. See ${LOG_FILE}" >&2
      return 1
    fi
    sleep 1
  done

  local pid
  pid="$(listener_pid || true)"
  if [[ -z "$pid" ]]; then
    pid="$launcher_pid"
  fi
  printf '%s\n' "$pid" > "$PID_FILE"

  local finished_at startup_seconds
  finished_at="$(now_epoch)"
  startup_seconds="$(
    python3 - "$started_at" "$finished_at" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
  )"
  local startup_ready_seconds
  startup_ready_seconds="$(
    python3 - "$health_json" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
value = payload.get("startup_ready_seconds")
print("" if value is None else value)
PY
  )"
  write_startup_json "$pid" "$startup_seconds" "$startup_ready_seconds"
}

stop_service() {
  if ! [[ -f "$PID_FILE" ]]; then
    return 0
  fi

  local pid
  pid="$(service_pid || true)"
  rm -f "$PID_FILE"
  if [[ -z "${pid}" ]]; then
    return 0
  fi

  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 30); do
      if ! kill -0 "$pid" 2>/dev/null; then
        return 0
      fi
      sleep 1
    done
    kill -9 "$pid" 2>/dev/null || true
  fi
}

case "$COMMAND" in
  start)
    start_service
    ;;
  stop)
    stop_service
    ;;
  *)
    echo "Usage: $0 {start|stop}" >&2
    exit 1
    ;;
esac
