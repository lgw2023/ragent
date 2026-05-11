from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from tools import export_mep_transformers_embedding_wheelhouse as exporter


def test_exporter_regenerates_constraints_from_existing_wheelhouse(tmp_path: Path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("litellm\n", encoding="utf-8")
    baseline_constraints = tmp_path / "baseline.txt"
    baseline_constraints.write_text(
        "numpy==1.26.4\ntokenizers==0.21.4\n",
        encoding="utf-8",
    )
    output = tmp_path / "wheelhouse"
    output.mkdir()
    (output / "litellm-1.83.0-py3-none-any.whl").write_bytes(b"fake")
    (output / "tiktoken-0.12.0-cp39-cp39-manylinux_2_28_aarch64.whl").write_bytes(
        b"fake"
    )
    constraints = tmp_path / "constraints.txt"

    manifest = exporter.export_wheelhouse(
        SimpleNamespace(
            requirements=requirements,
            baseline_constraints=baseline_constraints,
            constraints=constraints,
            output=output,
            clean=False,
            no_download=True,
            implementation="cp",
            python_version="39",
            platforms=("manylinux2014_aarch64",),
            abis=("cp39",),
            index_url=None,
            extra_index_url=[],
            timeout_seconds=30,
        )
    )

    constraints_text = constraints.read_text(encoding="utf-8")
    assert "litellm==1.83.0" in constraints_text
    assert "numpy==1.26.4" in constraints_text
    assert "tiktoken==0.12.0" in constraints_text
    assert manifest.wheel_count == 2
    assert (output / "manifest.json").is_file()
    assert (output / "downloaded-wheels.txt").is_file()
