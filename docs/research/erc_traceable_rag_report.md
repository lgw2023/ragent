# ERC Traceable RAG Research Report

This manuscript-style report materializes the ERC task in `Goal.md`: research questions, experimental design, live benchmark results, result analysis, cache behavior, and build/replay separation for provenance-aware ERC evidence graph RAG.

Overall result index: [`erc_traceable_rag_total_results.md`](./erc_traceable_rag_total_results.md).

## Abstract

Professional PDF question answering often requires combining definitions, tables, threshold rules, and provenance-bearing evidence across sections or documents. This report evaluates a provenance-aware Entity-Relation-Chunk (ERC) evidence graph for traceable multi-evidence RAG, using the current reproducible local benchmark artifacts rather than gold replay as system performance.

The primary empirical claim is scoped to retrieval-layer evidence coverage and provenance organization. Downstream answer quality metrics are retained only as diagnostics because a business system can consume retrieved graph evidence and assemble its own prompt, context, and final response.

The current live dataset is `benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl` with 186 questions, 42 source files, 331 matched project chunk links across 331 required source-reference annotations, and 16 calculation-oriented questions. The compared systems are B0 chunk-only, B1 chunk+rerank, B2 graph-only, B3 chunk+entity, B4 chunk+entity+relation, B5 chunk+entity+relation+graph expansion, B6 B5+query variants, B7 B6+rerank, Full B7+evidence selection.

## 1. Research Questions

RQ1: Does a provenance-aware ERC heterogeneous evidence graph improve multi-evidence coverage over chunk-only retrieval?

RQ2: Which retrieval components contribute most under the current implementation: chunk retrieval, entity/relation retrieval, graph expansion, rerank, query variants, or evidence selection?

RQ3: Does the engineering path support materialized evidence graphs, replayable build artifacts, read-only inference, and practical cache acceleration?

## 2. Experimental Design

### Data

The experiment uses `benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl`. The dataset split is: dqe_gold_mapped_full_186=186. Source files are: `0137412035e616d1c2ee4ac462d234af97e7f3bcce789a17ea5fb1ea86b3aaab.jpg`, `090f965b5fa56e981eb0b1235d39876065312fd3ffd8444d350271caecb08fd2.jpg`, `0b2d40a355a1dbb695ddd97b0f89472a468a953982d5e2968f5031d87a0ed4fe.jpg`, `20265bebe74dd6c9af46012bc03a798800d4902090aabcfbc91c6bde91a9eb89.jpg`, `25943dfb14f8bc88def8a5c1580cb1ae7bb16d5924744d6afbfd0369d1d6c87e.jpg`, `2b52cbccb44c310bf8fc926aa7e432743d541faeb5342dce21ce467c6850e1e9.jpg`, `2c7bd7a5253513221b72e6fc3ab7fc8deda173197c58497294f4da4b3f0d8d37.jpg`, `3221c854a39ae6e7239fc809ade486deef0822d31ea950dcaf6347d6cb16f45c.jpg`, `34a448bf51434bf76380611e8a24aee7183bd6318c80cc32e7223ad397cca524.jpg`, `3549de20596124689b56747b855ce5948d70908dc5f6749954ea770d60ec6e4d.jpg`, `39235c7f5bc83623117525b0977764bafed1d4513a4c8ac5dfa867e31261ebd6.jpg`, `442131518d8bc978baa3fd355611cc232ac7d793d77802ab1a0b1b80301dc363.jpg`, `466cf951d85d7d6a50ca81d19a13346b206709ddd3b8e5c3ac956894b3741416.jpg`, `5042957cc1d9cbd1d795ddfd291909de8f83fb193b014bdf47251c0374e15aa7.jpg`, `560c0fd9b565049b352b726d1ac90ca3f5637471781b65cb67d5b70bb921a0ab.jpg`, `5a6b22ff595d7d6777055286cb8ee75876e17bab86eb1ec147a70dadc2585187.jpg`, `6c30cd9091dbdcdc31253d5e8d0da0fb2742c6aee4ff6d7e3a515cd30fb2c8b4.jpg`, `740100138631c147bb2c90d59c961964affb6b1c33aec222bf41e195be68b3e1.jpg`, `81851e892b0b3af9b966981f64fe315ff2b85e8e85124f26755f111f82b5d847.jpg`, `86b6fd51ceea1dc466cc3e2bd5cd875554cc91eb903c155795df0c0f2ec4aafc.jpg`, `8a636c26b834f9566709ccf7933413c65d6d727c40ab821b8711b7de975fdd8c.jpg`, `96abc28f86f6813b24c70e31926a6b3dd7bdc306832d8a1c8ab56f5a7ef06b18.jpg`, `9875cf258e89b9241eba8a3a10c50b4e68d389400edffcf38015120eb4b3692d.jpg`, `GBT1354-2018bz.pdf`, `GBT22106-2008dz.pdf`, `a3530d9c77cf00c7f58e2afb6fd8df4efec7534466dd5e4fcd0d7134c53e8a17.jpg`, `a5573d90d7f91633a1cdf43e1b1b30bb7135c5e865d3c216ae6617a91f3b057e.jpg`, `aac0bff88b1ff2964e5e34c5ebf385f6ca7c6d3bb5a6897b41da5ccad8bab83a.jpg`, `ad7954613a614da5726a11df9a020976ded85a220a529132034b916a558d02e7.jpg`, `b38a9cfbb6a7506a340d8bd648ada0ccbf79758a53af7629e295817af573cdd5.jpg`, `bcfe2d01c1a4737c47778bc7c19646978218328b3b7fc2a10e3754a384b23e9c.jpg`, `c797926828f8f25692a56ec1ee21c451fe98a5147f8ef34f2c3ae17dddc413f4.jpg`, `cbbbc194bd2659e4a24895ae5d03a184d1f1e5271fb4b8ad44923567da9e4f5d.jpg`, `d3caf253c01ed7264b6618b96b91154276c99e29a0b069a75ccd50b4613e2271.jpg`, `d7946660abacea6d941e6dbfd40ed35489bbfc8c7563153f29a2c1cc3f34f547.jpg`, `e9772e706e0a129caf22f2a012f1f372590c5682ac819043c515eddbc0ff327c.jpg`, `ed72331475842d2551a578d068b7cc7e1bbe212d9d7d723131573c0943767346.jpg`, `f18eb9950d397556df8e5b5b1b842ea6c75ce97aa62add19d30dfaab90d899d6.jpg`, `fcb6e950b16d72e8d965488a6ca47481a5bfae1482570a81c48aae9e957b4d08.jpg`, `中国居民膳食指南_2022.pdf`, `成人肥胖食养指南_2024.pdf`, `成人高血压食养指南_2022.pdf`.

