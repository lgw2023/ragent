#!/usr/bin/env python3
"""One-off: append missing raw merge units for 中国居民膳食指南_2022.

The 2026-05-21 strict-offline shard run wrote 1132/1371 units before Dashscope
timeouts. This script only exports the remaining units and appends them to the
existing JSONL (no full re-export).

Usage (from repo root, with .env configured):

    .venv/bin/python example/resume_diet_guide_2022_raw_units_once.py

Optional:

    .venv/bin/python example/resume_diet_guide_2022_raw_units_once.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from integrations import (
    _build_md_rag_insert_plan,
    _clean_text_for_xml,
    _close_rag,
    _source_group_key_from_doc_name,
    initialize_rag,
)
from ragent.offline_replay import build_raw_merge_unit_from_text, raw_merge_unit_to_json_obj
from ragent.utils import clean_text, compute_mdhash_id

logger = logging.getLogger("ragent")

PDF_PATH = PROJECT_ROOT / "example" / "中国居民膳食指南_2022.pdf"
MD_PATH = (
    PROJECT_ROOT
    / "example"
    / "中国居民膳食指南_2022_md"
    / "txt"
    / "中国居民膳食指南_2022.md"
)
OUTPUT_JSONL = (
    PROJECT_ROOT / "example" / "qwen4b_diet_kg_raw_units" / "中国居民膳食指南_2022.raw-units.jsonl"
)
FAILURES_JSONL = OUTPUT_JSONL.with_suffix(".resume.failures.jsonl")


def _load_existing_doc_ids(jsonl_path: Path) -> set[str]:
    seen: set[str] = set()
    if not jsonl_path.exists():
        return seen
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL at {jsonl_path}:{line_number}: {exc}"
                ) from exc
            doc_id = payload.get("doc_id")
            if doc_id:
                seen.add(str(doc_id))
    return seen


def _plan_missing_units(
    insert_units: list[dict],
    seen_doc_ids: set[str],
) -> list[dict]:
    missing: list[dict] = []
    for unit in insert_units:
        text = (unit.get("text") or "").strip()
        if not text:
            continue
        content = clean_text(_clean_text_for_xml(text))
        doc_id = compute_mdhash_id(content, prefix="doc-")
        if doc_id in seen_doc_ids:
            continue
        missing.append({**unit, "_content": content, "_doc_id": doc_id})
    return missing


def _write_failure(record: dict) -> None:
    FAILURES_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with FAILURES_JSONL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


async def _run(*, dry_run: bool) -> dict[str, int]:
    load_dotenv(PROJECT_ROOT / ".env")

    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")
    if not MD_PATH.exists():
        raise FileNotFoundError(f"Markdown not found: {MD_PATH}")

    seen_doc_ids = _load_existing_doc_ids(OUTPUT_JSONL)
    logger.info("Loaded %s existing doc_id(s) from %s", len(seen_doc_ids), OUTPUT_JSONL)

    working_dir = tempfile.mkdtemp(prefix="ragent_raw_resume_")
    rag = await initialize_rag(working_dir)
    try:
        insert_plan = await _build_md_rag_insert_plan(
            rag,
            str(PDF_PATH),
            str(MD_PATH),
        )
        source_pdf_path = insert_plan["source_pdf_path"]
        doc_name_with_ext = insert_plan["doc_name_with_ext"]
        missing_units = _plan_missing_units(
            insert_plan["insert_units"],
            seen_doc_ids,
        )

        stats = {
            "existing_units": len(seen_doc_ids),
            "missing_units": len(missing_units),
            "exported_units": 0,
            "failed_units": 0,
        }
        logger.info(
            "Insert plan ready: existing=%s missing=%s output=%s",
            stats["existing_units"],
            stats["missing_units"],
            OUTPUT_JSONL,
        )

        if dry_run:
            by_type: dict[str, int] = {}
            for unit in missing_units:
                chunk_type = str(unit.get("chunk_type", "text"))
                by_type[chunk_type] = by_type.get(chunk_type, 0) + 1
            logger.info("Dry run only. missing_by_type=%s", by_type)
            return stats

        if not missing_units:
            logger.info("Nothing to resume; JSONL already complete.")
            return stats

        pipeline_status = {"latest_message": "", "history_messages": []}
        pipeline_status_lock = asyncio.Lock()
        OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

        with OUTPUT_JSONL.open("a", encoding="utf-8") as output_file:
            for index, unit in enumerate(missing_units, start=1):
                unit_doc_name = unit.get("doc_name", doc_name_with_ext)
                file_path = (
                    os.path.abspath(unit.get("file_paths", source_pdf_path))
                    if unit.get("file_paths")
                    else source_pdf_path
                )
                chunk_type = unit.get("chunk_type", "text")
                chunk_index = unit.get("chunk_index", index - 1)

                logger.info(
                    "[%s/%s] exporting missing unit doc_id=%s type=%s chunk_index=%s",
                    index,
                    len(missing_units),
                    unit["_doc_id"],
                    chunk_type,
                    chunk_index,
                )

                try:
                    raw_unit = await build_raw_merge_unit_from_text(
                        rag,
                        text=unit["_content"],
                        doc_name=unit_doc_name,
                        file_path=file_path,
                        doc_id=unit["_doc_id"],
                        metadata=unit.get("metadata") or {},
                        source_group_key=_source_group_key_from_doc_name(unit_doc_name),
                        pipeline_status=pipeline_status,
                        pipeline_status_lock=pipeline_status_lock,
                        clean_input=False,
                    )
                    output_file.write(
                        json.dumps(
                            raw_merge_unit_to_json_obj(raw_unit),
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    output_file.flush()
                    seen_doc_ids.add(unit["_doc_id"])
                    stats["exported_units"] += 1
                except Exception as exc:
                    stats["failed_units"] += 1
                    logger.error(
                        "Unit export failed (continuing): chunk_index=%s type=%s err=%s",
                        chunk_index,
                        chunk_type,
                        exc,
                    )
                    _write_failure(
                        {
                            "pdf_file_path": str(PDF_PATH),
                            "md_path": str(MD_PATH),
                            "doc_name": unit_doc_name,
                            "file_path": file_path,
                            "chunk_index": chunk_index,
                            "chunk_type": chunk_type,
                            "doc_id": unit["_doc_id"],
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        }
                    )

        final_count = len(_load_existing_doc_ids(OUTPUT_JSONL))
        stats["final_units"] = final_count
        logger.info(
            "Resume finished: exported=%s failed=%s final_jsonl_units=%s failures=%s",
            stats["exported_units"],
            stats["failed_units"],
            final_count,
            FAILURES_JSONL if stats["failed_units"] else "none",
        )
        return stats
    finally:
        await _close_rag(rag)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report how many units are missing; do not call LLM/embed.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s:%(message)s",
    )

    stats = asyncio.run(_run(dry_run=args.dry_run))
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
