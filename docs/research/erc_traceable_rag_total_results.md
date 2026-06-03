# ERC Traceable RAG Total Results Index

Updated: `2026-06-03`

This is the unified result index for the ERC Traceable RAG research line in [`Goal.md`](../../Goal.md). It defines the current source of truth, how the generated report maps to artifacts, which claims are supported, and which work remains.

## 1. Document Roles

| document or artifact | role | current use |
|---|---|---|
| [`Goal.md`](../../Goal.md) | Research controller. | Use its top status block for current execution state; older planning sections are historical. |
| [`erc_traceable_rag_total_results.md`](./erc_traceable_rag_total_results.md) | Unified result index. | Start here for source-of-truth paths, supported claims, and remaining work. |
| [`erc_traceable_rag_report.md`](./erc_traceable_rag_report.md) | Generated manuscript-style technical report. | Use for detailed tables, slice attribution, cache controls, fresh build audit, and verification commands. Regenerate through `tools/erc_research_report.py`. |
| [`summary.md`](../../benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/summary.md) | Per-run summary for the current main live matrix. | Compact machine-derived view of B0-B7-Full after the follow-up fixes. |
| [`summary.md`](../../benchmark/erc_full_eval_dqe_full_strict_cold_20260602_151636/summary.md) | Per-run summary for the strict Full-only cache control. | Supplemental cache and latency validation only. |
| [`separation_summary.json`](../../benchmark/erc_full_eval_20260527_155656/build_inference_separation/separation_summary.json) | Fresh build/raw replay/read-only audit. | Current engineering audit for fresh materialization; not the current retrieval/QA metric table. |
| [`fresh_online_build_audit.md`](../../benchmark/erc_full_eval_20260527_155656/fresh_online_build_audit.md) | Earlier checkpoint. | Historical only; prefer `separation_summary.json`. |

If documents disagree, prefer the underlying `jsonl`, `tsv`, `json`, and the explicit artifact paths in this index.

## 2. Current Source Of Truth

| evidence line | current artifact | purpose | paper use |
|---|---|---|---|
| DQE full mapped dataset | [`erc_evidence_questions_dqe_full_20260601_000156.jsonl`](../../benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl) | 186-question ERC dataset mapped to real ragent chunk provenance. | Main dataset. |
| Dataset audit | [`dataset_audit.md`](../../benchmark/erc_dqe_dataset_audit_20260601_000156/dataset_audit.md) | Question quality, distributions, duplicate, and answer-risk audit. | Dataset section evidence. |
| Provenance mapping audit | [`mapping_audit.md`](../../benchmark/erc_dqe_mapping_20260601_000156/mapping_audit.md) | DQE `source_unit_id` to real ragent `chunk_id` mapping and repair audit. | Provenance section evidence. |
| Current main live matrix | [`benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014`](../../benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014) | B0-B7-Full live ablation, LLM judge, DQE slices, component attribution, and cache phases after follow-up fixes. | Main retrieval/QA result line. |
| Strict cache control | [`benchmark/erc_full_eval_dqe_full_strict_cold_20260602_151636`](../../benchmark/erc_full_eval_dqe_full_strict_cold_20260602_151636) | Full-only live control with per-row cache clearing. | Supplemental latency and cache-semantics evidence. |
| Fresh build/replay audit | [`separation_summary.json`](../../benchmark/erc_full_eval_20260527_155656/build_inference_separation/separation_summary.json) | Fresh online build, raw replay, and read-only replay digest check. | Engineering section only; online/raw-replay equivalence is not validated. |
| Follow-up diagnostics | [`followup_diagnostics`](../../benchmark/erc_full_eval_20260527_155656/followup_diagnostics) | Selection-drop, query-variant, replay digest, and cache-semantics diagnosis from the pre-fix artifact. | Explains why the follow-up fixes were needed. |
| Selection-fix live subset | [`benchmark/erc_full_eval_followup_selection_fix_20260603`](../../benchmark/erc_full_eval_followup_selection_fix_20260603) | 17-case live validation for preserving high-scored rerank candidates during evidence selection. | Supports the repair diagnosis; not a headline table. |
| Query-variant live subset | [`benchmark/erc_full_eval_followup_query_variant_fix_20260603`](../../benchmark/erc_full_eval_followup_query_variant_fix_20260603) | 58-case live validation for weak split-only query-variant filtering. | Supports the repair diagnosis; not a headline table. |
| Gold replay harness | [`benchmark/erc_dqe_full_gold_replay_20260601_000156`](../../benchmark/erc_dqe_full_gold_replay_20260601_000156) | Deterministic scoring and attribution sanity check. | Appendix engineering sanity only; never report as live performance. |
| Previous live matrices | `benchmark/erc_full_eval_20260527_155656`, `benchmark/erc_full_eval_dqe_full_20260601_1233_retry1` | Earlier live results before the follow-up fixes or with different process state. | Historical process audit only. |

