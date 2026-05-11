from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DEPS_DIR = (
    PROJECT_ROOT
    / "mep"
    / "model_packages"
    / "bge-m3"
    / "modelDir"
    / "data"
    / "deps"
)
DEFAULT_PLATFORM_TAG = "linux-arm64-py3.9"
DEFAULT_REQUIREMENTS_FILE = MODEL_DEPS_DIR / f"requirements-{DEFAULT_PLATFORM_TAG}.txt"
DEFAULT_BASELINE_CONSTRAINTS_FILE = (
    MODEL_DEPS_DIR / f"image-baseline-constraints-{DEFAULT_PLATFORM_TAG}.txt"
)
DEFAULT_CONSTRAINTS_FILE = MODEL_DEPS_DIR / f"constraints-{DEFAULT_PLATFORM_TAG}.txt"
DEFAULT_OUTPUT_DIR = MODEL_DEPS_DIR / "wheelhouse" / DEFAULT_PLATFORM_TAG
DEFAULT_PLATFORMS = (
    "manylinux_2_34_aarch64",
    "manylinux_2_33_aarch64",
    "manylinux_2_32_aarch64",
    "manylinux_2_31_aarch64",
    "manylinux_2_30_aarch64",
    "manylinux_2_29_aarch64",
    "manylinux_2_28_aarch64",
    "manylinux_2_27_aarch64",
    "manylinux_2_26_aarch64",
    "manylinux_2_25_aarch64",
    "manylinux_2_24_aarch64",
    "manylinux_2_23_aarch64",
    "manylinux_2_22_aarch64",
    "manylinux_2_21_aarch64",
    "manylinux_2_20_aarch64",
    "manylinux_2_19_aarch64",
    "manylinux_2_18_aarch64",
    "manylinux_2_17_aarch64",
    "manylinux2014_aarch64",
)
DEFAULT_ABIS = ("cp39", "abi3")


@dataclass
class ExportManifest:
    created_at: str
    output_dir: str
    requirements_file: str
    baseline_constraints_file: str | None
    constraints_file: str
    python_version: str
    implementation: str
    platforms: list[str]
    abis: list[str]
    wheel_count: int
    wheels: list[str]
    command: list[str] | None


def _normalize_distribution_name(name: str) -> str:
    return name.replace("_", "-").lower()


def _iter_non_comment_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def _constraint_key(line: str) -> str:
    requirement = line.split("#", 1)[0].strip()
    if "==" not in requirement:
        return _normalize_distribution_name(requirement)
    name, _ = requirement.split("==", 1)
    return _normalize_distribution_name(name.strip())


def _wheel_constraint(wheel_name: str) -> str | None:
    if not wheel_name.endswith(".whl"):
        return None
    parts = wheel_name[:-4].split("-")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    return f"{_normalize_distribution_name(parts[0])}=={parts[1]}"


def _resolved_constraints_from_wheels(output_dir: Path) -> list[str]:
    constraints: dict[str, str] = {}
    for wheel_path in sorted(output_dir.glob("*.whl")):
        constraint = _wheel_constraint(wheel_path.name)
        if constraint is None:
            continue
        constraints[_constraint_key(constraint)] = constraint
    return [constraints[key] for key in sorted(constraints)]


def _merge_constraints(
    *,
    wheel_constraints: list[str],
    baseline_constraints_file: Path | None,
) -> list[str]:
    merged: dict[str, str] = {}
    if baseline_constraints_file is not None and baseline_constraints_file.is_file():
        for line in _iter_non_comment_lines(baseline_constraints_file):
            merged[_constraint_key(line)] = line
    for line in wheel_constraints:
        merged[_constraint_key(line)] = line
    return [merged[key] for key in sorted(merged)]


def _write_constraints(
    *,
    constraints_file: Path,
    constraints: list[str],
) -> None:
    constraints_file.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# Resolved MEP runtime constraints for Python 3.9 on Linux aarch64.",
        "# Generated from the transformers embedding wheelhouse.",
        "# Keep Ascend/PyTorch/transformers baseline packages pinned to the target image.",
        "",
    ]
    constraints_file.write_text(
        "\n".join([*header, *constraints]) + "\n",
        encoding="utf-8",
    )


