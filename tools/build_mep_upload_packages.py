from __future__ import annotations

import argparse
import json
import shutil
import tarfile
import zipfile
from pathlib import Path


REQUIRED_COMPONENT_FILES = (
    "config.json",
    "package.json",
    "process.py",
    "init.py",
    "mep_dependency_bootstrap.py",
)
OPTIONAL_COMPONENT_FILES = (
    "pyproject.toml",
    "setup.py",
)
LOCAL_RUNNER_FILE = "run_mep_local.py"
COMPONENT_DIRS = ("ragent",)
COMPONENT_EXCLUDED_NAMES = {
    "tests",
    "example",
    "benchmark",
    "vendor",
    "presentation",
    "MEP_platform_rule",
    ".venv",
    ".git",
}
IGNORE_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".DS_Store",
}
IGNORE_PATTERNS = (
    "*.pyc",
    "*.pyo",
)
ARCHIVE_FORMATS = {
    "zip": ("zip", ".zip"),
    "tar": ("tar", ".tar"),
    "tar.gz": ("gztar", ".tar.gz"),
}


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _ignore_by_name(ignore_names: set[str], _directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in ignore_names}
    for pattern in IGNORE_PATTERNS:
        if pattern.startswith("*."):
            suffix = pattern[1:]
            ignored.update(name for name in names if name.endswith(suffix))
    return ignored


def _ignore_generated(_directory: str, names: list[str]) -> set[str]:
    return _ignore_by_name(IGNORE_NAMES, _directory, names)


def _ignore_component(_directory: str, names: list[str]) -> set[str]:
    return _ignore_by_name(
        IGNORE_NAMES | COMPONENT_EXCLUDED_NAMES,
        _directory,
        names,
    )


def _reset_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)


def _validate_component_source(repo_root: Path, *, include_local_runner: bool) -> None:
    missing: list[str] = []
    for filename in REQUIRED_COMPONENT_FILES:
        if not (repo_root / filename).is_file():
            missing.append(filename)
    if include_local_runner and not (repo_root / LOCAL_RUNNER_FILE).is_file():
        missing.append(LOCAL_RUNNER_FILE)
    for dirname in COMPONENT_DIRS:
        if not (repo_root / dirname).is_dir():
            missing.append(f"{dirname}/")
    if missing:
        missing_text = ", ".join(missing)
        raise FileNotFoundError(
            f"Missing required component package source paths: {missing_text}"
        )


def _visible_model_root_children(model_root: Path) -> list[Path]:
    return sorted(
        (
            child
            for child in model_root.iterdir()
            if not child.name.startswith(".") and child.name not in IGNORE_NAMES
        ),
        key=lambda item: item.name,
    )


def _validate_model_root(model_root: Path) -> None:
    children = _visible_model_root_children(model_root)
    if not children:
        raise FileNotFoundError(
            "MEP modelDir/model/ must contain at least one Hugging Face model "
            f"directory: {model_root}"
        )

    invalid_children = [child for child in children if not child.is_dir()]
    if invalid_children:
        invalid_text = ", ".join(str(child) for child in invalid_children)
        raise ValueError(
            "MEP modelDir/model/ top level must contain only Hugging Face model "
            f"directories; found non-directory entries: {invalid_text}"
        )


def _validate_model_dir(model_dir_root: Path) -> None:
    if not model_dir_root.is_dir():
        raise FileNotFoundError(f"MEP modelDir not found: {model_dir_root}")

    required_dirs = {
        "model": model_dir_root / "model",
        "data": model_dir_root / "data",
        "meta": model_dir_root / "meta",
    }
    for name, source in required_dirs.items():
        if not source.is_dir():
            raise FileNotFoundError(f"MEP modelDir/{name}/ not found: {source}")
    _validate_model_root(required_dirs["model"])


def _validate_safe_output(
    *,
    repo_root: Path,
    source_model_package_dir: Path,
    output: Path,
) -> None:
    if output == repo_root:
        raise ValueError(f"Output directory must not be the repository root: {output}")
    if output == repo_root.parent:
        raise ValueError(
            f"Output directory must not be the repository parent: {output}"
        )
    if _path_is_relative_to(source_model_package_dir, output):
        raise ValueError(
            "Output directory must not contain the source model package directory: "
            f"{output}"
        )
    if _path_is_relative_to(output, source_model_package_dir):
        raise ValueError(
            "Output directory must not be inside the source model package directory: "
            f"{output}"
        )


def _copy_component_source(
    repo_root: Path,
    component_dir: Path,
    *,
    include_local_runner: bool,
) -> None:
    component_dir.mkdir(parents=True, exist_ok=True)

    for filename in REQUIRED_COMPONENT_FILES + OPTIONAL_COMPONENT_FILES:
        source = repo_root / filename
        if source.exists():
            shutil.copy2(source, component_dir / filename)
    if include_local_runner:
        shutil.copy2(repo_root / LOCAL_RUNNER_FILE, component_dir / LOCAL_RUNNER_FILE)

    for dirname in COMPONENT_DIRS:
        source = repo_root / dirname
        shutil.copytree(
            source,
            component_dir / dirname,
            ignore=_ignore_component,
            symlinks=False,
            dirs_exist_ok=True,
        )


def _copy_model_package(model_dir_root: Path, model_package_dir: Path) -> None:
    model_package_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        model_dir_root,
        model_package_dir / "modelDir",
        ignore=_ignore_generated,
        symlinks=False,
        dirs_exist_ok=True,
    )


