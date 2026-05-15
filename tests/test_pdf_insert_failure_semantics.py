from __future__ import annotations

import asyncio
from contextlib import nullcontext
from pathlib import Path

import pytest

import integrations


def _patch_pdf_insert_prelude(monkeypatch, tmp_path: Path) -> list[str]:
    progress_events: list[str] = []

    async def fake_startup_model_check_once():
        return None

    async def fake_build_enhanced_md(*args, **kwargs):
        md_path = tmp_path / "doc.md"
        md_path.write_text("ready", encoding="utf-8")
        return {
            "md_path": str(md_path),
            "pdf_outdir": str(tmp_path),
            "content_list_path": None,
        }

    monkeypatch.setattr(
        integrations,
        "ensure_startup_model_check_once",
        fake_startup_model_check_once,
    )
    monkeypatch.setattr(integrations, "build_enhanced_md", fake_build_enhanced_md)
    monkeypatch.setattr(
        integrations,
        "_maybe_create_usage_collector",
        lambda label: nullcontext(None),
    )
    monkeypatch.setattr(
        integrations,
        "_write_usage_report_if_needed",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        integrations,
        "_print_pipeline_progress",
        lambda stage, **kwargs: progress_events.append(stage),
    )
    return progress_events


def test_pdf_insert_raises_when_rag_indexing_times_out(monkeypatch, tmp_path: Path):
    progress_events = _patch_pdf_insert_prelude(monkeypatch, tmp_path)

    async def fake_index_md_to_rag(*args, **kwargs):
        await asyncio.sleep(60)

    monkeypatch.setattr(integrations, "index_md_to_rag", fake_index_md_to_rag)
    monkeypatch.setenv("RAG_INDEX_TIMEOUT_SECONDS", "0")

    with pytest.raises(RuntimeError, match="RAG indexing timeout"):
        asyncio.run(
            integrations.pdf_insert(
                "input.pdf",
                str(tmp_path / "mineru"),
                str(tmp_path / "kg"),
            )
        )

    assert "rag_index_timeout" in progress_events


def test_pdf_insert_raises_when_rag_indexing_fails(monkeypatch, tmp_path: Path):
    progress_events = _patch_pdf_insert_prelude(monkeypatch, tmp_path)

    async def fake_index_md_to_rag(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(integrations, "index_md_to_rag", fake_index_md_to_rag)
    monkeypatch.setenv("RAG_INDEX_TIMEOUT_SECONDS", "30")

    with pytest.raises(RuntimeError, match="RAG indexing failed") as exc_info:
        asyncio.run(
            integrations.pdf_insert(
                "input.pdf",
                str(tmp_path / "mineru"),
                str(tmp_path / "kg"),
            )
        )

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert "rag_index_failed" in progress_events
