# FoodScience KG Latency ANN Results

Remote experiment completed on 2026-06-04; supplemental items completed on 2026-06-05.

## Environment

| Item | Value |
| --- | --- |
| server hostname | DevServer-BMS-3d97cc99-0 |
| date/time | 2026-06-04T22:43+08:00 (build) / 2026-06-05T09:26+08:00 (supplement) |
| repo path | `/data/disk3/ragent-20260604_105639` |
| git commit | `2c13e06686a356fcd050a93318bea025041b71d5` |
| git status summary | Untracked: `.cursor/`, `benchmark_results/`, `benchmark/foodscience_kg_latency_ann_20260604_2243/` |
| Python version | 3.10.20 (`uv run`) |
| uv version | 0.11.14 |
| faiss version | 1.13.2 |
| project dir | `/data/disk3/FoodScience_KG_final_sharded` |

## Service Configuration

| Variant | URL | Backend | Sidecar dir | Notes |
| --- | --- | --- | --- | --- |
| Nano | `http://127.0.0.1:8101` | Nano JSON VDB | n/a | Pre-existing; log archived |
| FAISS exact | `http://127.0.0.1:8099` | FAISS sidecar | `/data/disk3/FoodScience_KG_final_sharded_sidecar_exact` | Pre-existing; log archived |
| FAISS HNSW ef128 | `http://127.0.0.1:8102` | FAISS sidecar | `/data/disk3/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef128` | Primary HNSW candidate |
| FAISS HNSW ef64 | `http://127.0.0.1:8103` | FAISS sidecar | `/data/disk3/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef64` | Sweep (manifest-only) |
| FAISS HNSW ef256 | `http://127.0.0.1:8104` | FAISS sidecar | `/data/disk3/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef256` | Sweep (manifest-only) |

## Sidecar Manifest Summary

Exact FAISS manifest:

| Namespace | Index type | Count | Search params |
| --- | --- | ---: | --- |
| chunks | flat | 58184 | `{}` |
| entities | flat | 228259 | `{}` |
| relationships | flat | 905580 | `{}` |

HNSW manifest (ef128 / ef64 / ef256 share the same FAISS index files; only `ef_search` differs):

| Namespace | Index type | Count | Search params |
| --- | --- | ---: | --- |
| chunks | flat | 58184 | `{}` |
| entities | flat | 228259 | `{}` |
| relationships | hnsw | 905580 | ef128: `{"ef_search":128}` · ef64: `{"ef_search":64}` · ef256: `{"ef_search":256}` |

## HNSW Build

| Metric | Value |
| --- | ---: |
| build wall time | 593.12 s (~9.9 min) |
| output size | 13G (ef128); ef64/ef256 are hardlink copies + manifest patch (no extra disk) |
| manifest path | `/data/disk3/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef128/manifest.json` |
| build command | `benchmark/foodscience_kg_latency_ann_20260604_2243/manifest/build_command.sh` |

## Retrieval-only Summary

`retrieval_only=true`, `enable_rerank=true`, `include_trace=true`.
10 queries × 3 baseline variants = 30 requests. All `cache_hit_count=0`.

| Variant | Runs | Median request s | p95 request s | Median query s | p95 query s | Median retrieval s | p95 retrieval s | Median relation index s | p95 relation index s | Median entity index s | p95 entity index s | Cache hits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nano | 10 | 75.76 | 105.11 | 75.72 | 105.06 | 75.64 | 104.95 | 54.15 | 81.32 | 15.16 | 18.88 | 0 |
| FAISS exact | 10 | 14.73 | 21.84 | 14.70 | 21.80 | 14.63 | 21.72 | 7.76 | 9.10 | 2.20 | 2.35 | 0 |
| FAISS HNSW ef128 | 10 | 9.09 | 12.79 | 9.06 | 12.74 | 8.99 | 12.63 | **0.04** | **0.08** | 2.10 | 2.30 | 0 |

