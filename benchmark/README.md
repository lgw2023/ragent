# Latency Benchmark Usage

This benchmark flow measures the HTTP benchmark service rather than invoking the query path in-process. The goal is to separate:

- service startup cost
- first request cost after loading a project session
- steady-state cold request cost
- steady-state retrieval-warm cost
- steady-state answer-warm cost

## Entrypoints

- `script/latency_service.sh`
  - `start`: start the long-running benchmark service and wait for `/health`
  - `stop`: stop the service started by the benchmark scripts
- `script/latency_test.sh`
  - starts the service
  - runs the benchmark matrix through `tools/latency_runner.py`
  - renders `summary.md` through `tools/latency_report.py`

## Quick Start

Run the default matrix:

```bash
bash script/latency_test.sh
```

Run a small smoke benchmark:

```bash
RUNS=1 \
MODES="graph hybrid" \
RERANK_OPTIONS="off on" \
PROJECT_DIR="example/demo_diet_kg_5" \
bash script/latency_test.sh
```

Use a custom output directory:

```bash
OUTPUT_DIR="benchmark/latency_smoke_manual" \
RUNS=1 \
bash script/latency_test.sh
```

## Common Environment Variables

- `PROJECT_DIR`: project directory to query. Relative paths are resolved from the repo root.
- `QUERY`: query text used for every run.
- `RUNS`: number of measured runs per scenario.
- `OUTPUT_DIR`: artifact directory. Defaults to `benchmark/latency_<timestamp>`.
- `MODES`: space-separated query modes, for example `graph hybrid`.
- `RERANK_OPTIONS`: space-separated rerank flags, for example `off on`.
- `LATENCY_SERVICE_PORT`: local benchmark service port.
- `LATENCY_SERVICE_URL`: local benchmark service URL. Usually derived from the port.
- `ENV_FILE`: `.env` file used for environment snapshotting.
- `REQUEST_TIMEOUT`: per-request HTTP timeout in seconds.
- `RESPONSE_TYPE`: query response format passed through to the service.

## Scenario Semantics

- `first_request`
  - resets the project session
  - clears query-cache entries
  - measures the first request against an unloaded project session
  - expected cache behavior: no query cache hit
- `steady_cold`
  - primes the project once so the session is loaded
  - clears all query-cache entries before each measured request
  - expected cache behavior: no query cache hit
- `steady_retrieval_warm`
  - primes the target query
  - clears only `answer` cache entries before each measured request
  - expected cache behavior: at least one of `retrieval_cache_hit`, `render_cache_hit`, `prompt_cache_hit`
  - expected cache behavior: no `answer_cache_hit`
- `steady_answer_warm`
  - primes the target query
  - measures the next request without clearing the answer cache
  - expected cache behavior: `answer_cache_hit`

## Output Files

- `summary.md`: human-readable summary across scenarios and configurations.
- `results.tsv`: one row per measured request.
- `service_startup.json`: service startup wall time and `/health` startup-ready time.
- `service.log`: benchmark service log for the whole run.
- `*.response.json`: raw benchmark service response for each prime step and measured run.
- `*.trace.json`: extracted trace payload for each prime step and measured run.
- `validation_errors.txt`: scenario validation failures. If this file exists, the warm/cold semantics did not match the expected path.

## How To Tell Warm Paths Were Measured Correctly

Check `validation_errors.txt` first.

- If the file is absent, the scenario checks passed.
- If it is present, at least one measured run did not match the intended cache state.

Then spot-check `results.tsv` or the per-run `*.response.json` files:

- `first_request`
  - `project_initialized_before_request=false`
  - `project_first_request=true`
  - `project_initialization_seconds` should be populated
  - `cache_hit_stages` should be empty
- `steady_cold`
  - `project_initialized_before_request=true`
  - `project_initialization_seconds` should be empty
  - `cache_hit_stages` should be empty
- `steady_retrieval_warm`
  - `cache_hit_stages` should include retrieval/render/prompt hits
  - `cache_hit_stages` must not include `answer_cache_hit`
- `steady_answer_warm`
  - `cache_hit_stages` should include `answer_cache_hit`

## Metric Reading

- `service_startup_wall_seconds`
  - process spawn to `/health` ready
- `startup_ready_seconds`
  - service-reported startup readiness from `/health`
- `project_initialization_seconds`
  - first-request project loading cost inside the service
- `query_seconds`
  - `onehop_total` reported by the service trace
- `request_wall_seconds`
  - client-observed HTTP latency for the measured request
