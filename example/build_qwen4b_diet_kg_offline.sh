#!/usr/bin/env bash
# Strict offline KG build: shard export (raw JSONL) + replay -> example/qwen4b_diet_kg
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PYTHON="${ROOT}/.venv/bin/python"
RAW_DIR="${ROOT}/example/qwen4b_diet_kg_raw_units"
OUT_DIR="${ROOT}/example/qwen4b_diet_kg"
LOG="${ROOT}/example/qwen4b_diet_kg_build.log"

mkdir -p "$RAW_DIR"

declare -a JOBS=(
  "example/GBT1354-2018bz.pdf|example/GBT1354-2018bz_md"
  "example/GBT22106-2008dz.pdf|example/GBT22106-2008dz_md"
  "example/成人肥胖食养指南_2024.pdf|example/成人肥胖食养指南_2024_md"
  "example/成人高血压食养指南_2022.pdf|example/成人高血压食养指南_2022_md"
  "example/中国居民膳食指南_2022.pdf|example/中国居民膳食指南_2022_md"
)

echo "=== qwen4b_diet_kg strict offline build started $(date -Iseconds) ===" | tee -a "$LOG"
echo "RAW_DIR=$RAW_DIR" | tee -a "$LOG"
echo "OUT_DIR=$OUT_DIR" | tee -a "$LOG"
echo "LLM_MODEL=${LLM_MODEL:-<unset>}" | tee -a "$LOG"
echo "EMBEDDING_MODEL=${EMBEDDING_MODEL:-<unset>}" | tee -a "$LOG"

idx=0
total=${#JOBS[@]}
for job in "${JOBS[@]}"; do
  idx=$((idx + 1))
  pdf="${job%%|*}"
  mineru_dir="${job##*|}"
  stem="$(basename "$pdf" .pdf)"
  out_jsonl="${RAW_DIR}/${stem}.raw-units.jsonl"
  echo "" | tee -a "$LOG"
  echo "[$idx/$total] raw export: $pdf -> $out_jsonl ($(date -Iseconds))" | tee -a "$LOG"
  "$PYTHON" singlefile.py parse "$pdf" "$mineru_dir" "$RAW_DIR" raw 2>&1 | tee -a "$LOG"
  if [[ ! -s "$out_jsonl" ]]; then
    echo "ERROR: missing or empty raw units: $out_jsonl" | tee -a "$LOG"
    exit 1
  fi
done

echo "" | tee -a "$LOG"
echo "=== replay raw units -> $OUT_DIR ($(date -Iseconds)) ===" | tee -a "$LOG"
"$PYTHON" tools/replay_raw_merge_units_to_project.py "$RAW_DIR" -o "$OUT_DIR" --overwrite 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== build finished $(date -Iseconds) ===" | tee -a "$LOG"
if [[ -f "$OUT_DIR/graph_chunk_entity_relation.graphml" ]]; then
  wc -c "$OUT_DIR/graph_chunk_entity_relation.graphml" | tee -a "$LOG"
else
  echo "WARN: graph file not found under $OUT_DIR" | tee -a "$LOG"
  exit 1
fi
