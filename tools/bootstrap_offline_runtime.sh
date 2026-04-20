#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/.venv}"
WHEELHOUSE_BASE="$PROJECT_ROOT/vendor/wheelhouse"

normalize_os() {
  case "$(uname -s | tr '[:upper:]' '[:lower:]')" in
    linux*) echo "linux" ;;
    darwin*) echo "darwin" ;;
    *) uname -s | tr '[:upper:]' '[:lower:]' ;;
  esac
}

normalize_arch() {
  case "$(uname -m)" in
    x86_64 | amd64) echo "amd64" ;;
    aarch64 | arm64) echo "arm64" ;;
    *) uname -m ;;
  esac
}

python_tag() {
  "$PYTHON_BIN" - <<'PY'
import sys
print(f"py{sys.version_info.major}.{sys.version_info.minor}")
PY
}

has_wheels() {
  [ -d "$1" ] && find "$1" -maxdepth 1 -name '*.whl' -print -quit | grep -q .
}

PLATFORM_TAG="${PLATFORM_TAG:-$(normalize_os)-$(normalize_arch)-$(python_tag)}"
if [ -z "${WHEELHOUSE+x}" ]; then
  WHEELHOUSE="$WHEELHOUSE_BASE/$PLATFORM_TAG"
  if ! has_wheels "$WHEELHOUSE" && has_wheels "$WHEELHOUSE_BASE"; then
    WHEELHOUSE="$WHEELHOUSE_BASE"
  fi
fi

cd "$PROJECT_ROOT"

"$PYTHON_BIN" tools/offline_runtime.py configure

if ! has_wheels "$WHEELHOUSE"; then
  echo "missing offline wheelhouse: $WHEELHOUSE" >&2
  echo "Expected platform tag: $PLATFORM_TAG" >&2
  if [ -d "$WHEELHOUSE_BASE" ]; then
    echo "Available wheelhouses:" >&2
    find "$WHEELHOUSE_BASE" -mindepth 1 -maxdepth 1 -type d -print >&2
  fi
  echo "Build it on a target-compatible online machine with tools/build_wheelhouse.sh." >&2
  exit 1
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -m pip --version >/dev/null 2>&1; then
  "$VENV_DIR/bin/python" -m ensurepip --upgrade
fi

"$VENV_DIR/bin/python" -m pip install --no-index --find-links "$WHEELHOUSE" --upgrade pip setuptools wheel
"$VENV_DIR/bin/python" -m pip install --no-index --find-links "$WHEELHOUSE" -e .
"$VENV_DIR/bin/python" tools/offline_runtime.py check

echo "offline runtime is ready"
