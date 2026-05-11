#!/usr/bin/env bash
set -euo pipefail

# Collect target MEP/vLLM image and container runtime facts needed before
# adapting this project to a replacement image.
#
# Typical usage on the target Docker host:
#   IMAGE='registry.example.com/path/to/new-image:tag' \
#     bash tools/collect_mep_image_runtime_info.sh
#
# Or:
#   bash tools/collect_mep_image_runtime_info.sh registry.example.com/path/to/new-image:tag
#
# The container name intentionally defaults to the name used by the existing
# validated MEP/vLLM script. Override only if the platform uses a different
# fixed name:
#   CONTAINER_NAME=vllm_ascend_910b_8cards IMAGE='...' bash tools/collect_mep_image_runtime_info.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PROJECT_ROOT

IMAGE="${IMAGE:-${1:-}}"
CONTAINER_NAME="${CONTAINER_NAME:-vllm_ascend_910b_8cards}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/.mep_image_probe/$(date +%Y%m%d_%H%M%S)}"
CONTAINER_PROBE_DIR="${CONTAINER_PROBE_DIR:-/tmp/ragent-mep-image-probe}"

PULL_IMAGE="${PULL_IMAGE:-1}"
RECREATE_CONTAINER="${RECREATE_CONTAINER:-1}"
KEEP_CONTAINER="${KEEP_CONTAINER:-1}"
MOUNT_PROJECT="${MOUNT_PROJECT:-1}"
INCLUDE_RAW_DOCKER_JSON="${INCLUDE_RAW_DOCKER_JSON:-0}"
INCLUDE_SECRET_VALUES="${INCLUDE_SECRET_VALUES:-0}"

ASCEND_VISIBLE_DEVICES="${ASCEND_VISIBLE_DEVICES:-0-7}"
START_COMMAND="${START_COMMAND:-while true; do sleep 3600; done}"
NO_PROXY_DEFAULT="localhost,127.0.0.1,::1,*.huawei.com,*.huaweicloud.com"
http_proxy="${http_proxy:-}"
https_proxy="${https_proxy:-}"
ftp_proxy="${ftp_proxy:-}"
no_proxy="${no_proxy:-$NO_PROXY_DEFAULT}"
NO_PROXY="${NO_PROXY:-$NO_PROXY_DEFAULT}"
HTTP_PROXY="${HTTP_PROXY:-$http_proxy}"
HTTPS_PROXY="${HTTPS_PROXY:-$https_proxy}"
FTP_PROXY="${FTP_PROXY:-$ftp_proxy}"

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

capture() {
  local path="$1"
  shift
  {
    printf '$'
    printf ' %q' "$@"
    printf '\n'
    "$@"
  } >"$path" 2>&1 || true
}

capture_shell() {
  local path="$1"
  local command_text="$2"
  {
    printf '$ %s\n' "$command_text"
    bash -lc "$command_text"
  } >"$path" 2>&1 || true
}

