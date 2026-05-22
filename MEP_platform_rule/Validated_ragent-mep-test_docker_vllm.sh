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
#   CONTAINER_NAME=qwen3_embedding_4b_vllm_ascend_validation \
#   NPU_HOST_ID=0 \
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
MODEL_PACKAGE="${MODEL_PACKAGE:-qwen3-embedding-4b}"
MODEL_PATH="${MODEL_PATH:-}"
IMAGE="${IMAGE:-swr.cn-southwest-2.myhuaweicloud.com/huaweiccs-hivoice-product-ga/vllm-ascend-0.10.2-910b-cann8.2.rc1-torch2.7.1rc1:1.2.9.300}"
CONTAINER_NAME="${CONTAINER_NAME:-qwen3_embedding_4b_vllm_ascend_validation}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen3-embedding-4b-local}"
EMBEDDING_DIMENSIONS="${EMBEDDING_DIMENSIONS:-2560}"
ASCEND_VISIBLE_DEVICES="${ASCEND_VISIBLE_DEVICES:-0}"
ASCEND_RT_VISIBLE_DEVICES="${ASCEND_RT_VISIBLE_DEVICES:-0}"
NPU_HOST_ID="${NPU_HOST_ID:-0}"
NPU_CONTAINER_ID="${NPU_CONTAINER_ID:-0}"
MAP_NPU_DEVICES="${MAP_NPU_DEVICES:-1}"
VLLM_PORT="${VLLM_PORT:-8000}"
VLLM_USE_V1="${VLLM_USE_V1:-1}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-64}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-32768}"
BLOCK_SIZE="${BLOCK_SIZE:-128}"
ATB_HOME_PATH="${ATB_HOME_PATH:-/usr/local/Ascend/nnal/atb/latest/atb}"
ATB_CXX_ABI="${ATB_CXX_ABI:-cxx_abi_0}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-900}"
RECREATE_CONTAINER="${RECREATE_CONTAINER:-1}"
CHMOD_TEST_DIR="${CHMOD_TEST_DIR:-1}"
ENTER_AFTER_TEST="${ENTER_AFTER_TEST:-0}"
INSTALL_VLLM_REPAIR_WHEELS="${INSTALL_VLLM_REPAIR_WHEELS:-0}"

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

DEVICE_ARGS=()
MOUNT_ARGS=()

build_device_args() {
  DEVICE_ARGS=()
  [ "$MAP_NPU_DEVICES" = "1" ] || return 0

  if [ ! -e "/dev/davinci${NPU_HOST_ID}" ]; then
    die "missing host NPU device: /dev/davinci${NPU_HOST_ID}; set NPU_HOST_ID or MAP_NPU_DEVICES=0"
  fi

  DEVICE_ARGS+=(--device "/dev/davinci${NPU_HOST_ID}:/dev/davinci${NPU_CONTAINER_ID}")
  for dev in /dev/davinci_manager /dev/devmm_svm /dev/hisi_hdc; do
    [ -e "$dev" ] && DEVICE_ARGS+=(--device "$dev")
  done
}

build_mount_args() {
  MOUNT_ARGS=(
    -v /dev/shm:/dev/shm
    -v /root/.cache:/root/.cache
    -v "$HOST_TEST_DIR:$CONTAINER_TEST_DIR:rw"
  )

  [ -d /usr/local/dcmi ] && MOUNT_ARGS+=(-v /usr/local/dcmi:/usr/local/dcmi)
  [ -f /usr/local/bin/npu-smi ] && MOUNT_ARGS+=(-v /usr/local/bin/npu-smi:/usr/local/bin/npu-smi)
  [ -d /usr/local/Ascend/driver/lib64 ] && MOUNT_ARGS+=(-v /usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64)
  [ -f /usr/local/Ascend/driver/version.info ] && MOUNT_ARGS+=(-v /usr/local/Ascend/driver/version.info:/usr/local/Ascend/driver/version.info)
  [ -f /etc/ascend_install.info ] && MOUNT_ARGS+=(-v /etc/ascend_install.info:/etc/ascend_install.info)
}

require_command docker
[ -d "$HOST_TEST_DIR" ] || die "HOST_TEST_DIR does not exist: $HOST_TEST_DIR"
[ -d "$HOST_TEST_DIR/ragent" ] || die "not a ragent repository/test bundle: $HOST_TEST_DIR"
[ -f "$HOST_TEST_DIR/tools/build_mep_layout.py" ] || die "missing tools/build_mep_layout.py under $HOST_TEST_DIR"

