#!/usr/bin/env python3
"""Build the ERC traceable RAG research report from local benchmark artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = REPO_ROOT / "docs" / "research" / "erc_traceable_rag_report.md"
ALLOWED_LIVE_LLM_MODEL_URL = "https://api.deepseek.com"
ALLOWED_LIVE_LLM_MODEL = "deepseek-v4-flash"
CONFIG_LABELS = {
    "B0": "chunk-only",
    "B1": "chunk+rerank",
    "B2": "graph-only",
    "B3": "chunk+entity",
    "B4": "chunk+entity+relation",
    "B5": "chunk+entity+relation+graph expansion",
    "B6": "B5+query variants",
    "B7": "B6+rerank",
    "Full": "B7+evidence selection",
}
FULL_CONFIG_ORDER = ["B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "Full"]
RETRIEVAL_LAYER_CONCLUSIONS = {
    "B0": "Text-chunk baseline; structured required-evidence coverage is weak.",
    "B1": "Rerank-only chunk retrieval is a control for reranking without graph evidence.",
    "B2": "Graph-only retrieval improves required-evidence coverage but loses chunk fusion.",
    "B3": "Entity retrieval improves structured coverage over chunk-only retrieval.",
    "B4": "Relation retrieval adds a clear structured-coverage gain over entity-only retrieval.",
    "B5": "Graph expansion is the main candidate-recall and required-coverage jump.",
    "B6": "Query variants should be read as a constraint-diversity stage and checked for recall drift.",
    "B7": "Rerank after graph/variant fusion is the strongest current end-to-end retrieval setting.",
    "Full": "Evidence selection is a negative result here: it drops final required evidence versus B7.",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render the ERC evidence-graph research report."
    )
    parser.add_argument(
        "--dataset",
        default="benchmark/erc_evidence_questions.jsonl",
        help="JSONL gold question file.",
    )
    parser.add_argument(
        "--latency-results",
        default="benchmark/latency_smoke_matrix_20260422/results.tsv",
        help="Latency benchmark results.tsv.",
    )
    parser.add_argument(
        "--retrieval-results",
        default="benchmark/retrieval_cross_no_cache_local_gliner_20260523_190243/results.tsv",
        help="No-cache retrieval benchmark results.tsv.",
    )
    parser.add_argument(
        "--keyword-cache-results",
        default="benchmark/keyword_cache_benefit_qwen4b_hybrid/results.tsv",
        help="Keyword candidate cache benchmark results.tsv.",
    )
    parser.add_argument(
        "--output",
        default="docs/research/erc_traceable_rag_report.md",
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--full-eval-dir",
        default="",
        help="Optional benchmark/erc_full_eval_* directory with final artifacts.",
    )
    parser.add_argument(
        "--fresh-build-audit",
        default="",
        help="Optional fresh online build audit JSON artifact.",
    )
    parser.add_argument(
        "--strict-cold-eval-dir",
        default="",
        help="Optional Full-only live artifact with per-row cache clearing.",
    )
    return parser.parse_args()


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            record["_line_number"] = line_number
            records.append(record)
    return records


def load_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _line_count(path: Path) -> int | None:
    if not path.exists():
        return None
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _dataset_suffix(dataset_path: Path) -> str | None:
    stem = dataset_path.stem
    for prefix in (
        "erc_evidence_questions_dqe_full_",
        "erc_evidence_questions_dqe_",
    ):
        if stem.startswith(prefix):
            return stem[len(prefix) :]
    return None


def _dqe_mapping_dir(dataset_path: Path) -> Path | None:
    suffix = _dataset_suffix(dataset_path)
    if suffix is None:
        return None
    return REPO_ROOT / "benchmark" / f"erc_dqe_mapping_{suffix}"


def _dqe_dataset_audit_dir(dataset_path: Path) -> Path | None:
    suffix = _dataset_suffix(dataset_path)
    if suffix is None:
        return None
    return REPO_ROOT / "benchmark" / f"erc_dqe_dataset_audit_{suffix}"


def _latest_full_eval_dir() -> Path | None:
    candidates = [
        path
        for path in (REPO_ROOT / "benchmark").glob("erc_full_eval_*")
        if path.is_dir() and (path / "metrics.tsv").exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _median_mean(values: list[float]) -> str:
    if not values:
        return "-"
    return f"{statistics.median(values):.3f} / {statistics.fmean(values):.3f}"


def _counter_table(counter: Counter[str], label: str) -> list[str]:
    lines = [f"| {label} | count |", "|---|---:|"]
    for key, count in sorted(counter.items()):
        lines.append(f"| `{key}` | {count} |")
    return lines


def _compact_counter(counter: dict[str, Any] | Counter[str], *, limit: int = 8) -> str:
    if not counter:
        return "-"
    items = sorted(counter.items(), key=lambda item: (-int(item[1]), str(item[0])))
    shown = [f"`{key}`={value}" for key, value in items[:limit]]
    if len(items) > limit:
        shown.append(f"... +{len(items) - limit}")
    return ", ".join(shown)


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return lines


def _dataset_mapping_audit_lines(dataset_path: Path) -> list[str]:
    audit_dir = _dqe_dataset_audit_dir(dataset_path)
    mapping_dir = _dqe_mapping_dir(dataset_path)
    if audit_dir is None or mapping_dir is None:
        return []

    dataset_audit = _load_json(audit_dir / "dataset_audit.json")
    mapping_audit = _load_json(mapping_dir / "mapping_audit.json")
    slice_manifest = _load_json(mapping_dir / "dqe_slice_manifest.json")
    if not dataset_audit and not mapping_audit and not slice_manifest:
        return []

    distributions = dataset_audit.get("distributions") or {}
    quality = dataset_audit.get("quality_counts") or {}
    mapping_rows = []
    if mapping_audit:
        mapping_rows.extend(
            [
                ["project chunks loaded", mapping_audit.get("project_chunk_count")],
                ["required DQE evidence items", mapping_audit.get("required_evidence_item_count")],
                ["matched evidence items", mapping_audit.get("matched_evidence_item_count")],
                ["unmatched evidence items", mapping_audit.get("unmatched_evidence_item_count")],
                ["unique resolved source units", mapping_audit.get("unique_resolved_source_unit_count")],
                ["source id repairs from gold evidence", mapping_audit.get("source_unit_repair_count")],
                [
                    "questions with >=1 matched evidence",
                    f"{sum(1 for item in (mapping_audit.get('question_mapping_stats') or {}).values() if item.get('matched_evidence_count', 0) >= 1)} / {dataset_audit.get('sample_count') or '-'}",
                ],
                [
                    "questions with >=2 matched evidence",
                    f"{sum(1 for item in (mapping_audit.get('question_mapping_stats') or {}).values() if item.get('matched_evidence_count', 0) >= 2)} / {dataset_audit.get('sample_count') or '-'}",
                ],
                ["source unit conflicts", len(mapping_audit.get("source_unit_conflicts") or [])],
                ["evidence index conflicts", len(mapping_audit.get("evidence_index_conflicts") or [])],
            ]
        )

    slice_rows = []
    slices = slice_manifest.get("slices") or {}
    for name in (
        "dqe_full_mapped",
        "dqe_phase8_keep",
        "dqe_phase8_replace_stress",
        "dqe_multi_evidence_ge2",
        "dqe_multi_evidence_ge3",
        "dqe_multi_document",
        "dqe_table_multimodal_stress",
        "dqe_repair_review_set",
        "dqe_calculation",
        "dqe_hard",
        "dqe_selection_stress_candidates",
    ):
        if name in slices:
            slice_rows.append([name, slices[name].get("count"), slices[name].get("criteria")])

    lines = [
        "### DQE Dataset Construction And Mapping Audit",
        "",
        f"- Dataset audit: `{_display_path(audit_dir / 'dataset_audit.md')}`",
        f"- Mapping audit: `{_display_path(mapping_dir / 'mapping_audit.md')}`",
        f"- Capability tags: `{_display_path(mapping_dir / 'dqe_capability_tags.jsonl')}`",
        f"- Slice manifest: `{_display_path(mapping_dir / 'dqe_slice_manifest.json')}`",
        "",
    ]
    if dataset_audit:
        lines.extend(
            [
                "Dataset quality checks retain the DQE full mapped pool while making known annotation risks explicit.",
                "",
                *_markdown_table(
                    ["check", "value"],
                    [
                        ["samples", dataset_audit.get("sample_count")],
                        ["answerability", _compact_counter(distributions.get("answerability") or {})],
                        ["document scope", _compact_counter(distributions.get("document_scope") or {})],
                        ["modality", _compact_counter(distributions.get("modality") or {})],
                        ["evidence source count", _compact_counter(distributions.get("evidence_source_count") or {})],
                        ["phase8 action", _compact_counter(distributions.get("phase8_action") or {})],
                        ["possibly over-general gold answers", quality.get("possibly_over_general_gold_answer")],
                        ["duplicate question groups", quality.get("duplicate_question_groups")],
                    ],
                ),
                "",
            ]
        )
    if mapping_rows:
        lines.extend(
            [
                "The DQE-to-ragent mapping uses only real project chunks and metadata; no pseudo pages, synthetic `chunk_id`, or fabricated `source_ref` values are introduced.",
                "",
                *_markdown_table(["mapping check", "value"], mapping_rows),
                "",
            ]
        )
    if slice_rows:
        lines.extend(
            [
                "The DQE slices are used as control variables for component attribution rather than as hand-picked favorable subsets.",
                "",
                *_markdown_table(["slice", "n", "criteria"], slice_rows),
            ]
        )
    return lines


def _dataset_summary_lines(records: list[dict[str, Any]], dataset_path: Path) -> list[str]:
    dataset_counts = Counter(str(record["dataset"]) for record in records)
    type_counts = Counter(str(record["question_type"]) for record in records)
    difficulty_counts = Counter(str(record["difficulty"]) for record in records)
    calc_count = sum(1 for record in records if record.get("requires_calculation"))

    lines = [
        "## Dataset",
        "",
        f"- Source: `{_display_path(dataset_path)}`",
        f"- Questions: `{len(records)}`",
        f"- Requires calculation: `{calc_count}`",
        "",
        "### Dataset Split",
        "",
        *_counter_table(dataset_counts, "dataset"),
        "",
        "### Question Types",
        "",
        *_counter_table(type_counts, "question_type"),
        "",
        "### Difficulty",
        "",
        *_counter_table(difficulty_counts, "difficulty"),
    ]
    return lines


def _latency_summary_lines(rows: list[dict[str, str]], path: Path) -> list[str]:
    lines = [
        "## Latency Evidence",
        "",
        f"- Source: `{_display_path(path)}`",
    ]
    if not rows:
        lines.append("- Status: missing artifact")
        return lines

    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["scenario"], row["mode"], row["rerank_enabled"])].append(row)

    lines.extend(
        [
            "",
            "| scenario | mode | rerank | request wall median/mean (s) | query median/mean (s) | cache hits | validation failures |",
            "|---|---|---|---:|---:|---|---:|",
        ]
    )
    for key in sorted(grouped):
        scenario, mode, rerank = key
        group = grouped[key]
        request_values = [
            value
            for value in (_float_or_none(row.get("request_wall_seconds")) for row in group)
            if value is not None
        ]
        query_values = [
            value
            for value in (_float_or_none(row.get("query_seconds")) for row in group)
            if value is not None
        ]
        cache_hits = sorted(
            {
                hit
                for row in group
                for hit in str(row.get("cache_hit_stages") or "").split(",")
                if hit
            }
        )
        failures = sum(1 for row in group if row.get("validation_status") == "fail")
        lines.append(
            f"| `{scenario}` | `{mode}` | `{rerank}` | "
            f"{_median_mean(request_values)} | {_median_mean(query_values)} | "
            f"{', '.join(cache_hits) if cache_hits else '-'} | {failures}/{len(group)} |"
        )
    return lines


def _retrieval_summary_lines(rows: list[dict[str, str]], path: Path) -> list[str]:
    lines = [
        "## Retrieval Evidence",
        "",
        f"- Source: `{_display_path(path)}`",
    ]
    if not rows:
        lines.append("- Status: missing artifact")
        return lines

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["mode"], row["retrieval_only"])].append(row)

    lines.extend(
        [
            "",
            "| mode | retrieval_only | wall median/mean (s) | retrieval median/mean (s) | answer median/mean (s) | ref chunks median/mean | keyword source | rerank used |",
            "|---|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for key in sorted(grouped):
        mode, retrieval_only = key
        group = grouped[key]
        wall_values = [
            value
            for value in (_float_or_none(row.get("request_wall_seconds")) for row in group)
            if value is not None
        ]
        retrieval_values = [
            value
            for value in (
                _float_or_none(row.get("hybrid_retrieval_total_seconds"))
                or _float_or_none(row.get("graph_retrieval_path_seconds"))
                for row in group
            )
            if value is not None
        ]
        answer_values = [
            value
            for value in (
                _float_or_none(row.get("answer_generation_seconds")) for row in group
            )
            if value is not None
        ]
        chunk_values = [
            value
            for value in (_float_or_none(row.get("reference_chunk_count")) for row in group)
            if value is not None
        ]
        keyword_sources = sorted({row.get("keyword_source") or "-" for row in group})
        rerank_used = sorted({row.get("rerank_used") or "-" for row in group})
        lines.append(
            f"| `{mode}` | `{retrieval_only}` | {_median_mean(wall_values)} | "
            f"{_median_mean(retrieval_values)} | {_median_mean(answer_values)} | "
            f"{_median_mean(chunk_values)} | {', '.join(keyword_sources)} | "
            f"{', '.join(rerank_used)} |"
        )
    return lines


def _keyword_cache_summary_lines(rows: list[dict[str, str]], path: Path) -> list[str]:
    lines = [
        "## Keyword Candidate Cache Evidence",
        "",
        f"- Source: `{_display_path(path)}`",
    ]
    if not rows:
        lines.append("- Status: missing artifact")
        return lines

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["phase"]].append(row)

    lines.extend(
        [
            "",
            "| phase | n | wall median/mean (s) | onehop median/mean (s) | keyword hits | entity vector median/mean (s) | relation vector median/mean (s) |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for phase in sorted(grouped):
        group = grouped[phase]
        wall_values = [
            value
            for value in (_float_or_none(row.get("wall_seconds")) for row in group)
            if value is not None
        ]
        onehop_values = [
            value
            for value in (_float_or_none(row.get("onehop_total_seconds")) for row in group)
            if value is not None
        ]
        hits = sum(
            int(_float_or_none(row.get("keyword_candidate_cache_hit_count")) or 0)
            for row in group
        )
        entity_values = [
            value
            for value in (
                _float_or_none(row.get("graph_entity_vector_seconds")) for row in group
            )
            if value is not None
        ]
        relation_values = [
            value
            for value in (
                _float_or_none(row.get("graph_relation_vector_seconds")) for row in group
            )
            if value is not None
        ]
        lines.append(
            f"| `{phase}` | {len(group)} | {_median_mean(wall_values)} | "
            f"{_median_mean(onehop_values)} | {hits} | "
            f"{_median_mean(entity_values)} | {_median_mean(relation_values)} |"
        )
    return lines


def _judge_status_counts(judge_path: Path) -> Counter[str]:
    if not judge_path.exists():
        return Counter()
    statuses = Counter()
    for line in judge_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            statuses["invalid_json"] += 1
            continue
        statuses[str(payload.get("status") or "missing")] += 1
    return statuses


def _cache_hit_stage_distribution(
    results_path: Path,
    *,
    config_id: str | None = None,
    cache_phase: str | None = None,
) -> Counter[str]:
    if not results_path.exists():
        return Counter()
    stages_by_label: Counter[str] = Counter()
    for line in results_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if config_id is not None and row.get("config_id") != config_id:
            continue
        if cache_phase is not None and row.get("cache_phase") != cache_phase:
            continue
        stages = row.get("cache_hit_stages") or []
        if isinstance(stages, str):
            stage_values = [stage for stage in stages.split(",") if stage]
        else:
            stage_values = [str(stage) for stage in stages if stage]
        stages_by_label[",".join(stage_values) or "none"] += 1
    return stages_by_label


def _latest_log_match(log_path: Path, patterns: tuple[str, ...]) -> str:
    if not log_path.exists():
        return "-"
    latest = "-"
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if any(pattern in line for pattern in patterns):
            latest = line.strip()
    return latest


def _format_counter(counter: Counter[str]) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{key}={counter[key]}" for key in sorted(counter))


def _duplicate_result_keys(path: Path) -> int | None:
    if not path.exists():
        return None
    keys: Counter[tuple[Any, Any, Any]] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        keys[
            (
                row.get("question_id"),
                row.get("config_id"),
                row.get("cache_phase", "full_no_cache"),
            )
        ] += 1
    duplicates = sum(count - 1 for count in keys.values() if count > 1)
    return duplicates


def _artifact_completeness_lines(full_eval_dir: Path | None) -> list[str]:
    if full_eval_dir is None:
        return []
    paths = {
        "results.jsonl": full_eval_dir / "results.jsonl",
        "judge_results.jsonl": full_eval_dir / "judge_results.jsonl",
        "metrics.tsv": full_eval_dir / "metrics.tsv",
        "dqe_slice_metrics.tsv": full_eval_dir / "dqe_slice_metrics.tsv",
        "component_delta_by_slice.tsv": full_eval_dir / "component_delta_by_slice.tsv",
        "per_question_component_attribution.jsonl": full_eval_dir / "per_question_component_attribution.jsonl",
        "annotated_dataset.jsonl": full_eval_dir / "annotated_dataset.jsonl",
    }
    rows = [
        [name, _line_count(path) if path.exists() else "missing"]
        for name, path in paths.items()
    ]
    before_rejudge = full_eval_dir / "judge_results.jsonl.before_rejudge"
    before_dedupe = full_eval_dir / "judge_results.jsonl.before_dedupe"
    provenance_rows: list[list[Any]] = []
    if before_rejudge.exists():
        provenance_rows.append(
            [
                "judge before rejudge",
                _line_count(before_rejudge),
                _format_counter(_judge_status_counts(before_rejudge)),
                _duplicate_result_keys(before_rejudge),
            ]
        )
    if before_dedupe.exists():
        provenance_rows.append(
            [
                "judge before dedupe",
                _line_count(before_dedupe),
                _format_counter(_judge_status_counts(before_dedupe)),
                _duplicate_result_keys(before_dedupe),
            ]
        )
    final_judge = paths["judge_results.jsonl"]
    if final_judge.exists():
        provenance_rows.append(
            [
                "final judge file",
                _line_count(final_judge),
                _format_counter(_judge_status_counts(final_judge)),
                _duplicate_result_keys(final_judge),
            ]
        )

    lines = [
        "### Artifact Completeness And Rejudge Provenance",
        "",
        "The selected live artifact is treated as complete only because the row counts, judge statuses, and attribution outputs are present. Rejudge/dedupe snapshots are retained to make the long-run recovery path auditable.",
        "",
        *_markdown_table(["artifact", "non-empty rows"], rows),
    ]
    if provenance_rows:
        lines.extend(
            [
                "",
                *_markdown_table(["snapshot", "rows", "judge statuses", "duplicate keys"], provenance_rows),
            ]
        )
    return lines


def _paper_eligibility(
    *,
    backend_kind: str,
    manifest: dict[str, Any],
    separation: dict[str, Any],
    judge_statuses: Counter[str],
) -> tuple[bool, str]:
    if backend_kind != "live":
        return False, "gold_replay/sanity backend"
    if separation.get("build_mode") != "fresh_online_and_raw_replay":
        return False, "not a fresh online-build plus raw-replay run"
    if separation.get("online_vs_replay_match") is not True:
        return False, "online/replay digest mismatch or not executed"
    if separation.get("readonly_snapshot_unchanged") is not True:
        return False, "read-only inference digest changed or not verified"
    if manifest.get("judge_mode") != "llm":
        return False, "answer quality was not scored by the fixed LLM judge"
    if judge_statuses and any(status != "ok" for status in judge_statuses):
        return False, f"judge failures present: {dict(judge_statuses)}"
    return True, "fresh live run with replay/read-only checks and LLM judge"


def _paper_scope(
    *,
    backend_kind: str,
    manifest: dict[str, Any],
    separation: dict[str, Any],
    judge_statuses: Counter[str],
) -> str:
    if backend_kind != "live":
        return "engineering sanity only"
    if manifest.get("judge_mode") != "llm":
        return "engineering smoke only; answer quality was not LLM-judged"
    if judge_statuses and any(status != "ok" for status in judge_statuses):
        return "engineering failure artifact; judge failures are present"
    if separation.get("build_mode") == "fresh_online_and_raw_replay":
        if (
            separation.get("online_vs_replay_match") is True
            and separation.get("readonly_snapshot_unchanged") is True
        ):
            return "full paper tables: retrieval/QA plus build/replay/read-only"
        if separation.get("readonly_snapshot_unchanged") is True:
            return "retrieval/QA plus read-only replay isolation; online/raw-replay equivalence not validated"
        if separation.get("online_vs_replay_match") is True:
            return "retrieval/QA plus online/raw-replay equivalence; read-only replay isolation not validated"
        return "retrieval/QA only; build/replay/read-only validation failed or is incomplete"
    if separation.get("build_mode") == "existing_project_copy":
        return "retrieval/QA ablation on an existing live project only; not evidence for fresh build/replay"
    return "live result with incomplete build provenance"


def _result_interpretation_lines(
    *,
    heading_prefix: str,
    paper_scope: str,
    paper_eligible: bool,
    main_rows: list[dict[str, str]],
    separation: dict[str, Any],
) -> list[str]:
    by_config = {row.get("config_id"): row for row in main_rows}

    def metric(config_id: str, field: str) -> float | None:
        row = by_config.get(config_id)
        if not row:
            return None
        return _float_or_none(row.get(field))

    lines = [
        f"### {heading_prefix} Result Interpretation",
        "",
        f"- Scope: {paper_scope}.",
    ]
    if not paper_eligible:
        lines.append(
            "- Do not use this artifact as the full paper main table for fresh build/replay claims."
        )
    if separation.get("build_mode") == "existing_project_copy":
        lines.append(
            "- Build/replay separation is not validated here; the project was copied from an existing live graph and only read-only inference was checked."
        )
    lines.append(
        "- Primary retrieval-layer claims should use evidence coverage, final evidence recall, required evidence coverage, and latency; final answer scores are downstream-generation diagnostics."
    )

    full_correctness = metric("Full", "correctness")
    b0_correctness = metric("B0", "correctness")
    b5_correctness = metric("B5", "correctness")
    full_recall = metric("Full", "evidence_recall_at_k")
    b0_recall = metric("B0", "evidence_recall_at_k")
    b5_recall = metric("B5", "evidence_recall_at_k")

    if full_correctness is not None and b0_correctness is not None:
        direction = "above" if full_correctness >= b0_correctness else "below"
        lines.append(
            f"- Downstream diagnostic: Full correctness is {direction} B0 ({full_correctness:.4f} vs {b0_correctness:.4f})."
        )
    if full_correctness is not None and b5_correctness is not None:
        direction = "above" if full_correctness >= b5_correctness else "below"
        lines.append(
            f"- Downstream diagnostic: Full correctness is {direction} B5 ({full_correctness:.4f} vs {b5_correctness:.4f}); report this without retuning or question selection."
        )
    if full_recall is not None and b0_recall is not None:
        direction = "above" if full_recall >= b0_recall else "below"
        lines.append(
            f"- Full Evidence Recall@K is {direction} B0 ({full_recall:.4f} vs {b0_recall:.4f})."
        )
    if full_recall is not None and b5_recall is not None:
        direction = "above" if full_recall >= b5_recall else "below"
        lines.append(
            f"- Full Evidence Recall@K is {direction} B5 ({full_recall:.4f} vs {b5_recall:.4f})."
        )
    return lines


def _retrieval_layer_result_rows(main_rows: list[dict[str, str]]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for row in main_rows:
        config_id = row["config_id"]
        rows.append(
            [
                config_id,
                row["config_name"],
                row["evidence_recall_at_k"],
                row["final_evidence_recall"],
                row["required_evidence_coverage"],
                row["latency_p50_seconds"],
                RETRIEVAL_LAYER_CONCLUSIONS.get(config_id, "-"),
            ]
        )
    return rows


def _cache_caveat_lines(cache_rows: list[dict[str, str]]) -> list[str]:
    if not cache_rows:
        return []
    by_phase = {row.get("cache_phase"): row for row in cache_rows}
    no_cache = by_phase.get("full_no_cache")
    retrieval_warm = by_phase.get("retrieval_cache_warm")
    answer_warm = by_phase.get("answer_cache_warm")
    keyword_warm = by_phase.get("keyword_candidate_cache_warm")
    lines = []
    if no_cache and (no_cache.get("cache_hit_stages") or "").strip():
        lines.append(
            f"- Cache caveat: `full_no_cache` still records `{no_cache.get('cache_hit_stages')}`, so this artifact should not be described as a strictly isolated cold-start latency run."
        )
    if no_cache and retrieval_warm:
        base = _metric(no_cache, "latency_p50_seconds")
        warm = _metric(retrieval_warm, "latency_p50_seconds")
        if base is not None and warm is not None and warm < base:
            lines.append(
                f"- Retrieval-cache warm p50 improves from {_fmt(base)}s to {_fmt(warm)}s under the same Full path."
            )
    if no_cache and answer_warm:
        base = _metric(no_cache, "latency_p50_seconds")
        warm = _metric(answer_warm, "latency_p50_seconds")
        if base is not None and warm is not None and warm < base:
            lines.append(
                f"- Answer-cache warm p50 improves from {_fmt(base)}s to {_fmt(warm)}s for repeated queries."
            )
    if no_cache and keyword_warm:
        base_mean = _metric(no_cache, "latency_mean_seconds")
        keyword_mean = _metric(keyword_warm, "latency_mean_seconds")
        if base_mean is not None and keyword_mean is not None and keyword_mean > base_mean:
            lines.append(
                f"- Keyword-candidate warm does not show a full-query latency win in this run: mean latency is {_fmt(keyword_mean)}s versus {_fmt(base_mean)}s for `full_no_cache`."
            )
    return lines


def _strict_cold_control_lines(
    strict_eval_dir: Path | None,
    main_full_eval_dir: Path | None,
) -> list[str]:
    if strict_eval_dir is None:
        return []

    metrics_path = strict_eval_dir / "metrics.tsv"
    manifest_path = strict_eval_dir / "run_manifest.json"
    results_path = strict_eval_dir / "results.jsonl"
    judge_path = strict_eval_dir / "judge_results.jsonl"
    terminal_log_path = Path(str(strict_eval_dir) + ".terminal.log")
    metrics_rows = load_tsv(metrics_path)
    if not metrics_rows:
        partial_no_cache_hit_stages = _cache_hit_stage_distribution(
            results_path,
            config_id="Full",
            cache_phase="full_no_cache",
        )
        return [
            "## Strict Per-Row Cold Cache Control",
            "",
            f"- Source: `{_display_path(strict_eval_dir)}`",
            "- Status: interrupted before `metrics.tsv` was written; this is an incomplete supplemental control and is not used as a result table.",
            f"- Results JSONL rows: `{_line_count(results_path)}`",
            f"- Judge JSONL rows: `{_line_count(judge_path)}`",
            f"- Judge statuses: `{dict(_judge_status_counts(judge_path))}`",
            f"- Strict no-cache row cache-hit distribution: `{_format_counter(partial_no_cache_hit_stages)}`",
            f"- Last failure signal: `{_latest_log_match(terminal_log_path, ('401 Unauthorized', 'invalid_api_key', 'HTTPStatusError'))}`",
        ]

    manifest = _load_json(manifest_path)
    strict_no_cache = next(
        (
            row
            for row in metrics_rows
            if row.get("config_id") == "Full"
            and row.get("cache_phase") == "full_no_cache"
        ),
        None,
    )
    strict_cache_rows = [
        row
        for row in metrics_rows
        if row.get("config_id") == "Full"
    ]
    strict_no_cache_hit_stages = _cache_hit_stage_distribution(
        results_path,
        config_id="Full",
        cache_phase="full_no_cache",
    )
    main_no_cache: dict[str, str] | None = None
    if main_full_eval_dir is not None:
        for row in load_tsv(main_full_eval_dir / "metrics.tsv"):
            if (
                row.get("config_id") == "Full"
                and row.get("cache_phase") == "full_no_cache"
            ):
                main_no_cache = row
                break

    comparison_fields = [
        ("latency_p50_seconds", "latency p50 s"),
        ("latency_p95_seconds", "latency p95 s"),
        ("latency_mean_seconds", "latency mean s"),
        ("evidence_recall_at_k", "evidence recall@k"),
        ("final_evidence_recall", "final evidence recall"),
        ("required_evidence_coverage", "required evidence coverage"),
        ("correctness", "downstream correctness"),
    ]
    comparison_rows = []
    for field, label in comparison_fields:
        main_value = _metric(main_no_cache, field)
        strict_value = _metric(strict_no_cache, field)
        comparison_rows.append(
            [
                label,
                _fmt(main_value),
                _fmt(strict_value),
                _metric_delta(strict_value, main_value),
            ]
        )

    lines = [
        "## Strict Per-Row Cold Cache Control",
        "",
        f"- Source: `{_display_path(strict_eval_dir)}`",
        f"- Clear cache per live row: `{manifest.get('clear_cache_per_live_row')}`",
        f"- Results JSONL rows: `{_line_count(results_path)}`",
        f"- Judge JSONL rows: `{_line_count(judge_path)}`",
        f"- Judge statuses: `{dict(_judge_status_counts(judge_path))}`",
        f"- Strict no-cache row cache-hit distribution: `{_format_counter(strict_no_cache_hit_stages)}`",
        "- Scope: supplemental cache-control experiment for Full only; it is not the main ablation table.",
        "",
        *_markdown_table(
            ["metric", "main Full no-cache", "strict per-row cold Full", "delta"],
            comparison_rows,
        ),
        "",
        "### Strict Cache Phases",
        "",
        *_markdown_table(
            ["cache_phase", "p50_s", "p95_s", "mean_s", "row_cache_hit_distribution"],
            [
                [
                    row["cache_phase"],
                    row["latency_p50_seconds"],
                    row["latency_p95_seconds"],
                    row["latency_mean_seconds"],
                    _format_counter(
                        _cache_hit_stage_distribution(
                            results_path,
                            config_id="Full",
                            cache_phase=row["cache_phase"],
                        )
                    ),
                ]
                for row in strict_cache_rows
            ],
        ),
    ]
    if strict_no_cache and (strict_no_cache.get("cache_hit_stages") or "").strip():
        lines.extend(
            [
                "",
                f"- Caveat: strict `full_no_cache` still records `{strict_no_cache.get('cache_hit_stages')}` in aggregate metrics; inspect row-level `cache_hit_stages` before claiming fully cold latency isolation.",
            ]
        )
    return lines


def _failure_counts_from_taxonomy(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    rows: list[list[str]] = []
    in_counts = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "## Failure Counts":
            in_counts = True
            continue
        if in_counts and line.startswith("## "):
            break
        if not in_counts or not line.startswith("- `"):
            continue
        label, _, count = line[3:].partition(":")
        rows.append([label.strip("` "), count.strip()])
    return rows


def _failure_tag_summary_from_taxonomy(path: Path, *, top_n: int = 5) -> list[list[str]]:
    if not path.exists():
        return []
    sections: dict[str, list[tuple[str, str]]] = {}
    current: str | None = None
    in_tags = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "## Tags By Failure Type":
            in_tags = True
            continue
        if not in_tags:
            continue
        if line.startswith("### "):
            current = line[4:].strip()
            sections[current] = []
            continue
        if current is None or not line.startswith("- `"):
            continue
        label, _, count = line[3:].partition(":")
        sections[current].append((label.strip("` "), count.strip()))
    rows: list[list[str]] = []
    for failure_type, tags in sections.items():
        if failure_type == "no_primary_failure":
            continue
        top_tags = ", ".join(f"`{tag}`={count}" for tag, count in tags[:top_n])
        rows.append([failure_type, top_tags or "-"])
    return rows


def _dqe_attribution_lines(full_eval_dir: Path | None) -> list[str]:
    if full_eval_dir is None:
        return []

    slice_path = full_eval_dir / "dqe_slice_metrics.tsv"
    delta_path = full_eval_dir / "component_delta_by_slice.tsv"
    attribution_path = full_eval_dir / "per_question_component_attribution.jsonl"
    taxonomy_path = full_eval_dir / "failure_taxonomy.md"
    slice_rows = load_tsv(slice_path)
    delta_rows = load_tsv(delta_path)
    if not slice_rows and not delta_rows:
        return []

    desired_slices = [
        "dqe_full_mapped",
        "dqe_phase8_keep",
        "dqe_phase8_replace_stress",
        "dqe_multi_evidence_ge2",
        "dqe_multi_evidence_ge3",
        "dqe_multi_document",
        "dqe_table_multimodal_stress",
        "dqe_repair_review_set",
        "dqe_calculation",
        "dqe_hard",
        "dqe_selection_stress_candidates",
    ]
    b7_slice_rows = [
        row
        for row in slice_rows
        if row.get("config_id") == "B7" and row.get("slice") in desired_slices
    ]
    b7_by_slice = {row.get("slice"): row for row in b7_slice_rows}
    ordered_b7_rows = [
        b7_by_slice[slice_name]
        for slice_name in desired_slices
        if slice_name in b7_by_slice
    ]
    full_delta_rows = [
        row
        for row in delta_rows
        if row.get("slice") == "dqe_full_mapped"
    ]
    slice_focus_rows = []
    for slice_name in ("dqe_repair_review_set", "dqe_selection_stress_candidates"):
        by_config = {
            row.get("config_id"): row
            for row in slice_rows
            if row.get("slice") == slice_name
        }
        if {"B0", "B7", "Full"} <= set(by_config):
            b0 = by_config["B0"]
            b7 = by_config["B7"]
            full = by_config["Full"]
            slice_focus_rows.append(
                [
                    slice_name,
                    b7["question_count"],
                    b0["required_evidence_coverage"],
                    b7["required_evidence_coverage"],
                    full["required_evidence_coverage"],
                    b7["final_evidence_recall"],
                    full["final_evidence_recall"],
                ]
            )
    failure_rows = _failure_counts_from_taxonomy(taxonomy_path)
    failure_tag_rows = _failure_tag_summary_from_taxonomy(taxonomy_path)

    lines = [
        "### 3.7 DQE Slice And Component Attribution",
        "",
        "The full DQE run is used as the measurement control layer: every aggregate result is decomposed by DQE question type, evidence count, document scope, modality, repair status, and stress tags. This prevents the report from claiming a component gain that only appears on an easy or hand-picked subset.",
        "",
        f"- Slice metrics: `{_display_path(slice_path)}`" if slice_path.exists() else "- Slice metrics: missing",
        f"- Component deltas: `{_display_path(delta_path)}`" if delta_path.exists() else "- Component deltas: missing",
        f"- Per-question attribution: `{_display_path(attribution_path)}`" if attribution_path.exists() else "- Per-question attribution: missing",
        f"- Failure taxonomy: `{_display_path(taxonomy_path)}`" if taxonomy_path.exists() else "- Failure taxonomy: missing",
    ]
    if ordered_b7_rows:
        lines.extend(
            [
                "",
                "B7 is the best current end-to-end retrieval setting, so the slice table below uses B7 as the main positive reference.",
                "",
                *_markdown_table(
                    [
                        "DQE slice",
                        "n",
                        "correctness",
                        "final_recall",
                        "required_coverage",
                        "unsupported_claim_rate",
                    ],
                    [
                        [
                            row["slice"],
                            row["question_count"],
                            row["correctness"],
                            row["final_evidence_recall"],
                            row["required_evidence_coverage"],
                            row["unsupported_claim_rate"],
                        ]
                        for row in ordered_b7_rows
                    ],
                ),
            ]
        )
    if full_delta_rows:
        lines.extend(
            [
                "",
                "The component deltas on the full mapped slice identify where the algorithmic changes actually add or lose evidence.",
                "",
                *_markdown_table(
                    [
                        "component",
                        "comparison",
                        "delta_final_recall",
                        "delta_required_coverage",
                        "delta_correctness",
                        "delta_faithfulness",
                    ],
                    [
                        [
                            row["component_delta"],
                            f"{row['before_config']} -> {row['after_config']}",
                            row["delta_final_evidence_recall"],
                            row["delta_required_evidence_coverage"],
                            row["delta_correctness"],
                            row["delta_faithfulness"],
                        ]
                        for row in full_delta_rows
                    ],
                ),
            ]
        )
    if slice_focus_rows:
        lines.extend(
            [
                "",
                "`dqe_repair_review_set` and `dqe_selection_stress_candidates` are especially important for auditability and failure diagnosis. The former checks repaired source-unit mappings; the latter isolates questions where final evidence selection is expected to preserve multi-evidence candidates.",
                "",
                *_markdown_table(
                    [
                        "slice",
                        "n",
                        "B0_required_coverage",
                        "B7_required_coverage",
                        "Full_required_coverage",
                        "B7_final_recall",
                        "Full_final_recall",
                    ],
                    slice_focus_rows,
                ),
            ]
        )
    if failure_rows:
        lines.extend(
            [
                "",
                "The failure taxonomy is retained as part of the result, not filtered away.",
                "",
                *_markdown_table(["failure type", "count"], failure_rows),
            ]
        )
    if failure_tag_rows:
        lines.extend(
            [
                "",
                "Failure tags show where the residual errors concentrate; these rows are retained as negative evidence rather than filtered out.",
                "",
                *_markdown_table(["failure type", "top concentration tags"], failure_tag_rows),
            ]
        )

    lines.extend(
        [
            "",
            "Interpretation: relation retrieval, graph expansion, and post-fusion reranking give measurable coverage or final-recall gains. Query variants alone regress final recall in this run and need tighter query filtering. Full evidence selection is currently a failure target because it drops final evidence recall and required coverage relative to B7.",
        ]
    )
    return lines


def _metric_delta(value: float | None, baseline: float | None) -> str:
    if value is None or baseline is None:
        return "-"
    return f"{value - baseline:+.4f}"


def _annotated_records_for_context(
    records: list[dict[str, Any]],
    context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not context:
        return records
    annotated_path = Path(context["dir"]) / "annotated_dataset.jsonl"
    if not annotated_path.exists():
        return records
    return load_jsonl(annotated_path)


def _matched_project_chunk_count(records: list[dict[str, Any]]) -> int:
    required_evidence = [
        evidence
        for record in records
        for evidence in record.get("required_evidence", [])
        if evidence.get("chunk_id")
    ]
    if required_evidence:
        return len(required_evidence)
    return sum(len(record.get("required_chunk_ids", [])) for record in records)


def _required_source_ref_count(records: list[dict[str, Any]]) -> int:
    return sum(len(record.get("required_source_refs", [])) for record in records)


def _best_config_summary(rows: list[dict[str, str]], field: str) -> tuple[str, float | None]:
    scored = [
        (row, _metric(row, field))
        for row in rows
        if _metric(row, field) is not None
    ]
    if not scored:
        return "-", None
    best_value = max(value for _row, value in scored if value is not None)
    best_ids = [
        row["config_id"]
        for row, value in scored
        if value is not None and abs(value - best_value) < 1e-9
    ]
    return ", ".join(f"`{config_id}`" for config_id in best_ids), best_value


def _retrieval_layer_analysis_lines(main_rows: list[dict[str, str]]) -> list[str]:
    if not main_rows:
        return []
    by_config = {row["config_id"]: row for row in main_rows}
    best_evidence_ids, best_evidence_value = _best_config_summary(
        main_rows,
        "evidence_recall_at_k",
    )
    best_final_ids, best_final_value = _best_config_summary(
        main_rows,
        "final_evidence_recall",
    )
    best_required_ids, best_required_value = _best_config_summary(
        main_rows,
        "required_evidence_coverage",
    )

    def value(config_id: str, field: str) -> float | None:
        return _metric(by_config.get(config_id), field)

    lines = [
        "### 3.1 Retrieval-Layer Framing",
        "",
        "The primary evaluation target is the knowledge-graph retrieval and evidence organization layer, not the downstream business answer generator. Final answer quality depends on prompt construction, context assembly, model choice, and response formatting outside this retrieval layer, so correctness and faithfulness are retained as diagnostics rather than used as the main claim.",
        "",
        "### 3.2 Retrieval-Layer Evidence Coverage",
        "",
        f"The strongest Evidence Recall@K value is {_fmt(best_evidence_value)}, reached by {best_evidence_ids}. The strongest Final Evidence Recall value is {_fmt(best_final_value)}, reached by {best_final_ids}. The strongest Required Evidence Coverage value is {_fmt(best_required_value)}, reached by {best_required_ids}.",
        "",
    ]

    b0_required = value("B0", "required_evidence_coverage")
    for config_id in ("B2", "B5", "B6", "B7", "Full"):
        config_required = value(config_id, "required_evidence_coverage")
        if config_required is not None and b0_required is not None:
            lines.append(
                f"- `{config_id}` required evidence coverage is {_fmt(config_required)}, {_metric_delta(config_required, b0_required)} versus B0."
            )
    lines.extend(
        [
            "",
            "### 3.3 Retrieval Component Findings",
            "",
        ]
    )

    comparisons = [
        (
            "B3",
            "B0",
            "Entity retrieval improves structured required-evidence coverage over chunk-only retrieval.",
            "required_evidence_coverage",
        ),
        (
            "B4",
            "B3",
            "Relation retrieval adds a clear coverage gain over entity-only retrieval.",
            "required_evidence_coverage",
        ),
        (
            "B5",
            "B4",
            "Graph expansion is the main recall jump and should be read separately from downstream answer-quality tradeoffs.",
            "final_evidence_recall",
        ),
        (
            "B6",
            "B5",
            "Query variants regress final evidence recall in this artifact, so query expansion needs tighter filtering.",
            "final_evidence_recall",
        ),
        (
            "B7",
            "B6",
            "Post-fusion rerank recovers final evidence after the query-variant stage.",
            "final_evidence_recall",
        ),
        (
            "Full",
            "B7",
            "Evidence selection reduces final evidence recall in this artifact, so the selection strategy still needs tuning.",
            "final_evidence_recall",
        ),
    ]
    for current, baseline, sentence, field in comparisons:
        current_value = value(current, field)
        baseline_value = value(baseline, field)
        if current_value is None or baseline_value is None:
            continue
        lines.append(
            f"- `{baseline} -> {current}`: {sentence} `{field}` {_fmt(baseline_value)} -> {_fmt(current_value)} ({_metric_delta(current_value, baseline_value)})."
        )
    return lines


def _metric(row: dict[str, str] | None, field: str) -> float | None:
    if not row:
        return None
    return _float_or_none(row.get(field))


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.4f}"


def _delta_phrase(value: float | None, baseline: float | None) -> str:
    if value is None or baseline is None:
        return "not comparable"
    delta = value - baseline
    direction = "higher" if delta >= 0 else "lower"
    return f"{abs(delta):.4f} {direction}"


def _source_docs(records: list[dict[str, Any]]) -> list[str]:
    docs: set[str] = set()
    for record in records:
        for evidence in record.get("required_evidence", []):
            file_path = evidence.get("file_path")
            if file_path:
                docs.add(Path(file_path).name)
        for source_ref in record.get("required_source_refs", []):
            doc_name = str(source_ref).split("|", 1)[0].strip()
            if doc_name:
                docs.add(doc_name)
    return sorted(docs)


def _compared_systems_text(config_ids: list[str]) -> str:
    if not config_ids:
        config_ids = FULL_CONFIG_ORDER
    ordered = [config_id for config_id in FULL_CONFIG_ORDER if config_id in config_ids]
    ordered.extend(config_id for config_id in config_ids if config_id not in ordered)
    return ", ".join(
        f"{config_id} {CONFIG_LABELS.get(config_id, '')}".strip()
        for config_id in ordered
    )


def _full_eval_context(full_eval_dir: Path | None) -> dict[str, Any]:
    if full_eval_dir is None:
        return {}
    metrics_rows = load_tsv(full_eval_dir / "metrics.tsv")
    if not metrics_rows:
        return {}
    manifest_path = full_eval_dir / "run_manifest.json"
    separation_path = full_eval_dir / "build_inference_separation" / "separation_summary.json"
    judge_path = full_eval_dir / "judge_results.jsonl"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    separation = (
        json.loads(separation_path.read_text(encoding="utf-8"))
        if separation_path.exists()
        else {}
    )
    main_rows = [row for row in metrics_rows if row.get("cache_phase") == "full_no_cache"]
    cache_rows = [row for row in metrics_rows if row.get("config_id") == "Full"]
    return {
        "dir": full_eval_dir,
        "metrics_rows": metrics_rows,
        "main_rows": main_rows,
        "cache_rows": cache_rows,
        "by_config": {row.get("config_id"): row for row in main_rows},
        "manifest": manifest,
        "separation": separation,
        "judge_statuses": _judge_status_counts(judge_path),
    }


def _fresh_build_audit_from_separation_data(
    full_eval_dir: Path,
    separation: dict[str, Any],
) -> dict[str, Any]:
    if separation.get("build_mode") != "fresh_online_and_raw_replay":
        return {}

    raw_units_dir_value = separation.get("raw_units_dir")
    raw_units_dir = _repo_path(raw_units_dir_value) if raw_units_dir_value else None
    raw_unit_files: list[dict[str, Any]] = []
    if raw_units_dir is not None and raw_units_dir.exists():
        for path in sorted(raw_units_dir.glob("*.jsonl")):
            raw_unit_files.append(
                {
                    "path": _display_path(path),
                    "line_count": _line_count(path),
                    "status": "present",
                }
            )

    online_snapshot = separation.get("online_build_snapshot") or {}
    offline_snapshot = separation.get("offline_replay_snapshot") or {}
    replay_files = offline_snapshot.get("file_digests") or {}
    replay_match = separation.get("online_vs_replay_match")
    status = "completed"
    paper_scope = "fresh live retrieval/QA plus build/replay/read-only"
    if replay_match is not True:
        status = "completed_with_digest_mismatch"
        paper_scope = "fresh live retrieval/QA and read-only replay isolation; online/raw-replay equivalence not validated"

    return {
        "artifact_dir": _display_path(full_eval_dir),
        "status": status,
        "paper_usable_scope": paper_scope,
        "online_build": {
            "completed_pdf_count": len(separation.get("pdfs") or []),
        },
        "online_build_snapshot": online_snapshot,
        "raw_export": {
            "completed_commands": raw_unit_files,
            "failed_commands": [],
            "raw_unit_files": raw_unit_files,
            "offline_replay_project_files": len(replay_files),
            "online_vs_replay_match": replay_match,
            "readonly_snapshot_unchanged": separation.get("readonly_snapshot_unchanged"),
            "offline_replay_digest": offline_snapshot.get("digest"),
        },
    }


def _load_fresh_build_audit(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    audit = json.loads(path.read_text(encoding="utf-8"))
    if audit.get("build_mode") == "fresh_online_and_raw_replay":
        full_eval_dir = (
            path.parents[1]
            if path.name == "separation_summary.json"
            and path.parent.name == "build_inference_separation"
            else path.parent
        )
        return _fresh_build_audit_from_separation_data(full_eval_dir, audit)
    return audit


def _fresh_build_audit_from_separation(full_eval_dir: Path | None) -> tuple[Path | None, dict[str, Any]]:
    if full_eval_dir is None:
        return None, {}
    separation_path = full_eval_dir / "build_inference_separation" / "separation_summary.json"
    if not separation_path.exists():
        return None, {}
    separation = json.loads(separation_path.read_text(encoding="utf-8"))
    audit = _fresh_build_audit_from_separation_data(full_eval_dir, separation)
    if not audit:
        return None, {}
    return separation_path, audit


def _default_fresh_build_audit_path() -> Path | None:
    path = (
        REPO_ROOT
        / "benchmark"
        / "erc_full_eval_20260527_155656"
        / "fresh_online_build_audit.json"
    )
    return path if path.exists() else None


def _manuscript_lines(
    *,
    records: list[dict[str, Any]],
    dataset_path: Path,
    full_eval_dir: Path | None,
    fresh_build_audit: dict[str, Any] | None = None,
) -> list[str]:
    context = _full_eval_context(full_eval_dir)
    annotated_records = _annotated_records_for_context(records, context)
    dataset_counts = Counter(str(record["dataset"]) for record in records)
    calc_count = sum(1 for record in records if record.get("requires_calculation"))
    matched_chunk_count = _matched_project_chunk_count(annotated_records)
    required_source_ref_count = _required_source_ref_count(annotated_records)
    docs = _source_docs(records)
    manifest_configs = []
    if context:
        manifest_configs = list((context.get("manifest") or {}).get("configs") or [])

    lines = [
        "## Abstract",
        "",
        "Professional PDF question answering often requires combining definitions, tables, threshold rules, and provenance-bearing evidence across sections or documents. This report evaluates a provenance-aware Entity-Relation-Chunk (ERC) evidence graph for traceable multi-evidence RAG, using the current reproducible local benchmark artifacts rather than gold replay as system performance.",
        "",
        "The primary empirical claim is scoped to retrieval-layer evidence coverage and provenance organization. Downstream answer quality metrics are retained only as diagnostics because a business system can consume retrieved graph evidence and assemble its own prompt, context, and final response.",
        "",
        f"The current live dataset is `{_display_path(dataset_path)}` with {len(records)} questions, {len(docs)} source files, {matched_chunk_count} matched project chunk links across {required_source_ref_count} required source-reference annotations, and {calc_count} calculation-oriented questions. The compared systems are {_compared_systems_text(manifest_configs)}.",
        "",
        "## 1. Research Questions",
        "",
        "RQ1: Does a provenance-aware ERC heterogeneous evidence graph improve multi-evidence coverage over chunk-only retrieval?",
        "",
        "RQ2: Which retrieval components contribute most under the current implementation: chunk retrieval, entity/relation retrieval, graph expansion, rerank, query variants, or evidence selection?",
        "",
        "RQ3: Does the engineering path support materialized evidence graphs, replayable build artifacts, read-only inference, and practical cache acceleration?",
        "",
        "## 2. Experimental Design",
        "",
        "### Data",
        "",
        f"The experiment uses `{_display_path(dataset_path)}`. The dataset split is: "
        + ", ".join(f"{name}={count}" for name, count in sorted(dataset_counts.items()))
        + ". Source files are: "
        + ", ".join(f"`{doc}`" for doc in docs)
        + ".",
        "",
        "Each question includes a gold answer, required entities/relations, and source-reference requirements. The full-evaluation artifact writes `annotated_dataset.jsonl` with matched `chunk_id`, `source_ref`, `page_numbers`, `section_path`, and `file_path` where a project chunk is found. Unmatched source-reference requirements remain explicitly marked as unmatched; no pseudo pages or synthetic chunks are generated.",
        "",
        *_dataset_mapping_audit_lines(dataset_path),
        "",
        "### Systems",
        "",
        "B0 is a flat chunk vector baseline. B1 adds rerank. B2 disables chunk vector retrieval and uses entity/relation graph retrieval plus graph expansion. B3 combines chunk and entity retrieval. B4 adds relation retrieval. B5 adds graph-neighborhood expansion. B6 adds query variants. B7 adds rerank after graph/variant fusion. Full adds coverage-aware evidence selection.",
        "",
        "### Metrics",
        "",
        "The primary retrieval-layer metrics are Evidence Recall@K, Final Evidence Recall, Required Evidence Coverage, and latency. These are computed from live retrieved/final chunks against true project chunk IDs and manually verified required evidence. Citation Precision/Recall and LLM-judged answer quality are reported as diagnostics for downstream citation grounding and business answer generation, not as the main retrieval-layer success criteria.",
        "",
        "### LLM Model Constraint",
        "",
        f"All external LLM-backed ERC experiments, LLM judge runs, reruns, and report-refresh measurements are constrained to `LLM_MODEL_URL={ALLOWED_LIVE_LLM_MODEL_URL}` and `LLM_MODEL={ALLOWED_LIVE_LLM_MODEL}`. The experiment protocol does not switch to `deepseek-v4-pro`, Claude Opus, or any other LLM to improve results; model-capability limits must be reported as limitations.",
    ]

    if not context:
        lines.extend(
            [
                "",
                "## 3. Live Results",
                "",
                "No complete live evaluation artifact is currently selected. Run `tools/erc_full_eval.py --backend live` and regenerate this report to populate result analysis.",
            ]
        )
        return lines

    by_config: dict[str, dict[str, str]] = context["by_config"]
    separation: dict[str, Any] = context["separation"]
    manifest: dict[str, Any] = context["manifest"]
    judge_statuses: Counter[str] = context["judge_statuses"]
    main_rows: list[dict[str, str]] = context["main_rows"]
    cache_rows: list[dict[str, str]] = context["cache_rows"]
    best_correctness = max(
        main_rows,
        key=lambda row: _metric(row, "correctness") or float("-inf"),
    )
    best_evidence = max(
        main_rows,
        key=lambda row: _metric(row, "evidence_recall_at_k") or float("-inf"),
    )
    b0 = by_config.get("B0")
    b5 = by_config.get("B5")
    full = by_config.get("Full")
    paper_scope = _paper_scope(
        backend_kind=manifest.get("backend_kind") or "-",
        manifest=manifest,
        separation=separation,
        judge_statuses=judge_statuses,
    )
    no_cache = next(
        (row for row in cache_rows if row.get("cache_phase") == "full_no_cache"),
        None,
    )
    answer_warm = next(
        (row for row in cache_rows if row.get("cache_phase") == "answer_cache_warm"),
        None,
    )
    if separation.get("build_mode") == "fresh_online_and_raw_replay":
        if (
            separation.get("online_vs_replay_match") is True
            and separation.get("readonly_snapshot_unchanged") is True
        ):
            build_replay_text = (
                f"This selected artifact has build mode `{separation.get('build_mode')}`. "
                "`online_vs_replay_match` and `readonly_snapshot_unchanged` are both `True`, "
                "so it supports retrieval/QA and build/replay/read-only claims."
            )
            build_discussion_text = (
                "The live result also separates two claims. The retrieval-layer evidence-coverage claim "
                "is supported by the selected live project, and the build/replay/read-only engineering "
                "claim is supported by matching online/replay and unchanged read-only digests."
            )
            limitation_text = (
                "The current 186-question DQE-mapped dataset is suitable for this retrieval-layer "
                "ablation, but it remains a single-domain mapped benchmark rather than a broad-domain "
                "performance estimate. Citation precision/recall remain weak and should be "
                "treated as downstream grounding diagnostics. The next method work should improve final "
                "evidence selection so that B6/B7 candidate-recall gains are preserved in final evidence."
            )
        else:
            build_replay_text = (
                f"This selected artifact has build mode `{separation.get('build_mode')}`. "
                f"`readonly_snapshot_unchanged` is `{separation.get('readonly_snapshot_unchanged')}` "
                f"and `online_vs_replay_match` is `{separation.get('online_vs_replay_match')}`. "
                "Therefore retrieval/QA ablation and read-only isolation can be discussed, but "
                "online-build versus raw-replay equivalence is not validated for a paper main table."
            )
            build_discussion_text = (
                "The live result also separates two claims. The retrieval-layer evidence-coverage claim "
                "is supported by the selected live project. The build/replay/read-only engineering claim "
                "is only partially supported here: raw replay completed and read-only inference preserved "
                "the replay digest, but online and replay logical snapshots did not match."
            )
            limitation_text = (
                "The current 186-question DQE-mapped dataset is suitable for this retrieval-layer "
                "ablation, but it remains a single-domain mapped benchmark rather than a broad-domain "
                "performance estimate. Citation precision/recall remain weak and should be "
                "treated as downstream grounding diagnostics. The next method work should improve final "
                "evidence selection so that B6/B7 candidate-recall gains are preserved in final evidence, "
                "and should diagnose the online/replay digest mismatch before making a full build/replay claim."
            )
    elif separation.get("build_mode") == "existing_project_copy":
        build_replay_text = (
            f"This selected artifact has build mode `{separation.get('build_mode')}`. "
            "It supports retrieval/QA ablation on the copied live project, but not fresh "
            "online-build versus raw-replay reproducibility."
        )
        build_discussion_text = (
            "The live result also separates two claims. The retrieval-layer evidence-coverage claim "
            "is supported by the selected live project. The build/replay/read-only engineering claim "
            "is not supported here because the evaluation used an existing project copy."
        )
        limitation_text = (
            "The current DQE full dataset is suitable for the main retrieval/QA ablation because it "
            "uses the full mapped DQE gold pool rather than the historical pilot. Citation precision/recall "
            "remain weak and should be treated as downstream grounding diagnostics. A fresh raw-unit replay "
            "artifact is still required before making build/replay paper claims."
        )
    else:
        build_replay_text = (
            f"This selected artifact has build mode `{separation.get('build_mode')}`. "
            "Build/replay provenance is incomplete, so only retrieval/QA results should be discussed."
        )
        build_discussion_text = (
            "The live result separates retrieval evidence-coverage from build/replay engineering claims; "
            "the latter remains incomplete for this artifact."
        )
        limitation_text = (
            "The current DQE-mapped dataset is suitable for this retrieval-layer ablation, but it remains "
            "a single-domain mapped benchmark rather than a broad-domain performance estimate. "
            "Citation precision/recall remain weak and should be "
            "treated as downstream grounding diagnostics."
        )

    lines.extend(
        [
            "",
            "## 3. Live Results",
            "",
            f"The selected live artifact is `{_display_path(context['dir'])}`. It was run with backend `{manifest.get('backend')}`, judge mode `{manifest.get('judge_mode')}`, configs `{', '.join(manifest.get('configs', []))}`, and judge statuses `{dict(judge_statuses)}`. Paper scope is: {paper_scope}.",
            "",
            *_retrieval_layer_analysis_lines(main_rows),
            "",
            "### 3.4 Downstream Answer Quality Diagnostic",
            "",
            f"The best downstream correctness in this artifact is `{best_correctness.get('config_id')}` at {_fmt(_metric(best_correctness, 'correctness'))}. Full reaches correctness {_fmt(_metric(full, 'correctness'))}, which is {_delta_phrase(_metric(full, 'correctness'), _metric(b0, 'correctness'))} than B0 and {_delta_phrase(_metric(full, 'correctness'), _metric(b5, 'correctness'))} than B5. This diagnostic is reported as observed, but it is not the main retrieval-layer claim.",
            "",
            f"Faithfulness follows a similar component-sensitive diagnostic pattern: B0={_fmt(_metric(b0, 'faithfulness'))}, B5={_fmt(_metric(b5, 'faithfulness'))}, Full={_fmt(_metric(full, 'faithfulness'))}. Unsupported claim rate is B0={_fmt(_metric(b0, 'unsupported_claim_rate'))}, B5={_fmt(_metric(b5, 'unsupported_claim_rate'))}, Full={_fmt(_metric(full, 'unsupported_claim_rate'))}.",
            "",
            "### 3.5 Latency And Cache Behavior",
            "",
            f"Full no-cache latency is p50={_fmt(_metric(no_cache, 'latency_p50_seconds'))}s, p95={_fmt(_metric(no_cache, 'latency_p95_seconds'))}s, mean={_fmt(_metric(no_cache, 'latency_mean_seconds'))}s. Answer-cache warm latency is p50={_fmt(_metric(answer_warm, 'latency_p50_seconds'))}s, showing that answer cache materially accelerates repeated queries under the current runtime path.",
            "",
            *_cache_caveat_lines(cache_rows),
            "",
            "### 3.6 Build, Replay, And Read-Only Inference",
            "",
            build_replay_text,
            "",
            *_dqe_attribution_lines(context["dir"]),
            "",
            "## 4. Discussion",
            "",
            "The component ablation should be read as an ordered retrieval-layer path from B0 through B7 and Full: B3 isolates entity retrieval, B4 relation retrieval, B5 graph expansion, B6 query variants, B7 rerank, and Full evidence selection. The main result is that graph-aware components improve structured required-evidence coverage and candidate recall, while later stages still need better selection and grounding to preserve those retrieved gains.",
            "",
            "This framing separates the knowledge-graph retrieval contract from downstream business answer generation. A business system can consume retrieved graph evidence, assemble its own context, and evaluate its final answer separately; therefore answer-quality scores in this report should remain diagnostic rather than the primary success criterion for the retrieval module.",
            "",
            build_discussion_text,
            "",
            "## 5. Limitations And Next Steps",
            "",
            limitation_text,
        ]
    )
    if fresh_build_audit:
        snapshot = fresh_build_audit.get("online_build_snapshot") or {}
        raw_export = fresh_build_audit.get("raw_export") or {}
        failed_commands = raw_export.get("failed_commands") or []
        failed_label = (
            failed_commands[0].get("label") if failed_commands else "raw export"
        )
        if raw_export.get("online_vs_replay_match") is True:
            fresh_audit_text = (
                f"A separate fresh online build audit is available at `{fresh_build_audit.get('artifact_dir')}`. "
                f"It completed {fresh_build_audit.get('online_build', {}).get('completed_pdf_count')} online PDF builds and materialized a graph with {snapshot.get('graph_nodes')} nodes, {snapshot.get('graph_edges')} edges, {snapshot.get('doc_status')} document status rows, and digest `{snapshot.get('digest')}`. Raw replay matched the online snapshot."
            )
        elif failed_commands:
            fresh_audit_text = (
                f"A separate fresh online build audit is available at `{fresh_build_audit.get('artifact_dir')}`. "
                f"It completed {fresh_build_audit.get('online_build', {}).get('completed_pdf_count')} online PDF builds and materialized a graph with {snapshot.get('graph_nodes')} nodes, {snapshot.get('graph_edges')} edges, {snapshot.get('doc_status')} document status rows, and digest `{snapshot.get('digest')}`. Raw replay remains incomplete: `online_vs_replay_match` is `{raw_export.get('online_vs_replay_match')}` after `{failed_label}` failed."
            )
        else:
            fresh_audit_text = (
                f"A separate fresh online build audit is available at `{fresh_build_audit.get('artifact_dir')}`. "
                f"It completed {fresh_build_audit.get('online_build', {}).get('completed_pdf_count')} online PDF builds and materialized a graph with {snapshot.get('graph_nodes')} nodes, {snapshot.get('graph_edges')} edges, {snapshot.get('doc_status')} document status rows, and digest `{snapshot.get('digest')}`. Raw replay did not validate equivalence: `online_vs_replay_match` is `{raw_export.get('online_vs_replay_match')}`."
            )
        discussion_index = lines.index("## 4. Discussion")
        lines[discussion_index:discussion_index] = [
            "",
            fresh_audit_text,
            "",
        ]
        old_limitations = "The current minimum dataset is intentionally small and manually curated. It is suitable for a reproducible pilot and ablation analysis, but it does not yet estimate broad-domain performance. Citation precision/recall remain weak and should be improved or explained before making a strong traceability claim. The ongoing fresh-build run should be used to populate the build/replay section if it completes with matching digests."
        if old_limitations in lines:
            lines[lines.index(old_limitations)] = "The current minimum dataset is intentionally small and manually curated. It is suitable for a reproducible pilot and ablation analysis, but it does not yet estimate broad-domain performance. Citation precision/recall remain weak and should be improved or explained before making a strong traceability claim. The fresh online build audit should be extended with a completed raw export, offline replay, and matching digest comparison before it is used for build/replay paper claims."
    return lines


def _fresh_build_audit_lines(audit_path: Path | None, audit: dict[str, Any]) -> list[str]:
    if not audit:
        return []
    snapshot = audit.get("online_build_snapshot") or {}
    online_build = audit.get("online_build") or {}
    raw_export = audit.get("raw_export") or {}
    failed_commands = raw_export.get("failed_commands") or []
    failed_error = failed_commands[0].get("error") if failed_commands else "-"
    rows = [
        ["artifact", audit.get("artifact_dir")],
        ["status", audit.get("status")],
        ["paper usable scope", audit.get("paper_usable_scope")],
        ["completed online PDF builds", online_build.get("completed_pdf_count")],
        ["graph nodes", snapshot.get("graph_nodes")],
        ["graph edges", snapshot.get("graph_edges")],
        ["entity VDB rows", snapshot.get("entity_vdb")],
        ["relationship VDB rows", snapshot.get("relationship_vdb")],
        ["chunk VDB rows", snapshot.get("chunk_vdb")],
        ["doc status rows", snapshot.get("doc_status")],
        ["text chunks", snapshot.get("text_chunks")],
        ["online project digest", snapshot.get("digest")],
        ["offline replay digest", raw_export.get("offline_replay_digest")],
        ["raw export completed commands", len(raw_export.get("completed_commands") or [])],
        ["raw export failed commands", len(failed_commands)],
        ["offline replay project files", raw_export.get("offline_replay_project_files")],
        ["online_vs_replay_match", raw_export.get("online_vs_replay_match")],
        ["readonly_snapshot_unchanged", raw_export.get("readonly_snapshot_unchanged")],
        ["raw export failure", failed_error],
    ]
    raw_rows = [
        [item.get("path"), item.get("line_count"), item.get("status")]
        for item in raw_export.get("raw_unit_files") or []
    ]
    if raw_export.get("online_vs_replay_match") is True:
        interpretation = (
            "Interpretation: this artifact supports fresh online evidence-graph materialization "
            "and raw replay equivalence."
        )
    elif failed_commands:
        interpretation = (
            "Interpretation: this artifact supports fresh online evidence-graph materialization, "
            "but it does not validate raw replay equivalence because raw export or replay failed."
        )
    else:
        interpretation = (
            "Interpretation: this artifact supports fresh online evidence-graph materialization, "
            "but raw replay equivalence is not validated."
        )
    lines = ["## Fresh Online Build Audit", ""]
    if audit_path is not None:
        lines.extend([f"- Source: `{_display_path(audit_path)}`", ""])
    lines.extend(
        [
            *_markdown_table(["check", "value"], rows),
            "",
            "### Raw Unit Export Status",
            "",
            *_markdown_table(["raw unit file", "lines", "status"], raw_rows),
            "",
            interpretation,
        ]
    )
    return lines


def _experiment_matrix_lines(full_eval_dir: Path | None) -> list[str]:
    covered_configs = set()
    if full_eval_dir is not None:
        for row in load_tsv(full_eval_dir / "metrics.tsv"):
            if row.get("cache_phase") == "full_no_cache" and row.get("config_id"):
                covered_configs.add(row["config_id"])
    configs = [
        ("B0", "Flat Chunk RAG", "chunk-only baseline"),
        ("B1", "Chunk + Rerank", "rerank-only gain"),
        ("B2", "Graph-only", "entity/relation/neighborhood contribution"),
        ("B3", "Chunk + Entity", "entity recall gain"),
        ("B4", "Chunk + Entity + Relation", "relation recall gain"),
        ("B5", "Chunk + Entity + Relation + Graph Expansion", "graph expansion gain"),
        ("B6", "B5 + Query Variants", "multi-constraint coverage gain"),
        ("B7", "B6 + Rerank", "rerank gain after graph/variant fusion"),
        ("Full", "B7 + Evidence Selection", "evidence-selection stage under test"),
    ]
    rows = [
        [
            config_id,
            name,
            purpose,
            "covered in current full eval artifact"
            if config_id in covered_configs
            else "not run in current full eval artifact",
        ]
        for config_id, name, purpose in configs
    ]
    return [
        "## Experiment Matrix",
        "",
        *_markdown_table(["ID", "Configuration", "Purpose", "Current status"], rows),
    ]


def _full_eval_summary_lines(full_eval_dir: Path | None) -> list[str]:
    if full_eval_dir is None:
        return [
            "## Full Evaluation",
            "",
            "- Status: missing `benchmark/erc_full_eval_*` artifact.",
            "- Reproduce with: `uv run python tools/erc_full_eval.py`",
        ]
    metrics_path = full_eval_dir / "metrics.tsv"
    summary_path = full_eval_dir / "summary.md"
    latency_path = full_eval_dir / "latency_cache_summary.md"
    separation_path = full_eval_dir / "build_inference_separation" / "separation_summary.json"
    results_path = full_eval_dir / "results.jsonl"
    manifest_path = full_eval_dir / "run_manifest.json"
    commands_path = full_eval_dir / "commands.md"
    judge_path = full_eval_dir / "judge_results.jsonl"
    annotated_dataset_path = full_eval_dir / "annotated_dataset.jsonl"
    metrics_rows = load_tsv(metrics_path)
    if not metrics_rows:
        return [
            "## Full Evaluation",
            "",
            f"- Source: `{_display_path(full_eval_dir)}`",
            "- Status: missing or empty `metrics.tsv`.",
        ]

    main_rows = [
        row for row in metrics_rows if row.get("cache_phase") == "full_no_cache"
    ]
    cache_rows = [
        row
        for row in metrics_rows
        if row.get("config_id") == "Full"
    ]
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    backend_kind = manifest.get("backend_kind") or (
        "live"
        if any(row.get("backend") == "live" for row in metrics_rows)
        else "sanity"
    )
    heading_prefix = "Live" if backend_kind == "live" else "Gold Replay Sanity"
    separation = {}
    if separation_path.exists():
        separation = json.loads(separation_path.read_text(encoding="utf-8"))
    judge_statuses = _judge_status_counts(judge_path)
    paper_eligible, paper_reason = _paper_eligibility(
        backend_kind=backend_kind,
        manifest=manifest,
        separation=separation,
        judge_statuses=judge_statuses,
    )
    paper_scope = _paper_scope(
        backend_kind=backend_kind,
        manifest=manifest,
        separation=separation,
        judge_statuses=judge_statuses,
    )

    lines = [
        "## Full Evaluation Artifacts",
        "",
        f"- Directory: `{_display_path(full_eval_dir)}`",
        f"- Result class: `{heading_prefix}`",
        f"- Fresh-build paper-table eligibility: `{'yes' if paper_eligible else 'no'}`",
        f"- Paper-usable scope: {paper_scope}",
        f"- Eligibility reason: {paper_reason}",
        f"- Judge mode: `{manifest.get('judge_mode') or '-'}`",
        f"- Allowed external LLM: `LLM_MODEL_URL={ALLOWED_LIVE_LLM_MODEL_URL}`, `LLM_MODEL={ALLOWED_LIVE_LLM_MODEL}`",
        f"- Judge statuses: `{dict(judge_statuses) if judge_statuses else {}}`",
        f"- Results JSONL: `{_display_path(results_path)}`",
        f"- Judge JSONL: `{_display_path(judge_path)}`",
        f"- Metrics TSV: `{_display_path(metrics_path)}`",
        f"- Summary: `{_display_path(summary_path)}`",
        f"- Cache summary: `{_display_path(latency_path)}`",
        f"- Commands: `{_display_path(commands_path)}`",
        f"- Annotated dataset: `{_display_path(annotated_dataset_path) if annotated_dataset_path.exists() else '-'}`",
        f"- Build/replay separation: `{_display_path(separation_path)}`",
        "",
        *_artifact_completeness_lines(full_eval_dir),
        "",
        *_result_interpretation_lines(
            heading_prefix=heading_prefix,
            paper_scope=paper_scope,
            paper_eligible=paper_eligible,
            main_rows=main_rows,
            separation=separation,
        ),
        "",
        f"### {heading_prefix} Retrieval-Layer Results",
        "",
        *_markdown_table(
            [
                "config",
                "name",
                "evidence_recall@k",
                "final_recall",
                "required_coverage",
                "latency_p50_s",
                "retrieval_layer_conclusion",
            ],
            _retrieval_layer_result_rows(main_rows),
        ),
        "",
        f"### {heading_prefix} Downstream Answer Diagnostic Results",
        "",
        *_markdown_table(
            [
                "config",
                "correctness",
                "completeness",
                "faithfulness",
                "numerical_accuracy",
                "required_coverage",
                "unsupported_claim_rate",
            ],
            [
                [
                    row["config_id"],
                    row["correctness"],
                    row["completeness"],
                    row["faithfulness"],
                    row["numerical_accuracy"],
                    row["required_evidence_coverage"],
                    row["unsupported_claim_rate"],
                ]
                for row in main_rows
            ],
        ),
        "",
        f"### {heading_prefix} Ablation Results",
        "",
        *_markdown_table(
            ["config", "name", "evidence_recall@k", "final_recall", "citation_p", "citation_r"],
            [
                [
                    row["config_id"],
                    row["config_name"],
                    row["evidence_recall_at_k"],
                    row["final_evidence_recall"],
                    row["citation_precision"],
                    row["citation_recall"],
                ]
                for row in main_rows
            ],
        ),
        "",
        f"### {heading_prefix} Evidence Coverage",
        "",
        *_markdown_table(
            ["config", "required_coverage", "keyword_sources", "rerank_used"],
            [
                [
                    row["config_id"],
                    row["required_evidence_coverage"],
                    row["keyword_sources"],
                    row["rerank_used"],
                ]
                for row in main_rows
            ],
        ),
        "",
        f"### {heading_prefix} Latency And Cache",
        "",
        *_markdown_table(
            ["cache_phase", "p50_s", "p95_s", "mean_s", "cache_hit_stages"],
            [
                [
                    row["cache_phase"],
                    row["latency_p50_seconds"],
                    row["latency_p95_seconds"],
                    row["latency_mean_seconds"],
                    row["cache_hit_stages"] or "-",
                ]
                for row in cache_rows
            ],
        ),
    ]

    if separation:
        snapshot = separation.get("online_build_snapshot") or {}
        lines.extend(
            [
                "",
                "### Build/Inference Separation",
                "",
                *_markdown_table(
                    ["check", "value"],
                    [
                        ["raw_units_count", separation.get("raw_units_count")],
                        ["online_vs_replay_match", separation.get("online_vs_replay_match")],
                        [
                            "readonly_snapshot_unchanged",
                            separation.get("readonly_snapshot_unchanged"),
                        ],
                        ["graph_nodes", snapshot.get("graph_nodes")],
                        ["graph_edges", snapshot.get("graph_edges")],
                        ["entity_vdb", snapshot.get("entity_vdb")],
                        ["relationship_vdb", snapshot.get("relationship_vdb")],
                        ["chunk_vdb", snapshot.get("chunk_vdb")],
                        ["doc_status", snapshot.get("doc_status")],
                    ],
                ),
            ]
        )

    lines.extend(
        [
            "",
            "### ERC Retrieval Path Case",
            "",
        ]
    )
    if summary_path.exists():
        summary_text = summary_path.read_text(encoding="utf-8")
        marker = "## ERC Retrieval Path Case"
        if marker in summary_text:
            case_text = summary_text.split(marker, 1)[1].split("## ", 1)[0].strip()
            lines.extend(case_text.splitlines())
        else:
            lines.append("- See `summary.md` for the case path.")
    else:
        lines.append("- See `summary.md` for the case path.")
    return lines


def _gold_replay_dir_for_dataset(dataset_path: Path) -> Path | None:
    suffix = _dataset_suffix(dataset_path)
    if suffix:
        candidate = REPO_ROOT / "benchmark" / f"erc_dqe_full_gold_replay_{suffix}"
        if (candidate / "metrics.tsv").exists():
            return candidate
    candidates = [
        path
        for path in (REPO_ROOT / "benchmark").glob("erc_dqe_full_gold_replay_*")
        if path.is_dir() and (path / "metrics.tsv").exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _gold_replay_sanity_lines(dataset_path: Path) -> list[str]:
    gold_dir = _gold_replay_dir_for_dataset(dataset_path)
    if gold_dir is None:
        return []
    metrics_rows = load_tsv(gold_dir / "metrics.tsv")
    main_rows = [
        row for row in metrics_rows if row.get("cache_phase") == "full_no_cache"
    ]
    if not main_rows:
        return []
    by_config = {row.get("config_id"): row for row in main_rows}
    ordered_rows = [
        by_config[config_id]
        for config_id in FULL_CONFIG_ORDER
        if config_id in by_config
    ]
    artifact_rows = [
        [name, _line_count(gold_dir / name) if (gold_dir / name).exists() else "missing"]
        for name in (
            "results.jsonl",
            "judge_results.jsonl",
            "metrics.tsv",
            "dqe_slice_metrics.tsv",
            "component_delta_by_slice.tsv",
            "per_question_component_attribution.jsonl",
        )
    ]
    failure_rows = _failure_counts_from_taxonomy(gold_dir / "failure_taxonomy.md")
    lines = [
        "## Gold Replay Harness Sanity Appendix",
        "",
        f"- Directory: `{_display_path(gold_dir)}`",
        "- Scope: engineering sanity only. These numbers are not live system performance and must not be used as the paper main table.",
        "- Interpretation: gold replay confirms the scoring schema and attribution pipeline can recognize required evidence when gold evidence is injected; it does not measure retrieval, online build quality, or raw replay equivalence.",
        "",
        *_markdown_table(
            [
                "config",
                "evidence_recall@k",
                "final_recall",
                "required_coverage",
                "correctness",
                "unsupported_claim_rate",
            ],
            [
                [
                    row["config_id"],
                    row["evidence_recall_at_k"],
                    row["final_evidence_recall"],
                    row["required_evidence_coverage"],
                    row["correctness"],
                    row["unsupported_claim_rate"],
                ]
                for row in ordered_rows
            ],
        ),
        "",
        *_markdown_table(["artifact", "non-empty rows"], artifact_rows),
    ]
    if failure_rows:
        lines.extend(
            [
                "",
                *_markdown_table(["failure type", "count"], failure_rows),
            ]
        )
    return lines


def _figure_artifact_note_lines(full_eval_dir: Path | None) -> list[str]:
    table_script = REPO_ROOT / "tools" / "render_erc_tables.py"
    cache_script = REPO_ROOT / "tools" / "render_erc_cache_figures.py"
    figure_dir = REPO_ROOT / "docs" / "research" / "figures"
    if not table_script.exists() and not cache_script.exists():
        return []
    full_eval_arg = (
        _display_path(full_eval_dir)
        if full_eval_dir is not None
        else "benchmark/erc_full_eval_<timestamp>"
    )
    return [
        "## Figure Artifact Note",
        "",
        f"- Figure/table images are written under `{_display_path(figure_dir)}`.",
        f"- `{_display_path(table_script)}` reads `metrics.tsv`, `annotated_dataset.jsonl`, and `build_inference_separation/separation_summary.json` from the selected full eval artifact.",
        f"- `{_display_path(cache_script)}` reads the selected full eval artifact for query-cache results and the keyword-cache TSV for retrieval-stage cache analysis.",
        f"- Regenerate with: `python3 tools/render_erc_tables.py --full-eval-dir {full_eval_arg}` and `python3 tools/render_erc_cache_figures.py --full-eval-dir {full_eval_arg}`.",
    ]


def render_report(
    *,
    dataset_path: Path,
    latency_path: Path,
    retrieval_path: Path,
    keyword_cache_path: Path,
    full_eval_dir: Path | None = None,
    fresh_build_audit_path: Path | None = None,
    strict_cold_eval_dir: Path | None = None,
) -> str:
    records = load_jsonl(dataset_path)
    latency_rows = load_tsv(latency_path)
    retrieval_rows = load_tsv(retrieval_path)
    keyword_cache_rows = load_tsv(keyword_cache_path)
    explicit_full_eval_dir = full_eval_dir is not None
    resolved_full_eval_dir = full_eval_dir or _latest_full_eval_dir()
    if fresh_build_audit_path is not None:
        resolved_fresh_build_audit_path = fresh_build_audit_path
        fresh_build_audit = _load_fresh_build_audit(resolved_fresh_build_audit_path)
    else:
        resolved_fresh_build_audit_path, fresh_build_audit = _fresh_build_audit_from_separation(
            resolved_full_eval_dir
        )
        if not fresh_build_audit and not explicit_full_eval_dir:
            resolved_fresh_build_audit_path = _default_fresh_build_audit_path()
            fresh_build_audit = _load_fresh_build_audit(resolved_fresh_build_audit_path)
    report_fresh_build_arg = (
        f" --fresh-build-audit {_display_path(resolved_fresh_build_audit_path)}"
        if resolved_fresh_build_audit_path is not None
        else ""
    )
    report_strict_cold_arg = (
        f"--strict-cold-eval-dir {_display_path(strict_cold_eval_dir)}"
        if strict_cold_eval_dir is not None
        else "--strict-cold-eval-dir benchmark/erc_full_eval_strict_cold_<timestamp>"
    )
    strict_live_project_dir = "example/qwen4b_diet_kg"
    if (
        resolved_fresh_build_audit_path is not None
        and resolved_fresh_build_audit_path.name == "separation_summary.json"
        and resolved_fresh_build_audit_path.parent.name == "build_inference_separation"
    ):
        strict_live_project_dir = _display_path(
            resolved_fresh_build_audit_path.parents[1]
            / "build_inference_separation"
            / "offline_replay_project"
        )

    lines = [
        "# ERC Traceable RAG Research Report",
        "",
        "This manuscript-style report materializes the ERC task in `Goal.md`: research questions, experimental design, live benchmark results, result analysis, cache behavior, and build/replay separation for provenance-aware ERC evidence graph RAG.",
        "",
        "Overall result index: [`erc_traceable_rag_total_results.md`](./erc_traceable_rag_total_results.md).",
        "",
        *_manuscript_lines(
            records=records,
            dataset_path=dataset_path,
            full_eval_dir=resolved_full_eval_dir,
            fresh_build_audit=fresh_build_audit,
        ),
        "",
        "## Implementation Mapping",
        "",
        "| Goal component | Existing implementation surface |",
        "|---|---|",
        "| ERC provenance fields | `source_ref`, `page_numbers`, `section_path`, `source_chunk_ids` in chunk/entity/relation contexts |",
        "| Chunk semantic retrieval | `hybrid_query()` vector chunk path and `chunks_vdb` |",
        "| Entity/relation retrieval | `graph_query()` and `hybrid_query()` entity/relationship vector paths |",
        "| Graph neighborhood expansion | `_find_most_related_text_unit_from_entities()` and `_find_related_text_unit_from_relationships()` |",
        "| Query variants | `_build_diversified_retrieval_queries()` and matched query variant metadata |",
        "| Rerank | `ragent.rerank.rerank_from_env()` integration, with fallback order when not configured |",
        "| Evidence selection | `_select_hybrid_context_entries()` coverage-aware final chunk selection |",
        "| Cache acceleration | query cache stages plus keyword candidate cache benchmark artifacts |",
        "| Offline replay/read-only inference | `ragent/offline_replay.py`, `tools/export_raw_merge_units.py`, `tools/replay_raw_merge_units_to_project.py` |",
        "",
        *_dataset_summary_lines(records, dataset_path),
        "",
        *_full_eval_summary_lines(resolved_full_eval_dir),
        "",
        *_strict_cold_control_lines(strict_cold_eval_dir, resolved_full_eval_dir),
        "",
        *_gold_replay_sanity_lines(dataset_path),
        "",
        *_fresh_build_audit_lines(
            resolved_fresh_build_audit_path,
            fresh_build_audit,
        ),
        "",
        *_retrieval_summary_lines(retrieval_rows, retrieval_path),
        "",
        *_latency_summary_lines(latency_rows, latency_path),
        "",
        *_keyword_cache_summary_lines(keyword_cache_rows, keyword_cache_path),
        "",
        *_experiment_matrix_lines(resolved_full_eval_dir),
        "",
        *_figure_artifact_note_lines(resolved_full_eval_dir),
        "",
        "## Verification Commands",
        "",
        "```bash",
        "uv run python tools/erc_full_eval.py --backend live --skip-live-build --live-project-dir example/qwen4b_diet_kg --dataset "
        f"{_display_path(dataset_path)} --configs B0 B1 B2 B3 B4 B5 B6 B7 Full --judge-mode llm --output-dir "
        "benchmark/erc_full_eval_<timestamp> --skip-report --resume-partial --live-concurrency 4 "
        "--live-max-attempts 5 --live-retry-sleep 20 --live-query-timeout 360 --live-judge-timeout 180",
        "uv run python tools/erc_full_eval.py --dataset "
        f"{_display_path(dataset_path)} --backend live --skip-live-build --live-project-dir "
        f"{strict_live_project_dir} "
        "--configs Full --judge-mode llm --live-concurrency 1 --clear-cache-per-live-row "
        "--output-dir benchmark/erc_full_eval_strict_cold_<timestamp> --skip-report",
        "uv run python tools/erc_research_report.py --dataset "
        f"{_display_path(dataset_path)} --full-eval-dir "
        f"{_display_path(resolved_full_eval_dir) if resolved_full_eval_dir else 'benchmark/erc_full_eval_<timestamp>'} "
        f"{report_fresh_build_arg} {report_strict_cold_arg} "
        f"--output {_display_path(DEFAULT_REPORT)}",
        "uv run pytest tests/test_erc_research_dataset.py tests/test_erc_full_eval.py tests/test_diversified_graph_retrieval.py",
        "RUNS=1 MODES=\"graph hybrid\" RERANK_OPTIONS=\"off on\" PROJECT_DIR=\"example/demo_diet_kg_5\" bash script/latency_test.sh",
        "uv run python benchmark/keyword_cache_benefit.py --project-dir benchmark/keyword_cache_benefit_qwen4b_manual/project --mode hybrid",
        "```",
        "",
        "## Completion Status",
        "",
        "Use only paper-eligible `live` full-evaluation artifacts for paper main tables. `gold_replay`, historical benchmarks, synthetic artifacts, and non-fresh live smoke runs are engineering self-checks only.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    dataset_path = _repo_path(args.dataset)
    latency_path = _repo_path(args.latency_results)
    retrieval_path = _repo_path(args.retrieval_results)
    keyword_cache_path = _repo_path(args.keyword_cache_results)
    full_eval_dir = _repo_path(args.full_eval_dir) if args.full_eval_dir else None
    fresh_build_audit_path = (
        _repo_path(args.fresh_build_audit) if args.fresh_build_audit else None
    )
    strict_cold_eval_dir = (
        _repo_path(args.strict_cold_eval_dir) if args.strict_cold_eval_dir else None
    )
    output_path = _repo_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_report(
            dataset_path=dataset_path,
            latency_path=latency_path,
            retrieval_path=retrieval_path,
            keyword_cache_path=keyword_cache_path,
            full_eval_dir=full_eval_dir,
            fresh_build_audit_path=fresh_build_audit_path,
            strict_cold_eval_dir=strict_cold_eval_dir,
        )
        + "\n",
        encoding="utf-8",
    )
    print(_display_path(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
