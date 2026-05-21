#!/usr/bin/env bash
# One-off wrapper: resume 239 missing raw units for 中国居民膳食指南_2022.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
exec "${ROOT}/.venv/bin/python" "${ROOT}/example/resume_diet_guide_2022_raw_units_once.py" "$@"