if [ "$INSTALL_VLLM_REPAIR_WHEELS" = "1" ]; then
  TRITON_WHEEL="$(single_match_glob "$HOST_TEST_DIR/triton_ascend-3.2.0*.whl" "triton-ascend repair wheel")"
  VLLM_WHEEL="$(single_match_glob "$HOST_TEST_DIR/vllm-0.13.0*.whl" "vllm repair wheel")"
  VLLM_ASCEND_WHEEL="$(single_match_glob "$HOST_TEST_DIR/vllm_ascend-0.13.0*.whl" "vllm-ascend repair wheel")"
fi

echo "repository/test bundle: $HOST_TEST_DIR"
echo "container mount:     $CONTAINER_TEST_DIR"
echo "image:               $IMAGE"
echo "container:           $CONTAINER_NAME"
echo "served model:        $SERVED_MODEL_NAME"
echo "embedding dim:       $EMBEDDING_DIMENSIONS"
echo "host NPU:            $NPU_HOST_ID -> container $NPU_CONTAINER_ID"
echo "install repair wheels: $INSTALL_VLLM_REPAIR_WHEELS"
if [ "$INSTALL_VLLM_REPAIR_WHEELS" = "1" ]; then
  echo "repair wheels:"
  echo "  $(basename "$TRITON_WHEEL")"
  echo "  $(basename "$VLLM_WHEEL")"
  echo "  $(basename "$VLLM_ASCEND_WHEEL")"
fi

chmod_test_dir
build_device_args
build_mount_args

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
  -e ASCEND_RT_VISIBLE_DEVICES="$NPU_CONTAINER_ID" \
  -e VLLM_USE_V1="$VLLM_USE_V1" \
  -e PYTORCH_NPU_ALLOC_CONF=max_split_size_mb:256 \
  -e HCCL_OP_EXPANSION_MODE=AIV \
  -e TOKENIZERS_PARALLELISM=true \
  -e OMP_NUM_THREADS=16 \
  -e ATB_HOME_PATH="$ATB_HOME_PATH" \
  -e ATB_CXX_ABI="$ATB_CXX_ABI" \
  -e http_proxy="$http_proxy" \
  -e https_proxy="$https_proxy" \
  -e ftp_proxy="$ftp_proxy" \
  -e HTTP_PROXY="$http_proxy" \
  -e HTTPS_PROXY="$https_proxy" \
  -e FTP_PROXY="$ftp_proxy" \
  -e no_proxy="$no_proxy" \
  -e NO_PROXY="$NO_PROXY" \
  "${DEVICE_ARGS[@]}" \
  "${MOUNT_ARGS[@]}" \
  "$IMAGE" \
  /bin/bash -lc "while true; do sleep 3600; done" >/dev/null

step "Run test steps inside the container"
docker exec -i \
  -e CONTAINER_TEST_DIR="$CONTAINER_TEST_DIR" \
  -e RUNTIME_DIR="$RUNTIME_DIR" \
  -e MODEL_PACKAGE="$MODEL_PACKAGE" \
  -e MODEL_PATH="$MODEL_PATH" \
  -e SERVED_MODEL_NAME="$SERVED_MODEL_NAME" \
  -e EMBEDDING_DIMENSIONS="$EMBEDDING_DIMENSIONS" \
  -e ASCEND_RT_VISIBLE_DEVICES="$NPU_CONTAINER_ID" \
  -e VLLM_PORT="$VLLM_PORT" \
  -e VLLM_USE_V1="$VLLM_USE_V1" \
  -e MAX_MODEL_LEN="$MAX_MODEL_LEN" \
  -e GPU_MEMORY_UTILIZATION="$GPU_MEMORY_UTILIZATION" \
  -e MAX_NUM_SEQS="$MAX_NUM_SEQS" \
  -e MAX_NUM_BATCHED_TOKENS="$MAX_NUM_BATCHED_TOKENS" \
  -e BLOCK_SIZE="$BLOCK_SIZE" \
  -e ATB_HOME_PATH="$ATB_HOME_PATH" \
  -e ATB_CXX_ABI="$ATB_CXX_ABI" \
  -e STARTUP_TIMEOUT_SECONDS="$STARTUP_TIMEOUT_SECONDS" \
  -e INSTALL_VLLM_REPAIR_WHEELS="$INSTALL_VLLM_REPAIR_WHEELS" \
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

