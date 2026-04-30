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
MEP_ALLOW_TEST_EMBEDDING_TRUNCATION="${MEP_ALLOW_TEST_EMBEDDING_TRUNCATION:-1}"

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
  "-e" "MEP_ALLOW_TEST_EMBEDDING_TRUNCATION=$MEP_ALLOW_TEST_EMBEDDING_TRUNCATION"
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
  RAG_KEYWORD_FALLBACK_ENABLED \
  RAG_KEYWORD_FALLBACK_MODEL \
  RAG_KEYWORD_FALLBACK_DEVICE \
  RAG_KEYWORD_FALLBACK_THRESHOLD \
  RAG_KEYWORD_FALLBACK_MAX_KEYWORDS \
  RAG_KEYWORD_FALLBACK_LABELS \
  COSINE_THRESHOLD \
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
  python3 "$CONTAINER_TEST_DIR/tools/validate_mep_full_chain_result.py" \
    request-requires-llm \
    "$CONTAINER_TEST_DIR" \
    "$MEP_REQUESTS"
}

requests_have_retrieval_only() {
  python3 "$CONTAINER_TEST_DIR/tools/validate_mep_full_chain_result.py" \
    request-has-retrieval-only \
    "$CONTAINER_TEST_DIR" \
    "$MEP_REQUESTS"
}

resolve_keyword_wheelhouse_dir() {
  local root="$1"
  python3 - "$root" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
if not root.is_dir():
    raise SystemExit(0)

try:
    from mep_dependency_bootstrap import iter_platform_tags
    tags = list(iter_platform_tags())
except Exception:
    tags = []

seen = set()
for tag in tags:
    candidate = (root / tag).resolve()
    if candidate.is_dir() and candidate not in seen:
        print(candidate)
        raise SystemExit(0)
    seen.add(candidate)

if any(root.glob("*.whl")):
    print(root)
PY
}

install_keyword_fallback_dependencies() {
  local required="$1"
  local model_dir="$RUNTIME_DIR/data/models/keyword_extraction/knowledgator-gliner-x-small"
  local wheelhouse_root="$RUNTIME_DIR/data/deps/keyword_wheelhouse"
  local wheelhouse_dir
  wheelhouse_dir="$(resolve_keyword_wheelhouse_dir "$wheelhouse_root")"

  if [ "$required" = "true" ]; then
    [ -d "$model_dir" ] || die "missing GLiNER keyword model directory: $model_dir"
    [ -f "$model_dir/gliner_config.json" ] || die "missing GLiNER keyword model gliner_config.json: $model_dir"
    if [ ! -f "$model_dir/model.safetensors" ] && [ ! -f "$model_dir/pytorch_model.bin" ]; then
      die "missing GLiNER keyword model weights under $model_dir"
    fi
    [ -n "$wheelhouse_dir" ] || die "missing keyword wheelhouse under $wheelhouse_root"
  elif [ -z "$wheelhouse_dir" ]; then
    return 0
  fi

  local wheels=()
  while IFS= read -r wheel_path; do
    wheels+=("$wheel_path")
  done < <(find "$wheelhouse_dir" -maxdepth 1 -type f -name '*.whl' ! -name '._*' | sort)
  if [ "${#wheels[@]}" -eq 0 ]; then
    [ "$required" = "true" ] && die "keyword wheelhouse has no wheels: $wheelhouse_dir"
    return 0
  fi

  echo "install keyword fallback wheelhouse: $wheelhouse_dir"
  echo "keyword wheel count: ${#wheels[@]}"
  python3 -m pip install --no-index --no-deps --force-reinstall "${wheels[@]}"

  python3 - "$model_dir" <<'PY'
from pathlib import Path
import sys

model_dir = Path(sys.argv[1]).resolve()
import gliner  # noqa: F401
import onnxruntime  # noqa: F401
import stanza  # noqa: F401

if not model_dir.is_dir():
    raise SystemExit(f"missing GLiNER keyword model directory: {model_dir}")
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

resolve_runtime_embedding_dimensions() {
  python3 - "$RUNTIME_DIR" <<'PY'
from pathlib import Path
import json
import sys

runtime_dir = Path(sys.argv[1]).resolve()
data_dir = runtime_dir / "data"


def parse_properties(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "!")):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            key, value = line, ""
        result[key.strip()] = value.strip()
    return result


def read_vdb_dim(path: Path) -> int | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    dim = payload.get("embedding_dim")
    return dim if isinstance(dim, int) and dim > 0 else None


vdb_dims = {
    dim
    for path in data_dir.glob("**/vdb_chunks.json")
    if (dim := read_vdb_dim(path)) is not None
}
if len(vdb_dims) == 1:
    print(next(iter(vdb_dims)))
    raise SystemExit(0)

for candidate in (
    data_dir / "config" / "embedding.properties",
    data_dir / "embedding.properties",
):
    properties = parse_properties(candidate)
    raw_dim = properties.get("embedding.dimensions")
    if raw_dim:
        try:
            dim = int(raw_dim)
        except ValueError:
            continue
        if dim > 0:
            print(dim)
            raise SystemExit(0)
PY
}

validate_result() {
  local stdout_path="$1"
  local request_work="$2"
  python3 "$CONTAINER_TEST_DIR/tools/validate_mep_full_chain_result.py" \
    "$stdout_path" \
    "$request_work"
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
export COSINE_THRESHOLD="${COSINE_THRESHOLD:--1}"

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
REQUESTS_HAVE_RETRIEVAL_ONLY="$(requests_have_retrieval_only)"
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

install_keyword_fallback_dependencies "$REQUESTS_HAVE_RETRIEVAL_ONLY"

if [ "$MEP_REUSE_EXISTING_VLLM" = "1" ]; then
  export EMBEDDING_MODEL="${MEP_EMBEDDING_MODEL:-BAAI-bge-m3}"
  export EMBEDDING_MODEL_KEY="${MEP_EMBEDDING_MODEL_KEY:-EMPTY}"
  export EMBEDDING_MODEL_URL="${MEP_EMBEDDING_MODEL_URL:-http://127.0.0.1:${VLLM_PORT}/v1}"
  export EMBEDDING_PROVIDER="${MEP_EMBEDDING_PROVIDER:-custom_openai}"
  if [ -n "${MEP_EMBEDDING_DIMENSIONS:-}" ]; then
    export EMBEDDING_DIMENSIONS="$MEP_EMBEDDING_DIMENSIONS"
  else
    RUNTIME_EMBEDDING_DIMENSIONS="$(resolve_runtime_embedding_dimensions || true)"
    if [ -n "$RUNTIME_EMBEDDING_DIMENSIONS" ]; then
      export EMBEDDING_DIMENSIONS="$RUNTIME_EMBEDDING_DIMENSIONS"
    else
      unset EMBEDDING_DIMENSIONS EMBEDDING_DIM
    fi
  fi
  echo "embedding runtime: reuse $EMBEDDING_MODEL_URL"
  echo "embedding dimensions: ${EMBEDDING_DIMENSIONS:-default}"
else
  unset EMBEDDING_MODEL EMBEDDING_MODEL_KEY EMBEDDING_MODEL_URL EMBEDDING_PROVIDER
  echo "embedding runtime: component autostart"
fi
if [ "${MEP_ALLOW_TEST_EMBEDDING_TRUNCATION:-0}" = "1" ]; then
  export RAGENT_TEST_ALLOW_EMBEDDING_TRUNCATION=1
  echo "embedding truncation: test-only enabled"
else
  unset RAGENT_TEST_ALLOW_EMBEDDING_TRUNCATION
  echo "embedding truncation: disabled"
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
