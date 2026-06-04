# FoodScience KG Latency ANN Remote Task

Date: 2026-06-04

This task is for the AI assistant running on the remote server that hosts the
large FoodScience knowledge graph. Do not run the experiment on a local machine
that does not have the graph files.

## Objective

Validate whether switching the relationships vector index from exact FAISS
`flat` to ANN `hnsw` can reduce retrieval latency enough for the large
FoodScience KG.

Primary question:

- Does `relationships` HNSW reduce `graph_relation_vector_index_search` from the
  current FAISS exact baseline of about 4.8 s to near or below 1.5 s without an
  obvious retrieval-quality regression?

Secondary question:

- After HNSW, is the remaining latency mostly vector retrieval, keyword
  extraction, rerank, or answer generation?

## Known Baseline

Remote project path:

```text
/data/disk3/FoodScience_KG_final_sharded
```

Existing one-query comparison reported by the user:

| Metric | FAISS sidecar `:8099` | Nano `:8101` | Ratio |
| --- | ---: | ---: | ---: |
| client wall clock | 22.77 s | 76.50 s | 3.36x |
| request_processing_seconds | 22.76 s | 76.49 s | 3.36x |
| onehop_total / query_seconds | 22.73 s | 76.45 s | 3.36x |
| hybrid_retrieval_total | 13.41 s | 63.10 s | 4.71x |
| answer_generation | 9.12 s | 13.11 s | 1.44x |
| relationships vector index search | 4.80 s | 47.98 s | about 10x |
| entities vector index search | 2.95 s | 9.80 s | about 3.3x |
| rerank | 0.96 s | 1.01 s | similar |
| reference_chunk_count | 10 | 10 | same |
| referenced_file_paths | 17 | 17 | same |

Interpretation:

- FAISS sidecar is already much faster than Nano.
- The current FAISS sidecar may still be exact `flat`.
- Full answer latency is still about 23 s, so ANN alone may not make the full
  chain less than 10 s because keyword extraction and answer generation are
  still significant.

## Non-goals

- Do not rebuild the knowledge graph.
- Do not re-run parsing, extraction, chunking, embedding, or graph construction.
- Do not change production code unless the existing sidecar/HNSW code is missing
  or broken.
- Do not claim success from a single query. Use the 10-query set in
  `queries.jsonl`.

## Required Checks Before Running

From the remote repository checkout:

```bash
cd /path/to/ragent
git status --short
git log -1 --oneline
test -f tools/build_vector_sidecars.py
test -f ragent/kg/faiss_sidecar_impl.py
test -d /data/disk3/FoodScience_KG_final_sharded
```

Confirm FAISS is installed in the `uv` environment:

```bash
uv run --frozen --no-sync python - <<'PY'
import faiss
import numpy as np

vectors = np.eye(4, dtype=np.float32)
index = faiss.IndexFlatIP(4)
index.add(vectors)
scores, ids = index.search(vectors[:1], 2)
print("faiss:", faiss.__version__)
print("ids:", ids.tolist())
print("scores:", scores.tolist())
PY
```

If that fails because the environment is not synced:

```bash
uv sync --frozen --no-dev --extra faiss --extra api
```

## Step 1: Identify Existing Services And Sidecars

If ports `8099` and `8101` are already running, preserve them as baselines:

- `:8099`: expected FAISS sidecar baseline.
- `:8101`: expected Nano baseline.
- new `:8102`: use for HNSW relationship sidecar.

Inspect the exact sidecar manifest used by the FAISS service. If the path is
unknown, inspect the service process environment:

```bash
ps eww -p "$(pgrep -f 'ragent.api.benchmark_service.*8099' | head -1)" \
  | tr ' ' '\n' \
  | rg 'RAG_VECTOR|RAG_PRELOAD|PORT|HOST'
```

Then check the manifest:

```bash
SIDECAR_DIR=/path/to/current/faiss_sidecar
jq -r '.namespaces | to_entries[] | "\(.key)\t\(.value.index_type)\t\(.value.count)\t\(.value.search_params)"' \
  "$SIDECAR_DIR/manifest.json"
```

Record whether `relationships` is `flat`, `hnsw`, or `ivf_flat` in
`RESULTS_TEMPLATE.md`.

## Step 2: Build A Relationships-HNSW Sidecar

Build all namespaces, but keep `chunks` and `entities` exact. Only override
`relationships` to HNSW.

```bash
PROJECT_DIR=/data/disk3/FoodScience_KG_final_sharded
OUTPUT_FINAL=/data/disk3/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef128
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
  --relationships-index-type hnsw \
  --hnsw-m 16 \
  --hnsw-ef-construction 200 \
  --hnsw-ef-search 128

test -f "$OUTPUT_TMP/manifest.json"
jq -r '.namespaces | to_entries[] | "\(.key)\t\(.value.index_type)\t\(.value.count)\t\(.value.search_params)"' \
  "$OUTPUT_TMP/manifest.json"
du -sh "$OUTPUT_TMP"
mv "$OUTPUT_TMP" "$OUTPUT_FINAL"
```