HNSW ef128 vs exact (retrieval-only medians): relation index **7.76 → 0.04 s**; hybrid retrieval **14.63 → 8.99 s** (**38.5%** faster).

## ef_search Sweep (retrieval-only)

10 queries each; services `:8103` (ef64) and `:8104` (ef256). All `cache_hit_count=0`.

| Variant | Median request s | p95 request s | Median relation index s | p95 relation index s | Median retrieval s | p95 retrieval s | q07 ref files (HNSW vs exact 15) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ef128 | 9.09 | 12.79 | 0.04 | 0.08 | 8.99 | 12.63 | 7 |
| ef64 | 9.27 | 14.09 | 0.03 | 0.07 | 9.15 | 13.98 | 12 |
| ef256 | 8.61 | 14.42 | 0.03 | 0.06 | 8.51 | 14.30 | 14 |

All ef_search values meet the **<1.5 s** relation-index median target. ef256 slightly improves q07 file-path alignment vs ef128 without meaningful latency regression.

## Full-chain Summary

`retrieval_only=false`, `enable_rerank=true`, `include_trace=true`.
**10 queries × 3 variants = 30 requests** (supplement completed 2026-06-05). All `cache_hit_count=0`.

| Variant | Runs | Median request s | p95 request s | Median query s | p95 query s | Median retrieval s | p95 retrieval s | Median answer_generation s | p95 answer_generation s | Cache hits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nano | 10 | 106.22 | 277.71 | 106.19 | 277.67 | 87.35 | 261.23 | 17.08 | 21.38 | 0 |
| FAISS exact | 10 | 29.93 | 37.98 | 29.89 | 37.94 | 13.60 | 15.42 | 16.50 | 22.96 | 0 |
| FAISS HNSW ef128 | 10 | 27.00 | 29.68 | 26.95 | 29.64 | 9.53 | 10.91 | 17.11 | 21.38 | 0 |

Full-chain HNSW ef128 vs exact: median request **29.93 → 27.00 s** (~10% faster); median retrieval **13.60 → 9.53 s** (~30% faster). `answer_generation` remains ~17 s (LLM-bound).

## Stage Breakdown

Median seconds.

| Variant | relation index | entity index | chunks index | vector_retrieval | keyword_extraction | rerank | answer_generation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nano retrieval-only | 54.15 | 15.16 | 0.59 | 2.35 | 3.88 | 1.01 | n/a |
| FAISS exact retrieval-only | 7.76 | 2.20 | 0.49 | 2.01 | 3.37 | 1.00 | n/a |
| FAISS HNSW ef128 retrieval-only | **0.04** | 2.10 | 0.23 | 1.80 | 3.26 | 0.99 | n/a |
| Nano full-chain | 55.70 | 15.21 | 0.72 | 2.70 | 3.22 | 1.02 | 17.08 |
| FAISS exact full-chain | 7.28 | 2.26 | 0.40 | 2.14 | 3.30 | 0.97 | 16.50 |
| FAISS HNSW ef128 full-chain | **0.03** | 2.11 | 0.25 | 1.77 | 3.09 | 0.98 | 17.11 |

## Per-query Quality Notes

Compare HNSW ef128 against exact FAISS (retrieval-only). Final chunk ID overlap **10/10** on all queries.

| Query ID | Exact ref chunks | HNSW ref chunks | Chunk overlap | Exact referenced files | HNSW referenced files | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| q01_dairy_shelf_life | 10 | 10 | 10 | 13 | 14 | |
| q02_prepackaged_labeling | 10 | 10 | 10 | 15 | 16 | |
| q03_preservative_limits | 10 | 10 | 10 | 7 | 12 | |
| q04_water_activity_spoilage | 10 | 10 | 10 | 20 | 20 | |
| q05_haccp_meat_products | 10 | 10 | 10 | 16 | 15 | |
| q06_seafood_cold_chain | 10 | 10 | 10 | 12 | 14 | |
| q07_cereal_mycotoxins | 10 | 10 | 10 | 15 | 7 | Chunk IDs match; file-path drift — ef256 sweep gives 14/15 |
| q08_fermented_dairy | 10 | 10 | 10 | 10 | 10 | |
| q09_food_allergens | 10 | 10 | 10 | 10 | 10 | |
| q10_thermal_processing | 10 | 10 | 10 | 17 | 16 | |

