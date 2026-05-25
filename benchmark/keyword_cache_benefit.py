#!/usr/bin/env python3
"""Measure keyword candidate cache benefit on an existing Ragent project.

The benchmark is intentionally retrieval-focused:
- explicit keywords avoid LLM/GLiNER keyword extraction variance
- only_need_context avoids final answer LLM variance
- full-query cache entries are cleared before every measured query
- keyword_candidate entries are cleared only between phases that need a cold cache
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ["MODEL_STARTUP_CHECK_ENABLED"] = "0"
os.environ["RAG_KEYWORD_FALLBACK_PRELOAD"] = "0"
os.environ["RAGENT_MEP_PRELOAD_KEYWORD_FALLBACK"] = "0"

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ragent.base import QueryParam
from ragent.benchmarking import collect_cache_hit_stages
from ragent.inference_runtime import _close_rag, initialize_rag
from ragent.operate import graph_query, hybrid_query

os.environ["MODEL_STARTUP_CHECK_ENABLED"] = "0"
os.environ["RAG_KEYWORD_FALLBACK_PRELOAD"] = "0"
os.environ["RAGENT_MEP_PRELOAD_KEYWORD_FALLBACK"] = "0"


FULL_QUERY_CACHE_TYPES = ["answer", "retrieval", "render", "prompt"]
ALL_QUERY_CACHE_TYPES = [*FULL_QUERY_CACHE_TYPES, "keyword_candidate"]


DEFAULT_CASES = [
    {
        "id": "q1_weight_loss_taiji",
        "query": "减重场景下，太极拳 100 分钟大约消耗多少能量？",
        "ll_keywords": ["减重", "太极拳", "能量消耗"],
        "hl_keywords": ["肥胖食养", "身体活动", "能量消耗"],
    },
    {
        "id": "q2_weight_loss_sugary_drink",
        "query": "减重场景下，喝一听 330ml 含糖饮料后应该关注哪些能量和添加糖限制？",
        "ll_keywords": ["减重", "含糖饮料", "添加糖"],
        "hl_keywords": ["肥胖食养", "控糖", "能量摄入"],
    },
    {
        "id": "q3_weight_loss_bmi",
        "query": "减重场景下，BMI 25 和腰围 95 的成年人应该如何判断肥胖风险？",
        "ll_keywords": ["减重", "BMI", "腰围"],
        "hl_keywords": ["肥胖食养", "肥胖判定", "健康风险"],
    },
]


@dataclass(frozen=True)
class PhaseConfig:
    name: str
    keyword_cache_enabled: bool
    keyword_cache_read_enabled: bool
    keyword_cache_write_enabled: bool
    clear_keyword_cache_before_phase: bool


PHASES = [
    PhaseConfig(
        name="baseline_cold",
        keyword_cache_enabled=False,
        keyword_cache_read_enabled=False,
        keyword_cache_write_enabled=False,
        clear_keyword_cache_before_phase=True,
    ),
    PhaseConfig(
        name="enabled_prewarm",
        keyword_cache_enabled=True,
        keyword_cache_read_enabled=True,
        keyword_cache_write_enabled=True,
        clear_keyword_cache_before_phase=True,
    ),
    PhaseConfig(
        name="enabled_warm",
        keyword_cache_enabled=True,
        keyword_cache_read_enabled=True,
        keyword_cache_write_enabled=True,
        clear_keyword_cache_before_phase=False,
    ),
]

READ_WRITE_MODE_PHASES = [
    PhaseConfig(
        name="write_only_prewarm",
        keyword_cache_enabled=True,
        keyword_cache_read_enabled=False,
        keyword_cache_write_enabled=True,
        clear_keyword_cache_before_phase=True,
    ),
    PhaseConfig(
        name="read_only_warm",
        keyword_cache_enabled=True,
        keyword_cache_read_enabled=True,
        keyword_cache_write_enabled=False,
        clear_keyword_cache_before_phase=False,
    ),
]


def _resolve_phases(args: argparse.Namespace) -> list[PhaseConfig]:
    phases = list(PHASES)
    if args.include_read_write_modes:
        phases.extend(READ_WRITE_MODE_PHASES)
    return phases


def _sha256_text(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _stage_sum(stage_timings: list[dict[str, Any]], predicate) -> float:
    total = 0.0
    for item in stage_timings:
        if not isinstance(item, dict) or not predicate(str(item.get("stage") or "")):
            continue
        total += float(item.get("seconds") or 0.0)
    return round(total, 6)


def _last_stage_seconds(stage_timings: list[dict[str, Any]], stage: str) -> float | None:
    for item in reversed(stage_timings):
        if isinstance(item, dict) and item.get("stage") == stage:
            return float(item.get("seconds") or 0.0)
    return None


def _keyword_hit_count(stage_timings: list[dict[str, Any]]) -> int:
    return sum(
        int(item.get("hit_count") or 0)
        for item in stage_timings
        if isinstance(item, dict) and item.get("stage") == "keyword_candidate_cache_hit"
    )


def _stage_names(stage_timings: list[dict[str, Any]]) -> list[str]:
    return [
        str(item.get("stage"))
        for item in stage_timings
        if isinstance(item, dict) and item.get("stage")
    ]


def _cache_counts(project_dir: Path) -> dict[str, int]:
    cache_path = project_dir / "kv_store_llm_response_cache.sqlite"
    if not cache_path.exists():
        return {}
    with sqlite3.connect(cache_path) as conn:
        rows = conn.execute(
            """
            SELECT mode, cache_type, COUNT(*)
            FROM query_cache_entries
            GROUP BY mode, cache_type
            ORDER BY mode, cache_type
            """
        ).fetchall()
    return {f"{mode}:{cache_type}": int(count) for mode, cache_type, count in rows}


async def _drop_cache_entries(
    rag: Any,
    *,
    mode: str,
    cache_types: list[str],
) -> bool:
    dropped = await rag.llm_response_cache.drop_cache_entries(
        modes=[mode],
        cache_types=cache_types,
    )
    await rag.llm_response_cache.index_done_callback()
    return bool(dropped)


def _build_param(
    *,
    args: argparse.Namespace,
    case: dict[str, Any],
    phase: PhaseConfig,
) -> QueryParam:
    param = QueryParam(mode=args.mode)
    param.only_need_context = True
    param.allow_llm_keyword_extraction = False
    param.enable_rerank = not args.no_rerank
    param.disable_rerank_for_retrieval_only = args.disable_rerank_for_retrieval_only
    param.response_type = args.response_type
    top_k = args.top_k
    if phase.name == "enabled_warm" and args.warm_top_k is not None:
        top_k = args.warm_top_k
    if top_k is not None:
        param.top_k = top_k
    if args.chunk_top_k is not None:
        param.chunk_top_k = args.chunk_top_k
    param.hl_keywords = [str(item) for item in case.get("hl_keywords") or []]
    param.ll_keywords = [str(item) for item in case.get("ll_keywords") or []]
    param.keyword_cache_enabled = phase.keyword_cache_enabled
    param.keyword_cache_read_enabled = phase.keyword_cache_read_enabled
    param.keyword_cache_write_enabled = phase.keyword_cache_write_enabled
    param.keyword_cache_top_k = args.keyword_cache_top_k
    return param


async def _run_query(
    rag: Any,
    *,
    args: argparse.Namespace,
    case: dict[str, Any],
    phase: PhaseConfig,
    run_index: int,
) -> dict[str, Any]:
    await _drop_cache_entries(rag, mode=args.mode, cache_types=FULL_QUERY_CACHE_TYPES)
    param = _build_param(args=args, case=case, phase=phase)
    global_config = await rag._build_runtime_global_config()

    started_at = time.perf_counter()
    if args.mode == "graph":
        context_text, referenced_file_paths, debug_payload = await graph_query(
            str(case["query"]).strip(),
            rag.chunk_entity_relation_graph,
            rag.entities_vdb,
            rag.relationships_vdb,
            rag.text_chunks,
            param,
            global_config,
            hashing_kv=rag.llm_response_cache,
            chunks_vdb=rag.chunks_vdb,
            return_debug=True,
        )
    else:
        context_text, referenced_file_paths, debug_payload = await hybrid_query(
            str(case["query"]).strip(),
            rag.chunks_vdb,
            rag.chunk_entity_relation_graph,
            rag.relationships_vdb,
            rag.entities_vdb,
            rag.text_chunks,
            param,
            global_config,
            hashing_kv=rag.llm_response_cache,
            return_debug=True,
        )
    wall_seconds = round(time.perf_counter() - started_at, 6)
    await rag._query_done()

    stage_timings = list(debug_payload.get("stage_timings") or [])
    final_context_document_chunks = list(
        debug_payload.get("final_context_document_chunks") or []
    )
    rerank_input_candidates = list(
        debug_payload.get("rerank_input_candidates")
        or debug_payload.get("merged_candidates")
        or []
    )
    rerank_output_candidates = list(
        debug_payload.get("rerank_output_candidates")
        or debug_payload.get("rerank_results")
        or []
    )
    referenced_file_paths = list(referenced_file_paths or [])

    return {
        "phase": phase.name,
        "run_index": run_index,
        "case_id": case["id"],
        "query": case["query"],
        "mode": args.mode,
        "keyword_cache_enabled": phase.keyword_cache_enabled,
        "keyword_cache_read_enabled": phase.keyword_cache_read_enabled,
        "keyword_cache_write_enabled": phase.keyword_cache_write_enabled,
        "keyword_cache_top_k": args.keyword_cache_top_k,
        "top_k": param.top_k,
        "chunk_top_k": param.chunk_top_k,
        "enable_rerank": param.enable_rerank,
        "wall_seconds": wall_seconds,
        "onehop_total_seconds": _last_stage_seconds(stage_timings, "onehop_total"),
        "keyword_candidate_cache_lookup_seconds": _stage_sum(
            stage_timings, lambda stage: stage == "keyword_candidate_cache_lookup"
        ),
        "keyword_candidate_cache_hit_count": _keyword_hit_count(stage_timings),
        "graph_entity_vector_seconds": _stage_sum(
            stage_timings, lambda stage: stage.startswith("graph_entity_vector")
        ),
        "graph_relation_vector_seconds": _stage_sum(
            stage_timings, lambda stage: stage.startswith("graph_relation_vector")
        ),
        "hybrid_chunk_vector_seconds": _stage_sum(
            stage_timings, lambda stage: stage.startswith("hybrid_chunk_vector")
        ),
        "embedding_seconds": _stage_sum(
            stage_timings, lambda stage: stage.endswith("_embedding")
        ),
        "index_search_seconds": _stage_sum(
            stage_timings, lambda stage: stage.endswith("_index_search")
        ),
        "cache_hit_stages": collect_cache_hit_stages(stage_timings),
        "stage_names": _stage_names(stage_timings),
        "stage_timings": stage_timings,
        "referenced_file_count": len(referenced_file_paths),
        "referenced_file_paths": referenced_file_paths,
        "referenced_file_paths_sha256": _sha256_text(referenced_file_paths),
        "context_chars": len(str(context_text)),
        "context_sha256": _sha256_text(str(context_text)),
        "final_context_document_chunk_count": len(final_context_document_chunks),
        "final_context_document_chunks_sha256": _sha256_text(
            final_context_document_chunks
        ),
        "merged_candidate_count": len(debug_payload.get("merged_candidates") or []),
        "rerank_used": bool(debug_payload.get("rerank_used", False)),
        "rerank_input_candidate_count": len(rerank_input_candidates),
        "rerank_output_candidate_count": len(rerank_output_candidates),
        "high_level_keywords": list(case.get("hl_keywords") or []),
        "low_level_keywords": list(case.get("ll_keywords") or []),
    }


def _load_cases(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return list(DEFAULT_CASES)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("--cases-json must contain a JSON list")
    return [dict(item) for item in payload]


def _write_tsv(path: Path, records: list[dict[str, Any]]) -> None:
    columns = [
        "phase",
        "run_index",
        "case_id",
        "mode",
        "wall_seconds",
        "onehop_total_seconds",
        "keyword_candidate_cache_hit_count",
        "keyword_candidate_cache_lookup_seconds",
        "graph_entity_vector_seconds",
        "graph_relation_vector_seconds",
        "hybrid_chunk_vector_seconds",
        "embedding_seconds",
        "index_search_seconds",
        "cache_hit_stages",
        "context_chars",
        "referenced_file_count",
        "final_context_document_chunk_count",
        "merged_candidate_count",
        "rerank_used",
        "rerank_input_candidate_count",
        "rerank_output_candidate_count",
        "top_k",
        "chunk_top_k",
        "keyword_cache_top_k",
    ]
    with path.open("w", encoding="utf-8") as handle:
        handle.write("\t".join(columns) + "\n")
        for record in records:
            row = []
            for column in columns:
                value = record.get(column)
                if isinstance(value, list):
                    value = ",".join(str(item) for item in value)
                row.append("" if value is None else str(value))
            handle.write("\t".join(row) + "\n")


def _phase_stats(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["phase"])].append(record)
    stats: dict[str, dict[str, Any]] = {}
    for phase, items in grouped.items():
        wall_values = [float(item["wall_seconds"]) for item in items]
        onehop_values = [
            float(item["onehop_total_seconds"])
            for item in items
            if item.get("onehop_total_seconds") is not None
        ]
        stats[phase] = {
            "count": len(items),
            "wall_mean": round(statistics.fmean(wall_values), 6),
            "wall_median": round(statistics.median(wall_values), 6),
            "onehop_mean": round(statistics.fmean(onehop_values), 6)
            if onehop_values
            else None,
            "keyword_hit_total": sum(
                int(item["keyword_candidate_cache_hit_count"]) for item in items
            ),
            "embedding_mean": round(
                statistics.fmean(float(item["embedding_seconds"]) for item in items),
                6,
            ),
            "index_search_mean": round(
                statistics.fmean(float(item["index_search_seconds"]) for item in items),
                6,
            ),
            "entity_vector_mean": round(
                statistics.fmean(
                    float(item["graph_entity_vector_seconds"]) for item in items
                ),
                6,
            ),
            "relation_vector_mean": round(
                statistics.fmean(
                    float(item["graph_relation_vector_seconds"]) for item in items
                ),
                6,
            ),
        }
    return stats


def _consistency_rows(records: list[dict[str, Any]]) -> list[str]:
    by_case_phase: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        by_case_phase[(str(record["case_id"]), str(record["phase"]))] = record

    rows = []
    for case_id in sorted({str(record["case_id"]) for record in records}):
        baseline = by_case_phase.get((case_id, "baseline_cold"))
        prewarm = by_case_phase.get((case_id, "enabled_prewarm"))
        warm = by_case_phase.get((case_id, "enabled_warm"))
        prewarm_warm_same = bool(
            prewarm
            and warm
            and prewarm.get("context_sha256") == warm.get("context_sha256")
            and prewarm.get("referenced_file_paths_sha256")
            == warm.get("referenced_file_paths_sha256")
        )
        baseline_enabled_same = bool(
            baseline
            and warm
            and baseline.get("context_sha256") == warm.get("context_sha256")
            and baseline.get("referenced_file_paths_sha256")
            == warm.get("referenced_file_paths_sha256")
        )
        rows.append(
            "| {case_id} | {prewarm_warm_same} | {baseline_enabled_same} | {base_chunks} | {warm_chunks} | {base_rerank_in} | {warm_rerank_in} |".format(
                case_id=case_id,
                prewarm_warm_same="yes" if prewarm_warm_same else "no",
                baseline_enabled_same="yes" if baseline_enabled_same else "no",
                base_chunks=baseline.get("final_context_document_chunk_count")
                if baseline
                else "",
                warm_chunks=warm.get("final_context_document_chunk_count")
                if warm
                else "",
                base_rerank_in=baseline.get("rerank_input_candidate_count")
                if baseline
                else "",
                warm_rerank_in=warm.get("rerank_input_candidate_count")
                if warm
                else "",
            )
        )
    return rows


def _write_summary(
    path: Path,
    *,
    args: argparse.Namespace,
    records: list[dict[str, Any]],
    cache_counts_by_phase: dict[str, dict[str, int]],
    phases: list[PhaseConfig],
) -> None:
    stats = _phase_stats(records)
    lines = [
        "# Keyword Candidate Cache Benefit",
        "",
        f"- project_dir: `{Path(args.project_dir).resolve()}`",
        f"- mode: `{args.mode}`",
        f"- query_count_per_phase: `{len(_load_cases(args.cases_json))}`",
        f"- runs_per_phase: `{args.runs_per_phase}`",
        f"- top_k: `{args.top_k}`",
        f"- warm_top_k: `{args.warm_top_k}`",
        f"- chunk_top_k: `{args.chunk_top_k}`",
        f"- keyword_cache_top_k: `{args.keyword_cache_top_k}`",
        f"- rerank_enabled: `{not args.no_rerank}`",
        "",
        "## Phase Stats",
        "",
        "| phase | n | wall_mean_s | wall_median_s | onehop_mean_s | keyword_hits | embedding_mean_s | index_search_mean_s | entity_vector_mean_s | relation_vector_mean_s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for phase in [phase.name for phase in phases]:
        item = stats.get(phase, {})
        lines.append(
            "| {phase} | {count} | {wall_mean} | {wall_median} | {onehop_mean} | {keyword_hit_total} | {embedding_mean} | {index_search_mean} | {entity_vector_mean} | {relation_vector_mean} |".format(
                phase=phase,
                count=item.get("count", 0),
                wall_mean=item.get("wall_mean", ""),
                wall_median=item.get("wall_median", ""),
                onehop_mean=item.get("onehop_mean", ""),
                keyword_hit_total=item.get("keyword_hit_total", ""),
                embedding_mean=item.get("embedding_mean", ""),
                index_search_mean=item.get("index_search_mean", ""),
                entity_vector_mean=item.get("entity_vector_mean", ""),
                relation_vector_mean=item.get("relation_vector_mean", ""),
            )
        )

    baseline = stats.get("baseline_cold")
    warm = stats.get("enabled_warm")
    if baseline and warm:
        delta = baseline["wall_mean"] - warm["wall_mean"]
        pct = (delta / baseline["wall_mean"] * 100) if baseline["wall_mean"] else 0.0
        lines.extend(
            [
                "",
                "## Baseline vs Warm",
                "",
                f"- wall_mean_delta_seconds: `{round(delta, 6)}`",
                f"- wall_mean_delta_percent: `{round(pct, 2)}%`",
            ]
        )

    lines.extend(
        [
            "",
            "## Consistency",
            "",
            "| case | prewarm_vs_warm_same | baseline_vs_warm_same | baseline_chunks | warm_chunks | baseline_rerank_in | warm_rerank_in |",
            "|---|---|---|---:|---:|---:|---:|",
            *_consistency_rows(records),
            "",
            "## Cache Counts",
            "",
            "```json",
            json.dumps(cache_counts_by_phase, ensure_ascii=False, indent=2),
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _run(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    artifact_dir = Path(args.artifact_dir).expanduser().resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    cases = _load_cases(args.cases_json)
    phases = _resolve_phases(args)

    init_stage_timings: list[dict[str, Any]] = []
    rag = await initialize_rag(
        str(project_dir),
        stage_timings=init_stage_timings,
        require_llm=False,
        enable_rerank=not args.no_rerank,
    )
    records: list[dict[str, Any]] = []
    cache_counts_by_phase: dict[str, dict[str, int]] = {}
    try:
        (artifact_dir / "init_stage_timings.json").write_text(
            json.dumps(init_stage_timings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        for phase in phases:
            if phase.clear_keyword_cache_before_phase:
                await _drop_cache_entries(
                    rag,
                    mode=args.mode,
                    cache_types=ALL_QUERY_CACHE_TYPES,
                )
            else:
                await _drop_cache_entries(
                    rag,
                    mode=args.mode,
                    cache_types=FULL_QUERY_CACHE_TYPES,
                )

            for run_index in range(1, args.runs_per_phase + 1):
                for case in cases:
                    record = await _run_query(
                        rag,
                        args=args,
                        case=case,
                        phase=phase,
                        run_index=run_index,
                    )
                    records.append(record)
                    print(
                        "{phase} run={run} case={case} wall={wall:.3f}s keyword_hits={hits}".format(
                            phase=phase.name,
                            run=run_index,
                            case=case["id"],
                            wall=record["wall_seconds"],
                            hits=record["keyword_candidate_cache_hit_count"],
                        ),
                        flush=True,
                    )
            cache_counts_by_phase[phase.name] = _cache_counts(project_dir)
    finally:
        await _close_rag(rag)

    (artifact_dir / "records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_tsv(artifact_dir / "results.tsv", records)
    _write_summary(
        artifact_dir / "summary.md",
        args=args,
        records=records,
        cache_counts_by_phase=cache_counts_by_phase,
        phases=phases,
    )
    print(f"wrote {artifact_dir / 'summary.md'}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark keyword candidate cache benefit."
    )
    parser.add_argument("project_dir", help="Ragent project directory to query.")
    parser.add_argument(
        "--artifact-dir",
        default=f"benchmark/keyword_cache_benefit_{int(time.time())}",
        help="Directory for records.json, results.tsv and summary.md.",
    )
    parser.add_argument("--mode", choices=["graph", "hybrid"], default="graph")
    parser.add_argument("--runs-per-phase", type=int, default=1)
    parser.add_argument("--keyword-cache-top-k", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument(
        "--warm-top-k",
        type=int,
        default=None,
        help="Override QueryParam.top_k only for enabled_warm.",
    )
    parser.add_argument("--chunk-top-k", type=int, default=None)
    parser.add_argument("--response-type", default="Multiple Paragraphs")
    parser.add_argument("--cases-json", type=Path)
    parser.add_argument("--no-rerank", action="store_true")
    parser.add_argument(
        "--include-read-write-modes",
        action="store_true",
        help="Also run write_only_prewarm and read_only_warm phases.",
    )
    parser.add_argument(
        "--disable-rerank-for-retrieval-only",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    return parser.parse_args()


def main() -> int:
    return asyncio.run(_run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
