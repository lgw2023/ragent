#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

PROJECT_DIR="${PROJECT_DIR:-example/demo_diet_kg_5}"
QUERY="${QUERY:-我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？}"
RUNS="${RUNS:-5}"
BENCHMARK_ROOT="${BENCHMARK_ROOT:-benchmark}"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
OUTPUT_DIR="${OUTPUT_DIR:-${BENCHMARK_ROOT}/latency_${TIMESTAMP}}"
ENV_FILE="${ENV_FILE:-${REPO_ROOT}/.env}"
RESPONSE_TYPE="${RESPONSE_TYPE:-Multiple Paragraphs}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-600}"
LATENCY_SERVICE_HOST="${LATENCY_SERVICE_HOST:-127.0.0.1}"
LATENCY_SERVICE_PORT="${LATENCY_SERVICE_PORT:-8099}"
LATENCY_SERVICE_URL="${LATENCY_SERVICE_URL:-http://${LATENCY_SERVICE_HOST}:${LATENCY_SERVICE_PORT}}"
MODES="${MODES:-graph hybrid}"
RERANK_OPTIONS="${RERANK_OPTIONS:-off on}"
PROJECT_PATH="$PROJECT_DIR"
if [[ "$PROJECT_PATH" != /* ]]; then
  PROJECT_PATH="${REPO_ROOT}/${PROJECT_PATH}"
fi

if [[ ! -d "$PROJECT_PATH" ]]; then
  echo "Project dir not found: $PROJECT_PATH" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo ".env not found: $ENV_FILE" >&2
  exit 1
fi

if ! [[ "$RUNS" =~ ^[1-9][0-9]*$ ]]; then
  echo "RUNS must be a positive integer, got: $RUNS" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(python3 - "$OUTPUT_DIR" <<'PY'
import os
import sys

print(os.path.abspath(sys.argv[1]))
PY
)"
LATENCY_SERVICE_PID_FILE="${OUTPUT_DIR}/service.pid"
LATENCY_SERVICE_LOG="${OUTPUT_DIR}/service.log"
LATENCY_SERVICE_STARTUP_JSON="${OUTPUT_DIR}/service_startup.json"

export LATENCY_SERVICE_HOST
export LATENCY_SERVICE_PORT
export LATENCY_SERVICE_URL
export LATENCY_SERVICE_PID_FILE
export LATENCY_SERVICE_LOG
export LATENCY_SERVICE_STARTUP_JSON

cleanup() {
  bash "${REPO_ROOT}/script/latency_service.sh" stop >/dev/null 2>&1 || true
}

trap cleanup EXIT

IFS=' ' read -r -a MODES_ARR <<< "$MODES"
IFS=' ' read -r -a RERANK_ARR <<< "$RERANK_OPTIONS"

bash "${REPO_ROOT}/script/latency_service.sh" start

uv run python tools/latency_runner.py \
  --service-url "$LATENCY_SERVICE_URL" \
  --project-dir "$PROJECT_DIR" \
  --query "$QUERY" \
  --output-dir "$OUTPUT_DIR" \
  --runs "$RUNS" \
  --response-type "$RESPONSE_TYPE" \
  --request-timeout "$REQUEST_TIMEOUT" \
  --env-file "$ENV_FILE" \
  --modes "${MODES_ARR[@]}" \
  --rerank-options "${RERANK_ARR[@]}"

uv run python tools/latency_report.py \
  --output-dir "$OUTPUT_DIR" \
  --project-dir "$PROJECT_DIR" \
  --query "$QUERY" \
  --runs "$RUNS"

printf 'Artifacts saved to %s\n' "$OUTPUT_DIR"