def _build_pip_download_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--dest",
        str(args.output),
        "--only-binary=:all:",
        "--implementation",
        args.implementation,
        "--python-version",
        args.python_version,
    ]
    for abi in args.abis:
        command.extend(["--abi", abi])
    for platform in args.platforms:
        command.extend(["--platform", platform])
    if args.index_url:
        command.extend(["--index-url", args.index_url])
    for extra_index_url in args.extra_index_url:
        command.extend(["--extra-index-url", extra_index_url])
    if args.baseline_constraints and args.baseline_constraints.is_file():
        command.extend(["-c", str(args.baseline_constraints)])
    command.extend(["-r", str(args.requirements)])
    return command


def export_wheelhouse(args: argparse.Namespace) -> ExportManifest:
    args.requirements = args.requirements.expanduser().resolve()
    args.output = args.output.expanduser().resolve()
    args.constraints = args.constraints.expanduser().resolve()
    if args.baseline_constraints is not None:
        args.baseline_constraints = args.baseline_constraints.expanduser().resolve()

    if not args.requirements.is_file():
        raise FileNotFoundError(f"requirements file not found: {args.requirements}")

    if args.clean and args.output.exists():
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True, exist_ok=True)

    command: list[str] | None = None
    if not args.no_download:
        command = _build_pip_download_command(args)
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=args.timeout_seconds,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "pip download failed with exit_code="
                f"{completed.returncode}\n{' '.join(command)}\n{completed.stdout}"
            )
        (args.output / "pip-download.log").write_text(
            completed.stdout,
            encoding="utf-8",
        )

    wheel_constraints = _resolved_constraints_from_wheels(args.output)
    constraints = _merge_constraints(
        wheel_constraints=wheel_constraints,
        baseline_constraints_file=args.baseline_constraints,
    )
    _write_constraints(constraints_file=args.constraints, constraints=constraints)

    wheels = sorted(path.name for path in args.output.glob("*.whl"))
    manifest = ExportManifest(
        created_at=datetime.now(timezone.utc).isoformat(),
        output_dir=str(args.output),
        requirements_file=str(args.requirements),
        baseline_constraints_file=(
            str(args.baseline_constraints) if args.baseline_constraints else None
        ),
        constraints_file=str(args.constraints),
        python_version=args.python_version,
        implementation=args.implementation,
        platforms=list(args.platforms),
        abis=list(args.abis),
        wheel_count=len(wheels),
        wheels=wheels,
        command=command,
    )
    (args.output / "manifest.json").write_text(
        json.dumps(asdict(manifest), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output / "downloaded-wheels.txt").write_text(
        "".join(f"{wheel}\n" for wheel in wheels),
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve and download the MEP transformers embedding runtime "
            "wheelhouse for Python 3.9 Linux aarch64."
        )
    )
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS_FILE)
    parser.add_argument(
        "--baseline-constraints",
        type=Path,
        default=DEFAULT_BASELINE_CONSTRAINTS_FILE,
    )
    parser.add_argument("--constraints", type=Path, default=DEFAULT_CONSTRAINTS_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--python-version", default="39")
    parser.add_argument("--implementation", default="cp")
    parser.add_argument("--platform", action="append", dest="platforms")
    parser.add_argument("--abi", action="append", dest="abis")
    parser.add_argument("--index-url")
    parser.add_argument("--extra-index-url", action="append", default=[])
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Only regenerate constraints and manifest from an existing wheelhouse.",
    )
    args = parser.parse_args()
    args.platforms = tuple(args.platforms or DEFAULT_PLATFORMS)
    args.abis = tuple(args.abis or DEFAULT_ABIS)
    return args


def main() -> None:
    manifest = export_wheelhouse(parse_args())
    print(json.dumps(asdict(manifest), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
