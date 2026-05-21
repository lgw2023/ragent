#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_DIR="$REPO_ROOT/mep/model_packages/qwen3-embedding-4b/modelDir/model"
DEFAULT_SOURCE="${HF_HOME:-$HOME/.cache/huggingface}/hub/models--Qwen--Qwen3-Embedding-4B/snapshots/5cf2132abc99cad020ac570b19d031efec650f2b"
SOURCE="${1:-$DEFAULT_SOURCE}"

if [ ! -d "$SOURCE" ]; then
  echo "missing Qwen3-Embedding-4B snapshot: $SOURCE" >&2
  exit 1
fi
if [ ! -f "$SOURCE/config.json" ] || [ ! -f "$SOURCE/tokenizer.json" ]; then
  echo "snapshot does not look like a Hugging Face model dir: $SOURCE" >&2
  exit 1
fi

mkdir -p "$(dirname "$MODEL_DIR")"
ln -sfn "$SOURCE" "$MODEL_DIR"
echo "linked $MODEL_DIR -> $SOURCE"
