# FAISS Sidecar Runtime Runbook

This runbook accelerates inference over an existing Ragent project without
re-running parsing, extraction, embedding, or graph construction.

## Build Sidecars

Use the existing final project as the source. The command reads only
`vdb_chunks.json`, `vdb_entities.json`, and `vdb_relationships.json`.

The default sidecar is project-local. With no custom index flags, the tool builds
`profile=default_hnsw_v1` into `<project-dir>/vector_sidecars/default`: chunks
stay exact/flat, while entities and relationships use HNSW ef128.

```bash
uv run python tools/build_vector_sidecars.py \
  --project-dir /data/disk3/FoodScience_KG_final_sharded
```

For comparison experiments, the exact FAISS profile remains useful as the
quality oracle:

```bash
uv run python tools/build_vector_sidecars.py \
  --project-dir /data/disk3/FoodScience_KG_final_sharded \
  --profile exact
```

The legacy explicit command for the validated FoodScience production profile is
equivalent to the current default except for its custom output directory:

```bash
uv run python tools/build_vector_sidecars.py \
  --project-dir /data/disk3/FoodScience_KG_final_sharded \
  --output-dir /data/disk3/FoodScience_KG_final_sharded_sidecar_ent_hnsw_e128_rel_hnsw_r128 \
  --index-type flat \
  --entities-index-type hnsw \
  --entities-hnsw-ef-search 128 \
  --relationships-index-type hnsw \
  --relationships-hnsw-ef-search 128 \
  --hnsw-m 16 \
  --hnsw-ef-construction 200
```

Custom profiles are still supported for experiments. Keep them out of
`vector_sidecars/default` unless intentionally replacing the default derived
artifact.

The earlier relationships-only HNSW profile is still useful for isolating the
relationship-search bottleneck:

```bash
uv run python tools/build_vector_sidecars.py \
  --project-dir /data/disk3/FoodScience_KG_final_sharded \
  --output-dir /data/disk3/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef128 \
  --index-type flat \
  --relationships-index-type hnsw \
  --hnsw-m 16 \
  --hnsw-ef-search 128
```

## Offline Raw Units Pipeline

Raw export only writes raw merge units. It does not build a sidecar because it
does not produce the final KG project.

Strict replay and finished-project merge build the project-local default sidecar
after writing the final KG:

```bash
uv run python tools/replay_raw_merge_units_to_project.py \
  raw-units.jsonl \
  --output /data/disk3/FoodScience_KG_final_sharded

uv run python tools/merge_kg_projects.py \
  /data/disk3/kg_part_a \
  /data/disk3/kg_part_b \
  /data/disk3/FoodScience_KG_final_sharded
```

Use `--no-vector-sidecar` only for explicit comparison or debug runs.

FoodScience validation summary, retrieval-only, 50 queries, cold cache:

- exact FAISS retrieval p50/p95: 14.46 s / 20.14 s.
- relationships HNSW ef128 retrieval p50/p95: 8.12 s / 11.20 s.
- entities+relationships HNSW ef128 retrieval p50/p95: 5.97 s / 9.87 s.
- entities+relationships HNSW had 600/600 successful benchmark requests across
  concurrency 1/2/4/8, with 0 errors and 0 cache hits.
- Final context chunk overlap versus exact had p50 10/10. The only below-8 case
  was `q043_emulsifiers_stabilizers`, where exact itself returned only 6 final
  chunks and all variants matched those chunks.

## Run Benchmark Service

The benchmark service defaults to the FAISS sidecar runtime and discovers each
project's sidecar from `<project-dir>/vector_sidecars/default`. Preload the
project at service startup:

```bash
export RAG_PRELOAD_PROJECT_DIRS=/data/disk3/FoodScience_KG_final_sharded

uv run python -m ragent.api.benchmark_service --host 127.0.0.1 --port 8100
```

`RAG_PRELOAD_PROJECT_DIRS` removes first-query initialization from user-facing
latency. The service should report the project in `/health` under
`loaded_projects`; `loaded_project_details` includes the loaded sidecar profile,
manifest digest, and keyword fallback preload state.

`faiss-cpu==1.13.2` is a standard project dependency. Ragent checks native
FAISS/PyTorch OpenMP linkage before importing FAISS, but it does not rewrite
installed wheels or set `KMP_DUPLICATE_LIB_OK`. Linux deployments use the normal
dependency path. On macOS, PyPI `faiss-cpu` and `torch` may ship separate
private `libomp.dylib` copies; if that known split is detected, startup fails
before FAISS import with a dependency-environment diagnostic. Fix the Python
environment instead: use a Linux/container runtime, a conda-forge environment
where FAISS and PyTorch share OpenMP, or a FAISS build linked against the same
OpenMP runtime as PyTorch.

The guard policy is controlled by `RAG_FAISS_OPENMP_COMPAT_POLICY`:

- `auto` (default): fail only for the known macOS private-OpenMP split; warn for
  mixed OpenMP linkage elsewhere.
- `warn`: never fail from the guard, but emit diagnostics for mixed linkage.
- `error`: fail on any detected mixed OpenMP linkage.
- `off`: skip the pre-import native runtime check.

Do not set global `RAG_VECTOR_SIDECAR_DIR` for multi-project service runs unless
you are intentionally forcing every project to use the same sidecar directory.
If a sidecar is missing or stale, startup or the first project initialization
fails fast. For explicit NanoVectorDB comparisons, set:

```bash
export RAG_VECTOR_RUNTIME_BACKEND=nano
```

## Compare Latency

Run the existing latency runner against both Nano and sidecar services. Keep
cache-cleared `steady_cold` as the main p95 gate.

```bash
uv run python tools/latency_runner.py \
  --service-url http://127.0.0.1:8100 \
  --project-dir /data/disk3/FoodScience_KG_final_sharded \
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

Set `RAG_VECTOR_RUNTIME_BACKEND=nano` and restart the service, or pass
`--no-vector-sidecar` on replay/merge commands for comparison builds. The
original project directory data is unchanged; sidecars are derived artifacts.