sanitize_file_in_place() {
  local path="$1"
  [ "$INCLUDE_SECRET_VALUES" = "1" ] && return 0
  [ -f "$path" ] || return 0
  local tmp_path
  tmp_path="$path.tmp"
  awk '
    BEGIN { IGNORECASE = 1 }
    {
      line = $0
      if (line ~ /(TOKEN|SECRET|PASSWORD|PASSWD|API[_-]?KEY|ACCESS[_-]?KEY|SECRET[_-]?KEY|CREDENTIAL|AUTHORIZATION|PRIVATE[_-]?KEY|COOKIE|SESSION|EMBEDDING_MODEL_KEY)/) {
        gsub(/=([^, "\047\]]+)/, "=<redacted>", line)
        gsub(/: "([^"]+)"/, ": \"<redacted>\"", line)
      }
      print line
    }
  ' "$path" >"$tmp_path"
  mv "$tmp_path" "$path"
}

write_summary() {
  local path="$1"
  {
    echo "# MEP Image Runtime Probe"
    echo
    echo "- image: $IMAGE"
    echo "- container: $CONTAINER_NAME"
    echo "- collected_at: $(date -Iseconds)"
    echo "- project_root: $PROJECT_ROOT"
    echo "- output_dir: $OUTPUT_DIR"
    echo
    echo "## What to share back"
    echo
    echo "Please share the generated tarball, or at least these files:"
    echo
    echo "- docker/container_inspect_summary.txt"
    echo "- container/probe/system.txt"
    echo "- container/probe/python.txt"
    echo "- container/probe/pip_freeze.txt"
    echo "- container/probe/pip_key_packages.txt"
    echo "- container/probe/vllm_probe.txt"
    echo "- container/probe/ascend_probe.txt"
    echo "- container/probe/mep_env.txt"
    echo "- container/probe/mep_paths.txt"
    echo "- project/project_context.txt"
    echo
    echo "Secret-looking environment values are redacted by default."
    echo "Set INCLUDE_SECRET_VALUES=1 only if you intentionally want raw values."
  } >"$path"
}

if [ -z "$IMAGE" ]; then
  die "IMAGE is required. Example: IMAGE='registry.example.com/new-image:tag' bash $0"
fi

require_command docker

mkdir -p "$OUTPUT_DIR"/host "$OUTPUT_DIR"/docker "$OUTPUT_DIR"/container "$OUTPUT_DIR"/project
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

exec > >(tee "$OUTPUT_DIR/run.log") 2>&1

step "Collect host facts"
capture_shell "$OUTPUT_DIR/host/system.txt" '
  date -Iseconds
  hostname || true
  uname -a || true
  command -v lsb_release >/dev/null 2>&1 && lsb_release -a || true
  [ -f /etc/os-release ] && cat /etc/os-release || true
  id || true
  arch || true
'
capture "$OUTPUT_DIR/host/docker_version.txt" docker version
capture "$OUTPUT_DIR/host/docker_info.txt" docker info
capture_shell "$OUTPUT_DIR/host/accelerator.txt" '
  command -v npu-smi >/dev/null 2>&1 && npu-smi info || true
  command -v lspci >/dev/null 2>&1 && lspci | grep -Ei "ascend|nvidia|huawei|gpu|npu" || true
  ls -l /dev/davinci* /dev/davinci_manager /dev/devmm_svm /dev/hisi_hdc 2>/dev/null || true
'
capture_shell "$OUTPUT_DIR/host/project_files.txt" '
  printf "PROJECT_ROOT=%s\n" "$PROJECT_ROOT"
  find "$PROJECT_ROOT" -maxdepth 2 -type f \( \
    -name "config.json" -o \
    -name "package.json" -o \
    -name "pyproject.toml" -o \
    -name "embedding.properties" -o \
    -name "sysconfig.properties" -o \
    -name "type.mf" \
  \) -print | sort
'

step "Collect local project context"
{
  echo "PROJECT_ROOT=$PROJECT_ROOT"
  echo
  for path in \
    "$PROJECT_ROOT/package.json" \
    "$PROJECT_ROOT/config.json" \
    "$PROJECT_ROOT/pyproject.toml" \
    "$PROJECT_ROOT/mep/model_packages/bge-m3/modelDir/meta/type.mf" \
    "$PROJECT_ROOT/mep/model_packages/bge-m3/modelDir/data/config/embedding.properties"
  do
    if [ -f "$path" ]; then
      echo
      echo "----- $path -----"
      sed -n '1,220p' "$path"
    fi
  done
} >"$OUTPUT_DIR/project/project_context.txt" 2>&1 || true
sanitize_file_in_place "$OUTPUT_DIR/project/project_context.txt"

if [ "$PULL_IMAGE" = "1" ]; then
  step "Pull image if needed"
  capture "$OUTPUT_DIR/docker/image_pull.txt" docker pull "$IMAGE"
fi

step "Collect image metadata"
capture "$OUTPUT_DIR/docker/image_history.txt" docker image history --no-trunc "$IMAGE"
capture "$OUTPUT_DIR/docker/image_inspect_summary.txt" docker image inspect \
  --format $'Id={{.Id}}\nRepoTags={{json .RepoTags}}\nRepoDigests={{json .RepoDigests}}\nCreated={{.Created}}\nArchitecture={{.Architecture}}\nOs={{.Os}}\nSize={{.Size}}\nUser={{.Config.User}}\nWorkingDir={{.Config.WorkingDir}}\nEntrypoint={{json .Config.Entrypoint}}\nCmd={{json .Config.Cmd}}\nExposedPorts={{json .Config.ExposedPorts}}\nVolumes={{json .Config.Volumes}}\nLabels={{json .Config.Labels}}\nEnv={{json .Config.Env}}' \
  "$IMAGE"
sanitize_file_in_place "$OUTPUT_DIR/docker/image_inspect_summary.txt"
if [ "$INCLUDE_RAW_DOCKER_JSON" = "1" ]; then
  capture "$OUTPUT_DIR/docker/image_inspect_raw.json" docker image inspect "$IMAGE"
  sanitize_file_in_place "$OUTPUT_DIR/docker/image_inspect_raw.json"
fi

step "Start or reuse container"
if docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  if [ "$RECREATE_CONTAINER" = "1" ]; then
    docker rm -f "$CONTAINER_NAME" >/dev/null
  else
    running_state="$(docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null || echo false)"
    if [ "$running_state" != "true" ]; then
      docker start "$CONTAINER_NAME" >/dev/null
    fi
  fi
fi

if ! docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  docker_run_cmd=(
    docker run -d
    --name "$CONTAINER_NAME"
    --network host
    --ipc=host
    --pids-limit 409600
    -e "ASCEND_VISIBLE_DEVICES=$ASCEND_VISIBLE_DEVICES"
    -e "http_proxy=$http_proxy"
    -e "https_proxy=$https_proxy"
    -e "ftp_proxy=$ftp_proxy"
    -e "HTTP_PROXY=$HTTP_PROXY"
    -e "HTTPS_PROXY=$HTTPS_PROXY"
    -e "FTP_PROXY=$FTP_PROXY"
    -e "no_proxy=$no_proxy"
    -e "NO_PROXY=$NO_PROXY"
    -v /dev/shm:/dev/shm
  )

  if [ -d /root/.cache ]; then
    docker_run_cmd+=(-v /root/.cache:/root/.cache)
  fi

  if [ "$MOUNT_PROJECT" = "1" ] && [ -f "$PROJECT_ROOT/package.json" ]; then
    docker_run_cmd+=(-v "$PROJECT_ROOT:/tmp/ragent-project:ro")
  fi

  if [ -n "${DOCKER_RUN_EXTRA_ARGS:-}" ]; then
    # shellcheck disable=SC2206
    extra_args=($DOCKER_RUN_EXTRA_ARGS)
    docker_run_cmd+=("${extra_args[@]}")
  fi

  docker_run_cmd+=("$IMAGE" /bin/bash -lc "$START_COMMAND")

  {
    printf '$'
    printf ' %q' "${docker_run_cmd[@]}"
    printf '\n'
  } >"$OUTPUT_DIR/docker/docker_run_command.txt"
  "${docker_run_cmd[@]}" >/dev/null
fi

step "Collect container metadata"
capture "$OUTPUT_DIR/docker/container_ps.txt" docker ps -a --no-trunc --filter "name=^/${CONTAINER_NAME}$"
capture "$OUTPUT_DIR/docker/container_logs_tail.txt" docker logs --tail 300 "$CONTAINER_NAME"
capture "$OUTPUT_DIR/docker/container_top.txt" docker top "$CONTAINER_NAME"
capture "$OUTPUT_DIR/docker/container_stats.txt" docker stats --no-stream "$CONTAINER_NAME"
capture "$OUTPUT_DIR/docker/container_inspect_summary.txt" docker inspect \
  --format $'Id={{.Id}}\nName={{.Name}}\nImage={{.Config.Image}}\nState={{json .State}}\nUser={{.Config.User}}\nWorkingDir={{.Config.WorkingDir}}\nEntrypoint={{json .Config.Entrypoint}}\nCmd={{json .Config.Cmd}}\nEnv={{json .Config.Env}}\nNetworkMode={{.HostConfig.NetworkMode}}\nIpcMode={{.HostConfig.IpcMode}}\nPidMode={{.HostConfig.PidMode}}\nPrivileged={{.HostConfig.Privileged}}\nRuntime={{.HostConfig.Runtime}}\nPidsLimit={{.HostConfig.PidsLimit}}\nBinds={{json .HostConfig.Binds}}\nPortBindings={{json .HostConfig.PortBindings}}\nDevices={{json .HostConfig.Devices}}\nMounts={{json .Mounts}}' \
  "$CONTAINER_NAME"
sanitize_file_in_place "$OUTPUT_DIR/docker/container_inspect_summary.txt"
if [ "$INCLUDE_RAW_DOCKER_JSON" = "1" ]; then
  capture "$OUTPUT_DIR/docker/container_inspect_raw.json" docker inspect "$CONTAINER_NAME"
  sanitize_file_in_place "$OUTPUT_DIR/docker/container_inspect_raw.json"
fi

step "Run read-only probe inside container"
docker exec -i \
  -e "RAGENT_MEP_PROBE_DIR=$CONTAINER_PROBE_DIR" \
  -e "INCLUDE_SECRET_VALUES=$INCLUDE_SECRET_VALUES" \
  "$CONTAINER_NAME" \
  /bin/bash -s <<'CONTAINER_SCRIPT'
set +e

PROBE_DIR="${RAGENT_MEP_PROBE_DIR:-/tmp/ragent-mep-image-probe}"
INCLUDE_SECRET_VALUES="${INCLUDE_SECRET_VALUES:-0}"
rm -rf "$PROBE_DIR"
mkdir -p "$PROBE_DIR"

capture() {
  local path="$1"
  shift
  {
    printf '$'
    printf ' %q' "$@"
    printf '\n'
    "$@"
  } >"$PROBE_DIR/$path" 2>&1
}

capture_shell() {
  local path="$1"
  local command_text="$2"
  {
    printf '$ %s\n' "$command_text"
    /bin/bash -lc "$command_text"
  } >"$PROBE_DIR/$path" 2>&1
}

sanitize_file_in_place() {
  local path="$1"
  [ "$INCLUDE_SECRET_VALUES" = "1" ] && return 0
  [ -f "$path" ] || return 0
  local tmp_path
  tmp_path="$path.tmp"
  awk '
    BEGIN { IGNORECASE = 1 }
    {
      line = $0
      if (line ~ /(TOKEN|SECRET|PASSWORD|PASSWD|API[_-]?KEY|ACCESS[_-]?KEY|SECRET[_-]?KEY|CREDENTIAL|AUTHORIZATION|PRIVATE[_-]?KEY|COOKIE|SESSION|EMBEDDING_MODEL_KEY)/) {
        gsub(/=([^, "\047\]]+)/, "=<redacted>", line)
        gsub(/: "([^"]+)"/, ": \"<redacted>\"", line)
      }
      print line
    }
  ' "$path" >"$tmp_path"
  mv "$tmp_path" "$path"
}

capture_shell system.txt '
  date -Iseconds
  hostname || true
  id || true
  pwd || true
  uname -a || true
  arch || true
  [ -f /etc/os-release ] && cat /etc/os-release || true
  printf "\n--- limits ---\n"
  ulimit -a || true
  printf "\n--- process 1 ---\n"
  ps -p 1 -o pid,ppid,user,args || true
'

env | sort >"$PROBE_DIR/env.sanitized.txt"
sanitize_file_in_place "$PROBE_DIR/env.sanitized.txt"

capture_shell mep_env.txt '
  env | sort | grep -E "^(MODEL_|RAGENT_|MEP_|SFS_|ASCEND_|VLLM_|HCCL_|NPU_|DEVICE_|PYTHON|LD_LIBRARY_PATH|PATH=|no_proxy=|NO_PROXY=|http_proxy=|https_proxy=|HTTP_PROXY=|HTTPS_PROXY=)" || true
'
sanitize_file_in_place "$PROBE_DIR/mep_env.txt"

capture_shell mep_paths.txt '
  for path in \
    /model \
    /data \
    /meta \
    /component \
    /opt/huawei/log \
    /home/mep \
    /usr/local/Ascend \
    /usr/local/python3.10.2 \
    /tmp/ragent-project \
    "$MODEL_ABSOLUTE_DIR" \
    "$MODEL_RELATIVE_DIR"; do
    [ -n "$path" ] || continue
    printf "\n----- %s -----\n" "$path"
    if [ -e "$path" ]; then
      ls -la "$path" || true
      find "$path" -maxdepth 3 -mindepth 1 \( -type f -o -type d -o -type l \) -printf "%y %p\n" 2>/dev/null | sort | head -300 || true
    else
      echo "missing"
    fi
  done
'

capture_shell mounts.txt '
  mount || true
  printf "\n--- df -h ---\n"
  df -h || true
'

capture_shell devices.txt '
  ls -l /dev/davinci* /dev/davinci_manager /dev/devmm_svm /dev/hisi_hdc 2>/dev/null || true
'

capture_shell ascend_probe.txt '
  command -v npu-smi >/dev/null 2>&1 && npu-smi info || true
  for path in \
    /usr/local/Ascend/ascend-toolkit/set_env.sh \
    /usr/local/Ascend/nnal/atb/set_env.sh \
    /usr/local/Ascend/ascend-toolkit/latest/bin/setenv.bash; do
    printf "\n----- %s -----\n" "$path"
    if [ -f "$path" ]; then
      ls -l "$path"
      sed -n "1,80p" "$path"
    else
      echo "missing"
    fi
  done
'

capture_shell python.txt '
  for python_bin in python3 python python3.10 /usr/local/python3.10.2/bin/python3; do
    if command -v "$python_bin" >/dev/null 2>&1 || [ -x "$python_bin" ]; then
      printf "\n----- %s -----\n" "$python_bin"
      "$python_bin" - <<'"'"'PY'"'"'
import importlib.util
import json
import os
import platform
import site
import sys

print("executable:", sys.executable)
print("version:", sys.version.replace("\n", " "))
print("platform:", platform.platform())
print("machine:", platform.machine())
print("prefix:", sys.prefix)
print("base_prefix:", sys.base_prefix)
print("cwd:", os.getcwd())
print("sys.path:", json.dumps(sys.path, ensure_ascii=False, indent=2))
try:
    print("sitepackages:", json.dumps(site.getsitepackages(), ensure_ascii=False, indent=2))
except Exception as exc:
    print("sitepackages_error:", repr(exc))

packages = [
    "vllm",
    "vllm_ascend",
    "torch",
    "torch_npu",
    "transformers",
    "tokenizers",
    "sentence_transformers",
    "numpy",
    "openai",
    "litellm",
    "pydantic",
    "cbor2",
    "triton",
    "triton_ascend",
    "ragent",
]
for name in packages:
    spec = importlib.util.find_spec(name)
    print(f"module {name}: {spec.origin if spec else 'missing'}")
PY
    fi
  done
'

capture_shell pip_freeze.txt '
  for python_bin in python3 python3.10 /usr/local/python3.10.2/bin/python3 python; do
    if command -v "$python_bin" >/dev/null 2>&1 || [ -x "$python_bin" ]; then
      printf "\n----- %s -m pip freeze -----\n" "$python_bin"
      "$python_bin" -m pip freeze 2>&1 || true
    fi
  done
'

capture_shell pip_key_packages.txt '
  packages="vllm vllm-ascend vllm_ascend torch torch-npu torch_npu transformers tokenizers sentence-transformers numpy openai litellm pydantic cbor2 triton triton-ascend model-hosting-container-standards"
  for python_bin in python3 python3.10 /usr/local/python3.10.2/bin/python3 python; do
    if command -v "$python_bin" >/dev/null 2>&1 || [ -x "$python_bin" ]; then
      printf "\n----- %s -m pip show key packages -----\n" "$python_bin"
      "$python_bin" -m pip show $packages 2>&1 || true
    fi
  done
'

capture_shell vllm_probe.txt '
  command -v vllm >/dev/null 2>&1 && vllm --version || true
  command -v vllm >/dev/null 2>&1 && timeout 20 vllm --help || true
  for python_bin in python3 python3.10 /usr/local/python3.10.2/bin/python3 python; do
    if command -v "$python_bin" >/dev/null 2>&1 || [ -x "$python_bin" ]; then
      printf "\n----- %s vLLM import/version/help -----\n" "$python_bin"
      "$python_bin" - <<'"'"'PY'"'"'
import importlib
mods = ["vllm", "vllm_ascend"]
for name in mods:
    try:
        mod = importlib.import_module(name)
        print(name, "version=", getattr(mod, "__version__", "unknown"), "file=", getattr(mod, "__file__", "unknown"))
    except Exception as exc:
        print(name, "import_error=", repr(exc))
PY
      timeout 20 "$python_bin" -m vllm.entrypoints.openai.api_server --help 2>&1 | sed -n "1,220p" || true
    fi
  done
'

capture_shell project_mount.txt '
  if [ -d /tmp/ragent-project ]; then
    cd /tmp/ragent-project || exit 0
    printf "mounted project root: %s\n" "$(pwd)"
    for path in package.json config.json pyproject.toml mep/model_packages/bge-m3/modelDir/meta/type.mf mep/model_packages/bge-m3/modelDir/data/config/embedding.properties; do
      if [ -f "$path" ]; then
        printf "\n----- %s -----\n" "$path"
        sed -n "1,220p" "$path"
      fi
    done
  else
    echo "/tmp/ragent-project is not mounted"
  fi
'
sanitize_file_in_place "$PROBE_DIR/project_mount.txt"

capture_shell command_matrix.txt '
  for cmd in bash sh curl wget gcc g++ cmake make git python python3 python3.10 pip pip3 npu-smi vllm; do
    printf "%-16s" "$cmd"
    command -v "$cmd" || true
  done
'

find "$PROBE_DIR" -maxdepth 1 -type f -print | sort >"$PROBE_DIR/file_list.txt"
CONTAINER_SCRIPT

docker cp "$CONTAINER_NAME:$CONTAINER_PROBE_DIR" "$OUTPUT_DIR/container/probe"

step "Archive collected diagnostics"
write_summary "$OUTPUT_DIR/README.md"
tar_path="$OUTPUT_DIR.tar.gz"
tar -czf "$tar_path" -C "$(dirname "$OUTPUT_DIR")" "$(basename "$OUTPUT_DIR")"

step "Done"
echo "Diagnostics directory: $OUTPUT_DIR"
echo "Diagnostics archive:   $tar_path"
echo
echo "Container kept running for manual follow-up:"
echo "  docker exec -it $CONTAINER_NAME /bin/bash"
echo "  docker rm -f $CONTAINER_NAME"

if [ "$KEEP_CONTAINER" != "1" ]; then
  docker rm -f "$CONTAINER_NAME" >/dev/null || true
  echo "Container removed because KEEP_CONTAINER=$KEEP_CONTAINER"
fi
