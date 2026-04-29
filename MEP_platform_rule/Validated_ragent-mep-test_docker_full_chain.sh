#!/usr/bin/env bash
set -euo pipefail

# Run this script on the Ascend host after copying the offline test bundle.
#
# It first runs the validated vLLM Ascend embedding check, then reuses that
# local OpenAI-compatible embedding service from the MEP component and executes
# CustomerModel.load/calc against the bundled KG snapshot.
#
# Typical usage:
#   cd /data/disk1/ragent-mep-test
#   MEP_ENV_FILE=/data/disk1/ragent-mep-test/.env \
#   bash MEP_platform_rule/Validated_ragent-mep-test_docker_full_chain.sh
#
# Useful overrides:
#   SKIP_VLLM_VALIDATION=1                  reuse an already running container/vLLM
#   MEP_REQUEST_NAME=sfs_create_request.json run a normal generation request sample
#   MEP_REQUIRE_RERANK=1                    fail if RERANK_* is incomplete
#   MEP_ENABLE_RERANK=false                 force rerank off for this validation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "MEP_platform_rule" ]; then
  DEFAULT_HOST_TEST_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  DEFAULT_HOST_TEST_DIR="$(pwd)"
fi

HOST_TEST_DIR="${HOST_TEST_DIR:-$DEFAULT_HOST_TEST_DIR}"
CONTAINER_TEST_DIR="${CONTAINER_TEST_DIR:-/tmp/ragent-mep-test}"
RUNTIME_DIR="${RUNTIME_DIR:-/tmp/ragent-mep-runtime}"
MODEL_PACKAGE="${MODEL_PACKAGE:-bge-m3}"
CONTAINER_NAME="${CONTAINER_NAME:-vllm_ascend_910b_8cards}"
VLLM_PORT="${VLLM_PORT:-8000}"
SKIP_VLLM_VALIDATION="${SKIP_VLLM_VALIDATION:-0}"
MEP_ENV_FILE="${MEP_ENV_FILE:-}"
MEP_REQUEST_NAME="${MEP_REQUEST_NAME:-retrieval_only_request.json}"
MEP_REQUESTS="${MEP_REQUESTS:-$MEP_REQUEST_NAME}"
MEP_OUTPUT_DIR="${MEP_OUTPUT_DIR:-/tmp/ragent-mep-output}"
MEP_LOG_DIR="${MEP_LOG_DIR:-/tmp/ragent-mep-full-chain}"
MEP_REQUIRE_RERANK="${MEP_REQUIRE_RERANK:-0}"
MEP_ENABLE_RERANK="${MEP_ENABLE_RERANK:-}"
MEP_KEEP_REQUEST_GENERATE_PATH="${MEP_KEEP_REQUEST_GENERATE_PATH:-0}"
MEP_KEEP_REQUEST_RERANK="${MEP_KEEP_REQUEST_RERANK:-0}"
MEP_REUSE_EXISTING_VLLM="${MEP_REUSE_EXISTING_VLLM:-1}"
MEP_CLEAR_PATH_ENV="${MEP_CLEAR_PATH_ENV:-1}"

die() {
  echo "error: $*" >&2
  exit 1
}

