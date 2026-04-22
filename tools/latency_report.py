#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from ragent.benchmarking import BENCHMARK_SCENARIO_DESCRIPTIONS


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate summary.md from latency benchmark outputs.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--runs", type=int, required=True)
    return parser.parse_args()


def _parse_float(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    return float(value)


def _format_metric(values: list[float]) -> str:
    if not values:
        return "-"
    return f"{statistics.median(values):.3f} / {statistics.fmean(values):.3f}"


def _load_rows(results_path: Path) -> list[dict[str, str]]:
    with results_path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _load_startup_summary(startup_path: Path) -> dict[str, object] | None:
    if not startup_path.exists():
        return None
    return json.loads(startup_path.read_text(encoding="utf-8"))


def _format_optional_float(value: object) -> str:
    if value in (None, ""):
        return "-"
    return f"{float(value):.3f}"


def main() -> int:
    args = _parse_args()
    output_dir = Path(args.output_dir).resolve()
    results_path = output_dir / "results.tsv"
    summary_path = output_dir / "summary.md"
    env_snapshot_path = output_dir / "env_snapshot.txt"
    startup_path = output_dir / "service_startup.json"
    validation_path = output_dir / "validation_errors.txt"

    rows = _load_rows(results_path)
    grouped_rows: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped_rows[(row["scenario"], row["mode"], row["rerank_enabled"])].append(row)

    startup_summary = _load_startup_summary(startup_path)
    scenario_order = list(BENCHMARK_SCENARIO_DESCRIPTIONS.keys())

    lines = [
        "# Latency Benchmark Summary",
        "",
        f"- Project: `{args.project_dir}`",
        f"- Query: {args.query}",
        f"- Runs per request scenario: {args.runs}",
        f"- Output dir: `{output_dir}`",
        f"- Environment snapshot: `{env_snapshot_path}`",
        f"- Service startup artifact: `{startup_path}`",
        "",
        "## Metric Definitions",
        "",
        "- `service_startup_wall_seconds`: process spawn to `/health` ready. This is the external service startup cost.",
        "- `startup_ready_seconds`: server-reported startup readiness time from `/health`, currently dominated by startup model checks.",
        "- `request_wall_seconds`: client-observed single HTTP request latency. This is the main online latency metric.",
        "- `project_initialization_seconds`: `rag_initialization_total` captured inside the first request after the project session is loaded.",
        "- `query_seconds`: request-side `onehop_total` captured by the service trace, excluding service startup and excluding project init unless it is folded into the measured first request path.",
        "",
        "## Scenario Semantics",
        "",
    ]

    for scenario_name, description in BENCHMARK_SCENARIO_DESCRIPTIONS.items():
        lines.append(f"- `{scenario_name}`: {description}")

    if startup_summary:
        lines.extend(
            [
                "",
                "## Service Startup",
                "",
                "| service_url | startup wall (s) | startup ready (s) | log |",
                "|---|---:|---:|---|",
                (
                    f"| `{startup_summary.get('service_url', '-')}` | "
                    f"{_format_optional_float(startup_summary.get('startup_wall_seconds'))} | "
                    f"{_format_optional_float(startup_summary.get('startup_ready_seconds'))} | "
                    f"`{startup_summary.get('log_file', '-')}` |"
                ),
            ]
        )

    lines.extend(
        [
            "",
            "## Request Summary",
            "",
            "| scenario | mode | rerank | request wall median/mean (s) | project init median/mean (s) | query execution median/mean (s) | validation failures | cache hits seen |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )

    def _collect_metric_values(
        scenario: str,
        mode: str,
        rerank_enabled: str,
        field: str,
    ) -> list[float]:
        values = [
            _parse_float(row[field]) for row in grouped_rows.get((scenario, mode, rerank_enabled), [])
        ]
        return [value for value in values if value is not None]

    all_configs = sorted({(mode, rerank) for _, mode, rerank in grouped_rows})

    for scenario in scenario_order:
        for mode, rerank_enabled in all_configs:
            scenario_rows = grouped_rows.get((scenario, mode, rerank_enabled), [])
            if not scenario_rows:
                continue
            request_wall_values = _collect_metric_values(
                scenario, mode, rerank_enabled, "request_wall_seconds"
            )
            init_values = _collect_metric_values(
                scenario, mode, rerank_enabled, "project_initialization_seconds"
            )
            query_values = _collect_metric_values(scenario, mode, rerank_enabled, "query_seconds")
            validation_failures = sum(row["validation_status"] == "fail" for row in scenario_rows)
            cache_hits_seen = sorted(
                {
                    hit
                    for row in scenario_rows
                    for hit in (row["cache_hit_stages"] or "").split(",")
                    if hit
                }
            )
            lines.append(
                f"| `{scenario}` | `{mode}` | `{rerank_enabled}` | "
                f"{_format_metric(request_wall_values)} | "
                f"{_format_metric(init_values)} | "
                f"{_format_metric(query_values)} | "
                f"{validation_failures}/{len(scenario_rows)} | "
                f"{', '.join(cache_hits_seen) if cache_hits_seen else '-'} |"
            )

    lines.extend(
        [
            "",
            "## Configuration View",
            "",
            "| mode | rerank | first request wall median/mean (s) | steady cold wall median/mean (s) | retrieval warm wall median/mean (s) | answer warm wall median/mean (s) |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )

    for mode, rerank_enabled in all_configs:
        lines.append(
            f"| `{mode}` | `{rerank_enabled}` | "
            f"{_format_metric(_collect_metric_values('first_request', mode, rerank_enabled, 'request_wall_seconds'))} | "
            f"{_format_metric(_collect_metric_values('steady_cold', mode, rerank_enabled, 'request_wall_seconds'))} | "
            f"{_format_metric(_collect_metric_values('steady_retrieval_warm', mode, rerank_enabled, 'request_wall_seconds'))} | "
            f"{_format_metric(_collect_metric_values('steady_answer_warm', mode, rerank_enabled, 'request_wall_seconds'))} |"
        )

    if validation_path.exists():
        lines.extend(
            [
                "",
                "## Validation Errors",
                "",
                "Warm/cold semantic validation failed for these runs:",
                "",
            ]
        )
        for item in validation_path.read_text(encoding="utf-8").splitlines():
            if item.strip():
                lines.append(f"- `{item.strip()}`")

    lines.extend(
        [
            "",
            "## Reading Guide",
            "",
            "- `first_request` should be read as `project_initialization_seconds + query_seconds` inside a warm service process.",
            "- `steady_cold` isolates steady-state request cost with the project already loaded but query caches cleared.",
            "- `steady_retrieval_warm` isolates the benefit of retrieval/render/prompt reuse without direct answer-cache hits.",
            "- `steady_answer_warm` isolates the direct answer-cache hit path.",
            "",
            "## Artifacts",
            "",
            "- `results.tsv`: measured request-level raw metrics.",
            "- `service_startup.json`: service startup cost and log pointer.",
            "- `*.response.json`: raw service responses for every measured run and prime step.",
            "- `*.trace.json`: extracted trace payloads for every measured run and prime step.",
            "- `service.log`: long-running benchmark service log.",
        ]
    )

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
