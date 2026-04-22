#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

from ragent.benchmarking import BENCHMARK_SCENARIO_DESCRIPTIONS


INTERESTING_ENV_KEYS = [
    "WORKSPACE",
    "LLM_MODEL",
    "EMBEDDING_MODEL",
    "RERANK_MODEL",
    "ENABLE_RERANK",
    "TOP_K",
    "CHUNK_TOP_K",
    "MAX_ENTITY_TOKENS",
    "MAX_RELATION_TOKENS",
    "MAX_TOTAL_TOKENS",
    "RAG_ANSWER_PROMPT_MODE",
    "QUERY_CACHE_TTL_SECONDS",
    "QUERY_CACHE_MAX_ENTRIES",
    "MODEL_STARTUP_CHECK_TIMEOUT_SECONDS",
    "LLM_API_TIMEOUT_SECONDS",
    "EMBEDDING_API_TIMEOUT_SECONDS",
    "RERANK_API_TIMEOUT_SECONDS",
    "IMAGE_MODEL_TIMEOUT",
]
RETRIEVAL_WARM_HIT_STAGES = {"retrieval_cache_hit", "render_cache_hit", "prompt_cache_hit"}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HTTP latency benchmark scenarios.")
    parser.add_argument("--service-url", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--response-type", default="Multiple Paragraphs")
    parser.add_argument("--request-timeout", type=float, default=600.0)
    parser.add_argument("--modes", nargs="+", default=["graph", "hybrid"])
    parser.add_argument("--rerank-options", nargs="+", default=["off", "on"])
    parser.add_argument("--env-file", default=".env")
    parser.add_argument(
        "--allow-validation-failures",
        action="store_true",
        help="Do not exit non-zero when scenario validation fails.",
    )
    return parser.parse_args()


def _normalize_rerank_options(values: list[str]) -> list[bool]:
    normalized: list[bool] = []
    for value in values:
        lowered = str(value).strip().lower()
        if lowered in {"on", "true", "1", "yes"}:
            normalized.append(True)
            continue
        if lowered in {"off", "false", "0", "no"}:
            normalized.append(False)
            continue
        raise ValueError(f"Unsupported rerank option: {value}")
    return normalized


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_env_snapshot(env_file: Path, output_path: Path, args: argparse.Namespace) -> None:
    env_values = dotenv_values(env_file) if env_file.exists() else {}
    lines = [
        f"service_url={args.service_url}",
        f"project_dir={args.project_dir}",
        f"runs={args.runs}",
        f"query={args.query}",
        f"modes={','.join(args.modes)}",
        f"rerank_options={','.join(args.rerank_options)}",
        f"response_type={args.response_type}",
    ]
    for key in INTERESTING_ENV_KEYS:
        raw_value = os.environ.get(key)
        if raw_value is None or raw_value == "":
            raw_value = env_values.get(key)
        if raw_value is None or raw_value == "":
            continue
        lines.append(f"{key}={raw_value}")
    _write_text(output_path, "\n".join(lines) + "\n")


def _write_config(output_path: Path, args: argparse.Namespace) -> None:
    lines = [
        f"service_url={args.service_url}",
        f"project_dir={args.project_dir}",
        f"query={args.query}",
        f"runs={args.runs}",
        f"response_type={args.response_type}",
        "",
        "[scenarios]",
    ]
    for name, description in BENCHMARK_SCENARIO_DESCRIPTIONS.items():
        lines.append(f"{name}={description}")
    _write_text(output_path, "\n".join(lines) + "\n")


def _request_json(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    json_payload: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    started_at = time.perf_counter()
    response = client.request(method, url, json=json_payload)
    elapsed = time.perf_counter() - started_at
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{method} {url} returned non-JSON status={response.status_code}: {response.text}"
        ) from exc
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {url} failed status={response.status_code}: {payload}")
    return elapsed, payload


def _query_payload(args: argparse.Namespace, *, mode: str, enable_rerank: bool) -> dict[str, Any]:
    return {
        "project_dir": args.project_dir,
        "query": args.query,
        "mode": mode,
        "enable_rerank": enable_rerank,
        "include_trace": True,
        "response_type": args.response_type,
    }


def _cache_clear(
    client: httpx.Client,
    args: argparse.Namespace,
    *,
    cache_types: list[str] | None = None,
) -> dict[str, Any]:
    _, payload = _request_json(
        client,
        "POST",
        f"{args.service_url.rstrip('/')}/v1/benchmark/cache/clear",
        json_payload={
            "project_dir": args.project_dir,
            "cache_types": cache_types or [],
        },
    )
    return payload


def _reset_project(
    client: httpx.Client,
    args: argparse.Namespace,
    *,
    clear_cache: bool,
) -> dict[str, Any]:
    _, payload = _request_json(
        client,
        "POST",
        f"{args.service_url.rstrip('/')}/v1/benchmark/project/reset",
        json_payload={
            "project_dir": args.project_dir,
            "clear_cache": clear_cache,
        },
    )
    return payload


def _validate_response(scenario: str, response_payload: dict[str, Any]) -> tuple[str, str]:
    cache_hits = set(response_payload.get("cache_hit_stages") or [])
    project_initialized_before_request = bool(
        response_payload.get("project_initialized_before_request")
    )
    project_first_request = bool(response_payload.get("project_first_request"))
    project_initialization_seconds = response_payload.get("project_initialization_seconds")

    problems: list[str] = []
    if scenario == "first_request":
        if project_initialized_before_request:
            problems.append("project session was already initialized before request")
        if not project_first_request:
            problems.append("request was not marked as the first project request")
        if project_initialization_seconds in (None, ""):
            problems.append("first request did not report project initialization time")
        if cache_hits:
            problems.append(f"unexpected cache hits: {','.join(sorted(cache_hits))}")
    elif scenario == "steady_cold":
        if project_initialization_seconds not in (None, ""):
            problems.append("steady cold request unexpectedly included project initialization")
        if cache_hits:
            problems.append(f"unexpected cache hits: {','.join(sorted(cache_hits))}")
    elif scenario == "steady_retrieval_warm":
        if "answer_cache_hit" in cache_hits:
            problems.append("answer cache hit was present after answer cache clear")
        if not (cache_hits & RETRIEVAL_WARM_HIT_STAGES):
            problems.append("retrieval/render/prompt cache hit was not observed")
    elif scenario == "steady_answer_warm":
        if "answer_cache_hit" not in cache_hits:
            problems.append("answer cache hit was not observed")
    else:
        problems.append(f"unknown scenario: {scenario}")

    if problems:
        return "fail", "; ".join(problems)
    return "pass", ""


def _measure_request(
    client: httpx.Client,
    args: argparse.Namespace,
    *,
    scenario: str,
    mode: str,
    enable_rerank: bool,
    label: str,
    results_writer: csv.DictWriter,
) -> tuple[str, str]:
    response_path = Path(args.output_dir) / f"{label}.response.json"
    trace_path = Path(args.output_dir) / f"{label}.trace.json"
    wall_seconds, payload = _request_json(
        client,
        "POST",
        f"{args.service_url.rstrip('/')}/v1/benchmark/query",
        json_payload=_query_payload(args, mode=mode, enable_rerank=enable_rerank),
    )
    _write_json(response_path, payload)
    _write_json(trace_path, payload.get("trace") or {})

    validation_status, validation_message = _validate_response(scenario, payload)
    results_writer.writerow(
        {
            "scenario": scenario,
            "mode": mode,
            "rerank_enabled": str(enable_rerank).lower(),
            "run_index": label.rsplit("run_", 1)[-1] if ".run_" in label else "",
            "request_wall_seconds": f"{wall_seconds:.6f}",
            "server_request_seconds": _fmt_float(payload.get("request_processing_seconds")),
            "project_initialized_before_request": str(
                bool(payload.get("project_initialized_before_request"))
            ).lower(),
            "project_first_request": str(bool(payload.get("project_first_request"))).lower(),
            "project_initialization_seconds": _fmt_float(
                payload.get("project_initialization_seconds")
            ),
            "startup_model_check_seconds": _fmt_float(
                payload.get("startup_model_check_seconds")
            ),
            "query_seconds": _fmt_float(payload.get("query_seconds")),
            "cache_hit_stages": ",".join(payload.get("cache_hit_stages") or []),
            "cache_hit_count": str(int(payload.get("cache_hit_count") or 0)),
            "validation_status": validation_status,
            "validation_message": validation_message,
            "response_file": str(response_path),
            "trace_file": str(trace_path),
        }
    )
    return validation_status, validation_message


def _fmt_float(value: Any) -> str:
    if value in (None, ""):
        return ""
    return f"{float(value):.6f}"


def _prime_request(
    client: httpx.Client,
    args: argparse.Namespace,
    *,
    mode: str,
    enable_rerank: bool,
    label: str,
) -> None:
    _, payload = _request_json(
        client,
        "POST",
        f"{args.service_url.rstrip('/')}/v1/benchmark/query",
        json_payload=_query_payload(args, mode=mode, enable_rerank=enable_rerank),
    )
    response_path = Path(args.output_dir) / f"{label}.response.json"
    trace_path = Path(args.output_dir) / f"{label}.trace.json"
    _write_json(response_path, payload)
    _write_json(trace_path, payload.get("trace") or {})


def _run_first_request_scenario(
    client: httpx.Client,
    args: argparse.Namespace,
    *,
    mode: str,
    enable_rerank: bool,
    results_writer: csv.DictWriter,
    validation_failures: list[str],
) -> None:
    for run_index in range(1, args.runs + 1):
        _reset_project(client, args, clear_cache=True)
        label = f"{mode}.rerank_{'on' if enable_rerank else 'off'}.first_request.run_{run_index}"
        status, message = _measure_request(
            client,
            args,
            scenario="first_request",
            mode=mode,
            enable_rerank=enable_rerank,
            label=label,
            results_writer=results_writer,
        )
        if status == "fail":
            validation_failures.append(f"{label}: {message}")


def _prepare_initialized_service(
    client: httpx.Client,
    args: argparse.Namespace,
    *,
    mode: str,
    enable_rerank: bool,
    label: str,
) -> None:
    _reset_project(client, args, clear_cache=True)
    _prime_request(client, args, mode=mode, enable_rerank=enable_rerank, label=label)


def _run_steady_cold_scenario(
    client: httpx.Client,
    args: argparse.Namespace,
    *,
    mode: str,
    enable_rerank: bool,
    results_writer: csv.DictWriter,
    validation_failures: list[str],
) -> None:
    base_label = f"{mode}.rerank_{'on' if enable_rerank else 'off'}.steady_cold"
    _prepare_initialized_service(
        client,
        args,
        mode=mode,
        enable_rerank=enable_rerank,
        label=f"{base_label}.prime",
    )
    for run_index in range(1, args.runs + 1):
        _cache_clear(client, args)
        label = f"{base_label}.run_{run_index}"
        status, message = _measure_request(
            client,
            args,
            scenario="steady_cold",
            mode=mode,
            enable_rerank=enable_rerank,
            label=label,
            results_writer=results_writer,
        )
        if status == "fail":
            validation_failures.append(f"{label}: {message}")


def _run_steady_retrieval_warm_scenario(
    client: httpx.Client,
    args: argparse.Namespace,
    *,
    mode: str,
    enable_rerank: bool,
    results_writer: csv.DictWriter,
    validation_failures: list[str],
) -> None:
    base_label = f"{mode}.rerank_{'on' if enable_rerank else 'off'}.steady_retrieval_warm"
    _prepare_initialized_service(
        client,
        args,
        mode=mode,
        enable_rerank=enable_rerank,
        label=f"{base_label}.prime",
    )
    for run_index in range(1, args.runs + 1):
        _cache_clear(client, args, cache_types=["answer"])
        label = f"{base_label}.run_{run_index}"
        status, message = _measure_request(
            client,
            args,
            scenario="steady_retrieval_warm",
            mode=mode,
            enable_rerank=enable_rerank,
            label=label,
            results_writer=results_writer,
        )
        if status == "fail":
            validation_failures.append(f"{label}: {message}")


def _run_steady_answer_warm_scenario(
    client: httpx.Client,
    args: argparse.Namespace,
    *,
    mode: str,
    enable_rerank: bool,
    results_writer: csv.DictWriter,
    validation_failures: list[str],
) -> None:
    base_label = f"{mode}.rerank_{'on' if enable_rerank else 'off'}.steady_answer_warm"
    _prepare_initialized_service(
        client,
        args,
        mode=mode,
        enable_rerank=enable_rerank,
        label=f"{base_label}.prime",
    )
    for run_index in range(1, args.runs + 1):
        label = f"{base_label}.run_{run_index}"
        status, message = _measure_request(
            client,
            args,
            scenario="steady_answer_warm",
            mode=mode,
            enable_rerank=enable_rerank,
            label=label,
            results_writer=results_writer,
        )
        if status == "fail":
            validation_failures.append(f"{label}: {message}")


def main() -> int:
    args = _parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    env_file = Path(args.env_file).resolve()
    _write_config(output_dir / "config.txt", args)
    _write_env_snapshot(env_file, output_dir / "env_snapshot.txt", args)

    rerank_options = _normalize_rerank_options(args.rerank_options)
    results_path = output_dir / "results.tsv"
    validation_failures: list[str] = []

    with results_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scenario",
                "mode",
                "rerank_enabled",
                "run_index",
                "request_wall_seconds",
                "server_request_seconds",
                "project_initialized_before_request",
                "project_first_request",
                "project_initialization_seconds",
                "startup_model_check_seconds",
                "query_seconds",
                "cache_hit_stages",
                "cache_hit_count",
                "validation_status",
                "validation_message",
                "response_file",
                "trace_file",
            ],
            delimiter="\t",
        )
        writer.writeheader()

        with httpx.Client(timeout=args.request_timeout, trust_env=False) as client:
            for mode in args.modes:
                for enable_rerank in rerank_options:
                    _run_first_request_scenario(
                        client,
                        args,
                        mode=mode,
                        enable_rerank=enable_rerank,
                        results_writer=writer,
                        validation_failures=validation_failures,
                    )
                    _run_steady_cold_scenario(
                        client,
                        args,
                        mode=mode,
                        enable_rerank=enable_rerank,
                        results_writer=writer,
                        validation_failures=validation_failures,
                    )
                    _run_steady_retrieval_warm_scenario(
                        client,
                        args,
                        mode=mode,
                        enable_rerank=enable_rerank,
                        results_writer=writer,
                        validation_failures=validation_failures,
                    )
                    _run_steady_answer_warm_scenario(
                        client,
                        args,
                        mode=mode,
                        enable_rerank=enable_rerank,
                        results_writer=writer,
                        validation_failures=validation_failures,
                    )

    if validation_failures:
        _write_text(output_dir / "validation_errors.txt", "\n".join(validation_failures) + "\n")
        if not args.allow_validation_failures:
            raise SystemExit(
                "Latency benchmark validation failed. See "
                f"{output_dir / 'validation_errors.txt'}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
