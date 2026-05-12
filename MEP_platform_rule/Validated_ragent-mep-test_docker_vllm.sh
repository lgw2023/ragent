#!/usr/bin/env bash
set -euo pipefail

# Run this script on the Ascend host from a full repository checkout.
#
# Typical usage:
#   cd /data/disk1/ragent
#   bash MEP_platform_rule/Validated_ragent-mep-test_docker_vllm.sh
#
# Optional overrides:
#   HOST_TEST_DIR=/data/disk1/ragent \
#   CONTAINER_NAME=vllm_ascend_910b_8cards \
#   ASCEND_VISIBLE_DEVICES=0-7 \
#   ASCEND_RT_VISIBLE_DEVICES=0 \
#   bash MEP_platform_rule/Validated_ragent-mep-test_docker_vllm.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "MEP_platform_rule" ]; then
  DEFAULT_HOST_TEST_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  DEFAULT_HOST_TEST_DIR="$(pwd)"
fi

HOST_TEST_DIR="${HOST_TEST_DIR:-$DEFAULT_HOST_TEST_DIR}"
CONTAINER_TEST_DIR="${CONTAINER_TEST_DIR:-/tmp/ragent}"
RUNTIME_DIR="${RUNTIME_DIR:-/tmp/ragent-mep-runtime}"
MODEL_PACKAGE="${MODEL_PACKAGE:-bge-m3}"
MODEL_PATH="${MODEL_PATH:-}"
IMAGE="${IMAGE:-swr.cn-southwest-2.myhuaweicloud.com/mep-dev-ga/vllm_ascend:910B_0.13.0rc0.20260417141425}"
CONTAINER_NAME="${CONTAINER_NAME:-vllm_ascend_910b_8cards}"
ASCEND_VISIBLE_DEVICES="${ASCEND_VISIBLE_DEVICES:-0-7}"
ASCEND_RT_VISIBLE_DEVICES="${ASCEND_RT_VISIBLE_DEVICES:-0}"
VLLM_PORT="${VLLM_PORT:-8000}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-900}"
RECREATE_CONTAINER="${RECREATE_CONTAINER:-1}"
CHMOD_TEST_DIR="${CHMOD_TEST_DIR:-1}"
ENTER_AFTER_TEST="${ENTER_AFTER_TEST:-0}"

NO_PROXY_DEFAULT="localhost,127.0.0.1,::1,*.huawei.com,*.huaweicloud.com"
http_proxy="${http_proxy:-}"
https_proxy="${https_proxy:-}"
ftp_proxy="${ftp_proxy:-}"
no_proxy="${no_proxy:-$NO_PROXY_DEFAULT}"
NO_PROXY="${NO_PROXY:-$NO_PROXY_DEFAULT}"

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

single_match_glob() {
  local pattern="$1"
  local label="$2"
  local matches=()
  while IFS= read -r path; do
    matches+=("$path")
  done < <(compgen -G "$pattern" | sort)

  if [ "${#matches[@]}" -ne 1 ]; then
    echo "expected exactly one $label matching: $pattern" >&2
    echo "found ${#matches[@]}:" >&2
    printf '  %s\n' "${matches[@]:-}" >&2
    exit 1
  fi
  printf '%s\n' "${matches[0]}"
}

chmod_test_dir() {
  [ "$CHMOD_TEST_DIR" = "1" ] || return 0
  step "Make repository/test bundle readable/writable by the container"
  if [ "$(id -u)" -eq 0 ]; then
    chmod -R a+rwX "$HOST_TEST_DIR"
  elif command -v sudo >/dev/null 2>&1; then
    sudo chmod -R a+rwX "$HOST_TEST_DIR"
  else
    echo "warning: sudo is unavailable; skip chmod. Set CHMOD_TEST_DIR=0 to silence this."
  fi
}

