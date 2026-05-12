from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

_NATIVE_WHEEL_SUFFIXES = (".so", ".pyd", ".dll", ".dylib")
DEFAULT_SITE_PACKAGE_DISTRIBUTIONS = ("litellm", "openai")
MANIFEST_FILENAME = "ragent-mep-site-packages-manifest.json"
ALL_PLATFORM_TAG_VALUES = {"all", "*"}
CURRENT_PLATFORM_TAG_VALUES = {"", "auto", "current"}


def normalize_distribution_name(value: str) -> str:
    return value.strip().replace("_", "-").lower()


def _normalize_os_name(value: str | None = None) -> str:
    normalized = (value or sys.platform).strip().lower()
    if normalized.startswith("linux"):
        return "linux"
    if normalized == "darwin":
        return "darwin"
    return normalized or "unknown"


def _normalize_arch_name(value: str | None = None) -> str:
    normalized = (value or platform.machine()).strip().lower()
    if normalized in {"x86_64", "amd64"}:
        return "amd64"
    if normalized in {"aarch64", "arm64"}:
        return "arm64"
    return normalized or "unknown"


def current_platform_tag() -> str:
    return (
        f"{_normalize_os_name()}-{_normalize_arch_name()}-"
        f"py{sys.version_info.major}.{sys.version_info.minor}"
    )


def resolve_site_packages_platform_tag(value: str | None = None) -> str | None:
    raw_value = (
        value
        if value is not None
        else os.getenv("RAGENT_MEP_MATERIALIZE_PLATFORM_TAG")
        or os.getenv("RAGENT_MEP_PLATFORM_TAG")
        or "current"
    )
    normalized = raw_value.strip().lower()
    if normalized in ALL_PLATFORM_TAG_VALUES:
        return None
    if normalized in CURRENT_PLATFORM_TAG_VALUES:
        return current_platform_tag()
    return raw_value.strip()


def distribution_name_from_wheel(wheel_path: Path) -> str | None:
    if wheel_path.suffix != ".whl":
        return None
    parts = wheel_path.name[:-4].split("-")
    if len(parts) < 2 or not parts[0]:
        return None
    return normalize_distribution_name(parts[0])


def _wheel_has_native_extensions(wheel_path: Path) -> bool:
    with zipfile.ZipFile(wheel_path) as wheel:
        return any(
            name.lower().endswith(_NATIVE_WHEEL_SUFFIXES)
            for name in wheel.namelist()
        )


def _safe_member_target(target_dir: Path, member_name: str) -> Path:
    member_path = Path(member_name)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise ValueError(f"Unsafe wheel member path: {member_name!r}")
    target = (target_dir / member_path).resolve()
    if not target.is_relative_to(target_dir.resolve()):
        raise ValueError(f"Unsafe wheel member path: {member_name!r}")
    return target


