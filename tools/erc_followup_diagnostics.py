#!/usr/bin/env python3
"""Generate follow-up diagnostics for the ERC DQE live artifact."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ragent.base import QueryParam
from ragent.operate import _select_hybrid_context_entries


DEFAULT_EVAL_DIR = Path("benchmark/erc_full_eval_20260527_155656")
DEFAULT_MAPPING_DIR = Path("benchmark/erc_dqe_mapping_20260601_000156")
DEFAULT_STRICT_DIR = Path("benchmark/erc_full_eval_dqe_full_strict_cold_20260602_151636")
FULL_NO_CACHE_CONFIGS = {"B0", "B5", "B6", "B7", "Full"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build ERC follow-up diagnostics from existing artifacts."
    )
    parser.add_argument("--eval-dir", default=str(DEFAULT_EVAL_DIR))
    parser.add_argument("--mapping-dir", default=str(DEFAULT_MAPPING_DIR))
    parser.add_argument("--strict-dir", default=str(DEFAULT_STRICT_DIR))
    parser.add_argument("--output-dir", default="")
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def chunk_ids(chunks: list[dict[str, Any]] | None) -> list[str]:
    return [
        str(chunk.get("chunk_id") or "").strip()
        for chunk in chunks or []
        if str(chunk.get("chunk_id") or "").strip()
    ]


def metric(row: dict[str, Any] | None, key: str) -> float:
    if not row:
        return 0.0
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    return float(metrics.get(key) or 0.0)


def hits(required: set[str], observed: list[str]) -> set[str]:
    return required & set(observed)


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def load_capability_tags(mapping_dir: Path) -> dict[str, dict[str, Any]]:
    path = mapping_dir / "dqe_capability_tags.jsonl"
    if not path.exists():
        return {}
    return {str(row.get("question_id") or ""): row for row in read_jsonl(path)}


def load_attribution(eval_dir: Path) -> dict[str, dict[str, Any]]:
    path = eval_dir / "per_question_component_attribution.jsonl"
    if not path.exists():
        return {}
    return {str(row.get("question_id") or ""): row for row in read_jsonl(path)}


def load_minimal_full_no_cache_results(eval_dir: Path) -> dict[str, dict[str, dict[str, Any]]]:
    rows: dict[str, dict[str, dict[str, Any]]] = {}
    with (eval_dir / "results.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("cache_phase") != "full_no_cache":
                continue
            config_id = str(row.get("config_id") or "")
            if config_id not in FULL_NO_CACHE_CONFIGS:
                continue
            question_id = str(row.get("question_id") or "")
            trace = row.get("trace") if isinstance(row.get("trace"), dict) else {}
            rows.setdefault(question_id, {})[config_id] = {
                "question_id": question_id,
                "config_id": config_id,
                "question": row.get("question") or "",
                "question_type": row.get("question_type") or "",
                "difficulty": row.get("difficulty") or "",
                "required_chunk_ids": list(row.get("required_chunk_ids") or []),
                "required_source_refs": list(row.get("required_source_refs") or []),
                "metrics": row.get("metrics") or {},
                "retrieved_ids": chunk_ids(row.get("retrieved_contexts")),
                "final_ids": chunk_ids(row.get("final_evidence_chunks")),
                "high_level_keywords": list(row.get("high_level_keywords") or []),
                "low_level_keywords": list(row.get("low_level_keywords") or []),
                "selected_candidate_indexes": list(trace.get("selected_candidate_indexes") or []),
            }
    return rows


def build_selection_drop_rows(
    by_question: dict[str, dict[str, dict[str, Any]]],
    attribution: dict[str, dict[str, Any]],
    capability_tags: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for question_id, configs in sorted(by_question.items()):
        b7 = configs.get("B7")
        full = configs.get("Full")
        if not b7 or not full:
            continue
        attr = attribution.get(question_id, {})
        if (
            attr.get("failure_type") != "selection_drop"
            and metric(full, "final_evidence_recall") >= metric(b7, "final_evidence_recall")
            and metric(full, "required_evidence_coverage") >= metric(b7, "required_evidence_coverage")
        ):
            continue

        required = set(str(item) for item in full.get("required_chunk_ids") or [])
        b7_final_hits = hits(required, b7["final_ids"])
        full_final_hits = hits(required, full["final_ids"])
        full_candidate_hits = hits(required, full["retrieved_ids"])
        lost_from_b7 = sorted(b7_final_hits - full_final_hits)
        full_candidate_not_final = sorted(full_candidate_hits - full_final_hits)
        tags = capability_tags.get(question_id, {}).get("capability_tags") or attr.get("capability_tags") or []
        rows.append(
            {
                "question_id": question_id,
                "question_type": full.get("question_type") or "",
                "difficulty": full.get("difficulty") or "",
                "capability_tags": ",".join(tags),
                "required_chunk_count": len(required),
                "b7_candidate_required_hits": len(hits(required, b7["retrieved_ids"])),
                "b7_final_required_hits": len(b7_final_hits),
                "full_candidate_required_hits": len(full_candidate_hits),
                "full_final_required_hits": len(full_final_hits),
                "b7_final_recall": f"{metric(b7, 'final_evidence_recall'):.4f}",
                "full_final_recall": f"{metric(full, 'final_evidence_recall'):.4f}",
                "b7_required_coverage": f"{metric(b7, 'required_evidence_coverage'):.4f}",
                "full_required_coverage": f"{metric(full, 'required_evidence_coverage'):.4f}",
                "lost_required_from_b7_to_full": ",".join(lost_from_b7),
                "full_retrieved_but_not_final_required": ",".join(full_candidate_not_final),
                "full_selected_candidate_indexes": ",".join(str(item) for item in full.get("selected_candidate_indexes") or []),
                "question": full.get("question") or "",
            }
        )
    return rows


def build_query_variant_rows(
    by_question: dict[str, dict[str, dict[str, Any]]],
    capability_tags: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for question_id, configs in sorted(by_question.items()):
        b5 = configs.get("B5")
        b6 = configs.get("B6")
        if not b5 or not b6:
            continue
        final_delta = metric(b6, "final_evidence_recall") - metric(b5, "final_evidence_recall")
        coverage_delta = metric(b6, "required_evidence_coverage") - metric(b5, "required_evidence_coverage")
        if final_delta >= 0 and coverage_delta >= 0:
            continue

        required = set(str(item) for item in b6.get("required_chunk_ids") or [])
        b5_candidate_hits = hits(required, b5["retrieved_ids"])
        b6_candidate_hits = hits(required, b6["retrieved_ids"])
        b5_final_hits = hits(required, b5["final_ids"])
        b6_final_hits = hits(required, b6["final_ids"])
        rows.append(
            {
                "question_id": question_id,
                "question_type": b6.get("question_type") or "",
                "difficulty": b6.get("difficulty") or "",
                "capability_tags": ",".join(capability_tags.get(question_id, {}).get("capability_tags") or []),
                "delta_final_recall_b6_minus_b5": f"{final_delta:.4f}",
                "delta_required_coverage_b6_minus_b5": f"{coverage_delta:.4f}",
                "b5_candidate_required_hits": len(b5_candidate_hits),
                "b6_candidate_required_hits": len(b6_candidate_hits),
                "b5_final_required_hits": len(b5_final_hits),
                "b6_final_required_hits": len(b6_final_hits),
                "lost_final_required_b5_to_b6": ",".join(sorted(b5_final_hits - b6_final_hits)),
                "b6_high_keywords": ",".join(b6.get("high_level_keywords") or []),
                "b6_low_keywords": ",".join(b6.get("low_level_keywords") or []),
                "question": b6.get("question") or "",
            }
        )
    return rows


def write_question_id_list(path: Path, rows: list[dict[str, Any]]) -> None:
    ids = sorted({str(row.get("question_id") or "") for row in rows if row.get("question_id")})
    path.write_text("\n".join(ids) + ("\n" if ids else ""), encoding="utf-8")


def build_selection_replay_rows(
    eval_dir: Path,
    question_ids: set[str],
) -> list[dict[str, Any]]:
    rows = []
    if not question_ids:
        return rows
    with (eval_dir / "results.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            question_id = str(row.get("question_id") or "")
            if question_id not in question_ids:
                continue
            if row.get("cache_phase") != "full_no_cache" or row.get("config_id") != "Full":
                continue
            trace = row.get("trace") if isinstance(row.get("trace"), dict) else {}
            results_text = list(trace.get("results_text") or [])
            result_ids = [str(item) for item in trace.get("results_chunk_ids") or []]
            metadata = list(trace.get("results_chunk_metadata") or [])
            file_paths = list(trace.get("results_file_paths") or [])
            rerank_results = list(trace.get("rerank_results") or [])
            if not results_text or not result_ids:
                continue
            selected, _ = _select_hybrid_context_entries(
                rerank_results=rerank_results,
                results_text=results_text,
                results_file_paths=file_paths,
                results_chunk_metadata=metadata,
                query_param=QueryParam(chunk_top_k=len(row.get("final_evidence_chunks") or []) or 10),
                query_variants=[
                    *list(row.get("low_level_keywords") or []),
                    *list(row.get("high_level_keywords") or []),
                ],
            )
            required = set(str(item) for item in row.get("required_chunk_ids") or [])
            old_final_ids = chunk_ids(row.get("final_evidence_chunks"))
            new_final_ids = [
                result_ids[index]
                for index in selected
                if 0 <= index < len(result_ids)
            ]
            old_hits = hits(required, old_final_ids)
            new_hits = hits(required, new_final_ids)
            rows.append(
                {
                    "question_id": question_id,
                    "required_chunk_count": len(required),
                    "old_full_final_required_hits": len(old_hits),
                    "replayed_full_final_required_hits": len(new_hits),
                    "hit_delta": len(new_hits) - len(old_hits),
                    "old_full_selected_indexes": ",".join(str(item) for item in trace.get("selected_candidate_indexes") or []),
                    "replayed_selected_indexes": ",".join(str(item) for item in selected),
                    "newly_preserved_required_chunks": ",".join(sorted(new_hits - old_hits)),
                    "still_missing_required_chunks": ",".join(sorted(required - new_hits)),
                }
            )
    return rows


def cache_stage_distribution(results_path: Path) -> dict[str, Counter[str]]:
    distributions: dict[str, Counter[str]] = {}
    if not results_path.exists():
        return distributions
    with results_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            phase = str(row.get("cache_phase") or "")
            stages = row.get("cache_hit_stages") or []
            if isinstance(stages, str):
                stages = [item.strip() for item in stages.split(",") if item.strip()]
            key = ",".join(sorted(stages)) if stages else "none"
            distributions.setdefault(phase, Counter())[key] += 1
    return distributions


def fmt_counter(counter: Counter[str]) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{key}={value}" for key, value in counter.most_common())


def write_cache_audit(path: Path, eval_dir: Path, strict_dir: Path) -> None:
    main_dist = cache_stage_distribution(eval_dir / "results.jsonl")
    strict_dist = cache_stage_distribution(strict_dir / "results.jsonl")
    lines = [
        "# ERC Cache Hit Semantics Audit",
        "",
        f"- Main artifact: `{eval_dir}`",
        f"- Strict cache-control artifact: `{strict_dir}`",
        "",
        "## Row-Level Cache-Hit Distribution",
        "",
        "| artifact | cache phase | row distribution |",
        "|---|---|---|",
    ]
    for phase, counter in sorted(main_dist.items()):
        lines.append(f"| main | `{phase}` | `{fmt_counter(counter)}` |")
    for phase, counter in sorted(strict_dist.items()):
        lines.append(f"| strict | `{phase}` | `{fmt_counter(counter)}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Strict `full_no_cache` should be used as the cold Full latency reference only when its row distribution is `none` for every row.",
            "- Retrieval-cache acceleration is not a durable paper claim unless `retrieval_cache_warm` shows consistent row-level retrieval-cache hits and stable retrieval output semantics.",
            "- Answer-cache warm is a repeated-query acceleration claim, not a retrieval-quality improvement.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_replay_digest_diff(path: Path, eval_dir: Path) -> None:
    summary_path = eval_dir / "build_inference_separation" / "separation_summary.json"
    if not summary_path.exists():
        path.write_text("# ERC Replay Digest Diff\n\nNo separation summary found.\n", encoding="utf-8")
        return
    summary = read_json(summary_path)
    online = summary.get("online_build_snapshot") or {}
    replay = summary.get("offline_replay_snapshot") or {}
    count_keys = [
        "graph_nodes",
        "graph_edges",
        "entity_vdb",
        "relationship_vdb",
        "chunk_vdb",
        "doc_status",
        "full_docs",
        "text_chunks",
    ]
    file_keys = sorted(set((online.get("file_digests") or {})) | set((replay.get("file_digests") or {})))
    lines = [
        "# ERC Online/Replay Digest Diff",
        "",
        f"- Source: `{summary_path}`",
        f"- `online_vs_replay_match`: `{summary.get('online_vs_replay_match')}`",
        f"- `readonly_snapshot_unchanged`: `{summary.get('readonly_snapshot_unchanged')}`",
        f"- Online digest: `{online.get('digest')}`",
        f"- Replay digest: `{replay.get('digest')}`",
        "",
        "## Count Deltas",
        "",
        "| field | online | replay | delta replay-online |",
        "|---|---:|---:|---:|",
    ]
    for key in count_keys:
        online_value = int(online.get(key) or 0)
        replay_value = int(replay.get(key) or 0)
        lines.append(f"| `{key}` | {online_value} | {replay_value} | {replay_value - online_value} |")
    lines.extend(["", "## File Digest Deltas", "", "| file | online digest | replay digest | status |", "|---|---|---|---|"])
    for key in file_keys:
        online_digest = (online.get("file_digests") or {}).get(key, "-")
        replay_digest = (replay.get("file_digests") or {}).get(key, "-")
        status = "match" if online_digest == replay_digest else "diff"
        lines.append(f"| `{key}` | `{online_digest}` | `{replay_digest}` | `{status}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The digest mismatch is structural, not just disposable query cache state, because graph/vector/doc-status file digests differ.",
            "- `readonly_snapshot_unchanged=True` still supports read-only replay inference isolation.",
            "- Online/raw replay equivalence remains unsupported until these deltas are diagnosed and resolved.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(
    path: Path,
    selection_rows: list[dict[str, Any]],
    selection_replay_rows: list[dict[str, Any]],
    query_variant_rows: list[dict[str, Any]],
    eval_dir: Path,
    strict_dir: Path,
) -> None:
    replay_improved = sum(
        1 for row in selection_replay_rows if int(row.get("hit_delta") or 0) > 0
    )
    lines = [
        "# ERC Follow-Up Diagnostics Summary",
        "",
        f"- Main artifact: `{eval_dir}`",
        f"- Strict cache-control artifact: `{strict_dir}`",
        f"- Selection-drop rows: `{len(selection_rows)}`",
        f"- Selection replay rows improved by current code: `{replay_improved} / {len(selection_replay_rows)}`",
        f"- Query-variant regression rows: `{len(query_variant_rows)}`",
        "",
        "## Generated Files",
        "",
        "- `selection_drop_cases.tsv`: B7-to-Full final-evidence losses and required chunks retrieved by Full but not selected.",
        "- `selection_replay_after_current_code.tsv`: offline replay of current selection code on stored Full traces for selection-drop questions.",
        "- `query_variant_regression_cases.tsv`: B5-to-B6 final-recall or required-coverage regressions.",
        "- `selection_drop_question_ids.txt`: question ids for a targeted live subset after selection repair.",
        "- `query_variant_regression_question_ids.txt`: question ids for a targeted live subset after query-variant repair.",
        "- `replay_digest_diff.md`: online/raw replay count and file-digest mismatch details.",
        "- `cache_hit_semantics_audit.md`: row-level cache-hit distributions for main and strict artifacts.",
        "",
        "## Immediate Use",
        "",
        "- Repair evidence selection against `selection_drop_question_ids.txt` before a full 186-question rerun.",
        "- Repair query-variant filtering against `query_variant_regression_question_ids.txt` before treating B6 as a positive stage.",
        "- Keep retrieval-cache acceleration out of paper claims until strict retrieval-cache row hits are explained.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    eval_dir = Path(args.eval_dir)
    mapping_dir = Path(args.mapping_dir)
    strict_dir = Path(args.strict_dir)
    output_dir = Path(args.output_dir) if args.output_dir else eval_dir / "followup_diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)

    capability_tags = load_capability_tags(mapping_dir)
    attribution = load_attribution(eval_dir)
    by_question = load_minimal_full_no_cache_results(eval_dir)

    selection_rows = build_selection_drop_rows(by_question, attribution, capability_tags)
    query_variant_rows = build_query_variant_rows(by_question, capability_tags)

    write_tsv(output_dir / "selection_drop_cases.tsv", selection_rows)
    selection_replay_rows = build_selection_replay_rows(
        eval_dir,
        {str(row.get("question_id") or "") for row in selection_rows},
    )
    write_tsv(output_dir / "selection_replay_after_current_code.tsv", selection_replay_rows)
    write_tsv(output_dir / "query_variant_regression_cases.tsv", query_variant_rows)
    write_question_id_list(output_dir / "selection_drop_question_ids.txt", selection_rows)
    write_question_id_list(output_dir / "query_variant_regression_question_ids.txt", query_variant_rows)
    write_replay_digest_diff(output_dir / "replay_digest_diff.md", eval_dir)
    write_cache_audit(output_dir / "cache_hit_semantics_audit.md", eval_dir, strict_dir)
    write_summary(
        output_dir / "diagnostic_summary.md",
        selection_rows,
        selection_replay_rows,
        query_variant_rows,
        eval_dir,
        strict_dir,
    )

    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
