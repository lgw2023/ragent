#!/usr/bin/env bash

# Collect read-only diagnostics from inside an MEP runtime image/container.
# Usage:
#   bash tools/collect_mep_image_info.sh [output_dir]
#
# Run this after entering the image, preferably from the component directory.
# The script writes a timestamped directory and a .tar.gz archive containing
# sanitized environment, runtime layout, Python package, and accelerator facts.

set -u
set -o pipefail

START_DIR="$(pwd -P 2>/dev/null || pwd)"
SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" 2>/dev/null && pwd -P || pwd)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S 2>/dev/null || printf unknown-time)"
DEFAULT_OUT_BASE="${TMPDIR:-/tmp}"
if [ ! -d "$DEFAULT_OUT_BASE" ] || [ ! -w "$DEFAULT_OUT_BASE" ]; then
  DEFAULT_OUT_BASE="$START_DIR"
fi
OUT_BASE="${1:-${DEFAULT_OUT_BASE}}"
OUT_DIR="${OUT_BASE%/}/mep_image_info_${TIMESTAMP}"
ARCHIVE="${OUT_DIR}.tar.gz"

if ! mkdir -p "$OUT_DIR"/{system,env,python,mep,component,commands,logs}; then
  printf 'Failed to create output directory: %s\n' "$OUT_DIR" >&2
  exit 1
fi

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S' 2>/dev/null || printf time)" "$*" | tee -a "$OUT_DIR/logs/collect.log" >/dev/null
}

have() {
  command -v "$1" >/dev/null 2>&1
}

run_cmd() {
  local outfile="$1"
  shift
  {
    printf '$'
    printf ' %q' "$@"
    printf '\n\n'
    "$@"
    local status=$?
    printf '\n[exit_code=%s]\n' "$status"
  } >"$outfile" 2>&1
}

run_shell() {
  local outfile="$1"
  local command_text="$2"
  {
    printf '$ %s\n\n' "$command_text"
    if have timeout; then
      timeout 20s sh -c "$command_text"
    else
      sh -c "$command_text"
    fi
    local status=$?
    printf '\n[exit_code=%s]\n' "$status"
  } >"$outfile" 2>&1
}

copy_if_exists() {
  local src="$1"
  local dst_dir="$2"
  if [ -e "$src" ]; then
    mkdir -p "$dst_dir"
    cp -a "$src" "$dst_dir/" 2>>"$OUT_DIR/logs/copy_errors.log" || true
  fi
}

redact_env() {
  env | sort | awk '
    BEGIN {
      sensitive = "(KEY|TOKEN|SECRET|PASSWORD|PASSWD|PASS|CREDENTIAL|COOKIE|SESSION|AUTH|ACCESS|PRIVATE|SIGNATURE)"
    }
    {
      pos = index($0, "=")
      if (pos == 0) {
        print $0
        next
      }
      name = substr($0, 1, pos - 1)
      value = substr($0, pos + 1)
      upper = toupper(name)
      if (upper ~ sensitive) {
        if (length(value) == 0) {
          print name "="
        } else {
          print name "=<redacted:length=" length(value) ">"
        }
      } else {
        print $0
      }
    }
  '
}

write_header() {
  cat >"$OUT_DIR/README.txt" <<EOF
MEP image information capture

Started at:        ${TIMESTAMP}
Start directory:   ${START_DIR}
Script path:       ${SCRIPT_PATH}
Script directory:  ${SCRIPT_DIR}
Output directory:  ${OUT_DIR}

Send back the .tar.gz archive or the text files most relevant to the failure.
Environment values whose names look secret-like are redacted in env/env.redacted.txt.
EOF
}

collect_system() {
  log "Collecting system facts"
  run_shell "$OUT_DIR/system/basic.txt" 'date; whoami; id; hostname; uname -a; printf "\n--- os-release ---\n"; cat /etc/os-release 2>/dev/null || true'
  run_shell "$OUT_DIR/system/resources.txt" 'printf "\n--- lscpu ---\n"; lscpu 2>/dev/null || true; printf "\n--- memory ---\n"; free -h 2>/dev/null || true; printf "\n--- disk ---\n"; df -hT 2>/dev/null || df -h 2>/dev/null || true'
  run_shell "$OUT_DIR/system/mounts.txt" 'mount 2>/dev/null || cat /proc/mounts 2>/dev/null || true'
  run_shell "$OUT_DIR/system/limits.txt" 'ulimit -a 2>/dev/null || true; printf "\n--- cgroups ---\n"; cat /proc/self/cgroup 2>/dev/null || true'
}