require_command docker
[ -d "$HOST_TEST_DIR" ] || die "HOST_TEST_DIR does not exist: $HOST_TEST_DIR"
[ -d "$HOST_TEST_DIR/ragent" ] || die "not a ragent repository/test bundle: $HOST_TEST_DIR"
[ -f "$HOST_TEST_DIR/tools/build_mep_layout.py" ] || die "missing tools/build_mep_layout.py under $HOST_TEST_DIR"

TRITON_WHEEL="$(single_match_glob "$HOST_TEST_DIR/triton_ascend-3.2.0*.whl" "triton-ascend repair wheel")"
VLLM_WHEEL="$(single_match_glob "$HOST_TEST_DIR/vllm-0.13.0*.whl" "vllm repair wheel")"
VLLM_ASCEND_WHEEL="$(single_match_glob "$HOST_TEST_DIR/vllm_ascend-0.13.0*.whl" "vllm-ascend repair wheel")"

echo "repository/test bundle: $HOST_TEST_DIR"
echo "container mount:     $CONTAINER_TEST_DIR"
echo "image:               $IMAGE"
echo "container:           $CONTAINER_NAME"
echo "repair wheels:"
echo "  $(basename "$TRITON_WHEEL")"
echo "  $(basename "$VLLM_WHEEL")"
echo "  $(basename "$VLLM_ASCEND_WHEEL")"

chmod_test_dir

step "Start Ascend vLLM container"
if docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  if [ "$RECREATE_CONTAINER" = "1" ]; then
    docker rm -f "$CONTAINER_NAME" >/dev/null
  else
    die "container already exists: $CONTAINER_NAME; set RECREATE_CONTAINER=1 to replace it"
  fi
fi

docker run -d \
  --name "$CONTAINER_NAME" \
  --network host \
  --ipc=host \
  --pids-limit 409600 \
  -e ASCEND_VISIBLE_DEVICES="$ASCEND_VISIBLE_DEVICES" \
  -e http_proxy="$http_proxy" \
  -e https_proxy="$https_proxy" \
  -e ftp_proxy="$ftp_proxy" \
  -e HTTP_PROXY="$http_proxy" \
  -e HTTPS_PROXY="$https_proxy" \
  -e FTP_PROXY="$ftp_proxy" \
  -e no_proxy="$no_proxy" \
  -e NO_PROXY="$NO_PROXY" \
  -v /dev/shm:/dev/shm \
  -v /root/.cache:/root/.cache \
  -v "$HOST_TEST_DIR:$CONTAINER_TEST_DIR:rw" \
  "$IMAGE" \
  /bin/bash -lc "while true; do sleep 3600; done" >/dev/null

step "Run test steps inside the container"
docker exec -i \
  -e CONTAINER_TEST_DIR="$CONTAINER_TEST_DIR" \
  -e RUNTIME_DIR="$RUNTIME_DIR" \
  -e MODEL_PACKAGE="$MODEL_PACKAGE" \
  -e MODEL_PATH="$MODEL_PATH" \
  -e ASCEND_RT_VISIBLE_DEVICES="$ASCEND_RT_VISIBLE_DEVICES" \
  -e VLLM_PORT="$VLLM_PORT" \
  -e STARTUP_TIMEOUT_SECONDS="$STARTUP_TIMEOUT_SECONDS" \
  "$CONTAINER_NAME" \
  bash -s <<'CONTAINER_SCRIPT'
set -euo pipefail

step() {
  echo
  echo "---- $*"
}

single_match_glob() {
  local pattern="$1"
  local label="$2"
  local matches=()
  while IFS= read -r path; do
    matches+=("$path")
  done < <(compgen -G "$pattern" | sort)
  if [ "${#matches[@]}" -ne 1 ]; then
    echo "expected exactly one $label matching: $pattern" >&2
    echo "found ${#matches[@]}:" >&2
    printf '  %s\n' "${matches[@]:-}" >&2
    exit 1
  fi
  printf '%s\n' "${matches[0]}"
}

source_if_exists() {
  local path="$1"
  if [ -f "$path" ]; then
    # shellcheck disable=SC1090
    set +u
    source "$path"
    set -u
  else
    echo "warning: Ascend env script not found: $path"
  fi
}

