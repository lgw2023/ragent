from __future__ import annotations

from pathlib import Path

from tools.build_mep_layout import build_mep_layout


def test_build_mep_layout_creates_platform_shaped_runtime(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    output = tmp_path / "runtime"

    result = build_mep_layout(
        repo_root=repo_root,
        model_package="bge-m3",
        output=output,
    )

    assert result["layout_mode"] == "symlink"
    assert (output / "component" / "process.py").exists()
    assert (output / "component" / "run_mep_local.py").exists()
    assert (output / "component" / "config.json").exists()
    assert (output / "component" / "ragent").is_dir()
    assert (output / "model").is_symlink()
    assert (output / "data").is_symlink()
    assert (output / "meta").is_symlink()
    assert (output / "model" / "baai_bge_m3" / "config.json").exists()
    assert (output / "data" / "config" / "embedding.properties").exists()
    assert (output / "data" / "kg" / "sample_kg").is_dir()
