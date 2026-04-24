from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tools.build_mep_layout import build_mep_layout


def _write_fake_repo(repo_root: Path) -> None:
    for filename in (
        "process.py",
        "init.py",
        "config.json",
        "package.json",
        "pyproject.toml",
        "setup.py",
        "run_mep_local.py",
        "mep_dependency_bootstrap.py",
    ):
        (repo_root / filename).write_text("# component file\n", encoding="utf-8")
    (repo_root / "ragent").mkdir()
    (repo_root / "ragent" / "__init__.py").write_text("", encoding="utf-8")

    model_dir = repo_root / "mep" / "model_packages" / "demo" / "modelDir"
    (model_dir / "model" / "hf_model").mkdir(parents=True)
    (model_dir / "model" / "hf_model" / "config.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (model_dir / "data" / "config").mkdir(parents=True)
    (model_dir / "data" / "config" / "embedding.properties").write_text(
        "model.relative_path=hf_model\n",
        encoding="utf-8",
    )
    (model_dir / "meta").mkdir()
    (model_dir / "meta" / "type.mf").write_text("model\n", encoding="utf-8")


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
    assert (output / "component" / "mep_dependency_bootstrap.py").exists()
    assert (output / "component" / "config.json").exists()
    assert (output / "component" / "ragent").is_dir()
    assert (output / "model").is_symlink()
    assert (output / "data").is_symlink()
    assert (output / "meta").is_symlink()
    assert (output / "model" / "baai_bge_m3" / "config.json").exists()
    assert (output / "data" / "config" / "embedding.properties").exists()
    assert (output / "data" / "kg" / "sample_kg").is_dir()


def test_build_mep_layout_materializes_and_archives_zip(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    output = tmp_path / "runtime"

    result = build_mep_layout(
        repo_root=repo_root,
        model_package="demo",
        output=output,
        materialize=True,
        archive_format="zip",
    )

    assert result["layout_mode"] == "copy"
    assert result["archive_format"] == "zip"
    archive_path = Path(result["archive_path"])
    assert archive_path == tmp_path / "runtime.zip"
    assert archive_path.exists()
    assert not (output / "model").is_symlink()
    assert (output / "component" / "mep_dependency_bootstrap.py").exists()

    with zipfile.ZipFile(archive_path) as zf:
        names = set(zf.namelist())
    assert "component/process.py" in names
    assert "component/mep_dependency_bootstrap.py" in names
    assert "model/hf_model/config.json" in names
    assert "data/config/embedding.properties" in names
    assert "meta/type.mf" in names


def test_build_mep_layout_archive_requires_materialize(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)

    with pytest.raises(ValueError, match="requires materialize=True"):
        build_mep_layout(
            repo_root=repo_root,
            model_package="demo",
            output=tmp_path / "runtime",
            archive_format="zip",
        )