step "Load Ascend runtime environment"
source_if_exists /usr/local/Ascend/ascend-toolkit/set_env.sh
source_if_exists /usr/local/Ascend/ascend-toolkit/latest/set_env.sh
source_if_exists /usr/local/Ascend/nnal/asdsip/set_env.sh
export ATB_HOME_PATH="${ATB_HOME_PATH:-/usr/local/Ascend/nnal/atb/latest/atb}"
export ATB_CXX_ABI="${ATB_CXX_ABI:-cxx_abi_0}"
ATB_LIB_PATH="${ATB_HOME_PATH}/${ATB_CXX_ABI}/lib"
case ":${LD_LIBRARY_PATH:-}:" in
  *":${ATB_LIB_PATH}:"*) ;;
  *) export LD_LIBRARY_PATH="${ATB_LIB_PATH}:${LD_LIBRARY_PATH:-}" ;;
esac
export ASCEND_RT_VISIBLE_DEVICES
export VLLM_LOGGING_LEVEL="${VLLM_LOGGING_LEVEL:-DEBUG}"
export VLLM_USE_V1="${VLLM_USE_V1:-1}"
export PYTORCH_NPU_ALLOC_CONF="${PYTORCH_NPU_ALLOC_CONF:-max_split_size_mb:256}"
export HCCL_OP_EXPANSION_MODE="${HCCL_OP_EXPANSION_MODE:-AIV}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-true}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-16}"

echo "ATB_HOME_PATH=$ATB_HOME_PATH"
echo "ATB_CXX_ABI=$ATB_CXX_ABI"
echo "ATB lib path: $ATB_LIB_PATH"

if [ "$INSTALL_VLLM_REPAIR_WHEELS" = "1" ]; then
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
else
  step "Use vLLM packages already installed in the target image"
  python3 - <<'PY'
try:
    import vllm
    print("vllm:", getattr(vllm, "__version__", "unknown"))
except Exception as exc:
    raise SystemExit(f"vllm import failed: {exc!r}")
try:
    import vllm_ascend
    print("vllm_ascend:", getattr(vllm_ascend, "__version__", "unknown"))
except Exception as exc:
    print("warning: vllm_ascend import failed:", repr(exc))
PY
fi

step "Start vLLM OpenAI-compatible embedding server"
LOG_PATH=/tmp/ragent-mep-vllm.log
RESPONSE_PATH=/tmp/ragent-mep-embedding-response.json
rm -f "$LOG_PATH" "$RESPONSE_PATH"
pkill -f "vllm serve" >/dev/null 2>&1 || true
pkill -f "vllm.entrypoints.openai.api_server" >/dev/null 2>&1 || true

vllm serve "$MODEL_PATH" \
  --served-model-name "$SERVED_MODEL_NAME" \
  --runner pooling \
  --task embed \
  --host 0.0.0.0 \
  --port "$VLLM_PORT" \
  --trust-remote-code \
  --dtype float16 \
  --max-model-len "$MAX_MODEL_LEN" \
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
  --max-num-seqs "$MAX_NUM_SEQS" \
  --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS" \
  --block-size "$BLOCK_SIZE" \
  --disable-log-requests \
  --uvicorn-log-level warning >"$LOG_PATH" 2>&1 &
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
    "model": "'"${SERVED_MODEL_NAME}"'",
    "input": [
      "你好，帮我生成一个 Qwen3-Embedding-4B 向量。",
      "vLLM Ascend NPU Qwen3 embedding test."
    ],
    "encoding_format": "float"
  }' | tee "$RESPONSE_PATH" | python3 -m json.tool

python3 - "$RESPONSE_PATH" "$EMBEDDING_DIMENSIONS" <<'PY'
import json
import sys

path = sys.argv[1]
expected_dim = int(sys.argv[2])
with open(path, "r", encoding="utf-8") as f:
    payload = json.load(f)

items = payload.get("data") or []
if len(items) != 2:
    raise SystemExit(f"expected 2 embedding results, got {len(items)}")

dimensions = [len(item.get("embedding") or []) for item in items]
if not all(dimensions):
    raise SystemExit(f"empty embedding returned: dimensions={dimensions}")
if dimensions != [expected_dim] * len(dimensions):
    raise SystemExit(
        f"unexpected embedding dimensions: {dimensions}; expected {expected_dim}"
    )

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
