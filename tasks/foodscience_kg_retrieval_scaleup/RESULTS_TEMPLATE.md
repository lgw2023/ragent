# FoodScience KG Retrieval Scale-up Results

Status: completed on 2026-06-05. This file records the remote retrieval-only
scale-up benchmark for promoting entities HNSW after relationships HNSW had
already been validated.

## Environment

| Item | Value |
| --- | --- |
| server hostname | `DevServer-BMS-3d97cc99-0` |
| date/time | 2026-06-05 11:32-13:11 CST |
| repo path | `/data/disk3/ragent-20260604_105639` |
| git commit | `5964b3e` |
| git status summary | read-only benchmark flow; no repo file edits reported |
| Python version | 3.10.20 |
| uv version | 0.11.14 |
| faiss version | 1.13.2 |
| project dir | `/data/disk3/FoodScience_KG_final_sharded` |
| result dir | `benchmark/foodscience_kg_retrieval_scaleup_20260605_1132/` |

All benchmark requests completed successfully: 600/600 success, 0 errors, 0
cache hits, and 0 timeout/5xx responses.

## Variants

| Variant | URL | Sidecar dir | chunks index | entities index | relationships index | Search params |
| --- | --- | --- | --- | --- | --- | --- |
| exact | `http://127.0.0.1:8099` | `/data/disk3/FoodScience_KG_final_sharded_sidecar_exact` | flat | flat | flat | `{}` |
| rel_hnsw_ef128 | `http://127.0.0.1:8102` | `/data/disk3/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef128` | flat | flat | hnsw | relationships `{"ef_search":128}` |
| ent_hnsw_e128_rel_hnsw_r128 | `http://127.0.0.1:8110` | `/data/disk3/FoodScience_KG_final_sharded_sidecar_ent_hnsw_e128_rel_hnsw_r128` | flat | hnsw | hnsw | entities `{"ef_search":128}`; relationships `{"ef_search":128}` |

## Candidate Builds

| Variant | Build time | Output size | Manifest path | Notes |
| --- | ---: | ---: | --- | --- |
| ent_hnsw_e128_rel_hnsw_r128 | 18:12 | 13 GB | `/data/disk3/FoodScience_KG_final_sharded_sidecar_ent_hnsw_e128_rel_hnsw_r128/manifest.json` | manifest confirmed entities and relationships are both `hnsw` with `ef_search=128` |

## Sequential Retrieval-only Summary

Concurrency `1`, 50 queries, `retrieval_only=true`, `enable_rerank=true`.

| Variant | Runs | Error count | Cache hits | Median request s | p95 request s | Median retrieval s | p95 retrieval s | Median entity index s | p95 entity index s | Median relation index s | p95 relation index s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| exact | 50 | 0 | 0 | 14.5871 | 20.2439 | 14.460 | 20.139 | 2.211 | 2.374 | 7.577 | 8.699 |
| rel_hnsw_ef128 | 50 | 0 | 0 | 8.2561 | 11.3078 | 8.116 | 11.202 | 2.093 | 2.288 | 0.022 | 0.056 |
| ent_hnsw_e128_rel_hnsw_r128 | 50 | 0 | 0 | 6.0817 | 9.9702 | 5.966 | 9.865 | 0.031 | 0.048 | 0.022 | 0.047 |

Relative to the current relationships-only HNSW default:

- retrieval p50 improved by 26%: 8.116 s -> 5.966 s.
- retrieval p95 improved by 12%: 11.202 s -> 9.865 s.
- entity index p50 improved by about 70x: 2.093 s -> 0.031 s.

## Concurrent Retrieval-only Summary

50 queries per variant per concurrency level. Request latency is user-side wall
time and includes benchmark service session queueing.

