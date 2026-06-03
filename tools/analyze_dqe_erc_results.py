#!/usr/bin/env python3
"""Analyze ERC full-eval results by DQE capability slices."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


METRIC_KEYS = [
    "correctness",
    "completeness",
    "faithfulness",
    "numerical_accuracy",
    "evidence_recall_at_k",
    "final_evidence_recall",
    "citation_precision",
    "citation_recall",
    "required_evidence_coverage",
    "unsupported_claim_rate",
]
DELTA_PAIRS = [
    ("B0", "B3", "chunk_to_chunk_entity"),
    ("B3", "B4", "entity_to_relation"),
    ("B4", "B5", "relation_to_graph_expansion"),
    ("B5", "B6", "graph_to_query_variants"),
    ("B6", "B7", "query_variants_to_rerank"),
    ("B7", "Full", "rerank_to_evidence_selection"),
    ("B0", "Full", "chunk_to_full"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze DQE-sliced ERC results.")
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--capability-tags", required=True)
    parser.add_argument("--slice-manifest", required=True)
    parser.add_argument("--output-dir", default="")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 6) if values else 0.0


def metric_value(result: dict[str, Any], key: str) -> float:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    return float(metrics.get(key) or 0.0)


def load_slice_manifest(path: Path) -> dict[str, set[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    slices = payload.get("slices") if isinstance(payload, dict) else {}
    return {
        name: set(item.get("question_ids") or [])
        for name, item in slices.items()
        if isinstance(item, dict)
    }


def result_rows_by_question(results: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    rows: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        if result.get("cache_phase") != "full_no_cache":
            continue
        rows[str(result.get("question_id") or "")][str(result.get("config_id") or "")] = result
    return rows


def compute_slice_metrics(
    results: list[dict[str, Any]],
    slices: dict[str, set[str]],
) -> list[dict[str, Any]]:
    rows = []
    for slice_name, question_ids in slices.items():
        for config_id in sorted({str(result.get("config_id") or "") for result in results}):
            group = [
                result
                for result in results
                if result.get("cache_phase") == "full_no_cache"
                and str(result.get("config_id") or "") == config_id
                and str(result.get("question_id") or "") in question_ids
            ]
            if not group:
                continue
            row = {
                "slice": slice_name,
                "config_id": config_id,
                "question_count": len(group),
            }
            for key in METRIC_KEYS:
                row[key] = f"{mean([metric_value(result, key) for result in group]):.4f}"
            rows.append(row)
    return rows


def compute_component_deltas(
    by_question: dict[str, dict[str, dict[str, Any]]],
    slices: dict[str, set[str]],
) -> list[dict[str, Any]]:
    rows = []
    for slice_name, question_ids in slices.items():
        for before, after, component in DELTA_PAIRS:
            comparable = [
                question_id
                for question_id in question_ids
                if before in by_question.get(question_id, {}) and after in by_question.get(question_id, {})
            ]
            if not comparable:
                continue
            row = {
                "slice": slice_name,
                "component_delta": component,
                "before_config": before,
                "after_config": after,
                "question_count": len(comparable),
            }
            for key in (
                "evidence_recall_at_k",
                "final_evidence_recall",
                "required_evidence_coverage",
                "correctness",
                "faithfulness",
            ):
                deltas = [
                    metric_value(by_question[question_id][after], key)
                    - metric_value(by_question[question_id][before], key)
                    for question_id in comparable
                ]
                row[f"delta_{key}"] = f"{mean(deltas):.4f}"
            rows.append(row)
    return rows


def classify_failure(configs: dict[str, dict[str, Any]]) -> str:
    full = configs.get("Full")
    b7 = configs.get("B7")
    b0 = configs.get("B0")
    if not full:
        return "missing_full"
    if b7 and metric_value(full, "evidence_recall_at_k") < metric_value(b7, "evidence_recall_at_k"):
        return "retrieval_regression"
    if b7 and metric_value(full, "final_evidence_recall") < metric_value(b7, "final_evidence_recall"):
        return "selection_drop"
    if b0 and metric_value(full, "required_evidence_coverage") <= metric_value(b0, "required_evidence_coverage"):
        return "no_required_coverage_gain"
    if metric_value(full, "unsupported_claim_rate") > 0.25:
        return "unsupported_claim_risk"
    return "no_primary_failure"


def compute_per_question_attribution(
    by_question: dict[str, dict[str, dict[str, Any]]],
    capability_by_qid: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for question_id, configs in sorted(by_question.items()):
        row = {
            "question_id": question_id,
            "question_type": capability_by_qid.get(question_id, {}).get("question_type", ""),
            "capability_tags": capability_by_qid.get(question_id, {}).get("capability_tags", []),
            "failure_type": classify_failure(configs),
            "candidate_to_final_loss_full": "",
            "metrics_by_config": {},
            "component_deltas": {},
        }
        for config_id, result in sorted(configs.items()):
            row["metrics_by_config"][config_id] = {
                key: metric_value(result, key)
                for key in (
                    "evidence_recall_at_k",
                    "final_evidence_recall",
                    "required_evidence_coverage",
                    "correctness",
                    "faithfulness",
                    "unsupported_claim_rate",
                )
            }
        full_metrics = row["metrics_by_config"].get("Full")
        if full_metrics:
            row["candidate_to_final_loss_full"] = round(
                full_metrics["evidence_recall_at_k"] - full_metrics["final_evidence_recall"],
                6,
            )
        for before, after, component in DELTA_PAIRS:
            if before not in configs or after not in configs:
                continue
            row["component_deltas"][component] = {
                key: round(metric_value(configs[after], key) - metric_value(configs[before], key), 6)
                for key in (
                    "evidence_recall_at_k",
                    "final_evidence_recall",
                    "required_evidence_coverage",
                )
            }
        rows.append(row)
    return rows


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_failure_taxonomy(path: Path, attribution_rows: list[dict[str, Any]]) -> None:
    counts = Counter(row["failure_type"] for row in attribution_rows)
    tag_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in attribution_rows:
        for tag in row.get("capability_tags") or []:
            tag_counts[row["failure_type"]][tag] += 1
    lines = ["# DQE ERC Failure Taxonomy", ""]
    lines.append("## Failure Counts")
    lines.append("")
    for name, count in sorted(counts.items()):
        lines.append(f"- `{name}`: {count}")
    lines.append("")
    lines.append("## Tags By Failure Type")
    lines.append("")
    for failure_type, counter in sorted(tag_counts.items()):
        lines.append(f"### {failure_type}")
        lines.append("")
        for tag, count in counter.most_common():
            lines.append(f"- `{tag}`: {count}")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir) if args.output_dir else results_dir
    results = read_jsonl(results_dir / "results.jsonl")
    capability_rows = read_jsonl(Path(args.capability_tags))
    capability_by_qid = {str(row.get("question_id") or ""): row for row in capability_rows}
    slices = load_slice_manifest(Path(args.slice_manifest))
    by_question = result_rows_by_question(results)

    slice_rows = compute_slice_metrics(results, slices)
    delta_rows = compute_component_deltas(by_question, slices)
    attribution_rows = compute_per_question_attribution(by_question, capability_by_qid)

    write_tsv(output_dir / "dqe_slice_metrics.tsv", slice_rows)
    write_tsv(output_dir / "component_delta_by_slice.tsv", delta_rows)
    write_jsonl(output_dir / "per_question_component_attribution.jsonl", attribution_rows)
    write_failure_taxonomy(output_dir / "failure_taxonomy.md", attribution_rows)
    print(str(output_dir))


if __name__ == "__main__":
    main()