LLM constraint for all ERC live experiments, LLM judge reruns, and report-refresh measurements: use only `.env` values `LLM_MODEL_URL=https://api.deepseek.com` and `LLM_MODEL=deepseek-v4-flash`. Do not switch to `deepseek-v4-pro`, Claude Opus, or any other LLM to improve results. DeepInfra embedding configuration may still be used from `.env`.

## 3. Goal.md Alignment

| Goal.md research target | current status | supporting artifact | interpretation |
|---|---|---|---|
| Real, traceable DQE-backed dataset | Complete for machine mapping | [`mapping_audit.md`](../../benchmark/erc_dqe_mapping_20260601_000156/mapping_audit.md) | 186 questions and 331 required evidence items map to real project chunks. Manual review remains for repaired and table-sensitive cases. |
| B0-B7-Full real live ablation | Complete after follow-up fixes | [`metrics.tsv`](../../benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/metrics.tsv) | Use retrieval-layer evidence coverage as the headline. |
| Selection/query follow-up repair | Complete for current round | Diagnostics plus the two follow-up subset artifacts | Selection-drop failures were materially reduced; query-variant regression was mitigated but not eliminated. |
| DQE capability slices and component attribution | Complete | [`dqe_slice_metrics.tsv`](../../benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/dqe_slice_metrics.tsv), [`component_delta_by_slice.tsv`](../../benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/component_delta_by_slice.tsv), [`per_question_component_attribution.jsonl`](../../benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/per_question_component_attribution.jsonl) | Supports per-component gains, regressions, and failure analysis. |
| Traceable provenance | Complete for mapped required evidence | [`mapping_audit.md`](../../benchmark/erc_dqe_mapping_20260601_000156/mapping_audit.md) | `page`, `source_ref`, `file_path`, `section_path`, and `chunk_id` come from real project metadata. |
| Full cache phase measurement | Complete, with caveats | Main live [`latency_cache_summary.md`](../../benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/latency_cache_summary.md), strict control [`latency_cache_summary.md`](../../benchmark/erc_full_eval_dqe_full_strict_cold_20260602_151636/latency_cache_summary.md) | Answer cache acceleration is supported; retrieval-cache and keyword-cache semantics remain caveated. |
| Fresh online build and raw replay | Partially complete | [`separation_summary.json`](../../benchmark/erc_full_eval_20260527_155656/build_inference_separation/separation_summary.json) | Both paths completed, but their logical snapshots differ. |
| Read-only replay inference | Complete | [`separation_summary.json`](../../benchmark/erc_full_eval_20260527_155656/build_inference_separation/separation_summary.json) | `readonly_snapshot_unchanged=True`. |
| Online/raw-replay equivalence | Not validated | [`separation_summary.json`](../../benchmark/erc_full_eval_20260527_155656/build_inference_separation/separation_summary.json) | `online_vs_replay_match=False`; do not claim equivalence. |

## 4. Dataset And Provenance Audit

The selected dataset is `dqe_gold_mapped_full_186`.

| item | value |
|---|---:|
| DQE current gold questions | 186 |
| Answerable questions | 186 |
| Empty gold evidence | 0 |
| Empty answer key points | 0 |
| Possibly over-general gold answers | 18 |
| Duplicate question groups | 1 (`g005`, `g170`) |
| Required DQE evidence items | 331 |
| Matched evidence items | 331 |
| Unmatched evidence items | 0 |
| Unique matched source units | 144 |
| Source-id repairs verified against paired gold evidence | 38 |
| Questions with at least two matched evidence items | 97 / 186 |

Mapping contract:

- DQE `source_unit_id` is not treated as a live ERC `chunk_id`.
- Repairs are constrained to the same DQE document and verified against paired `gold_evidence`.
- Real ragent metadata supplies `page`, `source_ref`, `file_path`, `section_path`, and `chunk_id`.
- Missing evidence must remain unmatched; synthetic provenance is not allowed.

## 5. Main Live Retrieval Results

Source: [`benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014`](../../benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014)

- Backend: `live`
- Dataset: `dqe_gold_mapped_full_186`
- External LLM / judge model: `deepseek-v4-flash`
- Questions: `186`
- Configurations: `B0, B1, B2, B3, B4, B5, B6, B7, Full`
- Result rows: `2232`
- Judge rows: `1674`
- Final judge statuses: `ok=1674`

