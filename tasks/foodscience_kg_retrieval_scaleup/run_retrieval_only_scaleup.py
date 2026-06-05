#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx


STAGES = [
    "hybrid_retrieval_total",
    "graph_entity_vector_index_search",
    "graph_relation_vector_index_search",
    "chunks_vector_index_search",
    "vector_retrieval",
    "keyword_extraction",
    "rerank",
]


def _parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Expected boolean value, got {value!r}")


def _parse_csv_ints(value: str) -> list[int]:
    items = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not items or any(item < 1 for item in items):
        raise argparse.ArgumentTypeError("Expected comma-separated positive integers")
    return items


def _parse_variant(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("Variant must be NAME=URL")
    name, url = value.split("=", 1)
    name = name.strip()
    url = url.strip().rstrip("/")
    if not name or not url:
        raise argparse.ArgumentTypeError("Variant must be NAME=URL")
    return name, url


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run retrieval-only larger-query and concurrency benchmarks."
    )
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--queries-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--variant",
        action="append",
        required=True,
        type=_parse_variant,
        help="Variant service as NAME=URL. Repeat for multiple variants.",
    )
    parser.add_argument("--baseline-variant", default="exact")
    parser.add_argument("--concurrency-levels", type=_parse_csv_ints, default=[1, 2, 4, 8])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--mode", default="hybrid", choices=["graph", "hybrid"])
    parser.add_argument("--enable-rerank", type=_parse_bool, default=True)
    parser.add_argument("--response-type", default="Multiple Paragraphs")
    parser.add_argument("--request-timeout", type=float, default=900.0)
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Call benchmark cache clear before each variant/concurrency batch.",
    )
    return parser.parse_args()


