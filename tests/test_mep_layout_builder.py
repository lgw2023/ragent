from __future__ import annotations

import os
import tarfile
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


def test_build_mep_layout_materialize_dereferences_source_symlinks(tmp_path: Path):
    if not hasattr(os, "symlink"):
        pytest.skip("symlink is not available on this platform")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    output = tmp_path / "runtime"

    external_config = tmp_path / "external_config.json"
    external_config.write_text('{"source": "external"}\n', encoding="utf-8")
    model_config = (
        repo_root
        / "mep"
        / "model_packages"
        / "demo"
        / "modelDir"
        / "model"
        / "hf_model"
        / "config.json"
    )
    model_config.unlink()
    try:
        model_config.symlink_to(external_config)
    except OSError as exc:
        pytest.skip(f"symlink creation is not available: {exc}")

    build_mep_layout(
        repo_root=repo_root,
        model_package="demo",
        output=output,
        materialize=True,
    )

    materialized_config = output / "model" / "hf_model" / "config.json"
    assert not materialized_config.is_symlink()
    assert materialized_config.read_text(encoding="utf-8") == '{"source": "external"}\n'


@pytest.mark.parametrize(
    ("archive_format", "archive_name", "expected_result_format"),
    [
        ("tar", "runtime.tar", "tar"),
        ("tar.gz", "runtime.tar.gz", "gztar"),
    ],
)
def test_build_mep_layout_materializes_and_archives_tar_formats(
    tmp_path: Path,
    archive_format: str,
    archive_name: str,
    expected_result_format: str,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    output = tmp_path / "runtime"
    archive_output = tmp_path / archive_name

    result = build_mep_layout(
        repo_root=repo_root,
        model_package="demo",
        output=output,
        materialize=True,
        archive_format=archive_format,
        archive_output=archive_output,
    )

    assert result["layout_mode"] == "copy"
    assert result["archive_format"] == expected_result_format
    assert Path(result["archive_path"]) == archive_output.resolve()

    with tarfile.open(archive_output, "r:*") as tf:
        names = set(tf.getnames())
    assert "component/process.py" in names
    assert "component/mep_dependency_bootstrap.py" in names
    assert "model/hf_model/config.json" in names
    assert "data/config/embedding.properties" in names
    assert "meta/type.mf" in names
    assert not any(name.startswith("runtime/") for name in names)


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


def test_build_mep_layout_rejects_archive_output_inside_runtime_root(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    output = tmp_path / "runtime"

    with pytest.raises(ValueError, match="outside the runtime root"):
        build_mep_layout(
            repo_root=repo_root,
            model_package="demo",
            output=output,
            materialize=True,
            archive_format="zip",
            archive_output=output / "runtime.zip",
        )


def test_build_mep_layout_rejects_archive_output_existing_directory(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    archive_output = tmp_path / "existing_dir"
    archive_output.mkdir()
    marker = archive_output / "marker.txt"
    marker.write_text("keep\n", encoding="utf-8")

    with pytest.raises(ValueError, match="file path, not a directory"):
        build_mep_layout(
            repo_root=repo_root,
            model_package="demo",
            output=tmp_path / "runtime",
            materialize=True,
            archive_format="zip",
            archive_output=archive_output,
        )

    assert marker.read_text(encoding="utf-8") == "keep\n"


def test_build_mep_layout_rejects_model_root_top_level_files(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    model_root = repo_root / "mep" / "model_packages" / "demo" / "modelDir" / "model"
    (model_root / "sysconfig.properties").write_text("legacy=true\n", encoding="utf-8")

    with pytest.raises(ValueError, match="top level must contain only"):
        build_mep_layout(
            repo_root=repo_root,
            model_package="demo",
            output=tmp_path / "runtime",
        )