## Decision

**Decision: Promote relationships HNSW with `ef_search=128` as default; keep `ef_search=256` as optional quality-tuning profile.**

**Reason:** All success criteria met on 10-query retrieval-only and full-chain sets. Relation-index medians are ~0.03–0.04 s (p95 <0.08 s). Hybrid retrieval improves ~38% vs exact FAISS. No chunk-level regression. ef256 improves referenced-file alignment on q07/q03 without sacrificing latency; ef64 does not materially improve quality.

## Raw Artifacts

| Artifact | Path |
| --- | --- |
| raw JSON directory | `benchmark/foodscience_kg_latency_ann_20260604_2243/raw/` (**80** files) |
| aggregated summary | `benchmark/foodscience_kg_latency_ann_20260604_2243/summary.json` |
| experiment runner | `benchmark/foodscience_kg_latency_ann_20260604_2243/run_latency_experiment.py` |
| supplement runner | `benchmark/foodscience_kg_latency_ann_20260604_2243/run_supplement.py` |
| summary regenerator | `benchmark/foodscience_kg_latency_ann_20260604_2243/regenerate_summary.py` |
| exact service logs | `benchmark/foodscience_kg_latency_ann_20260604_2243/logs/exact_service_8099.log` |
| Nano service logs | `benchmark/foodscience_kg_latency_ann_20260604_2243/logs/nano_service_8101.log` |
| HNSW ef128 service logs | `benchmark/foodscience_kg_latency_ann_20260604_2243/logs/hnsw_service_8102.log` |
| HNSW ef64 service logs | `benchmark/foodscience_kg_latency_ann_20260604_2243/logs/hnsw_ef64_service_8103.log` |
| HNSW ef256 service logs | `benchmark/foodscience_kg_latency_ann_20260604_2243/logs/hnsw_ef256_service_8104.log` |
| HNSW build log | `benchmark/foodscience_kg_latency_ann_20260604_2243/logs/build_hnsw_sidecar.log` |
| query run log (504 proxy fail) | `benchmark/foodscience_kg_latency_ann_20260604_2243/logs/run_experiment.log` |
| query run log (success) | `benchmark/foodscience_kg_latency_ann_20260604_2243/logs/run_experiment_retry.log` |
| full-chain supplement log | `benchmark/foodscience_kg_latency_ann_20260604_2243/logs/run_supplement_full_chain.log` |
| ef_search sweep log | `benchmark/foodscience_kg_latency_ann_20260604_2243/logs/run_supplement_ef_sweep.log` |
| build command | `benchmark/foodscience_kg_latency_ann_20260604_2243/manifest/build_command.sh` |
| environment notes | `benchmark/foodscience_kg_latency_ann_20260604_2243/manifest/environment_notes.md` |
| supplement notes | `benchmark/foodscience_kg_latency_ann_20260604_2243/manifest/supplement_notes.md` |

## Failures / incomplete items

| Item | Status |
| --- | --- |
| First query batch (39/39 HTTP 504) | **Resolved** — localhost proxy bypass; see `run_experiment_retry.log` |
| 10-query full-chain for all variants | **Completed** — 30/30 JSON; see `run_supplement_full_chain.log` |
| 8099 / 8101 service log capture | **Completed** — terminal archives under `logs/` |
| HNSW ef_search sweep (64 / 256) | **Completed** — manifest-only sidecars + `:8103`/`:8104`; see `ef_search_sweep` in `summary.json` |
| ef256 initial connection refused | **Resolved** — `:8104` preload finished; ef256 batch rerun succeeded |

**No open blockers.**