def _read_queries(path: Path) -> list[dict[str, str]]:
    queries: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            query_id = str(payload.get("id") or "").strip()
            query = str(payload.get("query") or "").strip()
            if not query_id or not query:
                raise ValueError(f"{path}:{line_number} must contain id and query")
            queries.append({"id": query_id, "query": query})
    if not queries:
        raise ValueError(f"No queries found in {path}")
    return queries


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def _stage_seconds(stage_timings: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for item in stage_timings:
        stage = str(item.get("stage") or "")
        if not stage:
            continue
        try:
            totals[stage] += float(item.get("seconds") or 0.0)
        except (TypeError, ValueError):
            continue
    return dict(totals)


def _final_chunk_ids(response: dict[str, Any]) -> list[str]:
    trace = response.get("trace") or {}
    chunks = trace.get("final_context_document_chunks") or []
    ids: list[str] = []
    for chunk in chunks:
        if isinstance(chunk, str):
            ids.append(chunk)
            continue
        if not isinstance(chunk, dict):
            continue
        for key in ("id", "chunk_id", "__id__", "source_id"):
            raw = chunk.get(key)
            if raw:
                ids.append(str(raw))
                break
    return ids


def _percentile(values: list[float], percentile: float) -> float | None:
    clean = sorted(value for value in values if isinstance(value, int | float))
    if not clean:
        return None
    rank = max(0, math.ceil((percentile / 100.0) * len(clean)) - 1)
    return round(clean[min(rank, len(clean) - 1)], 4)


async def _clear_cache(client: httpx.AsyncClient, url: str, project_dir: str) -> None:
    response = await client.post(
        f"{url}/v1/benchmark/cache/clear",
        json={"project_dir": project_dir, "cache_types": []},
    )
    response.raise_for_status()


async def _run_one(
    *,
    client: httpx.AsyncClient,
    service_url: str,
    project_dir: str,
    variant: str,
    query: dict[str, str],
    repeat: int,
    concurrency: int,
    sequence: int,
    args: argparse.Namespace,
    raw_dir: Path,
) -> dict[str, Any]:
    cache_buster = f"#scaleup-{variant}-c{concurrency}-r{repeat}-{query['id']}-{sequence}"
    request_payload = {
        "project_dir": project_dir,
        "query": f"{query['query']}\n\n{cache_buster}",
        "mode": args.mode,
        "enable_rerank": args.enable_rerank,
        "include_trace": True,
        "retrieval_only": True,
        "only_need_context": True,
        "response_type": args.response_type,
    }
    started_at = time.perf_counter()
    record: dict[str, Any] = {
        "variant": variant,
        "service_url": service_url,
        "query_id": query["id"],
        "repeat": repeat,
        "concurrency": concurrency,
        "sequence": sequence,
        "cache_buster": cache_buster,
        "request": request_payload,
    }
    try:
        response = await client.post(
            f"{service_url}/v1/benchmark/query",
            json=request_payload,
        )
        elapsed = time.perf_counter() - started_at
        record["request_wall_seconds"] = round(elapsed, 6)
        record["http_status"] = response.status_code
        response.raise_for_status()
        payload = response.json()
        stage_timings = list(payload.get("stage_timings") or [])
        stage_totals = _stage_seconds(stage_timings)
        record["response"] = payload
        record["metrics"] = {
            "request_wall_seconds": round(elapsed, 6),
            "request_processing_seconds": payload.get("request_processing_seconds"),
            "query_seconds": payload.get("query_seconds"),
            "cache_hit_count": payload.get("cache_hit_count"),
            "reference_chunk_count": payload.get("reference_chunk_count"),
            "referenced_file_count": len(payload.get("referenced_file_paths") or []),
            "final_chunk_ids": _final_chunk_ids(payload),
            "stage_totals": stage_totals,
        }
    except Exception as exc:  # noqa: BLE001 - write all remote failures to raw JSON
        record["error"] = repr(exc)
        record.setdefault("request_wall_seconds", round(time.perf_counter() - started_at, 6))

    raw_path = raw_dir / (
        f"{_safe_name(variant)}__c{concurrency}__r{repeat}__"
        f"{_safe_name(query['id'])}__{sequence:04d}.json"
    )
    raw_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    record["raw_path"] = str(raw_path)
    return record


def _summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(record["variant"], int(record["concurrency"]))].append(record)

    summary: dict[str, Any] = {}
    for (variant, concurrency), items in sorted(groups.items()):
        successes = [item for item in items if "metrics" in item]
        errors = [item for item in items if "metrics" not in item]

        def values(metric: str) -> list[float]:
            output: list[float] = []
            for item in successes:
                raw = item["metrics"].get(metric)
                if isinstance(raw, int | float):
                    output.append(float(raw))
            return output

        def stage_values(stage: str) -> list[float]:
            output: list[float] = []
            for item in successes:
                raw = item["metrics"].get("stage_totals", {}).get(stage)
                if isinstance(raw, int | float):
                    output.append(float(raw))
            return output

        metrics: dict[str, Any] = {
            "runs": len(items),
            "successes": len(successes),
            "errors": len(errors),
            "cache_hits": sum(
                int(item["metrics"].get("cache_hit_count") or 0) for item in successes
            ),
        }
        for metric in (
            "request_wall_seconds",
            "request_processing_seconds",
            "query_seconds",
            "reference_chunk_count",
            "referenced_file_count",
        ):
            metric_values = values(metric)
            metrics[f"{metric}_p50"] = _percentile(metric_values, 50)
            metrics[f"{metric}_p95"] = _percentile(metric_values, 95)
        for stage in STAGES:
            metric_values = stage_values(stage)
            metrics[f"{stage}_p50"] = _percentile(metric_values, 50)
            metrics[f"{stage}_p95"] = _percentile(metric_values, 95)

        summary.setdefault(variant, {})[str(concurrency)] = metrics
    return summary


def _quality_summary(
    records: list[dict[str, Any]],
    *,
    baseline_variant: str,
) -> list[dict[str, Any]]:
    baseline: dict[str, set[str]] = {}
    for record in records:
        if record.get("variant") != baseline_variant or int(record.get("concurrency") or 0) != 1:
            continue
        metrics = record.get("metrics") or {}
        baseline[record["query_id"]] = set(metrics.get("final_chunk_ids") or [])

    rows: list[dict[str, Any]] = []
    variants = sorted({record["variant"] for record in records if record["variant"] != baseline_variant})
    for variant in variants:
        overlaps: list[int] = []
        below_8: list[str] = []
        for record in records:
            if record.get("variant") != variant or int(record.get("concurrency") or 0) != 1:
                continue
            expected = baseline.get(record["query_id"], set())
            if not expected:
                continue
            observed = set((record.get("metrics") or {}).get("final_chunk_ids") or [])
            overlap = len(expected & observed)
            overlaps.append(overlap)
            if overlap < 8:
                below_8.append(record["query_id"])
        if overlaps:
            rows.append(
                {
                    "variant": variant,
                    "queries": len(overlaps),
                    "chunk_overlap_p50": _percentile([float(value) for value in overlaps], 50),
                    "chunk_overlap_min": min(overlaps),
                    "queries_below_8": below_8,
                }
            )
    return rows


