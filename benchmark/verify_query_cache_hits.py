#!/usr/bin/env python3
"""Verify benchmark warm runs used the layered query cache.

The script is intentionally format-light: it can inspect a benchmark trace JSON
file containing records with `trace.stage_timings`, and/or inspect a legacy
`kv_store_llm_response_cache.json` file or the sqlite-backed
`kv_store_llm_response_cache.sqlite` file for `{mode}:{cache_type}:{hash}` keys.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any


CACHE_HIT_STAGES = {
    "answer_cache_hit",
    "retrieval_cache_hit",
    "render_cache_hit",
    "prompt_cache_hit",
}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_cache_counts(path: Path) -> Counter[tuple[str, str]]:
    if path.suffix == ".sqlite":
        with sqlite3.connect(path) as conn:
            rows = conn.execute(
                """
                SELECT mode, cache_type, COUNT(*) AS entry_count
                FROM query_cache_entries
                GROUP BY mode, cache_type
                """
            ).fetchall()
        counts: Counter[tuple[str, str]] = Counter()
        for mode, cache_type, entry_count in rows:
            counts[(str(mode), str(cache_type))] = int(entry_count)
        return counts

    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise TypeError(f"Cache file is not a JSON object: {path}")

    counts: Counter[tuple[str, str]] = Counter()
    for key in payload:
        parts = str(key).split(":", 2)
        if len(parts) == 3:
            counts[(parts[0], parts[1])] += 1
    return counts


def _iter_records(payload: Any):
    if isinstance(payload, list):
        yield from payload
        return
    if not isinstance(payload, dict):
        return
    for key in ("records", "results", "runs", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            yield from value
            return
    yield payload


def _iter_traces(record: dict[str, Any]):
    trace = record.get("trace")
    if isinstance(trace, dict):
        yield trace
    if "stage_timings" in record:
        yield record
    for step in record.get("steps") or []:
        if isinstance(step, dict) and isinstance(step.get("trace"), dict):
            yield step["trace"]


def _stage_names(trace: dict[str, Any]) -> set[str]:
    names = set()
    for item in trace.get("stage_timings") or []:
        if isinstance(item, dict) and item.get("stage"):
            names.add(str(item["stage"]))
    return names


def _is_warm_record(record: dict[str, Any]) -> bool:
    for key in ("phase", "run", "scenario", "cache_state"):
        value = str(record.get(key) or "").lower()
        if value in {"warm", "warm_run", "cached"}:
            return True
    return bool(record.get("warm"))


def summarize_trace_hits(path: Path, *, require_warm_hit: bool) -> int:
    payload = _load_json(path)
    failures = 0
    rows = []
    for index, record in enumerate(_iter_records(payload), 1):
        if not isinstance(record, dict):
            continue
        hit_stages = set()
        for trace in _iter_traces(record):
            hit_stages.update(_stage_names(trace) & CACHE_HIT_STAGES)
        mode = record.get("mode") or record.get("query_mode") or "unknown"
        warm = _is_warm_record(record)
        rows.append(
            {
                "index": index,
                "mode": mode,
                "warm": warm,
                "hit_stages": sorted(hit_stages),
            }
        )
        if require_warm_hit and warm and not hit_stages:
            failures += 1

    print(f"Trace file: {path}")
    for row in rows:
        hit_label = ", ".join(row["hit_stages"]) if row["hit_stages"] else "none"
        warm_label = "warm" if row["warm"] else "cold/unspecified"
        print(f"- #{row['index']} mode={row['mode']} {warm_label} cache_hits={hit_label}")
    return failures


def summarize_cache_file(
    path: Path,
    *,
    required_entries: list[str],
) -> int:
    try:
        counts = _load_cache_counts(path)
    except (TypeError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Cache file: {path}")
    for (mode, cache_type), count in sorted(counts.items()):
        print(f"- {mode}:{cache_type} entries={count}")

    failures = 0
    for requirement in required_entries:
        parts = requirement.split(":", 1)
        if len(parts) != 2:
            print(
                f"Invalid --require-cache-entry value {requirement!r}; use mode:cache_type",
                file=sys.stderr,
            )
            failures += 1
            continue
        mode, cache_type = parts
        if counts[(mode, cache_type)] == 0:
            print(f"Missing required cache entry: {mode}:{cache_type}", file=sys.stderr)
            failures += 1
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify layered query cache hits in benchmark outputs."
    )
    parser.add_argument("--trace-json", type=Path, help="Benchmark trace JSON file.")
    parser.add_argument(
        "--cache-file",
        type=Path,
        help="Path to legacy kv_store_llm_response_cache.json or kv_store_llm_response_cache.sqlite.",
    )
    parser.add_argument(
        "--require-warm-hit",
        action="store_true",
        help="Fail if records marked warm do not contain a cache-hit stage.",
    )
    parser.add_argument(
        "--require-cache-entry",
        action="append",
        default=[],
        help="Require at least one flattened cache entry, e.g. graph:answer.",
    )
    args = parser.parse_args()

    if not args.trace_json and not args.cache_file:
        parser.error("Provide --trace-json and/or --cache-file.")

    failures = 0
    if args.trace_json:
        failures += summarize_trace_hits(
            args.trace_json,
            require_warm_hit=args.require_warm_hit,
        )
    if args.cache_file:
        failures += summarize_cache_file(
            args.cache_file,
            required_entries=args.require_cache_entry,
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