collect_commands() {
  log "Collecting command availability"
  {
    for name in sh bash python python3 pip pip3 uv conda nvidia-smi ascend-smi npu-smi lspci ss netstat lsof curl wget gcc g++ make git java node npm; do
      if have "$name"; then
        printf '%-16s %s\n' "$name" "$(command -v "$name")"
      else
        printf '%-16s <missing>\n' "$name"
      fi
    done
  } >"$OUT_DIR/commands/which.txt" 2>&1

  run_shell "$OUT_DIR/commands/tool_versions.txt" 'python3 --version 2>/dev/null || true; python --version 2>/dev/null || true; pip3 --version 2>/dev/null || true; pip --version 2>/dev/null || true; uv --version 2>/dev/null || true; gcc --version 2>/dev/null | head -5 || true; git --version 2>/dev/null || true'
}

collect_env() {
  log "Collecting redacted environment"
  redact_env >"$OUT_DIR/env/env.redacted.txt" 2>"$OUT_DIR/env/env_errors.txt" || true
  grep -E "^(MODEL_|RAGENT_|RAG_|LLM_|EMBEDDING_|RERANK_|IMAGE_|ASCEND|ATB|VLLM|PYTHON|LD_|PATH=|WORKSPACE|MINERU|LITELLM|ENABLE_|TOP_K|CHUNK_TOP_K|MAX_|COSINE_|NEO4J_|MILVUS_)" \
    "$OUT_DIR/env/env.redacted.txt" >"$OUT_DIR/env/mep_env_focus.txt" 2>/dev/null || true
}

collect_python() {
  log "Collecting Python facts"
  run_shell "$OUT_DIR/python/python_interpreters.txt" 'for py in python3 python; do if command -v "$py" >/dev/null 2>&1; then echo "--- $py ---"; "$py" - <<'"'"'PY'"'"'
import json, os, platform, site, sys, sysconfig
payload = {
    "executable": sys.executable,
    "version": sys.version,
    "version_info": list(sys.version_info[:5]),
    "platform": platform.platform(),
    "machine": platform.machine(),
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "cwd": os.getcwd(),
    "path": sys.path,
    "site_packages": site.getsitepackages() if hasattr(site, "getsitepackages") else [],
    "user_site": site.getusersitepackages() if hasattr(site, "getusersitepackages") else "",
    "sysconfig_platform": sysconfig.get_platform(),
}
print(json.dumps(payload, indent=2, ensure_ascii=False))
PY
fi; done'

  run_shell "$OUT_DIR/python/pip_freeze.txt" 'if command -v python3 >/dev/null 2>&1; then python3 -m pip freeze --all 2>/dev/null || true; fi; if command -v pip3 >/dev/null 2>&1; then pip3 freeze --all 2>/dev/null || true; fi'
  run_shell "$OUT_DIR/python/relevant_package_versions.txt" 'python3 - <<'"'"'PY'"'"'
from importlib import metadata
names = [
    "ragent", "aiohttp", "fastapi", "httpx", "litellm", "networkx", "numpy",
    "openai", "pydantic", "requests", "tenacity", "tiktoken", "uvicorn",
    "torch", "transformers", "vllm", "vllm-ascend", "triton", "triton-ascend",
    "sentence-transformers", "nano-vectordb", "faiss-cpu", "pymilvus",
]
for name in names:
    try:
        print(f"{name}=={metadata.version(name)}")
    except metadata.PackageNotFoundError:
        print(f"{name}=<not installed>")
PY'
}

