from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

try:
    from tools.mep_package_utils import (
        ARCHIVE_FORMATS,
        IGNORE_NAMES,
        ignore_by_name,
        ignore_generated,
        normalize_archive_format,
        path_is_relative_to,
        reset_path,
        safe_archive_stem,
        validate_model_dir,
        write_archive,
    )
except ModuleNotFoundError:
    from mep_package_utils import (
        ARCHIVE_FORMATS,
        IGNORE_NAMES,
        ignore_by_name,
        ignore_generated,
        normalize_archive_format,
        path_is_relative_to,
        reset_path,
        safe_archive_stem,
        validate_model_dir,
        write_archive,
    )

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


def _ignore_component(_directory: str, names: list[str]) -> set[str]:
    return ignore_by_name(
        IGNORE_NAMES | COMPONENT_EXCLUDED_NAMES,
        _directory,
        names,
    )


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
    if path_is_relative_to(source_model_package_dir, output):
        raise ValueError(
            "Output directory must not contain the source model package directory: "
            f"{output}"
        )
    if path_is_relative_to(output, source_model_package_dir):
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
        ignore=ignore_generated,
        symlinks=False,
        dirs_exist_ok=True,
    )


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
    return f"{safe_archive_stem(package_name, fallback=fallback)}-component"


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
    normalized_archive = normalize_archive_format(archive_format)

    _validate_component_source(
        repo_root,
        include_local_runner=include_local_runner,
    )
    validate_model_dir(source_model_dir_root)
    _validate_safe_output(
        repo_root=repo_root,
        source_model_package_dir=source_model_package_dir,
        output=output,
    )

    if output.exists() or output.is_symlink():
        reset_path(output)
    output.mkdir(parents=True, exist_ok=True)

    component_dir = output / "component_package"
    model_upload_dir = output / "model_package"
    _copy_component_source(
        repo_root,
        component_dir,
        include_local_runner=include_local_runner,
    )
    _copy_model_package(source_model_dir_root, model_upload_dir)
    validate_model_dir(model_upload_dir / "modelDir")

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
            / f"{safe_archive_stem(model_package, fallback='model_package')}-model"
            f"{archive_extension}"
        )
        write_archive(
            component_dir,
            component_archive_path,
            archive_format=archive_name,
        )
        write_archive(
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
