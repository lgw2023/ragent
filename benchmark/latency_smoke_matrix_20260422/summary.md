# Latency Benchmark Summary

- Project: `example/demo_diet_kg_5`
- Query: 我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？
- Runs per request scenario: 1
- Output dir: `/Volumes/SSD1/ragent/benchmark/latency_smoke_matrix_20260422`
- Environment snapshot: `/Volumes/SSD1/ragent/benchmark/latency_smoke_matrix_20260422/env_snapshot.txt`
- Service startup artifact: `/Volumes/SSD1/ragent/benchmark/latency_smoke_matrix_20260422/service_startup.json`

## Metric Definitions

- `service_startup_wall_seconds`: process spawn to `/health` ready. This is the external service startup cost.
- `startup_ready_seconds`: server-reported startup readiness time from `/health`, currently dominated by startup model checks.
- `request_wall_seconds`: client-observed single HTTP request latency. This is the main online latency metric.
- `project_initialization_seconds`: `rag_initialization_total` captured inside the first request after the project session is loaded.
- `query_seconds`: request-side `onehop_total` captured by the service trace, excluding service startup and excluding project init unless it is folded into the measured first request path.

## Scenario Semantics

- `first_request`: Service process is already up, but the project session is unloaded and the query cache is cleared before each measured request.
- `steady_cold`: Service process and project session stay warm, while the query cache is cleared before each measured request.
- `steady_retrieval_warm`: Service process and project session stay warm, the target query is primed, and only answer-cache entries are cleared before each measured request so retrieval/render/prompt caches remain warm.
- `steady_answer_warm`: Service process and project session stay warm, the target query is primed, and measured requests should hit the direct answer cache.

## Service Startup

| service_url | startup wall (s) | startup ready (s) | log |
|---|---:|---:|---|
| `http://127.0.0.1:18104` | 9.251 | 2.009 | `/Volumes/SSD1/ragent/benchmark/latency_smoke_matrix_20260422/service.log` |

## Request Summary

| scenario | mode | rerank | request wall median/mean (s) | project init median/mean (s) | query execution median/mean (s) | validation failures | cache hits seen |
|---|---|---|---:|---:|---:|---:|---|
| `first_request` | `graph` | `false` | 27.508 / 27.508 | 2.359 / 2.359 | 25.144 / 25.144 | 0/1 | - |
| `first_request` | `graph` | `true` | 19.106 / 19.106 | 2.637 / 2.637 | 16.462 / 16.462 | 0/1 | - |
| `first_request` | `hybrid` | `false` | 23.866 / 23.866 | 2.769 / 2.769 | 21.087 / 21.087 | 0/1 | - |
| `first_request` | `hybrid` | `true` | 16.353 / 16.353 | 2.526 / 2.526 | 13.818 / 13.818 | 0/1 | - |
| `steady_cold` | `graph` | `false` | 22.737 / 22.737 | - | 22.732 / 22.732 | 0/1 | - |
| `steady_cold` | `graph` | `true` | 18.860 / 18.860 | - | 18.855 / 18.855 | 0/1 | - |
| `steady_cold` | `hybrid` | `false` | 18.833 / 18.833 | - | 18.828 / 18.828 | 0/1 | - |
| `steady_cold` | `hybrid` | `true` | 16.795 / 16.795 | - | 16.790 / 16.790 | 0/1 | - |
| `steady_retrieval_warm` | `graph` | `false` | 13.744 / 13.744 | - | 13.740 / 13.740 | 0/1 | prompt_cache_hit, render_cache_hit, retrieval_cache_hit |
| `steady_retrieval_warm` | `graph` | `true` | 15.508 / 15.508 | - | 15.503 / 15.503 | 0/1 | prompt_cache_hit, render_cache_hit, retrieval_cache_hit |
| `steady_retrieval_warm` | `hybrid` | `false` | 16.545 / 16.545 | - | 16.540 / 16.540 | 0/1 | prompt_cache_hit, render_cache_hit, retrieval_cache_hit |
| `steady_retrieval_warm` | `hybrid` | `true` | 8.333 / 8.333 | - | 8.329 / 8.329 | 0/1 | prompt_cache_hit, render_cache_hit, retrieval_cache_hit |
| `steady_answer_warm` | `graph` | `false` | 0.011 / 0.011 | - | 0.006 / 0.006 | 0/1 | answer_cache_hit |
| `steady_answer_warm` | `graph` | `true` | 0.009 / 0.009 | - | 0.005 / 0.005 | 0/1 | answer_cache_hit |
| `steady_answer_warm` | `hybrid` | `false` | 0.010 / 0.010 | - | 0.004 / 0.004 | 0/1 | answer_cache_hit |
| `steady_answer_warm` | `hybrid` | `true` | 0.008 / 0.008 | - | 0.004 / 0.004 | 0/1 | answer_cache_hit |

## Configuration View

| mode | rerank | first request wall median/mean (s) | steady cold wall median/mean (s) | retrieval warm wall median/mean (s) | answer warm wall median/mean (s) |
|---|---|---:|---:|---:|---:|
| `graph` | `false` | 27.508 / 27.508 | 22.737 / 22.737 | 13.744 / 13.744 | 0.011 / 0.011 |
| `graph` | `true` | 19.106 / 19.106 | 18.860 / 18.860 | 15.508 / 15.508 | 0.009 / 0.009 |
| `hybrid` | `false` | 23.866 / 23.866 | 18.833 / 18.833 | 16.545 / 16.545 | 0.010 / 0.010 |
| `hybrid` | `true` | 16.353 / 16.353 | 16.795 / 16.795 | 8.333 / 8.333 | 0.008 / 0.008 |

## Reading Guide

- `first_request` should be read as `project_initialization_seconds + query_seconds` inside a warm service process.
- `steady_cold` isolates steady-state request cost with the project already loaded but query caches cleared.
- `steady_retrieval_warm` isolates the benefit of retrieval/render/prompt reuse without direct answer-cache hits.
- `steady_answer_warm` isolates the direct answer-cache hit path.

## Artifacts

- `results.tsv`: measured request-level raw metrics.
- `service_startup.json`: service startup cost and log pointer.
- `*.response.json`: raw service responses for every measured run and prime step.
- `*.trace.json`: extracted trace payloads for every measured run and prime step.
- `service.log`: long-running benchmark service log.