Each question includes a gold answer, required entities/relations, and source-reference requirements. The full-evaluation artifact writes `annotated_dataset.jsonl` with matched `chunk_id`, `source_ref`, `page_numbers`, `section_path`, and `file_path` where a project chunk is found. Unmatched source-reference requirements remain explicitly marked as unmatched; no pseudo pages or synthetic chunks are generated.

### DQE Dataset Construction And Mapping Audit

- Dataset audit: `benchmark/erc_dqe_dataset_audit_20260601_000156/dataset_audit.md`
- Mapping audit: `benchmark/erc_dqe_mapping_20260601_000156/mapping_audit.md`
- Capability tags: `benchmark/erc_dqe_mapping_20260601_000156/dqe_capability_tags.jsonl`
- Slice manifest: `benchmark/erc_dqe_mapping_20260601_000156/dqe_slice_manifest.json`

Dataset quality checks retain the DQE full mapped pool while making known annotation risks explicit.

| check | value |
|---|---|
| samples | 186 |
| answerability | `answerable`=186 |
| document scope | `single_document`=123, `multi_document`=63 |
| modality | `text_document`=124, `multimodal_document`=62 |
| evidence source count | `1`=89, `2`=71, `4`=13, `3`=9, `5`=3, `6`=1 |
| phase8 action | `keep`=152, `replace`=26, `no_decision`=8 |
| possibly over-general gold answers | 18 |
| duplicate question groups | 1 |

The DQE-to-ragent mapping uses only real project chunks and metadata; no pseudo pages, synthetic `chunk_id`, or fabricated `source_ref` values are introduced.

| mapping check | value |
|---|---|
| project chunks loaded | 1725 |
| required DQE evidence items | 331 |
| matched evidence items | 331 |
| unmatched evidence items | 0 |
| unique resolved source units | 144 |
| source id repairs from gold evidence | 38 |
| questions with >=1 matched evidence | 186 / 186 |
| questions with >=2 matched evidence | 97 / 186 |
| source unit conflicts | 0 |
| evidence index conflicts | 0 |

The DQE slices are used as control variables for component attribution rather than as hand-picked favorable subsets.

| slice | n | criteria |
|---|---|---|
| dqe_full_mapped | 186 | all selected mapped DQE current-gold questions |
| dqe_phase8_keep | 152 | phase8_action == keep |
| dqe_phase8_replace_stress | 26 | phase8_action == replace; stress/error-analysis only unless manually promoted |
| dqe_multi_evidence_ge2 | 97 | matched_evidence_count >= 2 |
| dqe_multi_evidence_ge3 | 26 | matched_evidence_count >= 3 |
| dqe_multi_document | 63 | document_scope == multi_document or source_doc_count >= 2 |
| dqe_table_multimodal_stress | 128 | modality == multimodal_document or source_type_mix includes table/image_description |
| dqe_repair_review_set | 15 | source unit id repaired by paired gold evidence |
| dqe_calculation | 16 | question_type == aggregation_calculation |
| dqe_hard | 120 | difficulty == hard |
| dqe_selection_stress_candidates | 72 | matched_evidence_count >= 2 and answer_key_point_count >= 4 |

### Systems

B0 is a flat chunk vector baseline. B1 adds rerank. B2 disables chunk vector retrieval and uses entity/relation graph retrieval plus graph expansion. B3 combines chunk and entity retrieval. B4 adds relation retrieval. B5 adds graph-neighborhood expansion. B6 adds query variants. B7 adds rerank after graph/variant fusion. Full adds coverage-aware evidence selection.

### Metrics

The primary retrieval-layer metrics are Evidence Recall@K, Final Evidence Recall, Required Evidence Coverage, and latency. These are computed from live retrieved/final chunks against true project chunk IDs and manually verified required evidence. Citation Precision/Recall and LLM-judged answer quality are reported as diagnostics for downstream citation grounding and business answer generation, not as the main retrieval-layer success criteria.

### LLM Model Constraint

All external LLM-backed ERC experiments, LLM judge runs, reruns, and report-refresh measurements are constrained to `LLM_MODEL_URL=https://api.deepseek.com` and `LLM_MODEL=deepseek-v4-flash`. The experiment protocol does not switch to `deepseek-v4-pro`, Claude Opus, or any other LLM to improve results; model-capability limits must be reported as limitations.

## 3. Live Results

The selected live artifact is `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014`. It was run with backend `live`, judge mode `llm`, configs `B0, B1, B2, B3, B4, B5, B6, B7, Full`, and judge statuses `{'ok': 1674}`. Paper scope is: retrieval/QA ablation on an existing live project only; not evidence for fresh build/replay.

### 3.1 Retrieval-Layer Framing

The primary evaluation target is the knowledge-graph retrieval and evidence organization layer, not the downstream business answer generator. Final answer quality depends on prompt construction, context assembly, model choice, and response formatting outside this retrieval layer, so correctness and faithfulness are retained as diagnostics rather than used as the main claim.

### 3.2 Retrieval-Layer Evidence Coverage

