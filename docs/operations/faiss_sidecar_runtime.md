# FAISS Sidecar Runtime Runbook

This runbook accelerates inference over an existing Ragent project without
re-running parsing, extraction, embedding, or graph construction.

## Build Sidecars

Use the existing final project as the source. The command reads only
`vdb_chunks.json`, `vdb_entities.json`, and `vdb_relationships.json`.

```bash
uv run python tools/build_vector_sidecars.py \
  --project-dir /data/disk1/FoodScience_KG_final_sharded \
  --output-dir /data/disk1/FoodScience_KG_final_sharded_sidecar_exact \
  --index-type flat
```

If exact FAISS still misses the p95 target, keep chunks/entities exact and build
an ANN relationship index:

```bash
uv run python tools/build_vector_sidecars.py \
  --project-dir /data/disk1/FoodScience_KG_final_sharded \
  --output-dir /data/disk1/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef128 \
  --index-type flat \
  --relationships-index-type hnsw \
  --hnsw-m 16 \
  --hnsw-ef-search 128
```

## Run Benchmark Service

Enable the sidecar vector storage and preload the project at service startup:

```bash
export RAG_VECTOR_RUNTIME_BACKEND=faiss_sidecar
export RAG_VECTOR_SIDECAR_DIR=/data/disk1/FoodScience_KG_final_sharded_sidecar_exact
export RAG_PRELOAD_PROJECT_DIRS=/data/disk1/FoodScience_KG_final_sharded

uv run python -m ragent.api.benchmark_service --host 127.0.0.1 --port 8100
```

`RAG_PRELOAD_PROJECT_DIRS` removes first-query initialization from user-facing
latency. The service should report the project in `/health` under
`loaded_projects`.

## Compare Latency

Run the existing latency runner against both Nano and sidecar services. Keep
cache-cleared `steady_cold` as the main p95 gate.

```bash
uv run python tools/latency_runner.py \
  --service-url http://127.0.0.1:8100 \
  --project-dir /data/disk1/FoodScience_KG_final_sharded \
  --query "GB 7718-2011 预包装食品标签 NRV 标示要求" \
  --output-dir benchmark/foodscience_faiss_sidecar_smoke \
  --runs 3 \
  --modes hybrid \
  --rerank-options on
```

For a 10-query smoke set, run this command once per query and preserve each
output directory. Compare:

- `request_wall_seconds`, `server_request_seconds`, and `query_seconds`
- `stage_timings` for `graph_relation_vector_index_search`
- returned final context chunk IDs in trace
- `cache_hit_stages` must be empty for cold-cache comparisons

## Rollback

Unset `RAG_VECTOR_RUNTIME_BACKEND` and `RAG_VECTOR_SIDECAR_DIR`, then restart the
service. The original project directory is unchanged.
