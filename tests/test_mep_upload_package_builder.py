from __future__ import annotations

import shutil
import tarfile
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from tools.build_mep_upload_packages import build_mep_upload_packages


def _write_fake_repo(repo_root: Path) -> None:
    files = {
        "config.json": '{"main_file": "process", "main_class": "CustomerModel"}\n',
        "package.json": (
            '{"scope": "demo", "version": "1", "type": "aiexplore", '
            '"name": "ragent_inference_mep"}\n'
        ),
        "process.py": "class CustomerModel:\n    pass\n",
        "init.py": "# init\n",
        "mep_dependency_bootstrap.py": "# bootstrap\n",
        "pyproject.toml": "[project]\nname = \"ragent\"\n",
        "setup.py": "from setuptools import setup\nsetup()\n",
        "run_mep_local.py": "# local runner\n",
    }
    for filename, contents in files.items():
        (repo_root / filename).write_text(contents, encoding="utf-8")

    (repo_root / "ragent").mkdir()
    (repo_root / "ragent" / "__init__.py").write_text("", encoding="utf-8")

    for excluded_dir in (
        "tests",
        "example",
        "benchmark",
        "vendor",
        "presentation",
        "MEP_platform_rule",
        ".venv",
        ".git",
    ):
        path = repo_root / excluded_dir
        path.mkdir()
        (path / "marker.txt").write_text("exclude\n", encoding="utf-8")

    model_dir = repo_root / "mep" / "model_packages" / "demo" / "modelDir"
    (model_dir / "model").mkdir(parents=True)
    (model_dir / "model" / "config.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    (model_dir / "model" / "tokenizer.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    (model_dir / "model" / "pytorch_model.bin").write_bytes(b"fake weights")
    (model_dir / "model" / "1_Pooling").mkdir()
    (model_dir / "model" / "1_Pooling" / "config.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    (model_dir / "data" / "config").mkdir(parents=True)
    (model_dir / "data" / "config" / "embedding.properties").write_text(
        "model.relative_path=.\n",
        encoding="utf-8",
    )
    wheelhouse = model_dir / "data" / "deps" / "wheelhouse" / "linux-arm64-py3.10"
    wheelhouse.mkdir(parents=True)
    (wheelhouse / "demo_dep-1.0.0-py3-none-any.whl").write_bytes(b"fake wheel")
    (wheelhouse / "demo_sdist-1.0.0.tar.gz").write_bytes(b"fake sdist")
    (model_dir / "meta").mkdir()
    (model_dir / "meta" / "type.mf").write_text("model\n", encoding="utf-8")


def test_build_mep_upload_packages_creates_upload_directories(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    output = tmp_path / "upload"

    result = build_mep_upload_packages(
        repo_root=repo_root,
        model_package="demo",
        output=output,
    )

    component_dir = output / "component_package"
    model_package_dir = output / "model_package"
    assert Path(result["component_package_dir"]) == component_dir.resolve()
    assert Path(result["model_package_dir"]) == model_package_dir.resolve()

    for filename in (
        "config.json",
        "package.json",
        "process.py",
        "init.py",
        "mep_dependency_bootstrap.py",
        "pyproject.toml",
        "setup.py",
    ):
        assert (component_dir / filename).is_file()
    assert (component_dir / "ragent" / "__init__.py").is_file()
    assert not (component_dir / "run_mep_local.py").exists()

    for excluded_dir in (
        "tests",
        "example",
        "benchmark",
        "vendor",
        "presentation",
        "MEP_platform_rule",
        ".venv",
        ".git",
    ):
        assert not (component_dir / excluded_dir).exists()

    assert [path.name for path in model_package_dir.iterdir()] == ["modelDir"]
    assert (model_package_dir / "modelDir" / "model" / "config.json").is_file()
    assert (model_package_dir / "modelDir" / "model" / "tokenizer.json").is_file()
    assert (model_package_dir / "modelDir" / "model" / "pytorch_model.bin").is_file()
    assert (
        model_package_dir / "modelDir" / "model" / "1_Pooling" / "config.json"
    ).is_file()
    assert (model_package_dir / "modelDir" / "data" / "config").is_dir()
    assert (
        model_package_dir
        / "modelDir"
        / "data"
        / "deps"
        / "wheelhouse"
        / "linux-arm64-py3.10"
        / "demo_dep-1.0.0-py3-none-any.whl"
    ).is_file()
    assert (
        model_package_dir
        / "modelDir"
        / "data"
        / "deps"
        / "wheelhouse"
        / "linux-arm64-py3.10"
        / "demo_sdist-1.0.0.tar.gz"
    ).is_file()
    assert (model_package_dir / "modelDir" / "meta" / "type.mf").is_file()
    assert not (model_package_dir / "modelDir" / "model").is_symlink()


def test_build_mep_upload_packages_can_include_local_runner(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)

    build_mep_upload_packages(
        repo_root=repo_root,
        model_package="demo",
        output=tmp_path / "upload",
        include_local_runner=True,
    )

    assert (tmp_path / "upload" / "component_package" / "run_mep_local.py").is_file()


def test_build_mep_upload_packages_filters_generated_files(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)

    (repo_root / "ragent" / "__pycache__").mkdir()
    (repo_root / "ragent" / "__pycache__" / "module.pyc").write_bytes(b"cached")
    (repo_root / "ragent" / ".DS_Store").write_text("finder\n", encoding="utf-8")
    (repo_root / "ragent" / ".pytest_cache").mkdir()
    (repo_root / "ragent" / ".pytest_cache" / "cache.txt").write_text(
        "cache\n",
        encoding="utf-8",
    )
    model_root = repo_root / "mep" / "model_packages" / "demo" / "modelDir"
    (model_root / "data" / ".DS_Store").write_text("finder\n", encoding="utf-8")
    (model_root / "model" / "__pycache__").mkdir()
    (model_root / "model" / "__pycache__" / "x.pyc").write_bytes(b"cached")
    (model_root / "model" / "x.pyo").write_bytes(b"optimized")

    build_mep_upload_packages(
        repo_root=repo_root,
        model_package="demo",
        output=tmp_path / "upload",
    )

    output = tmp_path / "upload"
    assert not (output / "component_package" / "ragent" / "__pycache__").exists()
    assert not (output / "component_package" / "ragent" / ".DS_Store").exists()
    assert not (output / "component_package" / "ragent" / ".pytest_cache").exists()
    assert not (output / "model_package" / "modelDir" / "data" / ".DS_Store").exists()
    assert not (
        output
        / "model_package"
        / "modelDir"
        / "model"
        / "__pycache__"
    ).exists()
    assert not (output / "model_package" / "modelDir" / "model" / "x.pyo").exists()


def test_build_mep_upload_packages_rejects_missing_component_file(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    (repo_root / "process.py").unlink()

    with pytest.raises(FileNotFoundError, match="process.py"):
        build_mep_upload_packages(
            repo_root=repo_root,
            model_package="demo",
            output=tmp_path / "upload",
        )


@pytest.mark.parametrize("missing_dir", ["model", "data", "meta"])
def test_build_mep_upload_packages_rejects_missing_model_dir(
    tmp_path: Path,
    missing_dir: str,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    model_dir = repo_root / "mep" / "model_packages" / "demo" / "modelDir"
    shutil.rmtree(model_dir / missing_dir)

    with pytest.raises(FileNotFoundError, match=f"modelDir/{missing_dir}/"):
        build_mep_upload_packages(
            repo_root=repo_root,
            model_package="demo",
            output=tmp_path / "upload",
        )


def test_build_mep_upload_packages_rejects_nested_model_directory(
    tmp_path: Path,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    model_root = repo_root / "mep" / "model_packages" / "demo" / "modelDir" / "model"
    for child in tuple(model_root.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    nested_model = model_root / "hf_model"
    nested_model.mkdir()
    (nested_model / "config.json").write_text("{}\n", encoding="utf-8")
    (nested_model / "tokenizer.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="directly contain Hugging Face model files"):
        build_mep_upload_packages(
            repo_root=repo_root,
            model_package="demo",
            output=tmp_path / "upload",
        )


@pytest.mark.parametrize(
    ("output_factory", "expected_match"),
    [
        (lambda repo_root: repo_root, "repository root"),
        (lambda repo_root: repo_root.parent, "repository parent"),
        (lambda repo_root: repo_root / "mep", "contain the source model package"),
        (lambda repo_root: repo_root / "ragent", "component source directory"),
        (lambda repo_root: repo_root / "config.json", "component source file"),
        (
            lambda repo_root: repo_root
            / "mep"
            / "model_packages"
            / "demo"
            / "nested",
            "inside the source model package",
        ),
    ],
)
def test_build_mep_upload_packages_rejects_dangerous_output(
    tmp_path: Path,
    output_factory: Callable[[Path], Path],
    expected_match: str,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    marker = repo_root / "config.json"
    original_config = marker.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match=expected_match):
        build_mep_upload_packages(
            repo_root=repo_root,
            model_package="demo",
            output=output_factory(repo_root),
        )

    assert marker.read_text(encoding="utf-8") == original_config
    assert (repo_root / "ragent" / "__init__.py").is_file()


def test_build_mep_upload_packages_rejects_missing_type_mf(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    type_mf = (
        repo_root
        / "mep"
        / "model_packages"
        / "demo"
        / "modelDir"
        / "meta"
        / "type.mf"
    )
    type_mf.unlink()

    with pytest.raises(FileNotFoundError, match="meta/type.mf"):
        build_mep_upload_packages(
            repo_root=repo_root,
            model_package="demo",
            output=tmp_path / "upload",
        )


def test_build_mep_upload_packages_rejects_empty_type_mf(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    type_mf = (
        repo_root
        / "mep"
        / "model_packages"
        / "demo"
        / "modelDir"
        / "meta"
        / "type.mf"
    )
    type_mf.write_text("  \n", encoding="utf-8")

    with pytest.raises(ValueError, match="type.mf must not be empty"):
        build_mep_upload_packages(
            repo_root=repo_root,
            model_package="demo",
            output=tmp_path / "upload",
        )


def test_build_mep_upload_packages_archives_zip_with_upload_shapes(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)

    result = build_mep_upload_packages(
        repo_root=repo_root,
        model_package="demo",
        output=tmp_path / "upload",
        archive_format="zip",
    )

    assert result["archive_format"] == "zip"
    component_archive = Path(result["component_archive_path"])
    model_archive = Path(result["model_archive_path"])
    assert component_archive.name == "ragent_inference_mep-component.zip"
    assert model_archive.name == "demo-model.zip"

    with zipfile.ZipFile(component_archive) as zf:
        component_names = set(zf.namelist())
    assert "config.json" in component_names
    assert "process.py" in component_names
    assert "mep_dependency_bootstrap.py" in component_names
    assert "ragent/__init__.py" in component_names
    assert not any(name.startswith("component_package/") for name in component_names)

    with zipfile.ZipFile(model_archive) as zf:
        model_names = set(zf.namelist())
    assert "modelDir/" in model_names
    assert "modelDir/model/config.json" in model_names
    assert "modelDir/model/tokenizer.json" in model_names
    assert "modelDir/model/pytorch_model.bin" in model_names
    assert "modelDir/model/1_Pooling/config.json" in model_names
    assert "modelDir/data/config/embedding.properties" in model_names
    assert (
        "modelDir/data/deps/wheelhouse/linux-arm64-py3.10/"
        "demo_dep-1.0.0-py3-none-any.whl"
    ) in model_names
    assert (
        "modelDir/data/deps/wheelhouse/linux-arm64-py3.10/"
        "demo_sdist-1.0.0.tar.gz"
    ) in model_names
    assert "modelDir/meta/type.mf" in model_names
    assert not any(name.startswith("model_package/") for name in model_names)


def test_build_mep_upload_packages_archives_to_custom_output_dir(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    archive_output_dir = tmp_path / "archives"

    result = build_mep_upload_packages(
        repo_root=repo_root,
        model_package="demo",
        output=tmp_path / "upload",
        archive_format="zip",
        archive_output_dir=archive_output_dir,
    )

    assert Path(result["archive_output_dir"]) == archive_output_dir.resolve()
    assert Path(result["component_archive_path"]).parent == archive_output_dir.resolve()
    assert Path(result["model_archive_path"]).parent == archive_output_dir.resolve()
    assert Path(result["component_archive_path"]).is_file()
    assert Path(result["model_archive_path"]).is_file()
    assert not (tmp_path / "upload" / "ragent_inference_mep-component.zip").exists()
    assert not (tmp_path / "upload" / "demo-model.zip").exists()


def test_build_mep_upload_packages_rejects_archive_output_dir_without_format(
    tmp_path: Path,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)

    with pytest.raises(ValueError, match="requires archive_format"):
        build_mep_upload_packages(
            repo_root=repo_root,
            model_package="demo",
            output=tmp_path / "upload",
            archive_output_dir=tmp_path / "archives",
        )


def test_build_mep_upload_packages_rejects_archive_output_dir_file(
    tmp_path: Path,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    archive_output_dir = tmp_path / "archives"
    archive_output_dir.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(ValueError, match="directory path"):
        build_mep_upload_packages(
            repo_root=repo_root,
            model_package="demo",
            output=tmp_path / "upload",
            archive_format="zip",
            archive_output_dir=archive_output_dir,
        )


def test_build_mep_upload_packages_rejects_archive_output_inside_component_package(
    tmp_path: Path,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    output = tmp_path / "upload"
    output.mkdir()
    marker = output / "marker.txt"
    marker.write_text("keep\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside the component package"):
        build_mep_upload_packages(
            repo_root=repo_root,
            model_package="demo",
            output=output,
            archive_format="zip",
            archive_output_dir=output / "component_package",
        )

    assert marker.read_text(encoding="utf-8") == "keep\n"


def test_build_mep_upload_packages_rejects_archive_output_inside_model_package(
    tmp_path: Path,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    output = tmp_path / "upload"
    output.mkdir()
    marker = output / "marker.txt"
    marker.write_text("keep\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside the model package"):
        build_mep_upload_packages(
            repo_root=repo_root,
            model_package="demo",
            output=output,
            archive_format="zip",
            archive_output_dir=output / "model_package",
        )

    assert marker.read_text(encoding="utf-8") == "keep\n"


def test_build_mep_upload_packages_rejects_archive_output_inside_source_package(
    tmp_path: Path,
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)
    output = tmp_path / "upload"
    output.mkdir()
    marker = output / "marker.txt"
    marker.write_text("keep\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Archive output directory must not be inside the source model package",
    ):
        build_mep_upload_packages(
            repo_root=repo_root,
            model_package="demo",
            output=output,
            archive_format="zip",
            archive_output_dir=repo_root / "mep" / "model_packages" / "demo" / "archives",
        )

    assert marker.read_text(encoding="utf-8") == "keep\n"


def test_build_mep_upload_packages_archives_tgz_alias(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_fake_repo(repo_root)

    result = build_mep_upload_packages(
        repo_root=repo_root,
        model_package="demo",
        output=tmp_path / "upload",
        archive_format="tgz",
    )

    assert result["archive_format"] == "gztar"
    component_archive = Path(result["component_archive_path"])
    model_archive = Path(result["model_archive_path"])
    assert component_archive.name == "ragent_inference_mep-component.tar.gz"
    assert model_archive.name == "demo-model.tar.gz"

    with tarfile.open(component_archive, "r:*") as tf:
        component_names = set(tf.getnames())
    assert "config.json" in component_names
    assert "ragent/__init__.py" in component_names

    with tarfile.open(model_archive, "r:*") as tf:
        model_names = set(tf.getnames())
    assert "modelDir/model/config.json" in model_names
    assert "modelDir/model/tokenizer.json" in model_names
    assert "modelDir/model/pytorch_model.bin" in model_names
    assert (
        "modelDir/data/deps/wheelhouse/linux-arm64-py3.10/"
        "demo_sdist-1.0.0.tar.gz"
    ) in model_names
    assert not any(name.startswith("model_package/") for name in model_names)