collect_component_files() {
  log "Collecting component source/config files"
  local seen_roots="|"
  for root in "$START_DIR" "$SCRIPT_DIR" "$SCRIPT_DIR/.." "$(dirname "$START_DIR")"; do
    [ -d "$root" ] || continue
    root="$(cd "$root" 2>/dev/null && pwd -P || printf '%s' "$root")"
    case "$seen_roots" in
      *"|$root|"*) continue ;;
    esac
    seen_roots="${seen_roots}${root}|"
    for file in config.json package.json pyproject.toml setup.py init.py process.py mep_dependency_bootstrap.py run_mep_local.py; do
      copy_if_exists "$root/$file" "$OUT_DIR/component/$(printf '%s' "$root" | sed 's#/#_#g')"
    done
  done

  run_shell "$OUT_DIR/component/start_dir_tree.txt" 'printf "PWD=%s\n\n" "$PWD"; find . -maxdepth 3 -mindepth 1 -printf "%M %u %g %s %TY-%Tm-%Td %TH:%TM %p\n" 2>/dev/null | sort | head -1000'
}

collect_mep_paths() {
  log "Collecting MEP path diagnostics"
  run_shell "$OUT_DIR/mep/path_probe.txt" 'python3 - <<'"'"'PY'"'"'
import json
import os
from pathlib import Path

def exists_payload(path):
    if not path:
        return {"path": "", "exists": False, "is_dir": False}
    p = Path(path).expanduser()
    try:
        resolved = p.resolve()
    except Exception:
        resolved = p
    return {
        "path": str(path),
        "resolved": str(resolved),
        "exists": resolved.exists(),
        "is_dir": resolved.is_dir(),
        "is_file": resolved.is_file(),
    }

cwd = Path.cwd().resolve()
candidates = {}
for name in [
    "MODEL_ABSOLUTE_DIR", "MODEL_RELATIVE_DIR", "RAGENT_MEP_MODEL_DIR",
    "RAGENT_MEP_DATA_DIR", "RAGENT_MEP_KG_DIR", "RAGENT_MEP_SNAPSHOT_DIR",
    "RAGENT_MEP_EMBEDDING_MODEL_PATH", "RAGENT_MEP_EMBEDDING_CONFIG_PATH",
    "path_appendix",
]:
    candidates[name] = exists_payload(os.getenv(name, ""))

model_sfs = os.getenv("MODEL_SFS", "")
model_object_id = os.getenv("MODEL_OBJECT_ID", "")
sfs_candidates = []
try:
    payload = json.loads(model_sfs) if model_sfs else {}
except Exception as exc:
    payload = {"_json_error": str(exc)}
if isinstance(payload, dict):
    base = payload.get("sfsBasePath")
    if isinstance(base, str) and model_object_id:
        root = Path(base).expanduser() / model_object_id
        for rel in ["", "model", "data", "meta"]:
            sfs_candidates.append(exists_payload(str(root / rel) if rel else str(root)))

component_parents = []
for candidate in [cwd, *cwd.parents]:
    if candidate.name == "component" or (candidate / "config.json").is_file():
        parent = candidate.parent
        component_parents.append({
            "component_candidate": str(candidate),
            "parent": str(parent),
            "model": exists_payload(parent / "model"),
            "data": exists_payload(parent / "data"),
            "meta": exists_payload(parent / "meta"),
        })

probe = None
try:
    import init
    probe = init.build_runtime_probe()
except Exception as exc:
    probe = {"error": repr(exc)}

print(json.dumps({
    "cwd": str(cwd),
    "model_sfs_raw_present": bool(model_sfs),
    "model_sfs_parsed": payload,
    "model_object_id": model_object_id,
    "env_path_candidates": candidates,
    "sfs_candidates": sfs_candidates,
    "component_parent_candidates": component_parents,
    "init_build_runtime_probe": probe,
}, indent=2, ensure_ascii=False, default=str))
PY'
}