step() {
  echo
  echo "==> $*"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

source_env_file() {
  local env_file="$1"
  [ -n "$env_file" ] || return 0
  [ -f "$env_file" ] || die "MEP_ENV_FILE does not exist: $env_file"
  step "Load model environment from $env_file"
  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
}

add_exec_env_if_set() {
  local name="$1"
  if [ "${!name+x}" = "x" ]; then
    EXEC_ENV_ARGS+=("-e" "$name=${!name}")
  fi
}

add_extra_exec_env_names() {
  local raw_names="${MEP_EXTRA_ENV_NAMES:-}"
  [ -n "$raw_names" ] || return 0
  local normalized_names="${raw_names//,/ }"
  local name
  for name in $normalized_names; do
    [ -n "$name" ] || continue
    add_exec_env_if_set "$name"
  done
}

require_command docker
[ -d "$HOST_TEST_DIR" ] || die "HOST_TEST_DIR does not exist: $HOST_TEST_DIR"
[ -f "$HOST_TEST_DIR/MEP_platform_rule/Validated_ragent-mep-test_docker_vllm.sh" ] || \
  die "missing validated vLLM script under $HOST_TEST_DIR"

if [ -z "$MEP_ENV_FILE" ] && [ -f "$HOST_TEST_DIR/.env" ]; then
  MEP_ENV_FILE="$HOST_TEST_DIR/.env"
fi
source_env_file "$MEP_ENV_FILE"

if [ "$MEP_REUSE_EXISTING_VLLM" != "1" ] && [ "$SKIP_VLLM_VALIDATION" != "1" ]; then
  die "MEP_REUSE_EXISTING_VLLM=0 requires SKIP_VLLM_VALIDATION=1 and a clean running container, otherwise the vLLM validation step will occupy the embedding port"
fi

if [ "$SKIP_VLLM_VALIDATION" != "1" ]; then
  step "Run validated vLLM Ascend embedding check"
  HOST_TEST_DIR="$HOST_TEST_DIR" \
  CONTAINER_TEST_DIR="$CONTAINER_TEST_DIR" \
  RUNTIME_DIR="$RUNTIME_DIR" \
  MODEL_PACKAGE="$MODEL_PACKAGE" \
  CONTAINER_NAME="$CONTAINER_NAME" \
  VLLM_PORT="$VLLM_PORT" \
  ENTER_AFTER_TEST=0 \
    bash "$HOST_TEST_DIR/MEP_platform_rule/Validated_ragent-mep-test_docker_vllm.sh"
else
  step "Skip vLLM validation and reuse existing container"
  docker inspect "$CONTAINER_NAME" >/dev/null 2>&1 || \
    die "container does not exist: $CONTAINER_NAME"
fi

if [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME")" != "true" ]; then
  die "container is not running: $CONTAINER_NAME"
fi

EXEC_ENV_ARGS=(
  "-e" "CONTAINER_TEST_DIR=$CONTAINER_TEST_DIR"
  "-e" "RUNTIME_DIR=$RUNTIME_DIR"
  "-e" "MODEL_PACKAGE=$MODEL_PACKAGE"
  "-e" "VLLM_PORT=$VLLM_PORT"
  "-e" "MEP_REQUESTS=$MEP_REQUESTS"
  "-e" "MEP_OUTPUT_DIR=$MEP_OUTPUT_DIR"
  "-e" "MEP_LOG_DIR=$MEP_LOG_DIR"
  "-e" "MEP_REQUIRE_RERANK=$MEP_REQUIRE_RERANK"
  "-e" "MEP_ENABLE_RERANK=$MEP_ENABLE_RERANK"
  "-e" "MEP_KEEP_REQUEST_GENERATE_PATH=$MEP_KEEP_REQUEST_GENERATE_PATH"
  "-e" "MEP_KEEP_REQUEST_RERANK=$MEP_KEEP_REQUEST_RERANK"
  "-e" "MEP_REUSE_EXISTING_VLLM=$MEP_REUSE_EXISTING_VLLM"
  "-e" "MEP_CLEAR_PATH_ENV=$MEP_CLEAR_PATH_ENV"
  "-e" "MEP_EMBEDDING_MODEL=${MEP_EMBEDDING_MODEL:-}"
  "-e" "MEP_EMBEDDING_MODEL_KEY=${MEP_EMBEDDING_MODEL_KEY:-}"
  "-e" "MEP_EMBEDDING_MODEL_URL=${MEP_EMBEDDING_MODEL_URL:-}"
  "-e" "MEP_EMBEDDING_PROVIDER=${MEP_EMBEDDING_PROVIDER:-}"
  "-e" "MEP_EMBEDDING_DIMENSIONS=${MEP_EMBEDDING_DIMENSIONS:-}"
)

for name in \
  LLM_MODEL_KEY \
  LLM_MODEL_URL \
  LLM_MODEL \
  LLM_API_BASE \
  LLM_API_PROVIDER \
  LLM_API_TIMEOUT_SECONDS \
  LLM_API_CLIENT_MAX_RETRIES \
  LLM_API_ENABLE_THINKING \
  MODEL_STARTUP_CHECK_ENABLED \
  MODEL_STARTUP_CHECK_TIMEOUT_SECONDS \
  RERANK_MODEL_KEY \
  RERANK_MODEL_URL \
  RERANK_MODEL \
  RERANK_TIMEOUT_SECONDS \
  ENABLE_RERANK \
  IMAGE_MODEL_KEY \
  IMAGE_MODEL_URL \
  IMAGE_MODEL \
  IMAGE_MODEL_TIMEOUT \
  RAG_ANSWER_PROMPT_MODE \
  RAG_RESPONSE_LANGUAGE \
  TOP_K \
  CHUNK_TOP_K \
  MAX_ENTITY_TOKENS \
  MAX_RELATION_TOKENS \
  MAX_TOTAL_TOKENS \
  HISTORY_TURNS \
  http_proxy \
  https_proxy \
  ftp_proxy \
  no_proxy \
  HTTP_PROXY \
  HTTPS_PROXY \
  FTP_PROXY \
  NO_PROXY
do
  add_exec_env_if_set "$name"
done
add_extra_exec_env_names

step "Run MEP component KG inference chain inside the container"
docker exec -i "${EXEC_ENV_ARGS[@]}" "$CONTAINER_NAME" bash -s <<'CONTAINER_SCRIPT'
set -euo pipefail

step() {
  echo
  echo "---- $*"
}

die() {
  echo "error: $*" >&2
  exit 1
}

json_pretty_utf8() {
  python3 -c 'import json, sys
if len(sys.argv) > 1:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        payload = json.load(f)
else:
    payload = json.load(sys.stdin)
json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
sys.stdout.write("\n")' "$@"
}

bool_from_string() {
  local value="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    1|true|yes|on) echo "true" ;;
    0|false|no|off) echo "false" ;;
    *) return 1 ;;
  esac
}

