#!/usr/bin/env bash
set -euo pipefail

# Export the offline MEP/vLLM test bundle used by
# MEP_platform_rule/Validated_ragent-mep-test_docker_vllm.sh.
#
# The target host/container is assumed to have no working pip index access.
# Do not export source files alone: the full platform wheelhouse and the
# root-level vLLM repair wheels are part of the test contract.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
DEST="${DEST:-/Volumes/Udisk2/ragent-mep-test}"
MODEL_PACKAGE="${MODEL_PACKAGE:-bge-m3}"
PLATFORM_TAG="${PLATFORM_TAG:-linux-arm64-py3.10}"

RSYNC_EXCLUDES=(
  --exclude "__pycache__/"
  --exclude ".pytest_cache/"
  --exclude ".DS_Store"
  --exclude "._*"
  --exclude "*.pyc"
  --exclude "*.pyo"
)

REPAIR_WHEEL_PATTERNS=(
  "triton_ascend-3.2.0*.whl"
  "vllm-0.13.0*.whl"
  "vllm_ascend-0.13.0*.whl"
)

die() {
  echo "error: $*" >&2
  exit 1
}

resolve_path() {
  "$PYTHON_BIN" - "$1" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).expanduser().resolve())
PY
}

require_file() {
  [ -f "$1" ] || die "missing required file: $1"
}

require_dir() {
  [ -d "$1" ] || die "missing required directory: $1"
}

rsync_file() {
  local source="$1"
  local target_dir="$2"
  require_file "$source"
  mkdir -p "$target_dir"
  COPYFILE_DISABLE=1 rsync -a "$source" "$target_dir/"
}

rsync_dir() {
  local source="$1"
  local target="$2"
  require_dir "$source"
  mkdir -p "$target"
  COPYFILE_DISABLE=1 rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$source/" "$target/"
}

single_match_for_pattern() {
  local pattern="$1"
  local matches=()
  while IFS= read -r path; do
    matches+=("$path")
  done < <(find "$WHEELHOUSE_SRC" -maxdepth 1 -type f -name "$pattern" -print | sort)

  if [ "${#matches[@]}" -ne 1 ]; then
    printf 'error: expected exactly one wheel for pattern %s under %s, found %s\n' \
      "$pattern" "$WHEELHOUSE_SRC" "${#matches[@]}" >&2
    printf 'matches:\n' >&2
    printf '  %s\n' "${matches[@]:-}" >&2
    exit 1
  fi
  printf '%s\n' "${matches[0]}"
}