| Variant | Concurrency | Runs | Error count | Cache hits | Median request s | p95 request s | Median retrieval s | p95 retrieval s | Median entity index s | p95 entity index s | Median relation index s | p95 relation index s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| exact | 2 | 50 | 0 | 0 | 28.2241 | 35.8272 | 13.858 | 18.549 | 2.282 | 2.345 | 7.147 | 8.715 |
| exact | 4 | 50 | 0 | 0 | 52.4740 | 63.8329 | 12.752 | 20.476 | 1.967 | 2.342 | 5.562 | 8.194 |
| exact | 8 | 50 | 0 | 0 | 100.3118 | 110.5366 | 12.487 | 16.586 | 2.105 | 2.329 | 5.853 | 8.297 |
| rel_hnsw_ef128 | 2 | 50 | 0 | 0 | 17.0239 | 24.6875 | 8.204 | 12.936 | 2.045 | 2.253 | 0.017 | 0.037 |
| rel_hnsw_ef128 | 4 | 50 | 0 | 0 | 38.3603 | 49.6712 | 8.908 | 13.478 | 2.106 | 2.234 | 0.019 | 0.044 |
| rel_hnsw_ef128 | 8 | 50 | 0 | 0 | 66.8714 | 88.3036 | 8.024 | 13.436 | 2.026 | 2.286 | 0.018 | 0.041 |
| ent_hnsw_e128_rel_hnsw_r128 | 2 | 50 | 0 | 0 | 12.4421 | 20.6792 | 5.721 | 10.846 | 0.025 | 0.037 | 0.015 | 0.039 |
| ent_hnsw_e128_rel_hnsw_r128 | 4 | 50 | 0 | 0 | 25.4655 | 42.5114 | 6.088 | 11.439 | 0.023 | 0.032 | 0.016 | 0.038 |
| ent_hnsw_e128_rel_hnsw_r128 | 8 | 50 | 0 | 0 | 55.5509 | 65.6294 | 5.923 | 11.331 | 0.022 | 0.039 | 0.014 | 0.038 |

At concurrency 8, the candidate reduced request p95 by 26% versus the
relationships-only HNSW default: 88.3036 s -> 65.6294 s.

## Stage Breakdown

Median seconds at concurrency 1.

| Variant | entity index | relation index | chunks index | vector_retrieval | keyword_extraction | rerank | hybrid_retrieval_total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| exact | 2.211 | 7.577 | n/a | 1.895 | 3.478 | 0.998 | 14.460 |
| rel_hnsw_ef128 | 2.093 | 0.022 | n/a | 1.845 | 2.677 | 0.980 | 8.116 |
| ent_hnsw_e128_rel_hnsw_r128 | 0.031 | 0.022 | n/a | 1.686 | 2.457 | 1.017 | 5.966 |

## Quality / Overlap

Final context chunk IDs were compared against exact at concurrency 1.

| Variant | Queries | Median chunk overlap | Min chunk overlap | Queries below 8/10 | Referenced-file drift notes |
| --- | ---: | ---: | ---: | --- | --- |
| rel_hnsw_ef128 | 50 | 10/10 | 6 | `q043_emulsifiers_stabilizers` | `q043` is not ANN drift: exact itself returned only 6 final chunks, and all variants returned the same chunk IDs and referenced files. |
| ent_hnsw_e128_rel_hnsw_r128 | 50 | 10/10 | 6 | `q043_emulsifiers_stabilizers` | Same as relationships-only HNSW; no additional quality drift observed from entities HNSW. |

## Decision

Decision: promote entities HNSW.

Production-recommended sidecar profile for this FoodScience KG:

| Namespace | Recommended index |
| --- | --- |
| chunks | flat |
| entities | hnsw, `ef_search=128` |
| relationships | hnsw, `ef_search=128` |

Reason:

- Relative to relationships-only HNSW, retrieval p50 and p95 both improved.
- `graph_entity_vector_index_search` dropped from about 2.1 s to about 0.03 s.
- 50-query quality matched relationships-only HNSW and exact at final chunk level except for `q043`, where exact also had only 6 final chunks.
- Concurrency 1/2/4/8 had no errors, no cache hits, and no timeout/5xx responses.
- Full-answer latency remains outside the project scope because answer generation is dominated by external LLM service time.

## Operational Notes

