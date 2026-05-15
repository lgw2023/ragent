from __future__ import annotations

import asyncio
from contextlib import nullcontext
from pathlib import Path

import integrations


def test_resolve_generated_output_file_can_use_single_actual_markdown(tmp_path: Path):
    actual_md = tmp_path / "generated.by.mineru.md"
    actual_md.write_text("# ready\n", encoding="utf-8")

    resolved = integrations._resolve_generated_output_file(
        str(tmp_path),
        "expected.name.md",
        suffix=".md",
    )

    assert resolved == str(actual_md)


class _DummyProgressTracker:
    enabled = False

    def start_estimated_phase(self, *args, **kwargs):
        return None

    def update(self, *args, **kwargs):
        return None

    def finish(self, *args, **kwargs):
        return None

    def fail(self, *args, **kwargs):
        return None


def test_build_enhanced_md_uses_full_pdf_stem_for_multi_dot_names(monkeypatch, tmp_path: Path):
    async def fake_startup_model_check_once():
        return None

    def fake_mineru_process(pdf_file_path, mineru_output_dir, keep_pdf_subdir=True):
        pdf_outdir = Path(mineru_output_dir) / "txt"
        pdf_outdir.mkdir(parents=True, exist_ok=True)
        pdf_stem = Path(pdf_file_path).stem
        (pdf_outdir / f"{pdf_stem}.md").write_text("# ready\n", encoding="utf-8")
        (pdf_outdir / f"{pdf_stem}_content_list.json").write_text("[]", encoding="utf-8")
        return str(pdf_outdir)

    monkeypatch.setattr(
        integrations,
        "ensure_startup_model_check_once",
        fake_startup_model_check_once,
    )
    monkeypatch.setattr(integrations, "mineru_process", fake_mineru_process)
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
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        integrations,
        "_print_md_ready_banner",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        integrations,
        "_TerminalProgressTracker",
        lambda *args, **kwargs: _DummyProgressTracker(),
    )

    pdf_path = tmp_path / "WHO_NMH_NHD_13.1_chi.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    mineru_output_dir = tmp_path / "WHO_NMH_NHD_13.1_chi_md"

    artifacts = asyncio.run(
        integrations.build_enhanced_md(
            str(pdf_path),
            str(mineru_output_dir),
            keep_pdf_subdir=False,
        )
    )

    assert Path(artifacts["md_path"]).name == "WHO_NMH_NHD_13.1_chi.md"
    assert Path(artifacts["content_list_path"]).name == "WHO_NMH_NHD_13.1_chi_content_list.json"