If build memory is insufficient, stop and report the failure. Do not delete the
source project.

## Step 3: Start HNSW Benchmark Service

Start the HNSW service on a separate port. Keep the exact FAISS and Nano
services running if possible.

```bash
PROJECT_DIR=/data/disk3/FoodScience_KG_final_sharded
HNSW_SIDECAR=/data/disk3/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef128

export RAG_VECTOR_RUNTIME_BACKEND=faiss_sidecar
export RAG_VECTOR_SIDECAR_DIR="$HNSW_SIDECAR"
export RAG_PRELOAD_PROJECT_DIRS="$PROJECT_DIR"

uv run --frozen --no-sync python -m ragent.api.benchmark_service \
  --host 127.0.0.1 \
  --port 8102
```

In another shell:

```bash
curl -sS http://127.0.0.1:8102/health | jq .
```

The health payload should list `/data/disk3/FoodScience_KG_final_sharded` under
`loaded_projects` after preload finishes.

## Step 4: Run Experiments

Run these service variants:

| Variant | URL | Purpose |
| --- | --- | --- |
| Nano | `http://127.0.0.1:8101` | slow baseline |
| FAISS exact | `http://127.0.0.1:8099` | current improved baseline |
| FAISS relationships HNSW | `http://127.0.0.1:8102` | candidate |

For each variant, run:

1. `retrieval_only=true`, `enable_rerank=true`, `include_trace=true`.
2. Full chain with `retrieval_only=false`, `enable_rerank=true`,
   `include_trace=true`.

Use `queries.jsonl` as the query set. Add a different meaningless cache-buster
suffix per request, for example `#cb-hnsw-q01-r01`, so query cache does not hide
backend differences. Record `cache_hit_count`; it should be `0` for cold-cache
comparisons.

If you write a small runner, save all raw JSON responses under:

```text
benchmark/foodscience_kg_latency_ann_YYYYMMDD_HHMM/
```

Minimum runs:

- 10 queries x 3 variants x retrieval-only = 30 requests.
- 10 queries x 3 variants x full-chain = 30 requests, if LLM cost and time are
  acceptable.

If full-chain cost is too high, run full-chain on at least 3 representative
queries and explain why the full 10-query set was skipped.

## Metrics To Extract

For every response, record:

- `request_processing_seconds`
- `query_seconds`
- `cache_hit_count`
- `project_first_request`
- `reference_chunk_count`
- `len(referenced_file_paths)`
- answer length for full-chain runs

From `stage_timings`, sum seconds by `stage` for at least:

- `hybrid_retrieval_total`
- `graph_relation_vector_index_search`
- `graph_entity_vector_index_search`
- `chunks_vector_index_search`
- `vector_retrieval`
- `rerank`
- `keyword_extraction`
- `answer_generation`

Also preserve top retrieval evidence for quality checks:

- final context chunk IDs from `trace.final_context_document_chunks`
- `referenced_file_paths`
- any relationship/entity hit IDs present in the trace

## Success Criteria

Treat this as a staged decision, not a yes/no from one query.

HNSW is a good candidate if:

- `relationships` manifest shows `index_type=hnsw`.
- Median `graph_relation_vector_index_search` is below 1.5 s.
- p95 `graph_relation_vector_index_search` is materially below exact FAISS.
- `hybrid_retrieval_total` improves over exact FAISS by at least 25 percent.
- `reference_chunk_count` stays non-zero and comparable.
- Final context chunk overlap with exact FAISS is not obviously broken.

HNSW is not ready if:

- relationship search is still close to exact FAISS timing.
- returned context collapses to irrelevant chunks.
- many responses show cache hits during cold-cache comparison.
- service logs show fallback to Nano or failure to load the HNSW sidecar.

If HNSW is faster but quality looks weaker, run one more HNSW sidecar with higher
search breadth:

```bash
--relationships-index-type hnsw \
--hnsw-m 16 \
--hnsw-ef-construction 200 \
--hnsw-ef-search 256
```

If HNSW quality is fine and speed is still not enough, try lower search breadth:

```bash
--relationships-index-type hnsw \
--hnsw-m 16 \
--hnsw-ef-construction 200 \
--hnsw-ef-search 64
```

## Required Output From Remote Assistant

Fill `RESULTS_TEMPLATE.md` with:

1. Environment and code version.
2. Exact, Nano, and HNSW service configuration.
3. Sidecar manifest summaries.
4. Build time and disk size for HNSW sidecar.
5. Retrieval-only latency table.
6. Full-chain latency table, if run.
7. Stage timing breakdown.
8. Quality/overlap notes against exact FAISS.
9. Decision: keep exact FAISS, promote HNSW, or run another HNSW/IVF sweep.
10. Paths to raw JSON outputs.

Do not just write a prose conclusion. Attach the raw JSON path and enough table
data for another person to verify the claim.