The strongest Evidence Recall@K value is 0.5033, reached by `B5`. The strongest Final Evidence Recall value is 0.4218, reached by `B7`. The strongest Required Evidence Coverage value is 0.6123, reached by `B7`.

- `B2` required evidence coverage is 0.5739, +0.1581 versus B0.
- `B5` required evidence coverage is 0.5954, +0.1796 versus B0.
- `B6` required evidence coverage is 0.5843, +0.1685 versus B0.
- `B7` required evidence coverage is 0.6123, +0.1965 versus B0.
- `Full` required evidence coverage is 0.6096, +0.1938 versus B0.

### 3.3 Retrieval Component Findings

- `B0 -> B3`: Entity retrieval improves structured required-evidence coverage over chunk-only retrieval. `required_evidence_coverage` 0.4158 -> 0.5575 (+0.1417).
- `B3 -> B4`: Relation retrieval adds a clear coverage gain over entity-only retrieval. `required_evidence_coverage` 0.5575 -> 0.5667 (+0.0092).
- `B4 -> B5`: Graph expansion is the main recall jump and should be read separately from downstream answer-quality tradeoffs. `final_evidence_recall` 0.3315 -> 0.3889 (+0.0574).
- `B5 -> B6`: Query variants regress final evidence recall in this artifact, so query expansion needs tighter filtering. `final_evidence_recall` 0.3889 -> 0.3658 (-0.0231).
- `B6 -> B7`: Post-fusion rerank recovers final evidence after the query-variant stage. `final_evidence_recall` 0.3658 -> 0.4218 (+0.0560).
- `B7 -> Full`: Evidence selection reduces final evidence recall in this artifact, so the selection strategy still needs tuning. `final_evidence_recall` 0.4218 -> 0.4164 (-0.0054).

### 3.4 Downstream Answer Quality Diagnostic

The best downstream correctness in this artifact is `B7` at 0.7456. Full reaches correctness 0.7404, which is 0.0525 higher than B0 and 0.0179 higher than B5. This diagnostic is reported as observed, but it is not the main retrieval-layer claim.

Faithfulness follows a similar component-sensitive diagnostic pattern: B0=0.6832, B5=0.7087, Full=0.7036. Unsupported claim rate is B0=0.2856, B5=0.2793, Full=0.2831.

### 3.5 Latency And Cache Behavior

Full no-cache latency is p50=19.1345s, p95=30.2838s, mean=19.7132s. Answer-cache warm latency is p50=0.0210s, showing that answer cache materially accelerates repeated queries under the current runtime path.

- Cache caveat: `full_no_cache` still records `answer_cache_hit`, so this artifact should not be described as a strictly isolated cold-start latency run.
- Retrieval-cache warm p50 improves from 19.1345s to 8.5570s under the same Full path.
- Answer-cache warm p50 improves from 19.1345s to 0.0210s for repeated queries.
- Keyword-candidate warm does not show a full-query latency win in this run: mean latency is 22.7958s versus 19.7132s for `full_no_cache`.

### 3.6 Build, Replay, And Read-Only Inference

This selected artifact has build mode `existing_project_copy`. It supports retrieval/QA ablation on the copied live project, but not fresh online-build versus raw-replay reproducibility.

### 3.7 DQE Slice And Component Attribution

The full DQE run is used as the measurement control layer: every aggregate result is decomposed by DQE question type, evidence count, document scope, modality, repair status, and stress tags. This prevents the report from claiming a component gain that only appears on an easy or hand-picked subset.

- Slice metrics: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/dqe_slice_metrics.tsv`
- Component deltas: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/component_delta_by_slice.tsv`
- Per-question attribution: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/per_question_component_attribution.jsonl`
- Failure taxonomy: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/failure_taxonomy.md`

B7 is the best current end-to-end retrieval setting, so the slice table below uses B7 as the main positive reference.

| DQE slice | n | correctness | final_recall | required_coverage | unsupported_claim_rate |
|---|---|---|---|---|---|
| dqe_full_mapped | 186 | 0.7456 | 0.4218 | 0.6123 | 0.2776 |
| dqe_phase8_keep | 152 | 0.7778 | 0.4227 | 0.6142 | 0.2575 |
| dqe_phase8_replace_stress | 26 | 0.6137 | 0.4115 | 0.6012 | 0.3854 |
| dqe_multi_evidence_ge2 | 97 | 0.6587 | 0.3242 | 0.5618 | 0.3357 |
| dqe_multi_evidence_ge3 | 26 | 0.6468 | 0.1327 | 0.4588 | 0.3827 |
| dqe_multi_document | 63 | 0.5952 | 0.2796 | 0.5409 | 0.3681 |
| dqe_table_multimodal_stress | 128 | 0.7179 | 0.3655 | 0.5828 | 0.3190 |
| dqe_repair_review_set | 15 | 0.5933 | 0.4111 | 0.5910 | 0.3133 |
| dqe_calculation | 16 | 0.9000 | 0.6250 | 0.6897 | 0.1000 |
| dqe_hard | 120 | 0.6895 | 0.3767 | 0.5865 | 0.3104 |
| dqe_selection_stress_candidates | 72 | 0.6558 | 0.2609 | 0.5276 | 0.3325 |

The component deltas on the full mapped slice identify where the algorithmic changes actually add or lose evidence.

| component | comparison | delta_final_recall | delta_required_coverage | delta_correctness | delta_faithfulness |
|---|---|---|---|---|---|
| chunk_to_chunk_entity | B0 -> B3 | 0.0000 | 0.1417 | 0.0388 | 0.0459 |
| entity_to_relation | B3 -> B4 | 0.0000 | 0.0092 | 0.0008 | -0.0158 |
| relation_to_graph_expansion | B4 -> B5 | 0.0573 | 0.0287 | -0.0050 | -0.0046 |
| graph_to_query_variants | B5 -> B6 | -0.0231 | -0.0111 | 0.0157 | -0.0277 |
| query_variants_to_rerank | B6 -> B7 | 0.0560 | 0.0280 | 0.0074 | 0.0252 |
| rerank_to_evidence_selection | B7 -> Full | -0.0054 | -0.0027 | -0.0052 | -0.0026 |
| chunk_to_full | B0 -> Full | 0.0849 | 0.1938 | 0.0525 | 0.0204 |