require_env() {
  local missing=()
  local name
  for name in "$@"; do
    if [ -z "${!name:-}" ]; then
      missing+=("$name")
    fi
  done
  if [ "${#missing[@]}" -ne 0 ]; then
    printf 'missing required env for full MEP inference: %s\n' "${missing[*]}" >&2
    printf 'set them in the image environment or pass MEP_ENV_FILE=/path/to/.env to the host script.\n' >&2
    exit 2
  fi
}

complete_rerank_config() {
  [ -n "${RERANK_MODEL_KEY:-}" ] && [ -n "${RERANK_MODEL_URL:-}" ] && [ -n "${RERANK_MODEL:-}" ]
}

requests_require_llm() {
  python3 - "$CONTAINER_TEST_DIR" "$MEP_REQUESTS" <<'PY'
from pathlib import Path
import json
import sys

container_test_dir = Path(sys.argv[1]).resolve()
request_items = [
    item.strip()
    for item in sys.argv[2].split(",")
    if item.strip()
]

for request_item in request_items:
    request_path = Path(request_item)
    if not request_path.is_absolute():
        request_path = container_test_dir / "example" / "mep_requests" / request_item
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        print("true")
        raise SystemExit(0)

    def is_true(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return False

    if not (is_true(data.get("retrieval_only")) or is_true(data.get("only_need_context"))):
        print("true")
        raise SystemExit(0)

print("false")
PY
}

prepare_runtime_if_needed() {
  if [ -d "$RUNTIME_DIR/component" ] && [ -d "$RUNTIME_DIR/data" ] && [ -d "$RUNTIME_DIR/model" ]; then
    return 0
  fi
  step "Build materialized MEP runtime layout"
  cd "$CONTAINER_TEST_DIR"
  rm -rf "$RUNTIME_DIR"
  python3 tools/build_mep_layout.py \
    --model-package "$MODEL_PACKAGE" \
    --output "$RUNTIME_DIR" \
    --materialize
}

prepare_request_copy() {
  local request_src="$1"
  local request_work="$2"
  local effective_rerank="$3"
  python3 - "$request_src" "$request_work" "$MEP_OUTPUT_DIR" "$effective_rerank" <<'PY'
from pathlib import Path
import json
import os
import sys

request_src = Path(sys.argv[1]).resolve()
request_work = Path(sys.argv[2]).resolve()
output_dir = Path(sys.argv[3]).resolve()
effective_rerank = sys.argv[4].strip().lower() == "true"
keep_generate_path = os.getenv("MEP_KEEP_REQUEST_GENERATE_PATH") == "1"
keep_rerank = os.getenv("MEP_KEEP_REQUEST_RERANK") == "1"

payload = json.loads(request_src.read_text(encoding="utf-8"))
data = payload.setdefault("data", {})
if not isinstance(data, dict):
    raise SystemExit("request data must be an object")

stem = request_src.stem
request_output_dir = output_dir / stem
generate_path = request_output_dir / "generatePath"

if not keep_generate_path:
    if data.get("action") == "create":
        data["basePath"] = str(request_output_dir / "basePath")
        file_info = data.setdefault("fileInfo", [{}])
        if not isinstance(file_info, list) or not file_info:
            file_info = [{}]
            data["fileInfo"] = file_info
        if not isinstance(file_info[0], dict):
            file_info[0] = {}
        file_info[0]["generatePath"] = str(generate_path)
    else:
        data["generatePath"] = str(generate_path)

if not keep_rerank:
    data["enable_rerank"] = effective_rerank

request_work.parent.mkdir(parents=True, exist_ok=True)
request_work.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(request_work)
PY
}

validate_result() {
  local stdout_path="$1"
  local request_work="$2"
  python3 - "$stdout_path" "$request_work" <<'PY'
from pathlib import Path
import json
import sys

stdout_path = Path(sys.argv[1]).resolve()
request_work = Path(sys.argv[2]).resolve()

result = json.loads(stdout_path.read_text(encoding="utf-8"))
request = json.loads(request_work.read_text(encoding="utf-8"))
recommend = result.get("recommendResult")
if not isinstance(recommend, dict):
    raise SystemExit(f"missing recommendResult in {stdout_path}")
code = str(recommend.get("code"))
if code != "0":
    raise SystemExit(f"recommendResult.code={code}, des={recommend.get('des')!r}")

data = request.get("data") or {}

def is_true(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False

retrieval_only = is_true(data.get("retrieval_only")) or is_true(data.get("only_need_context"))
retrieval_result = None
file_info = data.get("fileInfo")
generate_path = data.get("generatePath")
if not generate_path and isinstance(file_info, list) and file_info and isinstance(file_info[0], dict):
    generate_path = file_info[0].get("generatePath")

answer = None
gen_json_path = None
if isinstance(generate_path, str) and generate_path.strip():
    gen_json_path = Path(generate_path).expanduser().resolve() / "gen.json"
    if not gen_json_path.is_file():
        raise SystemExit(f"expected generated result file is missing: {gen_json_path}")
    generated = json.loads(gen_json_path.read_text(encoding="utf-8"))
    if str(generated.get("code")) != "0":
        raise SystemExit(f"generated payload code is not 0: {generated}")
    answer = str(generated.get("answer") or "").strip()
    if retrieval_only:
        retrieval_result = generated.get("retrieval_result")
else:
    content = recommend.get("content") or []
    if content and isinstance(content[0], dict):
        answer = str(content[0].get("answer") or "").strip()
        if retrieval_only:
            retrieval_result = content[0].get("retrieval_result")

if retrieval_only:
    if not isinstance(retrieval_result, dict):
        raise SystemExit("retrieval-only payload is missing retrieval_result")
    final_context_text = str(retrieval_result.get("final_context_text") or "").strip()
    final_context_chunks = retrieval_result.get("final_context_chunks") or []
    if not final_context_text and not final_context_chunks:
        raise SystemExit("retrieval-only payload has no final context")
elif not answer:
    raise SystemExit("MEP chain returned code=0 but answer is empty")

summary = {
    "recommendResult.code": code,
    "recommendResult.length": recommend.get("length"),
    "retrieval_only": retrieval_only,
    "answer_preview": answer[:160],
    "gen_json": str(gen_json_path) if gen_json_path else None,
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
PY
}

run_component_request() {
  local request_src="$1"
  local effective_rerank="$2"
  local request_base="$(basename "$request_src" .json)"
  local request_work="$MEP_LOG_DIR/${request_base}.runtime-request.json"
  local stdout_path="$MEP_LOG_DIR/${request_base}.stdout.json"
  local stderr_path="$MEP_LOG_DIR/${request_base}.stderr.log"

  step "Prepare request: $request_src"
  prepare_request_copy "$request_src" "$request_work" "$effective_rerank" >/dev/null
  json_pretty_utf8 "$request_work"

  local vllm_log="/tmp/ragent-mep-vllm.log"
  local before_size=0
  if [ -f "$vllm_log" ]; then
    before_size="$(stat -c '%s' "$vllm_log" 2>/dev/null || echo 0)"
  fi

  step "Call CustomerModel.load/calc via run_mep_local.py"
  if ! (
    cd "$RUNTIME_DIR/component"
    python3 run_mep_local.py --request "$request_work" >"$stdout_path" 2>"$stderr_path"
  ); then
    echo "run_mep_local.py failed. stderr tail:" >&2
    tail -200 "$stderr_path" >&2 || true
    echo "stdout:" >&2
    cat "$stdout_path" >&2 || true
    exit 1
  fi

  step "Component stderr"
  cat "$stderr_path"

  step "Component recommendResult"
  json_pretty_utf8 "$stdout_path"

  step "Validate recommendResult and generated payload"
  validate_result "$stdout_path" "$request_work"

  if [ -f "$vllm_log" ]; then
    local after_size
    after_size="$(stat -c '%s' "$vllm_log" 2>/dev/null || echo 0)"
    if [ "$after_size" -gt "$before_size" ]; then
      echo "vLLM log grew during component request: ${before_size} -> ${after_size} bytes"
    else
      echo "warning: vLLM log size did not grow during component request"
    fi
  fi

  echo
  echo "request log files:"
  echo "  request: $request_work"
  echo "  stdout:  $stdout_path"
  echo "  stderr:  $stderr_path"
}

cd "$CONTAINER_TEST_DIR"
prepare_runtime_if_needed
mkdir -p "$MEP_LOG_DIR" "$MEP_OUTPUT_DIR"

step "Inspect runtime layout"
test -d "$RUNTIME_DIR/component" || die "missing component dir: $RUNTIME_DIR/component"
test -d "$RUNTIME_DIR/model" || die "missing model dir: $RUNTIME_DIR/model"
test -d "$RUNTIME_DIR/data" || die "missing data dir: $RUNTIME_DIR/data"
test -d "$RUNTIME_DIR/data/kg" || die "missing KG dir: $RUNTIME_DIR/data/kg"
find "$RUNTIME_DIR/data/kg" -maxdepth 3 -type f | sort

if [ "$MEP_REUSE_EXISTING_VLLM" = "1" ]; then
  step "Verify existing vLLM embedding service"
  curl -fsS "http://127.0.0.1:${VLLM_PORT}/v1/models" | json_pretty_utf8
fi

REQUESTS_REQUIRE_LLM="$(requests_require_llm)"
if [ "$REQUESTS_REQUIRE_LLM" = "true" ]; then
  require_env LLM_MODEL_KEY LLM_MODEL_URL LLM_MODEL
else
  echo "all selected requests are retrieval-only; LLM_MODEL_KEY/LLM_MODEL_URL/LLM_MODEL are not required"
fi

if complete_rerank_config; then
  rerank_config_complete=true
else
  rerank_config_complete=false
fi

if [ "$MEP_REQUIRE_RERANK" = "1" ] && [ "$rerank_config_complete" != "true" ]; then
  die "MEP_REQUIRE_RERANK=1 but RERANK_MODEL_KEY/RERANK_MODEL_URL/RERANK_MODEL are incomplete"
fi

if [ -n "${MEP_ENABLE_RERANK:-}" ]; then
  EFFECTIVE_RERANK="$(bool_from_string "$MEP_ENABLE_RERANK")" || \
    die "invalid MEP_ENABLE_RERANK: $MEP_ENABLE_RERANK"
elif [ -n "${ENABLE_RERANK:-}" ]; then
  EFFECTIVE_RERANK="$(bool_from_string "$ENABLE_RERANK")" || \
    die "invalid ENABLE_RERANK: $ENABLE_RERANK"
elif [ "$rerank_config_complete" = "true" ]; then
  EFFECTIVE_RERANK=true
else
  EFFECTIVE_RERANK=false
fi

if [ "$EFFECTIVE_RERANK" = "true" ] && [ "$rerank_config_complete" != "true" ]; then
  die "rerank is enabled but RERANK_MODEL_KEY/RERANK_MODEL_URL/RERANK_MODEL are incomplete"
fi

export ENABLE_RERANK="$EFFECTIVE_RERANK"
echo "effective rerank: $EFFECTIVE_RERANK"
if [ "$rerank_config_complete" != "true" ]; then
  echo "warning: rerank env is incomplete; validation will run with rerank disabled"
fi

if [ "$MEP_REUSE_EXISTING_VLLM" = "1" ]; then
  export EMBEDDING_MODEL="${MEP_EMBEDDING_MODEL:-BAAI-bge-m3}"
  export EMBEDDING_MODEL_KEY="${MEP_EMBEDDING_MODEL_KEY:-EMPTY}"
  export EMBEDDING_MODEL_URL="${MEP_EMBEDDING_MODEL_URL:-http://127.0.0.1:${VLLM_PORT}/v1}"
  export EMBEDDING_PROVIDER="${MEP_EMBEDDING_PROVIDER:-custom_openai}"
  export EMBEDDING_DIMENSIONS="${MEP_EMBEDDING_DIMENSIONS:-1024}"
  echo "embedding runtime: reuse $EMBEDDING_MODEL_URL"
else
  unset EMBEDDING_MODEL EMBEDDING_MODEL_KEY EMBEDDING_MODEL_URL EMBEDDING_PROVIDER
  echo "embedding runtime: component autostart"
fi

if [ "$MEP_CLEAR_PATH_ENV" = "1" ]; then
  unset MODEL_SFS MODEL_OBJECT_ID MODEL_RELATIVE_DIR MODEL_ABSOLUTE_DIR path_appendix
  unset RAGENT_MEP_MODEL_DIR RAGENT_MEP_DATA_DIR RAGENT_MEP_KG_DIR RAGENT_MEP_SNAPSHOT_DIR
fi
export RAGENT_MEP_RUNTIME_ROOT="${RAGENT_MEP_RUNTIME_ROOT:-/tmp/ragent-mep-runtime-work}"
mkdir -p "$RAGENT_MEP_RUNTIME_ROOT"

IFS=',' read -r -a REQUEST_ITEMS <<< "$MEP_REQUESTS"
for request_item in "${REQUEST_ITEMS[@]}"; do
  request_item="$(printf '%s' "$request_item" | xargs)"
  [ -n "$request_item" ] || continue
  if [[ "$request_item" = /* ]]; then
    request_src="$request_item"
  else
    request_src="$CONTAINER_TEST_DIR/example/mep_requests/$request_item"
  fi
  [ -f "$request_src" ] || die "request sample does not exist: $request_src"
  run_component_request "$request_src" "$EFFECTIVE_RERANK"
done

step "Done"
echo "MEP full-chain validation passed"
echo "logs: $MEP_LOG_DIR"
echo "vLLM log: /tmp/ragent-mep-vllm.log"
CONTAINER_SCRIPT

step "Done"
echo "Container is still running for follow-up checks:"
echo "  docker exec -it $CONTAINER_NAME /bin/bash"
echo "  docker exec $CONTAINER_NAME tail -200 /tmp/ragent-mep-vllm.log"
echo "  docker exec $CONTAINER_NAME ls -la $MEP_LOG_DIR"
