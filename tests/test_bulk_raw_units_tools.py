from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from ragent.offline_replay import (
    RawMergeUnit,
    iter_raw_merge_units_jsonl,
    write_raw_merge_units_jsonl,
)
from ragent.utils import compute_mdhash_id, get_content_summary
from tools import export_raw_merge_units
from tools.merge_raw_units_canonical import merge_raw_units_canonical


def _raw_unit(doc_id: str, *, source_group_key: str) -> RawMergeUnit:
    content = f"{doc_id} content"
    return RawMergeUnit(
        doc_id=doc_id,
        doc_name=f"{doc_id}.md",
        file_path=f"/docs/{doc_id}.md",
        source_group_key=source_group_key,
        content=content,
        content_summary=get_content_summary(content),
        metadata={"file_path": f"/docs/{doc_id}.md"},
        chunks={},
        chunk_results=[],
    )


def _jsonl_lines(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_merge_raw_units_canonical_prefixes_source_group_keys(tmp_path: Path):
    pdf_units = tmp_path / "pdf.raw-units.jsonl"
    other_units = tmp_path / "other.raw-units.jsonl"
    output = tmp_path / "all.raw-units.jsonl"

    write_raw_merge_units_jsonl([_raw_unit("doc-a", source_group_key="paper")], pdf_units)
    write_raw_merge_units_jsonl(
        [_raw_unit("doc-b", source_group_key="paper")], other_units
    )

    stats = merge_raw_units_canonical(
        [f"pdf={pdf_units}", f"other={other_units}"],
        output,
    )

    merged = list(iter_raw_merge_units_jsonl(output))
    assert stats.input_units == 2
    assert stats.output_units == 2
    assert [unit.source_group_key for unit in merged] == ["pdf:paper", "other:paper"]


def test_merge_raw_units_canonical_can_dedupe_doc_ids(tmp_path: Path):
    first = tmp_path / "first.raw-units.jsonl"
    second = tmp_path / "second.raw-units.jsonl"
    output = tmp_path / "deduped.raw-units.jsonl"

    write_raw_merge_units_jsonl([_raw_unit("doc-a", source_group_key="a")], first)
    write_raw_merge_units_jsonl([_raw_unit("doc-a", source_group_key="b")], second)

    stats = merge_raw_units_canonical(
        [f"first={first}", f"second={second}"],
        output,
        dedupe_doc_ids=True,
    )

    merged = list(iter_raw_merge_units_jsonl(output))
    assert stats.input_units == 2
    assert stats.output_units == 1
    assert stats.skipped_duplicate_doc_ids == 1
    assert merged[0].source_group_key == "first:a"


def test_export_raw_merge_units_resume_skips_existing_doc_ids(
    tmp_path: Path, monkeypatch
):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    (input_dir / "a.md").write_text("alpha", encoding="utf-8")
    (input_dir / "b.md").write_text("beta", encoding="utf-8")

    class FakeRagent:
        def __init__(self, **_kwargs):
            pass

        async def initialize_storages(self):
            return None

        async def finalize_storages(self):
            return None

    async def fake_export_one_file(
        _rag,
        path: Path,
        *,
        content: str | None = None,
        doc_id: str | None = None,
        split_by_character: str | None = None,
        split_by_character_only: bool = False,
    ) -> RawMergeUnit:
        resolved_content = content or path.read_text(encoding="utf-8")
        resolved_doc_id = doc_id or compute_mdhash_id(resolved_content, prefix="doc-")
        return RawMergeUnit(
            doc_id=resolved_doc_id,
            doc_name=path.name,
            file_path=str(path),
            source_group_key=path.stem,
            content=resolved_content,
            content_summary=get_content_summary(resolved_content),
            metadata={"file_path": str(path)},
            chunks={},
            chunk_results=[],
        )

    monkeypatch.setattr(export_raw_merge_units, "Ragent", FakeRagent)
    monkeypatch.setattr(export_raw_merge_units, "_export_one_file", fake_export_one_file)

    output = tmp_path / "raw-units.jsonl"
    progress = tmp_path / "progress.ndjson"
    successes = tmp_path / "successes.ndjson"

    def args(*, resume: bool) -> argparse.Namespace:
        return argparse.Namespace(
            inputs=[str(input_dir)],
            output=str(output),
            glob="*.md",
            recursive=False,
            llm_model="fake-model",
            split_by_character=None,
            split_by_character_only=False,
            continue_on_error=False,
            failures_output=None,
            resume=resume,
            flush_each_unit=True,
            progress_output=str(progress),
            successes_output=str(successes),
        )

    first_stats = asyncio.run(
        export_raw_merge_units._run_with_working_dir(args(resume=False), tmp_path / "work1")
    )
    assert first_stats["exported_units"] == 2
    assert len(_jsonl_lines(output)) == 2
    output.write_text(output.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")

    (input_dir / "c.md").write_text("gamma", encoding="utf-8")
    second_stats = asyncio.run(
        export_raw_merge_units._run_with_working_dir(args(resume=True), tmp_path / "work2")
    )

    assert second_stats["preexisting_units"] == 2
    assert second_stats["skipped_existing"] == 2
    assert second_stats["exported_units"] == 1
    assert len(_jsonl_lines(output)) == 3
    assert len(_jsonl_lines(successes)) == 3
    assert "skipped_existing" in {record["status"] for record in _jsonl_lines(progress)}
