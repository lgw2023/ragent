from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


COMPONENT_FILES = (
    "process.py",
    "init.py",
    "config.json",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "run_mep_local.py",
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
        shutil.copytree(source, target, ignore=_ignore_generated, symlinks=True)
        return
    target.symlink_to(source, target_is_directory=True)


def build_mep_layout(
    *,
    repo_root: Path,
    model_package: str,
    output: Path,
    materialize: bool = False,
) -> dict[str, str]:
    repo_root = repo_root.expanduser().resolve()
    output = output.expanduser().resolve()
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

    if output.exists() or output.is_symlink():
        _reset_path(output)
    output.mkdir(parents=True, exist_ok=True)

    component_dir = output / "component"
    _copy_component_source(repo_root, component_dir)
    for name, source in required_dirs.items():
        _link_or_copy(source, output / name, materialize=materialize)

    return {
        "runtime_root": str(output),
        "component_dir": str(component_dir),
        "model_dir": str(output / "model"),
        "data_dir": str(output / "data"),
        "meta_dir": str(output / "meta"),
        "model_package_dir": str(model_dir_root),
        "layout_mode": "copy" if materialize else "symlink",
    }


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
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