resolve_model_path() {
  python3 - "$RUNTIME_DIR" "${MODEL_PATH:-}" <<'PY'
from pathlib import Path
import sys

runtime_dir = Path(sys.argv[1]).resolve()
configured = sys.argv[2].strip()


def looks_like_model_dir(path: Path) -> bool:
    return path.is_dir() and (path / "config.json").is_file() and (
        (path / "tokenizer.json").is_file()
        or (path / "tokenizer_config.json").is_file()
    )


if configured:
    candidate = Path(configured).expanduser()
    if not candidate.is_absolute():
        candidate = runtime_dir / candidate
    candidate = candidate.resolve()
    if not looks_like_model_dir(candidate):
        raise SystemExit(f"configured MODEL_PATH is not a valid model dir: {candidate}")
    print(candidate)
    raise SystemExit(0)

properties = {}
for config_path in (
    runtime_dir / "data" / "config" / "embedding.properties",
    runtime_dir / "data" / "config" / "sysconfig.properties",
    runtime_dir / "data" / "embedding.properties",
    runtime_dir / "data" / "sysconfig.properties",
):
    if not config_path.is_file():
        continue
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        properties[key.strip()] = value.strip()
    break

model_root = runtime_dir / "model"
for key in (
    "model.relative_path",
    "embedding.model_relative_path",
    "model.path",
    "embedding.model_path",
):
    raw_value = properties.get(key)
    if not raw_value:
        continue
    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        candidate = model_root / candidate
    candidate = candidate.resolve()
    if looks_like_model_dir(candidate):
        print(candidate)
        raise SystemExit(0)

if looks_like_model_dir(model_root):
    print(model_root.resolve())
    raise SystemExit(0)

candidates = sorted(path.resolve() for path in model_root.iterdir() if looks_like_model_dir(path))
if len(candidates) == 1:
    print(candidates[0])
    raise SystemExit(0)
if not candidates:
    raise SystemExit(f"no model directory found under {model_root}")
raise SystemExit(
    "multiple model directories found under "
    f"{model_root}; set MODEL_PATH explicitly: {', '.join(map(str, candidates))}"
)
PY
}

cd "$CONTAINER_TEST_DIR"

step "Build materialized MEP runtime layout"
rm -rf "$RUNTIME_DIR"
python3 tools/build_mep_layout.py \
  --model-package "$MODEL_PACKAGE" \
  --output "$RUNTIME_DIR" \
  --materialize
MODEL_PATH="$(resolve_model_path)"
echo "resolved model path: $MODEL_PATH"