safe_prepare_dest() {
  local dest_resolved project_resolved
  dest_resolved="$(resolve_path "$DEST")"
  project_resolved="$(resolve_path "$PROJECT_ROOT")"

  if [ "$dest_resolved" = "/" ]; then
    die "DEST must not be filesystem root"
  fi
  if [ "$dest_resolved" = "$project_resolved" ]; then
    die "DEST must not be the source repository"
  fi
  case "$dest_resolved" in
    "$project_resolved"/*)
      die "DEST must not be inside the source repository: $dest_resolved"
      ;;
  esac

  mkdir -p "$DEST"
}

MODEL_PACKAGE_SRC="$PROJECT_ROOT/mep/model_packages/$MODEL_PACKAGE"
MODEL_PACKAGE_DEST="$DEST/mep/model_packages/$MODEL_PACKAGE"
WHEELHOUSE_SRC="$MODEL_PACKAGE_SRC/modelDir/data/deps/wheelhouse/$PLATFORM_TAG"
WHEELHOUSE_DEST="$MODEL_PACKAGE_DEST/modelDir/data/deps/wheelhouse/$PLATFORM_TAG"

safe_prepare_dest

require_dir "$PROJECT_ROOT/ragent"
require_dir "$MODEL_PACKAGE_SRC"
require_dir "$WHEELHOUSE_SRC"

echo "Exporting offline MEP test bundle"
echo "  source: $PROJECT_ROOT"
echo "  dest:   $DEST"
echo "  model:  $MODEL_PACKAGE"
echo "  tag:    $PLATFORM_TAG"

for path in \
  config.json \
  package.json \
  process.py \
  init.py \
  mep_dependency_bootstrap.py \
  pyproject.toml \
  setup.py \
  run_mep_local.py
do
  if [ -f "$PROJECT_ROOT/$path" ]; then
    rsync_file "$PROJECT_ROOT/$path" "$DEST"
  fi
done

rsync_dir "$PROJECT_ROOT/ragent" "$DEST/ragent"

mkdir -p "$DEST/tools"
for path in \
  build_mep_layout.py \
  build_mep_upload_packages.py \
  mep_package_utils.py \
  export_mep_test_bundle_to_udisk.sh \
  export_mep_vllm_ascend_wheelhouse.py
do
  if [ -f "$PROJECT_ROOT/tools/$path" ]; then
    rsync_file "$PROJECT_ROOT/tools/$path" "$DEST/tools"
  fi
done

if [ -d "$PROJECT_ROOT/example/mep_requests" ]; then
  rsync_dir "$PROJECT_ROOT/example/mep_requests" "$DEST/example/mep_requests"
fi

mkdir -p "$DEST/MEP_platform_rule"
for path in \
  Validated_ragent-mep-test_docker_vllm.sh \
  Validated_ragent-mep-test_docker_full_chain.sh \
  Validated_ragent-mep-test_docker_vllm_requirements.freeze.txt
do
  if [ -f "$PROJECT_ROOT/MEP_platform_rule/$path" ]; then
    rsync_file "$PROJECT_ROOT/MEP_platform_rule/$path" "$DEST/MEP_platform_rule"
  fi
done

# This intentionally includes the HF model files, KG snapshot, dependency
# wheelhouse, source archives, and any pre-expanded site-packages.
rsync_dir "$MODEL_PACKAGE_SRC" "$MODEL_PACKAGE_DEST"

# The validation script installs these from /tmp/ragent-mep-test directly.
REPAIR_WHEEL_PATHS=()
REPAIR_WHEEL_NAMES=()
for pattern in "${REPAIR_WHEEL_PATTERNS[@]}"; do
  wheel_path="$(single_match_for_pattern "$pattern")"
  REPAIR_WHEEL_PATHS+=("$wheel_path")
  REPAIR_WHEEL_NAMES+=("$(basename "$wheel_path")")
done

while IFS= read -r existing_wheel; do
  existing_name="$(basename "$existing_wheel")"
  keep=0
  for desired_name in "${REPAIR_WHEEL_NAMES[@]}"; do
    if [ "$existing_name" = "$desired_name" ]; then
      keep=1
      break
    fi
  done
  if [ "$keep" -eq 0 ]; then
    rm -f "$existing_wheel"
  fi
done < <(find "$DEST" -maxdepth 1 -type f \( \
  -name 'triton_ascend-3.2.0*.whl' -o \
  -name 'vllm-0.13.0*.whl' -o \
  -name 'vllm_ascend-0.13.0*.whl' -o \
  -name '._triton_ascend-3.2.0*.whl' -o \
  -name '._vllm-0.13.0*.whl' -o \
  -name '._vllm_ascend-0.13.0*.whl' \
\) -print)

for wheel_path in "${REPAIR_WHEEL_PATHS[@]}"; do
  COPYFILE_DISABLE=1 rsync -a --size-only "$wheel_path" "$DEST/"
done

find "$DEST" -name '._*' -delete

"$PYTHON_BIN" - "$WHEELHOUSE_SRC" "$WHEELHOUSE_DEST" "$DEST" <<'PY'
from pathlib import Path
import sys

wheelhouse_src = Path(sys.argv[1])
wheelhouse_dest = Path(sys.argv[2])
dest = Path(sys.argv[3])


def visible_files(root: Path) -> dict[str, int]:
    return {
        item.name: item.stat().st_size
        for item in root.iterdir()
        if item.is_file() and not item.name.startswith("._")
    }


src_files = visible_files(wheelhouse_src)
dest_files = visible_files(wheelhouse_dest)
missing = sorted(set(src_files) - set(dest_files))
extra = sorted(set(dest_files) - set(src_files))
size_mismatch = sorted(
    name
    for name in set(src_files) & set(dest_files)
    if src_files[name] != dest_files[name]
)
if missing or extra or size_mismatch:
    raise SystemExit(
        "wheelhouse verification failed\n"
        f"missing={missing[:20]}\n"
        f"extra={extra[:20]}\n"
        f"size_mismatch={size_mismatch[:20]}"
    )

required_root_wheels = [
    "triton_ascend-3.2.0",
    "vllm-0.13.0",
    "vllm_ascend-0.13.0",
]
root_files = visible_files(dest)
for prefix in required_root_wheels:
    matches = [name for name in root_files if name.startswith(prefix) and name.endswith(".whl")]
    if len(matches) != 1:
        raise SystemExit(f"expected one root repair wheel for {prefix}, found {matches}")
    name = matches[0]
    source_size = src_files.get(name)
    if source_size is None:
        raise SystemExit(f"root repair wheel is not present in wheelhouse: {name}")
    if root_files[name] != source_size:
        raise SystemExit(f"root repair wheel size mismatch: {name}")

print(f"verified wheelhouse files: {len(src_files)}")
print("verified root repair wheels:")
for prefix in required_root_wheels:
    name = next(
        name
        for name in root_files
        if name.startswith(prefix) and name.endswith(".whl")
    )
    print(f"  {name} ({root_files[name]} bytes)")
PY

FAILED_REQUIREMENTS="$WHEELHOUSE_DEST/failed-requirements.txt"
if [ -s "$FAILED_REQUIREMENTS" ]; then
  echo
  echo "warning: wheelhouse exporter recorded unresolved requirements:"
  sed -n '1,80p' "$FAILED_REQUIREMENTS"
fi

du -sh "$DEST" "$WHEELHOUSE_DEST"
echo "offline MEP test bundle exported to $DEST"
