# FoodScience KG Retrieval Scale-up Results

Remote assistant should fill this after running the scale-up task.

## Environment

| Item | Value |
| --- | --- |
| server hostname | |
| date/time | |
| repo path | |
| git commit | |
| git status summary | |
| Python version | |
| uv version | |
| faiss version | |
| project dir | `/data/disk3/FoodScience_KG_final_sharded` |

## Variants

| Variant | URL | Sidecar dir | chunks index | entities index | relationships index | Search params |
| --- | --- | --- | --- | --- | --- | --- |
| exact | `http://127.0.0.1:8099` | | flat | flat | flat | |
| rel_hnsw_ef128 | `http://127.0.0.1:8102` | | flat | flat | hnsw | |
| ent_hnsw_e128_rel_hnsw_r128 | `http://127.0.0.1:8110` | | flat | hnsw | hnsw | |

## Candidate Builds

| Variant | Build time | Output size | Manifest path | Notes |
| --- | ---: | ---: | --- | --- |
| ent_hnsw_e128_rel_hnsw_r128 | | | | |

## Sequential Retrieval-only Summary

Concurrency `1`, 50 queries, `retrieval_only=true`.

| Variant | Runs | Error count | Cache hits | Median request s | p95 request s | Median retrieval s | p95 retrieval s | Median entity index s | p95 entity index s | Median relation index s | p95 relation index s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| exact | | | | | | | | | | | |
| rel_hnsw_ef128 | | | | | | | | | | | |
| ent_hnsw_e128_rel_hnsw_r128 | | | | | | | | | | | |

## Concurrent Retrieval-only Summary

50 queries per variant per concurrency level.

| Variant | Concurrency | Runs | Error count | Cache hits | Median request s | p95 request s | Median retrieval s | p95 retrieval s | Median entity index s | p95 entity index s | Median relation index s | p95 relation index s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| exact | 2 | | | | | | | | | | | |
| exact | 4 | | | | | | | | | | | |
| exact | 8 | | | | | | | | | | | |
| rel_hnsw_ef128 | 2 | | | | | | | | | | | |
| rel_hnsw_ef128 | 4 | | | | | | | | | | | |
| rel_hnsw_ef128 | 8 | | | | | | | | | | | |
| ent_hnsw_e128_rel_hnsw_r128 | 2 | | | | | | | | | | | |
| ent_hnsw_e128_rel_hnsw_r128 | 4 | | | | | | | | | | | |
| ent_hnsw_e128_rel_hnsw_r128 | 8 | | | | | | | | | | | |

## Stage Breakdown

Median seconds at concurrency 1.

| Variant | entity index | relation index | chunks index | vector_retrieval | keyword_extraction | rerank | hybrid_retrieval_total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| exact | | | | | | | |
| rel_hnsw_ef128 | | | | | | | |
| ent_hnsw_e128_rel_hnsw_r128 | | | | | | | |

## Quality / Overlap

Compare final context chunk IDs against exact at concurrency 1.

| Variant | Queries | Median chunk overlap | Min chunk overlap | Queries below 8/10 | Referenced-file drift notes |
| --- | ---: | ---: | ---: | ---: | --- |
| rel_hnsw_ef128 | | | | | |
| ent_hnsw_e128_rel_hnsw_r128 | | | | | |

## Decision

Choose one:

- Promote entities HNSW.
- Keep entities flat; relationships HNSW remains default.
- Run another entities HNSW/IVF sweep.
- Defer entities ANN and optimize keyword/rerank/service queueing.

Decision:

Reason:

## Raw Artifacts

| Artifact | Path |
| --- | --- |
| raw JSON directory | |
| summary.json | |
| summary.md | |
| service logs | |
| sidecar manifests | |