- The `:8102` manifest was previously mislabeled as ef256; it was patched to ef128 and the service was restarted before this experiment.
- New benchmark services need `RAGENT_SKIP_DOTENV=1 MODEL_STARTUP_CHECK_ENABLED=0`; otherwise `.env` may override the command-line environment and trigger model startup checks.
- Earlier `:8102` / `:8110` startup failures were due to `.env` override, proxy 302/timeout during model startup checks, and one SIGTERM interruption. The final run used the corrected environment and completed successfully.
- The local partial copy under `benchmark/foodscience_kg_retrieval_scaleup_20260605_1132/` currently includes `summary.json` and `summary.md`; the remote run also reported raw JSON and service logs at the paths below.

## Raw Artifacts

| Artifact | Path |
| --- | --- |
| raw JSON directory | `benchmark/foodscience_kg_retrieval_scaleup_20260605_1132/raw/` |
| summary.json | `benchmark/foodscience_kg_retrieval_scaleup_20260605_1132/summary.json` |
| summary.md | `benchmark/foodscience_kg_retrieval_scaleup_20260605_1132/summary.md` |
| service logs | `/tmp/benchmark_8102.log`, `/tmp/benchmark_8110.log` |
| sidecar manifest | `/data/disk3/FoodScience_KG_final_sharded_sidecar_ent_hnsw_e128_rel_hnsw_r128/manifest.json` |

## Local GLiNER Keyword-only Follow-up

Status: completed locally on 2026-06-05.

Scope: simulate keyword extraction only. This did not run KG retrieval, graph
expansion, rerank, or LLM answer generation.

| Item | Value |
| --- | --- |
| local result dir | `benchmark/foodscience_keyword_extraction_gliner_local_20260605/` |
| queries | `tasks/foodscience_kg_retrieval_scaleup/queries_50.jsonl` |
| query count / repeats | 50 queries / 5 repeats |
| predictions | 250 |
| GLiNER model | `mep/component_deps/models/keyword_extraction/knowledgator-gliner-x-small` |
| device | CPU |
| cold load + warmup | 6.910 s |

Warm resident prediction latency:

| Metric | Seconds |
| --- | ---: |
| min | 0.0207 |
| p50 | 0.0257 |
| mean | 0.0267 |
| p95 | 0.0318 |
| max | 0.0990 |

Keyword count:

| Metric | Value |
| --- | ---: |
| p50 | 7 |
| p95 | 9 |
| min | 4 |
| max | 9 |
| empty predictions | 0 |

Directional comparison against the remote LLM keyword stage from
`ent_hnsw_e128_rel_hnsw_r128`, concurrency 1:

| Keyword path | p50 | p95 |
| --- | ---: | ---: |
| remote LLM keyword stage | 2.457 s | 6.439 s |
| local GLiNER warm prediction | 0.0257 s | 0.0318 s |

Approximate speedup: about 95x at p50 and 202x at p95. This is directional
because the baseline was measured on the remote server while GLiNER was measured
on the local machine.

Sample output:

| Query | Extracted keywords |
| --- | --- |
| `q001_dairy_shelf_life` | `shelf life`, `dairy products`, `preservatives`, `packaging`, `storage temperature`, `pH`, `water activity`, `spoilage risk` |
| `q002_prepackaged_labeling` | `prepackaged food labeling`, `nutrition facts`, `ingredient lists`, `allergen declarations`, `shelf life`, `storage conditions` |
| `q003_preservative_limits` | `benzoic acid`, `sorbic acid`, `nitrite`, `preservatives`, `processed foods`, `safety factors` |

Decision:

- GLiNER is fast enough to remove `keyword_extraction` as a retrieval-layer
  latency bottleneck if the model is preloaded and kept resident.
- Cold load is not acceptable on the first user query, so production use should
  enable keyword fallback preload.
- Before replacing remote LLM keyword extraction in production, run a remote
  retrieval-only A/B with `keyword_source=gliner_fallback` and compare final
  context chunk overlap against the current LLM keyword path.