def _write_markdown(path: Path, summary: dict[str, Any], quality: list[dict[str, Any]]) -> None:
    lines = ["# Retrieval-only Scale-up Summary", ""]
    lines.append("| Variant | Concurrency | Runs | Errors | Cache hits | Request p50 | Request p95 | Retrieval p50 | Retrieval p95 | Entity index p50 | Entity index p95 | Relation index p50 | Relation index p95 |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for variant, by_concurrency in summary.items():
        for concurrency, metrics in by_concurrency.items():
            lines.append(
                "| {variant} | {concurrency} | {runs} | {errors} | {cache_hits} | "
                "{request_p50} | {request_p95} | {retrieval_p50} | {retrieval_p95} | "
                "{entity_p50} | {entity_p95} | {relation_p50} | {relation_p95} |".format(
                    variant=variant,
                    concurrency=concurrency,
                    runs=metrics["runs"],
                    errors=metrics["errors"],
                    cache_hits=metrics["cache_hits"],
                    request_p50=metrics["request_wall_seconds_p50"],
                    request_p95=metrics["request_wall_seconds_p95"],
                    retrieval_p50=metrics["hybrid_retrieval_total_p50"],
                    retrieval_p95=metrics["hybrid_retrieval_total_p95"],
                    entity_p50=metrics["graph_entity_vector_index_search_p50"],
                    entity_p95=metrics["graph_entity_vector_index_search_p95"],
                    relation_p50=metrics["graph_relation_vector_index_search_p50"],
                    relation_p95=metrics["graph_relation_vector_index_search_p95"],
                )
            )

    lines.extend(["", "## Quality vs Baseline", ""])
    lines.append("| Variant | Queries | Chunk overlap p50 | Min overlap | Queries below 8/10 |")
    lines.append("| --- | ---: | ---: | ---: | --- |")
    for row in quality:
        lines.append(
            "| {variant} | {queries} | {p50} | {minimum} | {below} |".format(
                variant=row["variant"],
                queries=row["queries"],
                p50=row["chunk_overlap_p50"],
                minimum=row["chunk_overlap_min"],
                below=", ".join(row["queries_below_8"]) or "",
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _main_async(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    queries = _read_queries(Path(args.queries_file))
    variants = dict(args.variant)
    timeout = httpx.Timeout(args.request_timeout)
    limits = httpx.Limits(max_connections=max(args.concurrency_levels) * len(variants) + 4)

    all_records: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=timeout, limits=limits, trust_env=False) as client:
        sequence = 0
        for variant, service_url in variants.items():
            for concurrency in args.concurrency_levels:
                if args.clear_cache:
                    await _clear_cache(client, service_url, args.project_dir)
                jobs = []
                for repeat in range(1, args.repeats + 1):
                    for query in queries:
                        sequence += 1
                        jobs.append((repeat, query, sequence))

                semaphore = asyncio.Semaphore(concurrency)

                async def run_guarded(repeat: int, query: dict[str, str], seq: int):
                    async with semaphore:
                        return await _run_one(
                            client=client,
                            service_url=service_url,
                            project_dir=args.project_dir,
                            variant=variant,
                            query=query,
                            repeat=repeat,
                            concurrency=concurrency,
                            sequence=seq,
                            args=args,
                            raw_dir=raw_dir,
                        )

                batch_records = await asyncio.gather(
                    *(run_guarded(repeat, query, seq) for repeat, query, seq in jobs)
                )
                all_records.extend(batch_records)

    summary = {
        "config": {
            "project_dir": args.project_dir,
            "queries_file": args.queries_file,
            "query_count": len(queries),
            "variants": variants,
            "baseline_variant": args.baseline_variant,
            "concurrency_levels": args.concurrency_levels,
            "repeats": args.repeats,
            "mode": args.mode,
            "enable_rerank": args.enable_rerank,
        },
        "groups": _summarize_records(all_records),
        "quality_vs_baseline": _quality_summary(
            all_records,
            baseline_variant=args.baseline_variant,
        ),
        "raw_record_count": len(all_records),
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(
        output_dir / "summary.md",
        summary["groups"],
        summary["quality_vs_baseline"],
    )
    print(json.dumps({"output_dir": str(output_dir), "summary": str(summary_path)}, indent=2))


def main() -> None:
    args = _parse_args()
    asyncio.run(_main_async(args))


if __name__ == "__main__":
    main()
