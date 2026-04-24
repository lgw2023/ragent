from __future__ import annotations

import argparse
import json
import shutil
import tarfile
import zipfile
from pathlib import Path


COMPONENT_FILES = (
    "process.py",
    "init.py",
    "config.json",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "run_mep_local.py",
    "mep_dependency_bootstrap.py",
)
COMPONENT_DIRS = ("ragent",)
IGNORE_NAMES = (
    "__pycache__",
    ".pytest_cache",
    ".DS_Store",
)
IGNORE_PATTERNS = (
    "*.pyc",
    "*.pyo",
)
ARCHIVE_FORMATS = {
    "zip": ("zip", ".zip"),
    "tar": ("tar", ".tar"),
    "tar.gz": ("gztar", ".tar.gz"),
    "tgz": ("gztar", ".tar.gz"),
    "gztar": ("gztar", ".tar.gz"),
}


def _ignore_generated(_directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in IGNORE_NAMES}
    for pattern in IGNORE_PATTERNS:
        if pattern.startswith("*."):
            suffix = pattern[1:]
            ignored.update(name for name in names if name.endswith(suffix))
    return ignored


def _reset_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)


def _copy_component_source(repo_root: Path, component_dir: Path) -> None:
    component_dir.mkdir(parents=True, exist_ok=True)
    for filename in COMPONENT_FILES:
        source = repo_root / filename
        if source.exists():
            shutil.copy2(source, component_dir / filename)
    for dirname in COMPONENT_DIRS:
        source = repo_root / dirname
        if source.exists():
            shutil.copytree(
                source,
                component_dir / dirname,
                ignore=_ignore_generated,
                dirs_exist_ok=True,
            )


def _link_or_copy(source: Path, target: Path, *, materialize: bool) -> None:
    if target.exists() or target.is_symlink():
        _reset_path(target)
    if materialize:
        shutil.copytree(source, target, ignore=_ignore_generated, symlinks=False)
        return
    target.symlink_to(source, target_is_directory=True)


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


def _default_archive_output(output: Path, archive_extension: str) -> Path:
    return output.with_name(output.name + archive_extension)


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _resolve_archive_output_path(
    *,
    runtime_root: Path,
    archive_extension: str,
    archive_output: Path | None,
) -> Path:
    archive_path = (
        archive_output.expanduser().resolve()
        if archive_output is not None
        else _default_archive_output(runtime_root, archive_extension)
    )
    if archive_path == runtime_root or _path_is_relative_to(archive_path, runtime_root):
        raise ValueError(
            "Archive output must be outside the runtime root to avoid archiving itself: "
            f"{archive_path}"
        )
    if archive_path.exists() and archive_path.is_dir() and not archive_path.is_symlink():
        raise ValueError(
            f"Archive output must be a file path, not a directory: {archive_path}"
        )
    return archive_path


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
            "MEP model/ must contain at least one Hugging Face model directory: "
            f"{model_root}"
        )

    invalid_children = [child for child in children if not child.is_dir()]
    if invalid_children:
        invalid_text = ", ".join(str(child) for child in invalid_children)
        raise ValueError(
            "MEP model/ top level must contain only Hugging Face model directories; "
            f"found non-directory entries: {invalid_text}"
        )


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


def _write_archive(
    *,
    runtime_root: Path,
    archive_format: str,
    archive_output: Path | None,
) -> Path:
    normalized_format, archive_extension = _normalize_archive_format(archive_format) or (
        "",
        "",
    )
    archive_path = _resolve_archive_output_path(
        runtime_root=runtime_root,
        archive_extension=archive_extension,
        archive_output=archive_output,
    )
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists() or archive_path.is_symlink():
        _reset_path(archive_path)

    if normalized_format == "zip":
        _write_zip_archive(runtime_root, archive_path)
    elif normalized_format == "tar":
        _write_tar_archive(runtime_root, archive_path, gzip=False)
    elif normalized_format == "gztar":
        _write_tar_archive(runtime_root, archive_path, gzip=True)
    else:
        raise ValueError(f"Unsupported archive format: {archive_format!r}")
    return archive_path


def build_mep_layout(
    *,
    repo_root: Path,
    model_package: str,
    output: Path,
    materialize: bool = False,
    archive_format: str | None = None,
    archive_output: Path | None = None,
) -> dict[str, str]:
    repo_root = repo_root.expanduser().resolve()
    output = output.expanduser().resolve()
    normalized_archive = _normalize_archive_format(archive_format)
    if normalized_archive is not None and not materialize:
        raise ValueError("Archive output requires materialize=True")
    if normalized_archive is not None:
        _resolve_archive_output_path(
            runtime_root=output,
            archive_extension=normalized_archive[1],
            archive_output=archive_output,
        )

    model_dir_root = (
        repo_root / "mep" / "model_packages" / model_package / "modelDir"
    )
    if not model_dir_root.is_dir():
        raise FileNotFoundError(f"MEP modelDir not found: {model_dir_root}")

    required_dirs = {
        "model": model_dir_root / "model",
        "data": model_dir_root / "data",
        "meta": model_dir_root / "meta",
    }
    for name, source in required_dirs.items():
        if not source.is_dir():
            raise FileNotFoundError(f"MEP {name}/ directory not found: {source}")
    _validate_model_root(required_dirs["model"])

    if output.exists() or output.is_symlink():
        _reset_path(output)
    output.mkdir(parents=True, exist_ok=True)

    component_dir = output / "component"
    _copy_component_source(repo_root, component_dir)
    for name, source in required_dirs.items():
        _link_or_copy(source, output / name, materialize=materialize)

    result = {
        "runtime_root": str(output),
        "component_dir": str(component_dir),
        "model_dir": str(output / "model"),
        "data_dir": str(output / "data"),
        "meta_dir": str(output / "meta"),
        "model_package_dir": str(model_dir_root),
        "layout_mode": "copy" if materialize else "symlink",
    }
    if normalized_archive is not None:
        archive_path = _write_archive(
            runtime_root=output,
            archive_format=archive_format or "",
            archive_output=archive_output,
        )
        result["archive_path"] = str(archive_path)
        result["archive_format"] = normalized_archive[0]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a local MEP-like runtime layout from this repository."
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
        help="Name under mep/model_packages/ to assemble.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output runtime root. Defaults to .mep_build/<model-package>/runtime.",
    )
    parser.add_argument(
        "--materialize",
        action="store_true",
        help="Copy model/data/meta instead of creating symlinks.",
    )
    parser.add_argument(
        "--archive-format",
        choices=sorted(ARCHIVE_FORMATS),
        help=(
            "Optionally write an archive of the assembled runtime. "
            "Requires --materialize."
        ),
    )
    parser.add_argument(
        "--archive-output",
        type=Path,
        help="Archive output path. Defaults beside --output using the selected extension.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else repo_root / ".mep_build" / args.model_package / "runtime"
    )
    result = build_mep_layout(
        repo_root=repo_root,
        model_package=args.model_package,
        output=output,
        materialize=args.materialize,
        archive_format=args.archive_format,
        archive_output=args.archive_output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
