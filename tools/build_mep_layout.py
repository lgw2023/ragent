from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

try:
    from tools.mep_package_utils import (
        ARCHIVE_FORMATS,
        ignore_generated,
        normalize_archive_format,
        reset_path,
        resolve_archive_output_path,
        validate_model_dir,
        write_archive,
    )
except ModuleNotFoundError:
    from mep_package_utils import (
        ARCHIVE_FORMATS,
        ignore_generated,
        normalize_archive_format,
        reset_path,
        resolve_archive_output_path,
        validate_model_dir,
        write_archive,
    )

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
                ignore=ignore_generated,
                dirs_exist_ok=True,
            )


def _link_or_copy(source: Path, target: Path, *, materialize: bool) -> None:
    if target.exists() or target.is_symlink():
        reset_path(target)
    if materialize:
        shutil.copytree(source, target, ignore=ignore_generated, symlinks=False)
        return
    target.symlink_to(source, target_is_directory=True)


def _resolve_archive_output_path(
    *,
    runtime_root: Path,
    archive_extension: str,
    archive_output: Path | None,
) -> Path:
    return resolve_archive_output_path(
        source_root=runtime_root,
        archive_extension=archive_extension,
        archive_output=archive_output,
        source_label="runtime root",
    )


def _write_archive(
    *,
    runtime_root: Path,
    archive_format: str,
    archive_output: Path | None,
) -> Path:
    normalized_format, archive_extension = normalize_archive_format(archive_format) or (
        "",
        "",
    )
    archive_path = _resolve_archive_output_path(
        runtime_root=runtime_root,
        archive_extension=archive_extension,
        archive_output=archive_output,
    )
    return write_archive(runtime_root, archive_path, archive_format=normalized_format)


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
    normalized_archive = normalize_archive_format(archive_format)
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
    validate_model_dir(
        model_dir_root,
        required_dir_label="MEP {name}/ directory",
        model_root_label="MEP model/",
    )

    required_dirs = {
        "model": model_dir_root / "model",
        "data": model_dir_root / "data",
        "meta": model_dir_root / "meta",
    }

    if output.exists() or output.is_symlink():
        reset_path(output)
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
