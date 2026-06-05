# FoodScience KG Retrieval Scale-up Remote Task

Date: 2026-06-05

This task continues the FoodScience KG performance work after relationships HNSW
proved effective. Full answer generation is out of scope here because it is
dominated by external LLM inference. Measure only retrieval-layer behavior.

## Objectives

1. Test whether `entities` should also use ANN after `relationships` moved to
   HNSW.
2. Tune namespace-level HNSW `ef_search` for entities and relationships.
3. Validate retrieval-only p50/p95 on a larger 50-query set.
4. Measure user-facing retrieval-only behavior under concurrent requests.

Do not rebuild the KG. Build sidecars only from the existing vdb JSON files.

## Required Code Capability

This task requires `tools/build_vector_sidecars.py` to support:

```text
--entities-index-type
--entities-hnsw-ef-search
--relationships-hnsw-ef-search
```

If the remote checkout does not have these options, sync the latest repo first.

Quick check:

```bash
cd /data/disk3/ragent-20260604_105639
uv run --frozen --no-sync python tools/build_vector_sidecars.py --help \
  | rg 'entities-index-type|entities-hnsw-ef-search|relationships-hnsw-ef-search'
```

## Baselines

Use the previous completed experiment as the baseline:

| Variant | URL | Meaning |
| --- | --- | --- |
| `exact` | `http://127.0.0.1:8099` | chunks/entities/relationships all flat |
| `rel_hnsw_ef128` | `http://127.0.0.1:8102` | chunks flat, entities flat, relationships HNSW ef128 |

`rel_hnsw_ef128` is the current candidate default. New variants should beat it
on retrieval-only latency without losing final context chunks.

## Candidate Sidecars

Build at least one entities-HNSW candidate:

```bash
PROJECT_DIR=/data/disk3/FoodScience_KG_final_sharded
OUTPUT_FINAL=/data/disk3/FoodScience_KG_final_sharded_sidecar_ent_hnsw_e128_rel_hnsw_r128
OUTPUT_TMP="${OUTPUT_FINAL}_building"

test ! -e "$OUTPUT_FINAL" || {
  echo "Refusing to overwrite existing output: $OUTPUT_FINAL"
  exit 1
}

rm -rf "$OUTPUT_TMP"
time uv run --frozen --no-sync python tools/build_vector_sidecars.py \
  --project-dir "$PROJECT_DIR" \
  --output-dir "$OUTPUT_TMP" \
  --index-type flat \
  --entities-index-type hnsw \
  --entities-hnsw-ef-search 128 \
  --relationships-index-type hnsw \
  --relationships-hnsw-ef-search 128 \
  --hnsw-m 16 \
  --hnsw-ef-construction 200

test -f "$OUTPUT_TMP/manifest.json"
jq -r '.namespaces | to_entries[] | "\(.key)\t\(.value.index_type)\t\(.value.count)\t\(.value.search_params)"' \
  "$OUTPUT_TMP/manifest.json"
du -sh "$OUTPUT_TMP"
mv "$OUTPUT_TMP" "$OUTPUT_FINAL"
```

Optional search profiles:

- `entities ef64 + relationships ef128`
- `entities ef256 + relationships ef128`
- `entities ef128 + relationships ef256` only if referenced-file alignment
  regresses.

For HNSW `ef_search` changes, the FAISS index does not need to be rebuilt; a
hardlink copy plus manifest patch is acceptable if the remote assistant records
the exact command.

## Start Candidate Services

Example:

```bash
PROJECT_DIR=/data/disk3/FoodScience_KG_final_sharded
SIDECAR=/data/disk3/FoodScience_KG_final_sharded_sidecar_ent_hnsw_e128_rel_hnsw_r128

export RAG_VECTOR_RUNTIME_BACKEND=faiss_sidecar
export RAG_VECTOR_SIDECAR_DIR="$SIDECAR"
export RAG_PRELOAD_PROJECT_DIRS="$PROJECT_DIR"

uv run --frozen --no-sync python -m ragent.api.benchmark_service \
  --host 127.0.0.1 \
  --port 8110
```

Use one port per candidate. Keep `:8099` and `:8102` running for exact and
current-default comparisons.

## Run Retrieval-only Scale-up

Primary run:

```bash
OUT=benchmark/foodscience_kg_retrieval_scaleup_$(date +%Y%m%d_%H%M)

uv run --frozen --no-sync python tasks/foodscience_kg_retrieval_scaleup/run_retrieval_only_scaleup.py \
  --project-dir /data/disk3/FoodScience_KG_final_sharded \
  --queries-file tasks/foodscience_kg_retrieval_scaleup/queries_50.jsonl \
  --output-dir "$OUT" \
  --variant exact=http://127.0.0.1:8099 \
  --variant rel_hnsw_ef128=http://127.0.0.1:8102 \
  --variant ent_hnsw_e128_rel_hnsw_r128=http://127.0.0.1:8110 \
  --baseline-variant exact \
  --concurrency-levels 1,2,4,8 \
  --repeats 1 \
  --enable-rerank true \
  --request-timeout 900
```

Notes:

- The benchmark service serializes same-project queries through a session lock,
  so concurrency measures user-facing queuing plus retrieval runtime, not raw
  FAISS index parallelism.
- If external rerank is unstable under concurrency, keep the primary run with
  `enable_rerank=true` for comparability and add a secondary run with
  `--enable-rerank false`.
- Every request appends a unique cache-buster. Cold-cache comparisons still must
  check `cache_hit_count=0`.

## Metrics To Decide

Promote entities HNSW only if it improves the current default:

| Gate | Required |
| --- | --- |
| cache hits | `0` for cold-cache comparisons |
| final chunk overlap vs exact | no broad drop; investigate any query below 8/10 |
| median entity index | materially lower than 2.1 s |
| retrieval-only median vs `rel_hnsw_ef128` | lower |
| retrieval-only p95 vs `rel_hnsw_ef128` | lower or not worse |
| concurrency error rate | no systematic 5xx/timeout increase |

If entities HNSW does not improve p95, keep entities flat and focus on
keyword extraction, rerank, or service-level queuing in later work.

## Required Output

Fill `RESULTS_TEMPLATE.md` after running:

1. Environment and exact code commit.
2. Sidecar manifests for all variants.
3. Build time and disk size for each candidate.
4. Sequential 50-query retrieval-only p50/p95.
5. Concurrent retrieval-only p50/p95 at concurrency 2/4/8.
6. Stage breakdown, especially entity index and relation index.
7. Quality overlap vs exact and vs current `rel_hnsw_ef128`.
8. Decision: promote entities HNSW, keep entities flat, or run another sweep.
9. Raw artifact paths.