def _extract_wheel(wheel_path: Path, target_dir: Path) -> list[str]:
    written_paths: list[str] = []
    with zipfile.ZipFile(wheel_path) as wheel:
        for member in wheel.infolist():
            if not member.filename or member.filename.endswith("/"):
                continue
            target = _safe_member_target(target_dir, member.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            with wheel.open(member) as source, target.open("wb") as destination:
                destination.write(source.read())
            written_paths.append(target.relative_to(target_dir).as_posix())
    return written_paths


def _find_distribution_wheels(
    wheelhouse_dir: Path,
    distributions: Iterable[str],
) -> tuple[list[Path], set[str]]:
    wanted = {normalize_distribution_name(distribution) for distribution in distributions}
    selected: list[Path] = []
    found: set[str] = set()
    for wheel_path in sorted(wheelhouse_dir.glob("*.whl")):
        distribution = distribution_name_from_wheel(wheel_path)
        if distribution not in wanted:
            continue
        selected.append(wheel_path)
        found.add(distribution)
    return selected, found


def materialize_wheelhouse_site_packages(
    *,
    wheelhouse_dir: Path,
    target_dir: Path,
    distributions: Iterable[str] = DEFAULT_SITE_PACKAGE_DISTRIBUTIONS,
    strict: bool = False,
) -> dict[str, Any]:
    wheelhouse_dir = wheelhouse_dir.expanduser().resolve()
    target_dir = target_dir.expanduser().resolve()
    wanted = tuple(distributions)
    if not wheelhouse_dir.is_dir():
        if strict:
            raise FileNotFoundError(f"MEP wheelhouse not found: {wheelhouse_dir}")
        return {
            "wheelhouse_dir": str(wheelhouse_dir),
            "target_dir": str(target_dir),
            "wheels": [],
            "missing_distributions": [
                normalize_distribution_name(distribution) for distribution in wanted
            ],
        }

    selected_wheels, found = _find_distribution_wheels(wheelhouse_dir, wanted)
    missing = sorted(
        normalize_distribution_name(distribution)
        for distribution in wanted
        if normalize_distribution_name(distribution) not in found
    )
    if strict and missing:
        raise FileNotFoundError(
            "MEP wheelhouse is missing required site-packages wheels: "
            + ", ".join(missing)
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "wheelhouse_dir": str(wheelhouse_dir),
        "target_dir": str(target_dir),
        "wheels": [],
        "missing_distributions": missing,
    }
    for wheel_path in selected_wheels:
        distribution = distribution_name_from_wheel(wheel_path) or wheel_path.stem
        if _wheel_has_native_extensions(wheel_path):
            raise ValueError(
                "Refusing to pre-extract native wheel into MEP site-packages: "
                f"{wheel_path}"
            )
        written_paths = _extract_wheel(wheel_path, target_dir)
        manifest["wheels"].append(
            {
                "distribution": distribution,
                "wheel": wheel_path.name,
                "file_count": len(written_paths),
            }
        )

    (target_dir / MANIFEST_FILENAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def iter_platform_wheelhouse_dirs(model_dir_root: Path) -> Iterable[Path]:
    wheelhouse_root = model_dir_root / "data" / "deps" / "wheelhouse"
    if not wheelhouse_root.is_dir():
        return ()
    return tuple(
        path
        for path in sorted(wheelhouse_root.iterdir())
        if path.is_dir() and any(path.glob("*.whl"))
    )


def materialize_model_site_packages(
    model_dir_root: Path,
    *,
    platform_tag: str | None = None,
    distributions: Iterable[str] = DEFAULT_SITE_PACKAGE_DISTRIBUTIONS,
    strict: bool = False,
) -> list[dict[str, Any]]:
    model_dir_root = model_dir_root.expanduser().resolve()
    deps_dir = model_dir_root / "data" / "deps"
    if platform_tag:
        wheelhouse_dirs = (deps_dir / "wheelhouse" / platform_tag,)
    else:
        wheelhouse_dirs = tuple(iter_platform_wheelhouse_dirs(model_dir_root))

    manifests: list[dict[str, Any]] = []
    for wheelhouse_dir in wheelhouse_dirs:
        requirements_file = deps_dir / f"requirements-{wheelhouse_dir.name}.txt"
        if requirements_file.is_file():
            continue
        target_dir = deps_dir / "site-packages" / wheelhouse_dir.name
        manifest = materialize_wheelhouse_site_packages(
            wheelhouse_dir=wheelhouse_dir,
            target_dir=target_dir,
            distributions=distributions,
            strict=strict,
        )
        manifests.append(manifest)
    return manifests


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Pre-extract selected pure-Python MEP wheelhouse wheels into "
            "data/deps/site-packages/<platform-tag>/."
        )
    )
    parser.add_argument(
        "--model-dir-root",
        type=Path,
        required=True,
        help="Path to an MEP modelDir directory.",
    )
    parser.add_argument(
        "--platform-tag",
        help="Optional platform tag. Defaults to every platform wheelhouse directory.",
    )
    parser.add_argument(
        "--distribution",
        action="append",
        dest="distributions",
        help=(
            "Distribution name to pre-extract. May be passed multiple times. "
            f"Defaults to: {', '.join(DEFAULT_SITE_PACKAGE_DISTRIBUTIONS)}."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when a requested distribution wheel is missing.",
    )
    args = parser.parse_args()

    manifests = materialize_model_site_packages(
        args.model_dir_root,
        platform_tag=args.platform_tag,
        distributions=args.distributions or DEFAULT_SITE_PACKAGE_DISTRIBUTIONS,
        strict=args.strict,
    )
    print(json.dumps(manifests, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