collect_trees() {
  log "Collecting model/data/meta trees"
  run_shell "$OUT_DIR/mep/runtime_trees.txt" 'python3 - <<'"'"'PY'"'"'
import json, os
from pathlib import Path

def add_path(paths, value):
    if not value:
        return
    try:
        p = Path(value).expanduser().resolve()
    except Exception:
        p = Path(value).expanduser()
    if p not in paths:
        paths.append(p)

paths = []
cwd = Path.cwd().resolve()
for p in [cwd, cwd.parent, cwd.parent.parent if cwd.parent else cwd]:
    for name in ["model", "data", "meta", "component"]:
        add_path(paths, p / name)
for key in [
    "MODEL_ABSOLUTE_DIR", "RAGENT_MEP_MODEL_DIR", "RAGENT_MEP_DATA_DIR",
    "RAGENT_MEP_KG_DIR", "RAGENT_MEP_SNAPSHOT_DIR", "RAGENT_MEP_EMBEDDING_MODEL_PATH",
]:
    add_path(paths, os.getenv(key))

raw_sfs = os.getenv("MODEL_SFS", "")
object_id = os.getenv("MODEL_OBJECT_ID", "")
try:
    payload = json.loads(raw_sfs) if raw_sfs else {}
except Exception:
    payload = {}
if isinstance(payload, dict) and payload.get("sfsBasePath") and object_id:
    root = Path(payload["sfsBasePath"]).expanduser() / object_id
    for name in ["", "model", "data", "meta"]:
        add_path(paths, root / name if name else root)

for root in paths:
    print(f"\n===== {root} =====")
    print(f"exists={root.exists()} is_dir={root.is_dir()} is_file={root.is_file()}")
    if not root.is_dir():
        continue
    count = 0
    for child in sorted(root.rglob("*"), key=lambda p: str(p))[:1200]:
        try:
            stat = child.lstat()
            kind = "d" if child.is_dir() else "l" if child.is_symlink() else "f"
            rel = child.relative_to(root)
            print(f"{kind} {stat.st_size:>12} {rel}")
            count += 1
        except Exception as exc:
            print(f"? {child}: {exc}")
    if count >= 1200:
        print("[truncated after 1200 entries]")
PY'
}

collect_mep_runtime() {
  log "Collecting MEP runtime/tool state"
  run_shell "$OUT_DIR/mep/accelerator.txt" 'nvidia-smi 2>/dev/null || true; ascend-smi info 2>/dev/null || true; npu-smi info 2>/dev/null || true; lspci 2>/dev/null | grep -Ei "nvidia|huawei|ascend|gpu|npu" || true'
  run_shell "$OUT_DIR/mep/processes.txt" 'ps -ef 2>/dev/null | grep -Ei "python|vllm|uvicorn|gunicorn|mep|ascend|atb" | grep -v grep || true'
  run_shell "$OUT_DIR/mep/network_ports.txt" 'ss -lntup 2>/dev/null || netstat -lntup 2>/dev/null || lsof -i -P -n 2>/dev/null | head -200 || true'
  run_shell "$OUT_DIR/mep/local_embedding_endpoint.txt" 'for port in 8000 8080 9000; do echo "--- localhost:$port/v1/models ---"; curl -fsS --max-time 3 "http://127.0.0.1:$port/v1/models" 2>&1 || true; echo; done'
  run_shell "$OUT_DIR/mep/ascend_env_files.txt" 'for f in /usr/local/Ascend/ascend-toolkit/set_env.sh /usr/local/Ascend/nnal/atb/set_env.sh; do echo "--- $f ---"; if [ -f "$f" ]; then ls -l "$f"; sed -n "1,80p" "$f"; else echo "<missing>"; fi; done'
}

collect_manifests() {
  log "Collecting dependency/config manifests"
  run_shell "$OUT_DIR/mep/manifests.txt" 'find . /tmp /home /usr/local/Ascend -maxdepth 6 \( -name manifest.json -o -name embedding.properties -o -name "*.freeze.txt" -o -name "requirements*.txt" -o -name type.mf \) -type f 2>/dev/null | sort | head -500 | while read -r f; do echo "===== $f ====="; ls -l "$f" 2>/dev/null || true; sed -n "1,160p" "$f" 2>/dev/null || true; done'
}

create_archive() {
  log "Creating archive"
  if tar -czf "$ARCHIVE" -C "$(dirname "$OUT_DIR")" "$(basename "$OUT_DIR")" 2>"$OUT_DIR/logs/tar_errors.log"; then
    printf '%s\n' "$ARCHIVE" >"$OUT_DIR/ARCHIVE_PATH.txt"
    log "Archive created: $ARCHIVE"
  else
    log "Archive creation failed; output directory remains: $OUT_DIR"
  fi
}

main() {
  write_header
  collect_system
  collect_commands
  collect_env
  collect_python
  collect_component_files
  collect_mep_paths
  collect_trees
  collect_mep_runtime
  collect_manifests
  create_archive

  printf '\nDone.\nOutput directory: %s\nArchive: %s\n' "$OUT_DIR" "$ARCHIVE"
}

main "$@"
