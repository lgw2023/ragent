# Latency Benchmark Summary

- Project: `example/demo_diet_kg_5`
- Runs per scenario: 5
- Cache targets: `/Volumes/SSD1/ragent/example/demo_diet_kg_5/kv_store_llm_response_cache.sqlite`
- Environment snapshot: `benchmark/latency_20260421_212345/env_snapshot.txt`
- Query: 我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？
- Warm scenarios are primed once before measured runs; cold scenarios clear the query cache before every measured run.
- Warm runs now honor direct answer-cache hits before retrieval when the code path supports it, so they reflect end-to-end warm latency more accurately.
- `wall_seconds`: external `/usr/bin/time`, includes `uv` + Python startup/import overhead.
- `in_process_wall_seconds`: from `initialize_rag()` start to query shutdown inside Python.
- `init_seconds`: `rag_initialization_total` from code trace.
- `query_seconds`: `onehop_total` from code trace.
- Each run also saves raw stdout/stderr in the same output directory for postmortem analysis.

| scenario | wall median/mean (s) | inproc median/mean (s) | init median/mean (s) | query median/mean (s) | warm hit runs | cache hits seen |
|---|---:|---:|---:|---:|---:|---|
| `graph.rerank_off.cache_cold` | 34.090 / 33.648 | 23.158 / 24.029 | 4.231 / 4.359 | 18.898 / 19.645 | 0/0 | 0 |
| `graph.rerank_off.cache_warm` | 10.410 / 10.414 | 4.054 / 4.076 | 4.036 / 4.064 | 0.005 / 0.005 | 5/5 | answer_cache_hit |
| `graph.rerank_on.cache_cold` | 35.310 / 34.428 | 26.491 / 26.238 | 4.416 / 4.630 | 22.054 / 21.587 | 0/0 | 0 |
| `graph.rerank_on.cache_warm` | 13.330 / 13.216 | 4.454 / 4.716 | 4.437 / 4.701 | 0.008 / 0.008 | 5/5 | answer_cache_hit |
| `hybrid.rerank_off.cache_cold` | 23.000 / 23.696 | 17.203 / 17.009 | 3.828 / 4.111 | 12.776 / 12.876 | 0/0 | 0 |
| `hybrid.rerank_off.cache_warm` | 10.250 / 10.234 | 3.594 / 3.595 | 3.584 / 3.583 | 0.006 / 0.006 | 5/5 | answer_cache_hit |
| `hybrid.rerank_on.cache_cold` | 26.450 / 26.806 | 18.288 / 18.686 | 4.445 / 4.623 | 13.949 / 14.040 | 0/0 | 0 |
| `hybrid.rerank_on.cache_warm` | 11.350 / 11.616 | 4.101 / 4.109 | 4.089 / 4.096 | 0.007 / 0.007 | 5/5 | answer_cache_hit |