| config | retrieval role | evidence recall@k | final evidence recall | required evidence coverage | downstream correctness |
|---|---|---:|---:|---:|---:|
| B0 | Flat Chunk RAG | 0.3315 | 0.3315 | 0.4158 | 0.6879 |
| B1 | Chunk + Rerank | 0.3315 | 0.3315 | 0.4158 | 0.7204 |
| B2 | Graph-only | 0.4581 | 0.3468 | 0.5739 | 0.7004 |
| B3 | Chunk + Entity | 0.3315 | 0.3315 | 0.5575 | 0.7267 |
| B4 | Chunk + Entity + Relation | 0.3315 | 0.3315 | 0.5667 | 0.7276 |
| B5 | + Graph Expansion | 0.5033 | 0.3889 | 0.5954 | 0.7225 |
| B6 | + Query Variants | 0.4565 | 0.3658 | 0.5843 | 0.7382 |
| B7 | + Rerank | 0.4565 | 0.4218 | 0.6123 | 0.7456 |
| Full | B7 + Evidence Selection | 0.4565 | 0.4164 | 0.6096 | 0.7404 |

Supported headline conclusions:

1. Entity retrieval improves structured required evidence coverage: `B0 0.4158 -> B3 0.5575`.
2. Graph expansion gives the strongest candidate recall: `B5 evidence_recall@k=0.5033`.
3. Post-fusion rerank is the strongest current end-to-end retrieval setting: `B7 final_evidence_recall=0.4218`, `required_evidence_coverage=0.6123`.
4. Full evidence selection is improved but still not the main success claim: `B7 -> Full` drops final evidence recall `0.4218 -> 0.4164` and required evidence coverage `0.6123 -> 0.6096`.
5. Downstream correctness remains diagnostic. The best correctness is `B7=0.7456`; `Full=0.7404` is above `B0=0.6879` and `B5=0.7225`.

## 6. Follow-Up Fix Results

The follow-up work started from the pre-fix artifact `benchmark/erc_full_eval_20260527_155656` and diagnosed two algorithmic failure modes.

### 6.1 Evidence Selection

- Diagnostic set: 17 selection-drop cases.
- Offline selector replay after the patch improved 9/17 cases and worsened 0/17.
- Live subset artifact: [`benchmark/erc_full_eval_followup_selection_fix_20260603`](../../benchmark/erc_full_eval_followup_selection_fix_20260603).
- Selection subset result: Full final evidence recall improved from 0.1373 to 0.4657 on the targeted cases; B7 remains stronger than Full on the same subset.
- Full rerun result: `selection_drop` failure count is now 2 in the current failure taxonomy, versus 15 in the pre-fix artifact.

Interpretation: the preservation fix materially reduces evidence-selection damage, but Full still trails B7 by a small margin in the full matrix. It should be reported as a repaired negative result, not as the primary success claim.

### 6.2 Query Variants

- Diagnostic set: 58 query-variant regression cases.
- Live subset artifact: [`benchmark/erc_full_eval_followup_query_variant_fix_20260603`](../../benchmark/erc_full_eval_followup_query_variant_fix_20260603).
- On the targeted subset, the B6-B5 final-recall gap improved from -0.1408 to -0.0201, and old final-recall regressions dropped from 13 to 5.
- Full rerun result: B6 still trails B5 in final evidence recall (`0.3658` vs `0.3889`) and evidence recall@k (`0.4565` vs `0.5033`).

Interpretation: weak split-only query variant filtering reduces the regression, but query variants are still a tuning target rather than a settled positive result.

## 7. Slice Attribution And Failure Analysis

The current live matrix includes:

- [`dqe_slice_metrics.tsv`](../../benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/dqe_slice_metrics.tsv)
- [`component_delta_by_slice.tsv`](../../benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/component_delta_by_slice.tsv)
- [`per_question_component_attribution.jsonl`](../../benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/per_question_component_attribution.jsonl)
- [`failure_taxonomy.md`](../../benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/failure_taxonomy.md)

Key B7 slices:

| DQE slice | n | correctness | final recall | required coverage |
|---|---:|---:|---:|---:|
| Full mapped dataset | 186 | 0.7456 | 0.4218 | 0.6123 |
| Multi-evidence `>=2` | 97 | 0.6587 | 0.3242 | 0.5618 |
| Multi-document | 63 | 0.5952 | 0.2796 | 0.5409 |
| Repair review set | 15 | 0.5933 | 0.4111 | 0.5910 |
| Calculation | 16 | 0.9000 | 0.6250 | 0.6897 |
| Hard | 120 | 0.6895 | 0.3767 | 0.5865 |

Failure taxonomy:

| failure type | count |
|---|---:|
| no_primary_failure | 105 |
| no_required_coverage_gain | 11 |
| selection_drop | 2 |
| unsupported_claim_risk | 68 |

## 8. Cache And Latency Results

### 8.1 Current Main Live Matrix

The main live artifact measures Full cache phases, but its `full_no_cache` aggregate still records `answer_cache_hit`. Use these values for the observed runtime path, not for a strict cold-start claim.