`dqe_repair_review_set` and `dqe_selection_stress_candidates` are especially important for auditability and failure diagnosis. The former checks repaired source-unit mappings; the latter isolates questions where final evidence selection is expected to preserve multi-evidence candidates.

| slice | n | B0_required_coverage | B7_required_coverage | Full_required_coverage | B7_final_recall | Full_final_recall |
|---|---|---|---|---|---|---|
| dqe_repair_review_set | 15 | 0.4889 | 0.5910 | 0.5910 | 0.4111 | 0.4111 |
| dqe_selection_stress_candidates | 72 | 0.3704 | 0.5276 | 0.5310 | 0.2609 | 0.2678 |

The failure taxonomy is retained as part of the result, not filtered away.

| failure type | count |
|---|---|
| no_primary_failure | 105 |
| no_required_coverage_gain | 11 |
| selection_drop | 2 |
| unsupported_claim_risk | 68 |

Failure tags show where the residual errors concentrate; these rows are retained as negative evidence rather than filtered out.

| failure type | top concentration tags |
|---|---|
| no_required_coverage_gain | `multi_evidence_ge2`=10, `selection_stress_candidate`=7, `hard`=6, `multi_document`=6, `keypoint_dense`=5 |
| selection_drop | `hard`=2, `table_or_multimodal`=2 |
| unsupported_claim_risk | `table_or_multimodal`=52, `hard`=46, `multi_evidence_ge2`=38, `selection_stress_candidate`=32, `multi_document`=27 |

Interpretation: relation retrieval, graph expansion, and post-fusion reranking give measurable coverage or final-recall gains. Query variants alone regress final recall in this run and need tighter query filtering. Full evidence selection is currently a failure target because it drops final evidence recall and required coverage relative to B7.


A separate fresh online build audit is available at `benchmark/erc_full_eval_20260527_155656`. It completed 8 online PDF builds and materialized a graph with 7093 nodes, 24202 edges, 1982 document status rows, and digest `33c855d175fbecc814b33dccd3daeb21`. Raw replay did not validate equivalence: `online_vs_replay_match` is `False`.

## 4. Discussion

The component ablation should be read as an ordered retrieval-layer path from B0 through B7 and Full: B3 isolates entity retrieval, B4 relation retrieval, B5 graph expansion, B6 query variants, B7 rerank, and Full evidence selection. The main result is that graph-aware components improve structured required-evidence coverage and candidate recall, while later stages still need better selection and grounding to preserve those retrieved gains.

This framing separates the knowledge-graph retrieval contract from downstream business answer generation. A business system can consume retrieved graph evidence, assemble its own context, and evaluate its final answer separately; therefore answer-quality scores in this report should remain diagnostic rather than the primary success criterion for the retrieval module.

The live result also separates two claims. The retrieval-layer evidence-coverage claim is supported by the selected live project. The build/replay/read-only engineering claim is not supported here because the evaluation used an existing project copy.

## 5. Limitations And Next Steps

The current DQE full dataset is suitable for the main retrieval/QA ablation because it uses the full mapped DQE gold pool rather than the historical pilot. Citation precision/recall remain weak and should be treated as downstream grounding diagnostics. A fresh raw-unit replay artifact is still required before making build/replay paper claims.

## Implementation Mapping

| Goal component | Existing implementation surface |
|---|---|
| ERC provenance fields | `source_ref`, `page_numbers`, `section_path`, `source_chunk_ids` in chunk/entity/relation contexts |
| Chunk semantic retrieval | `hybrid_query()` vector chunk path and `chunks_vdb` |
| Entity/relation retrieval | `graph_query()` and `hybrid_query()` entity/relationship vector paths |
| Graph neighborhood expansion | `_find_most_related_text_unit_from_entities()` and `_find_related_text_unit_from_relationships()` |
| Query variants | `_build_diversified_retrieval_queries()` and matched query variant metadata |
| Rerank | `ragent.rerank.rerank_from_env()` integration, with fallback order when not configured |
| Evidence selection | `_select_hybrid_context_entries()` coverage-aware final chunk selection |
| Cache acceleration | query cache stages plus keyword candidate cache benchmark artifacts |
| Offline replay/read-only inference | `ragent/offline_replay.py`, `tools/export_raw_merge_units.py`, `tools/replay_raw_merge_units_to_project.py` |

## Dataset

- Source: `benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl`
- Questions: `186`
- Requires calculation: `16`

### Dataset Split

| dataset | count |
|---|---:|
| `dqe_gold_mapped_full_186` | 186 |

### Question Types

| question_type | count |
|---|---:|
| `aggregation_calculation` | 16 |
| `comparison` | 15 |
| `condition_filtering` | 16 |
| `fact_lookup` | 13 |
| `multi_document_multimodal_reasoning` | 28 |
| `multi_document_text_reasoning` | 35 |
| `single_document_multimodal_reasoning` | 34 |
| `single_document_text_reasoning` | 29 |

### Difficulty

| difficulty | count |
|---|---:|
| `easy` | 13 |
| `hard` | 120 |
| `medium` | 53 |

## Full Evaluation Artifacts

