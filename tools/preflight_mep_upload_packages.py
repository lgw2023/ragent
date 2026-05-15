from __future__ import annotations

import argparse
import json
import tarfile
import zipfile
from collections.abc import Iterable
from pathlib import Path

try:
    from tools.mep_package_utils import (
        validate_component_package_dir,
        validate_model_package_dir,
    )
    from tools.validate_mep_wheelhouse import validate_wheelhouse_dirs
except ModuleNotFoundError:
    from mep_package_utils import (
        validate_component_package_dir,
        validate_model_package_dir,
    )
    from validate_mep_wheelhouse import validate_wheelhouse_dirs


def _iter_wheelhouse_dirs(
    model_dir_root: Path,
    *,
    platform_tags: tuple[str, ...],
    include_keyword: bool,
) -> Iterable[Path]:
    deps_dir = model_dir_root / "data" / "deps"
    root_names = ["wheelhouse"]
    if include_keyword:
        root_names.append("keyword_wheelhouse")
    for root_name in root_names:
        root = deps_dir / root_name
        if platform_tags:
            for platform_tag in platform_tags:
                yield root / platform_tag
            continue
        if not root.is_dir():
            yield root
            continue
        yielded = False
        for candidate in sorted(root.iterdir()):
            if candidate.is_dir():
                yielded = True
                yield candidate
        if any(root.glob("*.whl")):
            yielded = True
            yield root
        if not yielded:
            yield root


def _archive_members(archive_path: Path) -> set[str]:
    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as archive:
            return set(archive.namelist())
    with tarfile.open(archive_path, "r:*") as archive:
        return set(archive.getnames())


def _top_level_entries(names: Iterable[str]) -> set[str]:
    result: set[str] = set()
    for name in names:
        stripped = name.strip("/")
        if not stripped:
            continue
        result.add(stripped.split("/", 1)[0])
    return result


def _validate_component_archive(archive_path: Path) -> None:
    if not archive_path.is_file():
        raise FileNotFoundError(f"MEP component archive not found: {archive_path}")
    names = _archive_members(archive_path)
    top_level = _top_level_entries(names)
    if "component_package" in top_level:
        raise ValueError(
            "MEP component archive must contain config.json/process.py/ragent "
            "at archive root, not under component_package/"
        )
    for required in ("config.json", "process.py", "mep_dependency_bootstrap.py"):
        if required not in names:
            raise FileNotFoundError(
                f"MEP component archive is missing root entry: {required}"
            )
    if not any(name.startswith("ragent/") for name in names):
        raise FileNotFoundError("MEP component archive is missing ragent/")


def _validate_model_archive(archive_path: Path) -> None:
    if not archive_path.is_file():
        raise FileNotFoundError(f"MEP model archive not found: {archive_path}")
    names = _archive_members(archive_path)
    top_level = _top_level_entries(names)
    if top_level != {"modelDir"}:
        raise ValueError(
            "MEP model archive first-level entry must be exactly modelDir, got "
            f"{sorted(top_level)}"
        )
    for required in (
        "modelDir/model/config.json",
        "modelDir/data/config/embedding.properties",
        "modelDir/meta/type.mf",
    ):
        if required not in names:
            raise FileNotFoundError(f"MEP model archive is missing entry: {required}")


def _validate_wheelhouse_payloads(
    model_dir_root: Path,
    *,
    platform_tags: tuple[str, ...],
    include_keyword: bool,
) -> int:
    checked, invalid = validate_wheelhouse_dirs(
        _iter_wheelhouse_dirs(
            model_dir_root,
            platform_tags=platform_tags,
            include_keyword=include_keyword,
        )
    )
    if checked == 0 and not invalid:
        raise FileNotFoundError("no wheel files found in MEP wheelhouse")
    if invalid:
        details = "\n".join(f"- {detail}" for detail in invalid[:50])
        if len(invalid) > 50:
            details += f"\n... {len(invalid) - 50} more invalid artifact(s)"
        raise ValueError(f"invalid MEP wheelhouse artifact(s):\n{details}")
    return checked


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run upload-shape preflight checks for MEP component and model packages."
    )
    parser.add_argument(
        "--upload-root",
        type=Path,
        help="Directory containing component_package/ and model_package/.",
    )
    parser.add_argument(
        "--component-package-dir",
        type=Path,
        help="Component package directory. Defaults to <upload-root>/component_package.",
    )
    parser.add_argument(
        "--model-package-dir",
        type=Path,
        help="Model package directory. Defaults to <upload-root>/model_package.",
    )
    parser.add_argument(
        "--component-archive",
        type=Path,
        help="Optional component upload archive to validate.",
    )
    parser.add_argument(
        "--model-archive",
        type=Path,
        help="Optional model upload archive to validate.",
    )
    parser.add_argument(
        "--platform-tag",
        action="append",
        default=[],
        help="Required wheelhouse platform tag, such as linux-arm64-py3.9.",
    )
    parser.add_argument(
        "--allow-local-runner",
        action="store_true",
        help="Allow run_mep_local.py in component_package for local debug bundles.",
    )
    parser.add_argument(
        "--no-wheelhouse-payload-check",
        action="store_true",
        help="Skip zip integrity checks for wheelhouse .whl files.",
    )
    parser.add_argument(
        "--no-keyword-wheelhouse",
        action="store_true",
        help="Skip keyword_wheelhouse payload validation.",
    )
    args = parser.parse_args()

    if args.upload_root is None and (
        args.component_package_dir is None or args.model_package_dir is None
    ):
        parser.error(
            "provide --upload-root or both --component-package-dir and --model-package-dir"
        )
    if args.upload_root is not None:
        upload_root = args.upload_root.expanduser().resolve()
        if args.component_package_dir is None:
            args.component_package_dir = upload_root / "component_package"
        if args.model_package_dir is None:
            args.model_package_dir = upload_root / "model_package"
    args.platform_tag = tuple(args.platform_tag)
    return args


def main() -> int:
    args = parse_args()
    component_dir = args.component_package_dir.expanduser().resolve()
    model_package_dir = args.model_package_dir.expanduser().resolve()

    validate_component_package_dir(
        component_dir,
        allow_local_runner=args.allow_local_runner,
    )
    validate_model_package_dir(
        model_package_dir,
        required_platform_tags=args.platform_tag,
    )
    model_dir_root = model_package_dir / "modelDir"

    wheel_count = None
    if not args.no_wheelhouse_payload_check:
        wheel_count = _validate_wheelhouse_payloads(
            model_dir_root,
            platform_tags=args.platform_tag,
            include_keyword=not args.no_keyword_wheelhouse,
        )

    if args.component_archive is not None:
        _validate_component_archive(args.component_archive.expanduser().resolve())
    if args.model_archive is not None:
        _validate_model_archive(args.model_archive.expanduser().resolve())

    result = {
        "component_package_dir": str(component_dir),
        "model_package_dir": str(model_package_dir),
        "model_dir_root": str(model_dir_root),
        "platform_tags": list(args.platform_tag),
        "wheel_payloads_checked": wheel_count,
        "status": "ok",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