def _normalize_archive_format(archive_format: str | None) -> tuple[str, str] | None:
    if archive_format is None:
        return None
    normalized = archive_format.strip().lower()
    if not normalized:
        return None
    if normalized not in ARCHIVE_FORMATS:
        supported = " | ".join(sorted(ARCHIVE_FORMATS))
        raise ValueError(f"Unsupported archive format: {archive_format!r}. Use {supported}")
    return ARCHIVE_FORMATS[normalized]


def _safe_archive_stem(value: str, *, fallback: str) -> str:
    safe = "".join(
        char if char.isalnum() or char in {"-", "_", "."} else "-"
        for char in value.strip()
    ).strip(".-")
    return safe or fallback


def _component_archive_stem(repo_root: Path) -> str:
    fallback = "component_package"
    package_json = repo_root / "package.json"
    if not package_json.is_file():
        return fallback
    try:
        package_data = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback
    package_name = package_data.get("name")
    if not isinstance(package_name, str):
        return fallback
    return f"{_safe_archive_stem(package_name, fallback=fallback)}-component"


def _archive_members(root: Path) -> list[Path]:
    return sorted(
        root.rglob("*"),
        key=lambda item: item.relative_to(root).as_posix(),
    )


def _write_zip_archive(root: Path, archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in _archive_members(root):
            arcname = path.relative_to(root).as_posix()
            if path.is_dir():
                zf.writestr(arcname + "/", "")
            else:
                zf.write(path, arcname)


def _write_tar_archive(root: Path, archive_path: Path, *, gzip: bool) -> None:
    mode = "w:gz" if gzip else "w"
    with tarfile.open(archive_path, mode) as tf:
        for path in _archive_members(root):
            arcname = path.relative_to(root).as_posix()
            tf.add(path, arcname=arcname, recursive=False)


def _write_archive(root: Path, archive_path: Path, *, archive_format: str) -> Path:
    if archive_path.exists() or archive_path.is_symlink():
        _reset_path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    if archive_format == "zip":
        _write_zip_archive(root, archive_path)
    elif archive_format == "tar":
        _write_tar_archive(root, archive_path, gzip=False)
    elif archive_format == "gztar":
        _write_tar_archive(root, archive_path, gzip=True)
    else:
        raise ValueError(f"Unsupported archive format: {archive_format!r}")
    return archive_path


def build_mep_upload_packages(
    *,
    repo_root: Path,
    model_package: str,
    output: Path,
    include_local_runner: bool = False,
    archive_format: str | None = None,
) -> dict[str, str]:
    repo_root = repo_root.expanduser().resolve()
    output = output.expanduser().resolve()
    source_model_package_dir = (
        repo_root / "mep" / "model_packages" / model_package
    ).resolve()
    source_model_dir_root = source_model_package_dir / "modelDir"
    normalized_archive = _normalize_archive_format(archive_format)

    _validate_component_source(
        repo_root,
        include_local_runner=include_local_runner,
    )
    _validate_model_dir(source_model_dir_root)
    _validate_safe_output(
        repo_root=repo_root,
        source_model_package_dir=source_model_package_dir,
        output=output,
    )

    if output.exists() or output.is_symlink():
        _reset_path(output)
    output.mkdir(parents=True, exist_ok=True)

    component_dir = output / "component_package"
    model_upload_dir = output / "model_package"
    _copy_component_source(
        repo_root,
        component_dir,
        include_local_runner=include_local_runner,
    )
    _copy_model_package(source_model_dir_root, model_upload_dir)
    _validate_model_dir(model_upload_dir / "modelDir")

    result = {
        "output_root": str(output),
        "component_package_dir": str(component_dir),
        "model_package_dir": str(model_upload_dir),
        "model_dir_root": str(model_upload_dir / "modelDir"),
        "source_model_package_dir": str(source_model_package_dir),
    }
    if normalized_archive is not None:
        archive_name, archive_extension = normalized_archive
        component_archive_path = (
            output / f"{_component_archive_stem(repo_root)}{archive_extension}"
        )
        model_archive_path = (
            output
            / f"{_safe_archive_stem(model_package, fallback='model_package')}-model"
            f"{archive_extension}"
        )
        _write_archive(
            component_dir,
            component_archive_path,
            archive_format=archive_name,
        )
        _write_archive(
            model_upload_dir,
            model_archive_path,
            archive_format=archive_name,
        )
        result["archive_format"] = archive_name
        result["component_archive_path"] = str(component_archive_path)
        result["model_archive_path"] = str(model_archive_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build MEP upload-ready component and model package directories."
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Repository root. Defaults to the parent of tools/.",
    )
    parser.add_argument(
        "--model-package",
        default="bge-m3",
        help="Name under mep/model_packages/ to package.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output root. Defaults to .mep_upload/<model-package>/.",
    )
    parser.add_argument(
        "--include-local-runner",
        action="store_true",
        help="Include run_mep_local.py in the component upload package.",
    )
    parser.add_argument(
        "--archive-format",
        choices=sorted(ARCHIVE_FORMATS),
        help="Optionally archive component_package and model_package separately.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else repo_root / ".mep_upload" / args.model_package
    )
    result = build_mep_upload_packages(
        repo_root=repo_root,
        model_package=args.model_package,
        output=output,
        include_local_runner=args.include_local_runner,
        archive_format=args.archive_format,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