| cache phase | p50 s | p95 s | mean s |
|---|---:|---:|---:|
| Full no cache, observed runtime path | 19.1345 | 30.2838 | 19.7132 |
| Retrieval cache warm | 8.5570 | 19.2100 | 9.6978 |
| Answer cache warm | 0.0210 | 0.0600 | 0.0279 |
| Keyword candidate cache warm | 20.5190 | 43.8780 | 22.7958 |

### 8.2 Strict Per-Row Full Control

Source: [`benchmark/erc_full_eval_dqe_full_strict_cold_20260602_151636`](../../benchmark/erc_full_eval_dqe_full_strict_cold_20260602_151636)

- `clear_cache_per_live_row=True`
- Result rows: `744`
- Judge rows: `186`
- Judge statuses: `ok=186`
- Strict `full_no_cache` row distribution: `none=186`

| cache phase | p50 s | p95 s | mean s | row cache-hit distribution |
|---|---:|---:|---:|---|
| Full no cache | 20.2990 | 33.8945 | 21.9469 | `none=186` |
| Retrieval cache warm | 20.7230 | 34.8985 | 21.6960 | `none=184`, `retrieval_cache_hit=1`, `answer_cache_hit=1` |
| Answer cache warm | 0.0140 | 0.0437 | 0.0214 | `answer_cache_hit=186` |
| Keyword candidate cache warm | 22.8380 | 36.8957 | 22.5431 | `keyword_candidate_cache_hit=159`, `none=26`, `answer_cache_hit=1` |

This strict control confirms the Full cold-path latency and answer-cache acceleration. It also shows that retrieval-cache warm semantics need diagnosis before retrieval-cache acceleration is promoted as a durable conclusion.

## 9. Build, Replay, And Read-Only Audit

Current source: [`separation_summary.json`](../../benchmark/erc_full_eval_20260527_155656/build_inference_separation/separation_summary.json)

| check | online build | offline raw replay |
|---|---:|---:|
| PDF or raw-unit files | 8 | 8 |
| Graph nodes | 7093 | 7213 |
| Graph edges | 24202 | 24657 |
| Entity VDB rows | 7078 | 7197 |
| Relationship VDB rows | 24135 | 24657 |
| Chunk VDB rows | 1992 | 1992 |
| Doc status rows | 1982 | 1982 |
| Digest | `33c855d175fbecc814b33dccd3daeb21` | `0c5ec700ccd0e71662d7fade074b00b0` |

Audit result:

- Fresh online build completed for 8 PDFs.
- Raw export and offline replay completed for 8 raw-unit files.
- `readonly_snapshot_unchanged=True`: read-only replay inference isolation is validated.
- `online_vs_replay_match=False`: online build and raw replay equivalence is not validated.

Paper-usable engineering scope: retrieval/QA plus read-only replay isolation. Do not claim online/raw-replay equivalence until the digest mismatch is diagnosed and resolved.

## 10. Historical And Non-Main Results

| artifact family | classification | treatment |
|---|---|---|
| `benchmark/erc_full_eval_20260527_155656` | Pre-fix live matrix plus current fresh build/replay audit. | Use only for engineering audit and before/after comparison, not current retrieval metrics. |
| `benchmark/erc_full_eval_dqe_full_20260601_1233_retry1` | Earlier 186-question DQE live run against `existing_project_copy`. | Historical process audit only. |
| `benchmark/erc_full_eval_20260527_155656/historical_20q_backup_20260602_103907` | Superseded 20-question live pilot. | Do not use for current claims. |
| `benchmark/erc_dqe_full_gold_replay_20260601_000156` | Gold replay sanity harness. | Appendix only. It proves the scoring and attribution pipeline can recognize injected gold evidence. |
| `benchmark/latency_smoke_*`, `benchmark/retrieval_cross_*`, `benchmark/keyword_cache_benefit_*` | Earlier standalone latency, retrieval, and keyword-cache diagnostics. | Historical engineering evidence. Do not replace the 186-question live and strict-control results with these numbers. |
| Historical DQE-Bench system scores from `/Volumes/SSD1/ragent_benchmark` | External benchmark background. | May describe question-set quality and discrimination only. Never present as ERC live results. |

## 11. Remaining Work

1. Improve Full evidence selection so it preserves B7 evidence while still providing coverage-aware final context selection.
2. Further tighten query-variant generation/filtering because B6 remains below B5 in candidate and final evidence recall.
3. Manually review repaired and table-sensitive evidence mappings, especially the 38 source-id repairs and the repair-review slice.
4. Diagnose the online/raw-replay digest mismatch across graph nodes, edges, entity VDB, relationship VDB, chunk metadata, and materialization order.
5. Diagnose retrieval-cache and keyword-candidate-cache semantics before promoting non-answer-cache speedups as durable claims.
6. Treat downstream answer quality as a separate grounding/prompting track; do not use stronger external LLMs to hide retrieval-layer limitations.
