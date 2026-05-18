#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ragent.llm.openai import env_openai_complete, openai_embed
from ragent.offline_replay import (
    RawMergeUnit,
    build_raw_merge_unit_from_text,
    raw_merge_unit_to_json_obj,
)
from ragent.ragent import Ragent
from ragent.utils import (
    ModelUsageCollector,
    clean_text,
    compute_mdhash_id,
    write_model_usage_report,
)


def _iter_input_files(
    inputs: list[str],
    *,
    pattern: str,
    recursive: bool,
) -> list[Path]:
    files: list[Path] = []
    for item in inputs:
        path = Path(item).expanduser().resolve()
        if path.is_dir():
            iterator = path.rglob(pattern) if recursive else path.glob(pattern)
            files.extend(sorted(candidate for candidate in iterator if candidate.is_file()))
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(f"Input path does not exist: {path}")
    return sorted(dict.fromkeys(files))


def _source_group_key(path: Path) -> str:
    return path.stem or path.name or "unknown_source"


def _default_failures_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}.failures.jsonl")


def _write_failure_record(
    failures_path: Path,
    *,
    input_file: Path,
    error: Exception,
) -> None:
    failures_path.parent.mkdir(parents=True, exist_ok=True)
    with failures_path.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(
                {
                    "input_file": str(input_file),
                    "error": str(error),
                    "error_type": type(error).__name__,
                },
                ensure_ascii=False,
            )
            + "\n"
        )


async def _export_one_file(
    rag: Ragent,
    path: Path,
    *,
    content: str | None = None,
    doc_id: str | None = None,
    split_by_character: str | None,
    split_by_character_only: bool,
) -> RawMergeUnit:
    content = clean_text(path.read_text(encoding="utf-8")) if content is None else content
    doc_id = doc_id or compute_mdhash_id(content, prefix="doc-")
    doc_name = path.name
    file_path = str(path)
    metadata = {"file_path": file_path}

    pipeline_status = {"latest_message": "", "history_messages": []}
    pipeline_status_lock = asyncio.Lock()
    return await build_raw_merge_unit_from_text(
        rag,
        text=content,
        doc_name=doc_name,
        file_path=file_path,
        doc_id=doc_id,
        source_group_key=_source_group_key(path),
        metadata=metadata,
        split_by_character=split_by_character,
        split_by_character_only=split_by_character_only,
        pipeline_status=pipeline_status,
        pipeline_status_lock=pipeline_status_lock,
        clean_input=False,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export raw Ragent extraction units from markdown files without building "
            "the final KG graph."
        )
    )
    parser.add_argument("inputs", nargs="+", help="Markdown files or directories.")
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output raw merge unit JSONL file.",
    )
    parser.add_argument(
        "--glob",
        default="*.md",
        help="Glob used for directory inputs. Defaults to *.md.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan directory inputs.",
    )
    parser.add_argument(
        "--working-dir",
        default=None,
        help="Temporary shard working dir for extraction caches. Defaults to a temp dir.",
    )
    parser.add_argument(
        "--overwrite-working-dir",
        action="store_true",
        help="Replace --working-dir if it already exists.",
    )
    parser.add_argument(
        "--llm-model",
        default=os.getenv("LLM_MODEL"),
        help="LLM model name. Defaults to LLM_MODEL from the environment.",
    )
    parser.add_argument(
        "--split-by-character",
        default=None,
        help="Optional chunk split character, matching Ragent insert.",
    )
    parser.add_argument(
        "--split-by-character-only",
        action="store_true",
        help="Only split by the provided character.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue exporting later files and record failed files to JSONL.",
    )
    parser.add_argument(
        "--failures-output",
        default=None,
        help=(
            "Failure JSONL path used with --continue-on-error. Defaults to "
            "<output-stem>.failures.jsonl next to --output."
        ),
    )
    return parser.parse_args()


async def _run_with_working_dir(
    args: argparse.Namespace,
    working_dir: Path,
) -> dict[str, Any]:
    if not args.llm_model:
        raise ValueError("Missing --llm-model or LLM_MODEL environment variable.")

    output_path = Path(args.output).expanduser().resolve()
    failures_path = (
        Path(args.failures_output).expanduser().resolve()
        if args.failures_output
        else _default_failures_path(output_path)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    collector = ModelUsageCollector("export_raw_merge_units")
    stats: dict[str, Any] | None = None
    try:
        with collector:
            rag: Ragent | None = None
            exported = 0
            skipped_duplicates = 0
            failed_files = 0
            seen_doc_ids: set[str] = set()
            try:
                rag = Ragent(
                    working_dir=str(working_dir),
                    embedding_func=openai_embed,
                    llm_model_func=env_openai_complete,
                    llm_model_name=args.llm_model,
                    auto_manage_storages_states=False,
                )
                await rag.initialize_storages()
                input_files = _iter_input_files(
                    args.inputs,
                    pattern=args.glob,
                    recursive=args.recursive,
                )
                with output_path.open("w", encoding="utf-8") as file:
                    for input_file in input_files:
                        try:
                            content = clean_text(input_file.read_text(encoding="utf-8"))
                            doc_id = compute_mdhash_id(content, prefix="doc-")
                            if doc_id in seen_doc_ids:
                                skipped_duplicates += 1
                                continue
                            unit = await _export_one_file(
                                rag,
                                input_file,
                                content=content,
                                doc_id=doc_id,
                                split_by_character=args.split_by_character,
                                split_by_character_only=args.split_by_character_only,
                            )
                            file.write(
                                json.dumps(
                                    raw_merge_unit_to_json_obj(unit), ensure_ascii=False
                                )
                                + "\n"
                            )
                            seen_doc_ids.add(doc_id)
                            exported += 1
                        except Exception as exc:
                            failed_files += 1
                            if not args.continue_on_error:
                                raise
                            _write_failure_record(
                                failures_path,
                                input_file=input_file,
                                error=exc,
                            )
                            continue
                stats = {
                    "input_files": len(input_files),
                    "exported_units": exported,
                    "skipped_duplicates": skipped_duplicates,
                    "failed_files": failed_files,
                    "output": str(output_path),
                }
                if failed_files:
                    stats["failures"] = str(failures_path)
            finally:
                if rag is not None:
                    await rag.finalize_storages()
                    for attr_name in ("embedding_func", "llm_model_func"):
                        shutdown = getattr(
                            getattr(rag, attr_name, None), "shutdown", None
                        )
                        if callable(shutdown):
                            await shutdown()
    finally:
        report_path = write_model_usage_report(
            collector,
            str(output_path.parent),
            task_name="raw_export",
            metadata={
                "inputs": ", ".join(str(Path(item).expanduser()) for item in args.inputs),
                "output": str(output_path),
                "working_dir": str(working_dir),
            },
        )
        if stats is not None:
            stats["model_usage_report"] = report_path
    if stats is None:
        raise RuntimeError("raw export finished without stats")
    return stats


async def _run(args: argparse.Namespace) -> None:
    if args.working_dir:
        working_dir = Path(args.working_dir).expanduser().resolve()
        if working_dir.exists() and args.overwrite_working_dir:
            shutil.rmtree(working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)
        stats = await _run_with_working_dir(args, working_dir)
    else:
        with tempfile.TemporaryDirectory(prefix="ragent_raw_export_") as temp_dir:
            stats = await _run_with_working_dir(args, Path(temp_dir))
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def main() -> None:
    args = _parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
