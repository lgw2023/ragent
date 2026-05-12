from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from typing import Iterable


def _describe_non_zip_payload(path: Path) -> str:
    try:
        prefix = path.read_bytes()[:256]
    except OSError as exc:
        return f"could not read file prefix: {exc}"

    if prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
        return "looks like a Git LFS pointer, not the real wheel payload"
    stripped = prefix.lstrip()
    if stripped.startswith((b"<!DOCTYPE html", b"<html", b"<HTML")):
        return "looks like an HTML download/error page"
    if not prefix:
        return "file is empty"
    return "file is not a zip archive"


def _iter_platform_dirs(root: Path, platform_tags: tuple[str, ...]) -> Iterable[Path]:
    if not root.is_dir():
        return
    if platform_tags:
        for platform_tag in platform_tags:
            candidate = root / platform_tag
            if candidate.is_dir():
                yield candidate
        return

    for candidate in sorted(root.iterdir()):
        if candidate.is_dir():
            yield candidate
    if any(root.glob("*.whl")):
        yield root


def _iter_wheelhouse_dirs(args: argparse.Namespace) -> Iterable[Path]:
    for wheelhouse_dir in args.wheelhouse_dir:
        yield wheelhouse_dir.expanduser().resolve()

    if args.model_dir_root is None:
        return

    deps_dir = args.model_dir_root.expanduser().resolve() / "data" / "deps"
    yield from _iter_platform_dirs(deps_dir / "wheelhouse", args.platform_tag)
    if args.include_keyword:
        yield from _iter_platform_dirs(deps_dir / "keyword_wheelhouse", args.platform_tag)


def validate_wheelhouse_dirs(wheelhouse_dirs: Iterable[Path]) -> tuple[int, list[str]]:
    checked = 0
    invalid: list[str] = []
    seen: set[Path] = set()
    for wheelhouse_dir in wheelhouse_dirs:
        if wheelhouse_dir in seen:
            continue
        seen.add(wheelhouse_dir)
        if not wheelhouse_dir.is_dir():
            invalid.append(f"{wheelhouse_dir}: directory does not exist")
            continue
        for wheel_path in sorted(wheelhouse_dir.glob("*.whl")):
            if wheel_path.name.startswith("._"):
                continue
            checked += 1
            try:
                with zipfile.ZipFile(wheel_path) as wheel:
                    corrupt_member = wheel.testzip()
            except (OSError, zipfile.BadZipFile) as exc:
                invalid.append(
                    f"{wheel_path}: {exc}; {_describe_non_zip_payload(wheel_path)}"
                )
                continue
            if corrupt_member is not None:
                invalid.append(f"{wheel_path}: corrupt archive member {corrupt_member}")
    return checked, invalid


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate that MEP offline wheelhouse .whl files are real zip archives."
    )
    parser.add_argument(
        "--model-dir-root",
        type=Path,
        help="MEP modelDir root containing data/deps/wheelhouse.",
    )
    parser.add_argument(
        "--wheelhouse-dir",
        type=Path,
        action="append",
        default=[],
        help="Specific wheelhouse directory to validate. Can be repeated.",
    )
    parser.add_argument(
        "--platform-tag",
        action="append",
        default=[],
        help="Platform tag such as linux-arm64-py3.9. Can be repeated.",
    )
    parser.add_argument(
        "--include-keyword",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also validate data/deps/keyword_wheelhouse for the selected tags.",
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=50,
        help="Maximum invalid wheel details to print.",
    )
    args = parser.parse_args()
    args.platform_tag = tuple(args.platform_tag)
    if args.model_dir_root is None and not args.wheelhouse_dir:
        parser.error("provide --model-dir-root or at least one --wheelhouse-dir")
    return args


def main() -> int:
    args = parse_args()
    checked, invalid = validate_wheelhouse_dirs(_iter_wheelhouse_dirs(args))
    if checked == 0 and not invalid:
        print("no wheel files found for the requested MEP wheelhouse path(s)", file=sys.stderr)
        return 1
    if invalid:
        print("invalid MEP wheelhouse artifact(s):", file=sys.stderr)
        for detail in invalid[: args.max_errors]:
            print(f"- {detail}", file=sys.stderr)
        if len(invalid) > args.max_errors:
            print(
                f"... {len(invalid) - args.max_errors} more invalid artifact(s)",
                file=sys.stderr,
            )
        return 1
    print(f"validated {checked} wheel(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
