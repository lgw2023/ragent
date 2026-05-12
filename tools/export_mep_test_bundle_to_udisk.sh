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
KEYWORD_MODEL_SRC="$MODEL_PACKAGE_SRC/modelDir/data/models/keyword_extraction/knowledgator-gliner-x-small"
KEYWORD_MODEL_DEST="$MODEL_PACKAGE_DEST/modelDir/data/models/keyword_extraction/knowledgator-gliner-x-small"
KEYWORD_WHEELHOUSE_SRC="$MODEL_PACKAGE_SRC/modelDir/data/deps/keyword_wheelhouse/$PLATFORM_TAG"
KEYWORD_WHEELHOUSE_DEST="$MODEL_PACKAGE_DEST/modelDir/data/deps/keyword_wheelhouse/$PLATFORM_TAG"

safe_prepare_dest

require_dir "$PROJECT_ROOT/ragent"
require_dir "$MODEL_PACKAGE_SRC"
require_dir "$WHEELHOUSE_SRC"
require_dir "$KEYWORD_MODEL_SRC"
require_dir "$KEYWORD_WHEELHOUSE_SRC"

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
  mep_site_packages.py \
  mep_package_utils.py \
  export_mep_keyword_fallback_assets.py \
  export_mep_test_bundle_to_udisk.sh \
  export_mep_vllm_ascend_wheelhouse.py \
  validate_mep_full_chain_result.py
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

# Ensure zip-unsafe startup wheels such as LiteLLM are available as real
# site-packages directories before copying the model package.
python "$PROJECT_ROOT/tools/mep_site_packages.py" \
  --model-dir-root "$MODEL_PACKAGE_SRC/modelDir" \
  --platform-tag "$PLATFORM_TAG"

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

"$PYTHON_BIN" - \
  "$WHEELHOUSE_SRC" \
  "$WHEELHOUSE_DEST" \
  "$DEST" \
  "$KEYWORD_MODEL_SRC" \
  "$KEYWORD_MODEL_DEST" \
  "$KEYWORD_WHEELHOUSE_SRC" \
  "$KEYWORD_WHEELHOUSE_DEST" <<'PY'
from pathlib import Path
import hashlib
import sys
import zipfile

wheelhouse_src = Path(sys.argv[1])
wheelhouse_dest = Path(sys.argv[2])
dest = Path(sys.argv[3])
keyword_model_src = Path(sys.argv[4])
keyword_model_dest = Path(sys.argv[5])
keyword_wheelhouse_src = Path(sys.argv[6])
keyword_wheelhouse_dest = Path(sys.argv[7])


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def visible_files(root: Path) -> dict[str, dict[str, object]]:
    return {
        item.name: {
            "size": item.stat().st_size,
            "sha256": file_sha256(item),
        }
        for item in root.iterdir()
        if item.is_file() and not item.name.startswith("._")
    }


def validate_wheels(root: Path, label: str) -> None:
    invalid: list[str] = []
    for wheel_path in sorted(root.glob("*.whl")):
        if wheel_path.name.startswith("._"):
            continue
        try:
            with zipfile.ZipFile(wheel_path) as wheel:
                corrupt_member = wheel.testzip()
        except (OSError, zipfile.BadZipFile) as exc:
            invalid.append(f"{wheel_path.name}: {exc}")
            continue
        if corrupt_member is not None:
            invalid.append(f"{wheel_path.name}: corrupt archive member {corrupt_member}")
    if invalid:
        raise SystemExit(
            f"{label} contains invalid wheel files under {root}\n"
            + "\n".join(f"- {detail}" for detail in invalid[:20])
        )


src_files = visible_files(wheelhouse_src)
dest_files = visible_files(wheelhouse_dest)
missing = sorted(set(src_files) - set(dest_files))
extra = sorted(set(dest_files) - set(src_files))
size_mismatch = sorted(
    name
    for name in set(src_files) & set(dest_files)
    if src_files[name]["size"] != dest_files[name]["size"]
)
hash_mismatch = sorted(
    name
    for name in set(src_files) & set(dest_files)
    if src_files[name]["sha256"] != dest_files[name]["sha256"]
)
if missing or extra or size_mismatch or hash_mismatch:
    raise SystemExit(
        "wheelhouse verification failed\n"
        f"missing={missing[:20]}\n"
        f"extra={extra[:20]}\n"
        f"size_mismatch={size_mismatch[:20]}\n"
        f"hash_mismatch={hash_mismatch[:20]}"
    )
validate_wheels(wheelhouse_src, "source wheelhouse")
validate_wheels(wheelhouse_dest, "exported wheelhouse")

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
    if root_files[name]["size"] != source_size["size"]:
        raise SystemExit(f"root repair wheel size mismatch: {name}")
    if root_files[name]["sha256"] != source_size["sha256"]:
        raise SystemExit(f"root repair wheel hash mismatch: {name}")
validate_wheels(dest, "root repair wheel directory")

for required_name in ("gliner_config.json", "tokenizer_config.json"):
    source_file = keyword_model_src / required_name
    dest_file = keyword_model_dest / required_name
    if not source_file.is_file():
        raise SystemExit(f"keyword model source missing required file: {source_file}")
    if not dest_file.is_file():
        raise SystemExit(f"keyword model dest missing required file: {dest_file}")
if not (
    (keyword_model_dest / "model.safetensors").is_file()
    or (keyword_model_dest / "pytorch_model.bin").is_file()
):
    raise SystemExit(f"keyword model missing weights under {keyword_model_dest}")

keyword_src_files = visible_files(keyword_wheelhouse_src)
keyword_dest_files = visible_files(keyword_wheelhouse_dest)
keyword_missing = sorted(set(keyword_src_files) - set(keyword_dest_files))
keyword_extra = sorted(set(keyword_dest_files) - set(keyword_src_files))
keyword_size_mismatch = sorted(
    name
    for name in set(keyword_src_files) & set(keyword_dest_files)
    if keyword_src_files[name]["size"] != keyword_dest_files[name]["size"]
)
keyword_hash_mismatch = sorted(
    name
    for name in set(keyword_src_files) & set(keyword_dest_files)
    if keyword_src_files[name]["sha256"] != keyword_dest_files[name]["sha256"]
)
if keyword_missing or keyword_extra or keyword_size_mismatch or keyword_hash_mismatch:
    raise SystemExit(
        "keyword wheelhouse verification failed\n"
        f"missing={keyword_missing[:20]}\n"
        f"extra={keyword_extra[:20]}\n"
        f"size_mismatch={keyword_size_mismatch[:20]}\n"
        f"hash_mismatch={keyword_hash_mismatch[:20]}"
    )
validate_wheels(keyword_wheelhouse_src, "source keyword wheelhouse")
validate_wheels(keyword_wheelhouse_dest, "exported keyword wheelhouse")
for prefix in ("gliner-", "stanza-", "onnxruntime-", "langdetect-"):
    matches = [
        name
        for name in keyword_dest_files
        if name.startswith(prefix) and name.endswith(".whl")
    ]
    if not matches:
        raise SystemExit(f"keyword wheelhouse missing required wheel prefix: {prefix}")

print(f"verified wheelhouse files: {len(src_files)}")
print(f"verified keyword wheelhouse files: {len(keyword_src_files)}")
print(f"verified keyword model: {keyword_model_dest}")
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