step "Install validated vLLM repair wheels from the offline bundle"
CBOR2_WHEEL="$(single_match_glob "$RUNTIME_DIR/data/deps/wheelhouse/*/cbor2-*.whl" "cbor2 repair wheel")"
WHEELHOUSE_DIR="$(dirname "$CBOR2_WHEEL")"
TRITON_WHEEL="$(single_match_glob "$CONTAINER_TEST_DIR/triton_ascend-3.2.0*.whl" "triton-ascend repair wheel")"
VLLM_WHEEL="$(single_match_glob "$CONTAINER_TEST_DIR/vllm-0.13.0*.whl" "vllm repair wheel")"
VLLM_ASCEND_WHEEL="$(single_match_glob "$CONTAINER_TEST_DIR/vllm_ascend-0.13.0*.whl" "vllm-ascend repair wheel")"
WHEELHOUSE_WHEELS=()
while IFS= read -r wheel_path; do
  WHEELHOUSE_WHEELS+=("$wheel_path")
done < <(find "$WHEELHOUSE_DIR" -maxdepth 1 -type f -name '*.whl' ! -name '._*' | sort)
if [ "${#WHEELHOUSE_WHEELS[@]}" -eq 0 ]; then
  echo "no wheel files found under $WHEELHOUSE_DIR" >&2
  exit 1
fi
echo "using wheelhouse: $WHEELHOUSE_DIR"
echo "wheelhouse wheel count: ${#WHEELHOUSE_WHEELS[@]}"
echo "required repair wheels:"
echo "  $(basename "$CBOR2_WHEEL")"
echo "  $(basename "$TRITON_WHEEL")"
echo "  $(basename "$VLLM_WHEEL")"
echo "  $(basename "$VLLM_ASCEND_WHEEL")"

python3 -m pip uninstall vllm vllm-ascend -y || true
python3 -m pip install --no-index --no-deps --force-reinstall "${WHEELHOUSE_WHEELS[@]}"

step "Load Ascend runtime environment"
source_if_exists /usr/local/Ascend/ascend-toolkit/set_env.sh
source_if_exists /usr/local/Ascend/ascend-toolkit/latest/set_env.sh
source_if_exists /usr/local/Ascend/nnal/atb/set_env.sh
source_if_exists /usr/local/Ascend/nnal/atb/latest/atb/set_env.sh
export ASCEND_RT_VISIBLE_DEVICES
export VLLM_LOGGING_LEVEL="${VLLM_LOGGING_LEVEL:-DEBUG}"
export VLLM_PLUGINS="${VLLM_PLUGINS:-ascend}"

step "Start vLLM OpenAI-compatible embedding server"
LOG_PATH=/tmp/ragent-mep-vllm.log
RESPONSE_PATH=/tmp/ragent-mep-embedding-response.json
rm -f "$LOG_PATH" "$RESPONSE_PATH"
pkill -f "vllm.entrypoints.openai.api_server" >/dev/null 2>&1 || true

python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_PATH" \
  --runner pooling \
  --served-model-name BAAI-bge-m3 \
  --host 0.0.0.0 \
  --port "$VLLM_PORT" \
  --max-model-len 8192 \
  --dtype auto >"$LOG_PATH" 2>&1 &
VLLM_PID=$!
echo "$VLLM_PID" >/tmp/ragent-mep-vllm.pid

step "Wait for vLLM readiness"
deadline=$((SECONDS + STARTUP_TIMEOUT_SECONDS))
until curl -fsS "http://127.0.0.1:${VLLM_PORT}/v1/models" >/tmp/ragent-mep-models.json 2>/dev/null; do
  if ! kill -0 "$VLLM_PID" >/dev/null 2>&1; then
    echo "vLLM exited before becoming ready. Log tail:" >&2
    tail -200 "$LOG_PATH" >&2 || true
    exit 1
  fi
  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "timed out waiting for vLLM. Log tail:" >&2
    tail -200 "$LOG_PATH" >&2 || true
    exit 1
  fi
  sleep 5
done

step "Call /v1/embeddings"
curl -fsS "http://127.0.0.1:${VLLM_PORT}/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "BAAI-bge-m3",
    "input": [
      "你好，帮我生成一个向量。",
      "vLLM Ascend NPU embedding test."
    ],
    "encoding_format": "float"
  }' | tee "$RESPONSE_PATH" | python3 -m json.tool

python3 - "$RESPONSE_PATH" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    payload = json.load(f)

items = payload.get("data") or []
if len(items) != 2:
    raise SystemExit(f"expected 2 embedding results, got {len(items)}")

dimensions = [len(item.get("embedding") or []) for item in items]
if not all(dimensions):
    raise SystemExit(f"empty embedding returned: dimensions={dimensions}")

print(f"embedding request OK: count={len(items)}, dimensions={dimensions}")
PY

echo
echo "vLLM log: $LOG_PATH"
echo "vLLM pid: $VLLM_PID"
CONTAINER_SCRIPT

step "Done"
echo "Container is still running for follow-up checks:"
echo "  docker exec -it $CONTAINER_NAME /bin/bash"
echo "  docker exec $CONTAINER_NAME tail -200 /tmp/ragent-mep-vllm.log"
echo "  docker rm -f $CONTAINER_NAME"

if [ "$ENTER_AFTER_TEST" = "1" ]; then
  docker exec -it "$CONTAINER_NAME" /bin/bash
fi