- Directory: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014`
- Result class: `Live`
- Fresh-build paper-table eligibility: `no`
- Paper-usable scope: retrieval/QA ablation on an existing live project only; not evidence for fresh build/replay
- Eligibility reason: not a fresh online-build plus raw-replay run
- Judge mode: `llm`
- Allowed external LLM: `LLM_MODEL_URL=https://api.deepseek.com`, `LLM_MODEL=deepseek-v4-flash`
- Judge statuses: `{'ok': 1674}`
- Results JSONL: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/results.jsonl`
- Judge JSONL: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/judge_results.jsonl`
- Metrics TSV: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/metrics.tsv`
- Summary: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/summary.md`
- Cache summary: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/latency_cache_summary.md`
- Commands: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/commands.md`
- Annotated dataset: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/annotated_dataset.jsonl`
- Build/replay separation: `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/build_inference_separation/separation_summary.json`

### Artifact Completeness And Rejudge Provenance

The selected live artifact is treated as complete only because the row counts, judge statuses, and attribution outputs are present. Rejudge/dedupe snapshots are retained to make the long-run recovery path auditable.

| artifact | non-empty rows |
|---|---|
| results.jsonl | 2232 |
| judge_results.jsonl | 1674 |
| metrics.tsv | 13 |
| dqe_slice_metrics.tsv | 100 |
| component_delta_by_slice.tsv | 78 |
| per_question_component_attribution.jsonl | 186 |
| annotated_dataset.jsonl | 186 |

| snapshot | rows | judge statuses | duplicate keys |
|---|---|---|---|
| final judge file | 1674 | ok=1674 | 0 |

### Live Result Interpretation

- Scope: retrieval/QA ablation on an existing live project only; not evidence for fresh build/replay.
- Do not use this artifact as the full paper main table for fresh build/replay claims.
- Build/replay separation is not validated here; the project was copied from an existing live graph and only read-only inference was checked.
- Primary retrieval-layer claims should use evidence coverage, final evidence recall, required evidence coverage, and latency; final answer scores are downstream-generation diagnostics.
- Downstream diagnostic: Full correctness is above B0 (0.7404 vs 0.6879).
- Downstream diagnostic: Full correctness is above B5 (0.7404 vs 0.7225); report this without retuning or question selection.
- Full Evidence Recall@K is above B0 (0.4565 vs 0.3315).
- Full Evidence Recall@K is below B5 (0.4565 vs 0.5033).

### Live Retrieval-Layer Results

| config | name | evidence_recall@k | final_recall | required_coverage | latency_p50_s | retrieval_layer_conclusion |
|---|---|---|---|---|---|---|
| B0 | Flat Chunk RAG | 0.3315 | 0.3315 | 0.4158 | 10.2985 | Text-chunk baseline; structured required-evidence coverage is weak. |
| B1 | Chunk + Rerank | 0.3315 | 0.3315 | 0.4158 | 12.1315 | Rerank-only chunk retrieval is a control for reranking without graph evidence. |
| B2 | Graph-only | 0.4581 | 0.3468 | 0.5739 | 15.7055 | Graph-only retrieval improves required-evidence coverage but loses chunk fusion. |
| B3 | Chunk + Entity | 0.3315 | 0.3315 | 0.5575 | 13.0380 | Entity retrieval improves structured coverage over chunk-only retrieval. |
| B4 | Chunk + Entity + Relation | 0.3315 | 0.3315 | 0.5667 | 10.9350 | Relation retrieval adds a clear structured-coverage gain over entity-only retrieval. |
| B5 | + Graph Expansion | 0.5033 | 0.3889 | 0.5954 | 12.9890 | Graph expansion is the main candidate-recall and required-coverage jump. |
| B6 | + Query Variants | 0.4565 | 0.3658 | 0.5843 | 14.9680 | Query variants should be read as a constraint-diversity stage and checked for recall drift. |
| B7 | + Rerank | 0.4565 | 0.4218 | 0.6123 | 16.8905 | Rerank after graph/variant fusion is the strongest current end-to-end retrieval setting. |
| Full | B7 + Evidence Selection | 0.4565 | 0.4164 | 0.6096 | 19.1345 | Evidence selection is a negative result here: it drops final required evidence versus B7. |

### Live Downstream Answer Diagnostic Results

| config | correctness | completeness | faithfulness | numerical_accuracy | required_coverage | unsupported_claim_rate |
|---|---|---|---|---|---|---|
| B0 | 0.6879 | 0.7330 | 0.6832 | 0.8860 | 0.4158 | 0.2856 |
| B1 | 0.7204 | 0.7578 | 0.6988 | 0.8825 | 0.4158 | 0.2687 |
| B2 | 0.7004 | 0.7356 | 0.6588 | 0.8238 | 0.5739 | 0.3073 |
| B3 | 0.7267 | 0.7664 | 0.7291 | 0.8718 | 0.5575 | 0.2430 |
| B4 | 0.7276 | 0.7794 | 0.7133 | 0.8512 | 0.5667 | 0.2479 |
| B5 | 0.7225 | 0.7664 | 0.7087 | 0.8607 | 0.5954 | 0.2793 |
| B6 | 0.7382 | 0.7826 | 0.6810 | 0.8746 | 0.5843 | 0.2840 |
| B7 | 0.7456 | 0.7853 | 0.7062 | 0.8632 | 0.6123 | 0.2776 |
| Full | 0.7404 | 0.7814 | 0.7036 | 0.8967 | 0.6096 | 0.2831 |

### Live Ablation Results

| config | name | evidence_recall@k | final_recall | citation_p | citation_r |
|---|---|---|---|---|---|
| B0 | Flat Chunk RAG | 0.3315 | 0.3315 | 0.0511 | 0.3315 |
| B1 | Chunk + Rerank | 0.3315 | 0.3315 | 0.0511 | 0.3315 |
| B2 | Graph-only | 0.4581 | 0.3468 | 0.0500 | 0.3468 |
| B3 | Chunk + Entity | 0.3315 | 0.3315 | 0.0511 | 0.3315 |
| B4 | Chunk + Entity + Relation | 0.3315 | 0.3315 | 0.0511 | 0.3315 |
| B5 | + Graph Expansion | 0.5033 | 0.3889 | 0.0575 | 0.3889 |
| B6 | + Query Variants | 0.4565 | 0.3658 | 0.0548 | 0.3658 |
| B7 | + Rerank | 0.4565 | 0.4218 | 0.0624 | 0.4218 |
| Full | B7 + Evidence Selection | 0.4565 | 0.4164 | 0.0624 | 0.4164 |

### Live Evidence Coverage

| config | required_coverage | keyword_sources | rerank_used |
|---|---|---|---|
| B0 | 0.4158 | request | false |
| B1 | 0.4158 | request | true |
| B2 | 0.5739 | llm | false |
| B3 | 0.5575 | llm | false |
| B4 | 0.5667 | llm | false |
| B5 | 0.5954 | llm | false |
| B6 | 0.5843 | llm | false |
| B7 | 0.6123 | llm | true |
| Full | 0.6096 | llm | true |

### Live Latency And Cache

| cache_phase | p50_s | p95_s | mean_s | cache_hit_stages |
|---|---|---|---|---|
| full_no_cache | 19.1345 | 30.2838 | 19.7132 | answer_cache_hit |
| retrieval_cache_warm | 8.5570 | 19.2100 | 9.6978 | answer_cache_hit,retrieval_cache_hit |
| answer_cache_warm | 0.0210 | 0.0600 | 0.0279 | answer_cache_hit |
| keyword_candidate_cache_warm | 20.5190 | 43.8780 | 22.7958 | answer_cache_hit,keyword_candidate_cache_hit |

### Build/Inference Separation

| check | value |
|---|---|
| raw_units_count | 0 |
| online_vs_replay_match | None |
| readonly_snapshot_unchanged | True |
| graph_nodes | 6157 |
| graph_edges | 21792 |
| entity_vdb | 6156 |
| relationship_vdb | 21792 |
| chunk_vdb | 1725 |
| doc_status | 1715 |

### ERC Retrieval Path Case

Question: 高血压指南里的 DASH 饮食和东方健康膳食模式，有哪些共同点？DASH 另外更明确限制什么？
Keywords: high=['高血压饮食管理', 'DASH饮食', '东方健康膳食模式', '膳食模式比较'] low=['共同点', '限制', '钠摄入', '饱和脂肪', '胆固醇'] source=llm
Final evidence:
- chunk-4a624c814cc4083973da6b17e1bd5f9e | 成人高血压食养指南_2022.pdf | p.10 | page=10 | section=
- chunk-2200c39b3e4569cd9a3039df17b1fba2 | 成人高血压食养指南_2022.pdf | p.67-68 | page=67 | section=
- chunk-88f6469c3b8016428bb2effc1ff022ff | 中国居民膳食指南_2022.pdf | p.309 | page=309 | section=
- chunk-5bcf7fc12b3c264b2603cd3eed526136 | 中国居民膳食指南_2022.pdf | p.312-314 | page=312 | section=
- chunk-208db66021481d7264a387bd1af0f0da | 中国居民膳食指南_2022.pdf | p.16-18 | page=16 | section=
- chunk-2f26be4ca086c255519837089ca6cf4b | 中国居民膳食指南_2022.pdf | p.316-318 | page=316 | section=
- chunk-0d2daf974b2829ef06984b9dc2e3ec5a | 成人高血压食养指南_2022.pdf | p.6-8 | page=6 | section=
- chunk-8eda6684e54a38a1497c0495844e2165 | 中国居民膳食指南_2022.pdf | p.117 | page=117 | section=
- chunk-869fa5c82c66541525e27f4f27def6bb | 成人高血压食养指南_2022.pdf | p.69 | page=69 | section=
- chunk-239c090ef22ded2157d93c1f978743c3 | 中国居民膳食指南_2022.pdf | p.109-110 | page=109 | section=

## Strict Per-Row Cold Cache Control

- Source: `benchmark/erc_full_eval_dqe_full_strict_cold_20260602_151636`
- Clear cache per live row: `True`
- Results JSONL rows: `744`
- Judge JSONL rows: `186`
- Judge statuses: `{'ok': 186}`
- Strict no-cache row cache-hit distribution: `none=186`
- Scope: supplemental cache-control experiment for Full only; it is not the main ablation table.

| metric | main Full no-cache | strict per-row cold Full | delta |
|---|---|---|---|
| latency p50 s | 19.1345 | 20.2990 | +1.1645 |
| latency p95 s | 30.2838 | 33.8945 | +3.6107 |
| latency mean s | 19.7132 | 21.9469 | +2.2337 |
| evidence recall@k | 0.4565 | 0.3247 | -0.1318 |
| final evidence recall | 0.4164 | 0.2674 | -0.1490 |
| required evidence coverage | 0.6096 | 0.5303 | -0.0793 |
| downstream correctness | 0.7404 | 0.7244 | -0.0160 |

### Strict Cache Phases

| cache_phase | p50_s | p95_s | mean_s | row_cache_hit_distribution |
|---|---|---|---|---|
| full_no_cache | 20.2990 | 33.8945 | 21.9469 | none=186 |
| retrieval_cache_warm | 20.7230 | 34.8985 | 21.6960 | answer_cache_hit=1, none=184, retrieval_cache_hit=1 |
| answer_cache_warm | 0.0140 | 0.0437 | 0.0214 | answer_cache_hit=186 |
| keyword_candidate_cache_warm | 22.8380 | 36.8957 | 22.5431 | answer_cache_hit=1, keyword_candidate_cache_hit=159, none=26 |

## Gold Replay Harness Sanity Appendix

- Directory: `benchmark/erc_dqe_full_gold_replay_20260601_000156`
- Scope: engineering sanity only. These numbers are not live system performance and must not be used as the paper main table.
- Interpretation: gold replay confirms the scoring schema and attribution pipeline can recognize required evidence when gold evidence is injected; it does not measure retrieval, online build quality, or raw replay equivalence.

| config | evidence_recall@k | final_recall | required_coverage | correctness | unsupported_claim_rate |
|---|---|---|---|---|---|
| B0 | 0.8233 | 0.8090 | 0.6545 | 0.7409 | 0.1910 |
| B1 | 0.8494 | 0.8233 | 0.6616 | 0.7462 | 0.1767 |
| B2 | 0.9830 | 0.9744 | 0.9503 | 0.9628 | 0.0256 |
| B3 | 0.9797 | 0.8494 | 0.8798 | 0.9098 | 0.1506 |
| B4 | 0.9919 | 0.9797 | 0.9560 | 0.9670 | 0.0203 |
| B5 | 1.0000 | 0.9919 | 0.9837 | 0.9878 | 0.0081 |
| B6 | 1.0000 | 1.0000 | 0.9889 | 0.9917 | 0.0000 |
| B7 | 1.0000 | 1.0000 | 0.9987 | 0.9990 | 0.0000 |
| Full | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |

| artifact | non-empty rows |
|---|---|
| results.jsonl | 2232 |
| judge_results.jsonl | 0 |
| metrics.tsv | 13 |
| dqe_slice_metrics.tsv | 100 |
| component_delta_by_slice.tsv | 78 |
| per_question_component_attribution.jsonl | 186 |

| failure type | count |
|---|---|
| no_primary_failure | 186 |

## Fresh Online Build Audit

- Source: `benchmark/erc_full_eval_20260527_155656/build_inference_separation/separation_summary.json`

| check | value |
|---|---|
| artifact | benchmark/erc_full_eval_20260527_155656 |
| status | completed_with_digest_mismatch |
| paper usable scope | fresh live retrieval/QA and read-only replay isolation; online/raw-replay equivalence not validated |
| completed online PDF builds | 8 |
| graph nodes | 7093 |
| graph edges | 24202 |
| entity VDB rows | 7078 |
| relationship VDB rows | 24135 |
| chunk VDB rows | 1992 |
| doc status rows | 1982 |
| text chunks | 1993 |
| online project digest | 33c855d175fbecc814b33dccd3daeb21 |
| offline replay digest | 0c5ec700ccd0e71662d7fade074b00b0 |
| raw export completed commands | 8 |
| raw export failed commands | 0 |
| offline replay project files | 8 |
| online_vs_replay_match | False |
| readonly_snapshot_unchanged | True |
| raw export failure | - |

### Raw Unit Export Status

| raw unit file | lines | status |
|---|---|---|
| benchmark/erc_full_eval_20260527_155656/build_inference_separation/raw_units/GB-31607-2021.raw-units.jsonl | 11 | present |
| benchmark/erc_full_eval_20260527_155656/build_inference_separation/raw_units/GB29938-2020.raw-units.jsonl | 221 | present |
| benchmark/erc_full_eval_20260527_155656/build_inference_separation/raw_units/GB31647-2018.raw-units.jsonl | 35 | present |
| benchmark/erc_full_eval_20260527_155656/build_inference_separation/raw_units/GBT1354-2018bz.raw-units.jsonl | 65 | present |
| benchmark/erc_full_eval_20260527_155656/build_inference_separation/raw_units/GBT22106-2008dz.raw-units.jsonl | 66 | present |
| benchmark/erc_full_eval_20260527_155656/build_inference_separation/raw_units/中国居民膳食指南_2022.raw-units.jsonl | 1370 | present |
| benchmark/erc_full_eval_20260527_155656/build_inference_separation/raw_units/成人肥胖食养指南_2024.raw-units.jsonl | 107 | present |
| benchmark/erc_full_eval_20260527_155656/build_inference_separation/raw_units/成人高血压食养指南_2022.raw-units.jsonl | 107 | present |

Interpretation: this artifact supports fresh online evidence-graph materialization, but raw replay equivalence is not validated.

## Retrieval Evidence

- Source: `benchmark/retrieval_cross_no_cache_local_gliner_20260523_190243/results.tsv`

| mode | retrieval_only | wall median/mean (s) | retrieval median/mean (s) | answer median/mean (s) | ref chunks median/mean | keyword source | rerank used |
|---|---:|---:|---:|---:|---:|---|---|
| `graph` | `false` | 11.843 / 12.017 | 4.964 / 4.621 | 6.581 / 7.243 | 10.000 / 10.000 | llm | False |
| `graph` | `true` | 3.753 / 3.868 | 3.640 / 3.730 | - | 10.000 / 10.000 | gliner_fallback | False |
| `hybrid` | `false` | 19.978 / 21.608 | 4.951 / 5.303 | 14.956 / 16.236 | 10.000 / 10.000 | llm | True |
| `hybrid` | `true` | 4.619 / 4.588 | 4.446 / 4.446 | - | 10.000 / 10.000 | gliner_fallback | True |

## Latency Evidence

- Source: `benchmark/latency_smoke_matrix_20260422/results.tsv`

| scenario | mode | rerank | request wall median/mean (s) | query median/mean (s) | cache hits | validation failures |
|---|---|---|---:|---:|---|---:|
| `first_request` | `graph` | `false` | 27.508 / 27.508 | 25.144 / 25.144 | - | 0/1 |
| `first_request` | `graph` | `true` | 19.106 / 19.106 | 16.462 / 16.462 | - | 0/1 |
| `first_request` | `hybrid` | `false` | 23.866 / 23.866 | 21.087 / 21.087 | - | 0/1 |
| `first_request` | `hybrid` | `true` | 16.353 / 16.353 | 13.818 / 13.818 | - | 0/1 |
| `steady_answer_warm` | `graph` | `false` | 0.011 / 0.011 | 0.006 / 0.006 | answer_cache_hit | 0/1 |
| `steady_answer_warm` | `graph` | `true` | 0.009 / 0.009 | 0.005 / 0.005 | answer_cache_hit | 0/1 |
| `steady_answer_warm` | `hybrid` | `false` | 0.010 / 0.010 | 0.004 / 0.004 | answer_cache_hit | 0/1 |
| `steady_answer_warm` | `hybrid` | `true` | 0.008 / 0.008 | 0.004 / 0.004 | answer_cache_hit | 0/1 |
| `steady_cold` | `graph` | `false` | 22.737 / 22.737 | 22.732 / 22.732 | - | 0/1 |
| `steady_cold` | `graph` | `true` | 18.860 / 18.860 | 18.855 / 18.855 | - | 0/1 |
| `steady_cold` | `hybrid` | `false` | 18.833 / 18.833 | 18.828 / 18.828 | - | 0/1 |
| `steady_cold` | `hybrid` | `true` | 16.795 / 16.795 | 16.790 / 16.790 | - | 0/1 |
| `steady_retrieval_warm` | `graph` | `false` | 13.744 / 13.744 | 13.740 / 13.740 | prompt_cache_hit, render_cache_hit, retrieval_cache_hit | 0/1 |
| `steady_retrieval_warm` | `graph` | `true` | 15.508 / 15.508 | 15.503 / 15.503 | prompt_cache_hit, render_cache_hit, retrieval_cache_hit | 0/1 |
| `steady_retrieval_warm` | `hybrid` | `false` | 16.545 / 16.545 | 16.540 / 16.540 | prompt_cache_hit, render_cache_hit, retrieval_cache_hit | 0/1 |
| `steady_retrieval_warm` | `hybrid` | `true` | 8.333 / 8.333 | 8.329 / 8.329 | prompt_cache_hit, render_cache_hit, retrieval_cache_hit | 0/1 |

## Keyword Candidate Cache Evidence

- Source: `benchmark/keyword_cache_benefit_qwen4b_hybrid/results.tsv`

| phase | n | wall median/mean (s) | onehop median/mean (s) | keyword hits | entity vector median/mean (s) | relation vector median/mean (s) |
|---|---:|---:|---:|---:|---:|---:|
| `baseline_cold` | 3 | 5.211 / 6.007 | 5.211 / 6.007 | 0 | 2.703 / 2.621 | 3.399 / 3.142 |
| `enabled_prewarm` | 3 | 5.053 / 5.101 | 5.053 / 5.101 | 4 | 2.667 / 2.307 | 2.268 / 2.208 |
| `enabled_warm` | 3 | 5.383 / 5.349 | 5.383 / 5.350 | 24 | 0.000 / 0.000 | 0.000 / 0.000 |

## Experiment Matrix

| ID | Configuration | Purpose | Current status |
|---|---|---|---|
| B0 | Flat Chunk RAG | chunk-only baseline | covered in current full eval artifact |
| B1 | Chunk + Rerank | rerank-only gain | covered in current full eval artifact |
| B2 | Graph-only | entity/relation/neighborhood contribution | covered in current full eval artifact |
| B3 | Chunk + Entity | entity recall gain | covered in current full eval artifact |
| B4 | Chunk + Entity + Relation | relation recall gain | covered in current full eval artifact |
| B5 | Chunk + Entity + Relation + Graph Expansion | graph expansion gain | covered in current full eval artifact |
| B6 | B5 + Query Variants | multi-constraint coverage gain | covered in current full eval artifact |
| B7 | B6 + Rerank | rerank gain after graph/variant fusion | covered in current full eval artifact |
| Full | B7 + Evidence Selection | evidence-selection stage under test | covered in current full eval artifact |

## Figure Artifact Note

- Figure/table images are written under `docs/research/figures`.
- `tools/render_erc_tables.py` reads `metrics.tsv`, `annotated_dataset.jsonl`, and `build_inference_separation/separation_summary.json` from the selected full eval artifact.
- `tools/render_erc_cache_figures.py` reads the selected full eval artifact for query-cache results and the keyword-cache TSV for retrieval-stage cache analysis.
- Regenerate with: `python3 tools/render_erc_tables.py --full-eval-dir benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014` and `python3 tools/render_erc_cache_figures.py --full-eval-dir benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014`.

## Verification Commands

```bash
uv run python tools/erc_full_eval.py --backend live --skip-live-build --live-project-dir example/qwen4b_diet_kg --dataset benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl --configs B0 B1 B2 B3 B4 B5 B6 B7 Full --judge-mode llm --output-dir benchmark/erc_full_eval_<timestamp> --skip-report --resume-partial --live-concurrency 4 --live-max-attempts 5 --live-retry-sleep 20 --live-query-timeout 360 --live-judge-timeout 180
uv run python tools/erc_full_eval.py --dataset benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl --backend live --skip-live-build --live-project-dir benchmark/erc_full_eval_20260527_155656/build_inference_separation/offline_replay_project --configs Full --judge-mode llm --live-concurrency 1 --clear-cache-per-live-row --output-dir benchmark/erc_full_eval_strict_cold_<timestamp> --skip-report
uv run python tools/erc_research_report.py --dataset benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl --full-eval-dir benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014  --fresh-build-audit benchmark/erc_full_eval_20260527_155656/build_inference_separation/separation_summary.json --strict-cold-eval-dir benchmark/erc_full_eval_dqe_full_strict_cold_20260602_151636 --output docs/research/erc_traceable_rag_report.md
uv run pytest tests/test_erc_research_dataset.py tests/test_erc_full_eval.py tests/test_diversified_graph_retrieval.py
RUNS=1 MODES="graph hybrid" RERANK_OPTIONS="off on" PROJECT_DIR="example/demo_diet_kg_5" bash script/latency_test.sh
uv run python benchmark/keyword_cache_benefit.py --project-dir benchmark/keyword_cache_benefit_qwen4b_manual/project --mode hybrid
```

## Completion Status

Use only paper-eligible `live` full-evaluation artifacts for paper main tables. `gold_replay`, historical benchmarks, synthetic artifacts, and non-fresh live smoke runs are engineering self-checks only.
