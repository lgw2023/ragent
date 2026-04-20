#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RUNTIME_DIR="$PROJECT_ROOT/.runtime"

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

PY_TAG="$("$PYTHON_BIN" - <<'PY'
import sys
print(f"py{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
PLATFORM_TAG="${PLATFORM_TAG:-$(normalize_os)-$(normalize_arch)-$PY_TAG}"
WHEELHOUSE="${WHEELHOUSE:-$PROJECT_ROOT/vendor/wheelhouse/$PLATFORM_TAG}"
REQ_FILE="$RUNTIME_DIR/requirements.offline.$PLATFORM_TAG.txt"

mkdir -p "$WHEELHOUSE" "$RUNTIME_DIR"

cd "$PROJECT_ROOT"
if command -v uv >/dev/null 2>&1; then
  uv export --format requirements-txt --no-hashes --output-file "$REQ_FILE"
  grep -vE '^-e[[:space:]]+(\.|file:)' "$REQ_FILE" > "$REQ_FILE.tmp"
  mv "$REQ_FILE.tmp" "$REQ_FILE"
else
  "$PYTHON_BIN" - <<'PY' > "$REQ_FILE"
from pathlib import Path
import sys

try:
    import tomllib
except ModuleNotFoundError:
    raise SystemExit("Python 3.11+ or uv is required to read pyproject.toml")

pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
for dep in pyproject["project"]["dependencies"]:
    print(dep)
PY
fi

"$PYTHON_BIN" -m pip wheel \
  --wheel-dir "$WHEELHOUSE" \
  --prefer-binary \
  --requirement "$REQ_FILE" \
  pip setuptools wheel
echo "wheelhouse written to $WHEELHOUSE"
