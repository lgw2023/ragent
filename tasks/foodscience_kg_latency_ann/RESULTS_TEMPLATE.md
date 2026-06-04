# FoodScience KG Latency ANN Results

Remote assistant should fill this file after running the experiment.

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

## Service Configuration

| Variant | URL | Backend | Sidecar dir | Notes |
| --- | --- | --- | --- | --- |
| Nano | `http://127.0.0.1:8101` | Nano | n/a | |
| FAISS exact | `http://127.0.0.1:8099` | FAISS sidecar | | |
| FAISS HNSW | `http://127.0.0.1:8102` | FAISS sidecar | `/data/disk3/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef128` | |

## Sidecar Manifest Summary

Exact FAISS manifest:

| Namespace | Index type | Count | Search params |
| --- | --- | ---: | --- |
| chunks | | | |
| entities | | | |
| relationships | | | |

HNSW manifest:

| Namespace | Index type | Count | Search params |
| --- | --- | ---: | --- |
| chunks | | | |
| entities | | | |
| relationships | | | |

## HNSW Build

| Metric | Value |
| --- | ---: |
| build wall time | |
| output size | |
| manifest path | |
| build command | |

## Retrieval-only Summary

`retrieval_only=true`, `enable_rerank=true`, `include_trace=true`.

| Variant | Runs | Median request s | p95 request s | Median query s | p95 query s | Median retrieval s | p95 retrieval s | Median relation index s | p95 relation index s | Median entity index s | p95 entity index s | Cache hits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nano | | | | | | | | | | | | |
| FAISS exact | | | | | | | | | | | | |
| FAISS HNSW | | | | | | | | | | | | |

## Full-chain Summary

`retrieval_only=false`, `enable_rerank=true`, `include_trace=true`.

| Variant | Runs | Median request s | p95 request s | Median query s | p95 query s | Median retrieval s | p95 retrieval s | Median answer_generation s | p95 answer_generation s | Cache hits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nano | | | | | | | | | | |
| FAISS exact | | | | | | | | | | |
| FAISS HNSW | | | | | | | | | | |

## Stage Breakdown

Fill with median seconds unless another aggregation is stated.

| Variant | relation index | entity index | chunks index | vector_retrieval | keyword_extraction | rerank | answer_generation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nano retrieval-only | | | | | | | n/a |
| FAISS exact retrieval-only | | | | | | | n/a |
| FAISS HNSW retrieval-only | | | | | | | n/a |
| Nano full-chain | | | | | | | |
| FAISS exact full-chain | | | | | | | |
| FAISS HNSW full-chain | | | | | | | |

## Per-query Quality Notes

Compare HNSW against exact FAISS. Record obvious misses, empty contexts, or large
reference changes.

| Query ID | Exact ref chunks | HNSW ref chunks | Chunk overlap | Exact referenced files | HNSW referenced files | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| q01_dairy_shelf_life | | | | | | |
| q02_prepackaged_labeling | | | | | | |
| q03_preservative_limits | | | | | | |
| q04_water_activity_spoilage | | | | | | |
| q05_haccp_meat_products | | | | | | |
| q06_seafood_cold_chain | | | | | | |
| q07_cereal_mycotoxins | | | | | | |
| q08_fermented_dairy | | | | | | |
| q09_food_allergens | | | | | | |
| q10_thermal_processing | | | | | | |

## Decision

Choose one:

- Keep exact FAISS for now.
- Promote relationships HNSW.
- Run another HNSW sweep.
- Try IVF/IVF_FLAT.

Decision:

Reason:

## Raw Artifacts

| Artifact | Path |
| --- | --- |
| raw JSON directory | |
| exact service logs | |
| Nano service logs | |
| HNSW service logs | |
| HNSW manifest | |
