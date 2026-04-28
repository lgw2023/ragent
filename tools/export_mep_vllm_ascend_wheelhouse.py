from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse


DEFAULT_FREEZE_FILE = (
    Path(__file__).resolve().parents[1]
    / "MEP_platform_rule"
    / "Validated_ragent-mep-test_docker_vllm_requirements.freeze.txt"
)
DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "mep"
    / "model_packages"
    / "bge-m3"
    / "modelDir"
    / "data"
    / "deps"
    / "wheelhouse"
    / "linux-arm64-py3.10"
)
DEFAULT_PLATFORMS = (
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
DEFAULT_ABIS = ("cp310", "abi3")
DEFAULT_EXTRA_REQUIREMENTS: tuple[str, ...] = ()
DEFAULT_RESOLVABLE_LOCAL_FILE_PREFIXES = ("/tmp/ragent-mep-test",)
PINNED_REQUIREMENT_RE = re.compile(r"^[A-Za-z0-9_.-]+(?:\[[^]]+\])?==[^#;\s]+$")


@dataclass
class ExportManifest:
    freeze_file: str
    output_dir: str
    python_version: str
    implementation: str
    platforms: list[str]
    abis: list[str]
    downloaded: list[str]
    source_archives: list[str]
    failed: list[dict[str, str]]
    extra_requirements: list[str]
    local_file_requirements: list[str]
    copied_local_wheels: list[str]
    resolved_local_file_requirements: list[str]
    skipped_non_pinned_requirements: list[str]


def _iter_freeze_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def _classify_requirements(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    pinned: list[str] = []
    local_file: list[str] = []
    non_pinned: list[str] = []
    for line in lines:
        if " @ file://" in line:
            local_file.append(line)
        elif PINNED_REQUIREMENT_RE.match(line):
            pinned.append(line)
        else:
            non_pinned.append(line)
    return pinned, local_file, non_pinned


def _path_from_file_url(requirement: str) -> Path | None:
    if " @ file://" not in requirement:
        return None
    _, file_url = requirement.split(" @ ", 1)
    parsed = urlparse(file_url)
    if parsed.scheme != "file":
        return None
    return Path(unquote(parsed.path))


def _wheel_requirement_from_local_file_requirement(requirement: str) -> str | None:
    if " @ file://" not in requirement:
        return None
    raw_name, _ = requirement.split(" @ ", 1)
    path = _path_from_file_url(requirement)
    if path is None or path.suffix != ".whl":
        return None
    wheel_parts = path.name[:-4].split("-")
    if len(wheel_parts) < 2:
        return None
    version = wheel_parts[1]
    name = raw_name.strip().replace("_", "-")
    if not name or not version:
        return None
    return f"{name}=={version}"


def _wheel_dist_and_version(wheel_name: str) -> tuple[str, str] | None:
    if not wheel_name.endswith(".whl"):
        return None
    parts = wheel_name[:-4].split("-")
    if len(parts) < 2:
        return None
    return parts[0].replace("_", "-").lower(), parts[1]


def _find_local_wheel(requirement: str, local_wheel_dirs: list[Path]) -> Path | None:
    path = _path_from_file_url(requirement)
    if path is not None and path.is_file():
        return path

    wheel_requirement = _wheel_requirement_from_local_file_requirement(requirement)
    if wheel_requirement is None:
        return None
    req_name, req_version = wheel_requirement.split("==", 1)
    req_key = req_name.replace("_", "-").lower()
    expected_name = path.name if path is not None else None
    for wheel_dir in local_wheel_dirs:
        if not wheel_dir.is_dir():
            continue
        if expected_name is not None:
            candidate = wheel_dir / expected_name
            if candidate.is_file():
                return candidate
        for candidate in sorted(wheel_dir.glob("*.whl")):
            parsed = _wheel_dist_and_version(candidate.name)
            if parsed == (req_key, req_version):
                return candidate
    return None


def _copy_local_wheel(source: Path, output_dir: Path) -> str:
    target = output_dir / source.name
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target.name


def _is_under_prefix(path: Path, prefix: Path) -> bool:
    try:
        path.resolve().relative_to(prefix.resolve())
    except ValueError:
        return False
    return True


def _should_resolve_local_file_requirement(
    requirement: str,
    resolvable_prefixes: list[Path],
) -> bool:
    path = _path_from_file_url(requirement)
    if path is None:
        return False
    return any(_is_under_prefix(path, prefix) for prefix in resolvable_prefixes)


def _download_requirement(
    requirement: str,
    *,
    output_dir: Path,
    python_version: str,
    implementation: str,
    platforms: list[str],
    abis: list[str],
    index_url: str | None,
    extra_index_urls: list[str],
    timeout_seconds: int,
) -> tuple[bool, str]:
    command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--dest",
        str(output_dir),
        "--only-binary=:all:",
        "--no-deps",
        "--implementation",
        implementation,
        "--python-version",
        python_version,
    ]
    for platform in platforms:
        command.extend(["--platform", platform])
    for abi in abis:
        command.extend(["--abi", abi])
    if index_url:
        command.extend(["--index-url", index_url])
    for extra_index_url in extra_index_urls:
        command.extend(["--extra-index-url", extra_index_url])
    command.append(requirement)

    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode == 0:
        return True, completed.stdout.strip()
    return False, completed.stdout.strip()


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text(
        "".join(f"{line}\n" for line in lines),
        encoding="utf-8",
    )


def _requirement_key(requirement: str) -> str:
    return requirement.split("==", 1)[0].replace("_", "-").lower()


def export_wheelhouse(args: argparse.Namespace) -> ExportManifest:
    freeze_file = args.freeze_file.expanduser().resolve()
    output_dir = args.output.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pinned, local_file, non_pinned = _classify_requirements(
        _iter_freeze_lines(freeze_file)
    )
    _write_lines(output_dir / "validated.freeze.pypi.txt", pinned)
    local_wheel_dirs = [path.expanduser().resolve() for path in args.local_wheel_dir]
    _write_lines(output_dir / "local-file-requirements.txt", local_file)
    _write_lines(output_dir / "non-pinned-requirements.txt", non_pinned)
    _write_lines(output_dir / "extra-requirements.txt", args.extra_requirement)

    requirements_to_download = list(pinned)
    seen_requirements = {_requirement_key(requirement) for requirement in pinned}
    for requirement in args.extra_requirement:
        if _requirement_key(requirement) in seen_requirements:
            continue
        requirements_to_download.append(requirement)
        seen_requirements.add(_requirement_key(requirement))

    copied_local_wheels: list[str] = []
    resolved_local_file_requirements: list[str] = []
    resolvable_local_file_prefixes = [
        Path(path).expanduser().resolve()
        for path in args.resolvable_local_file_prefix
    ]
    should_resolve_local_files = args.resolve_local_file_wheels
    should_copy_local_files = bool(local_wheel_dirs) or should_resolve_local_files
    for requirement in local_file:
        if should_copy_local_files:
            copied_wheel = _find_local_wheel(requirement, local_wheel_dirs)
            if copied_wheel is not None:
                copied_local_wheels.append(_copy_local_wheel(copied_wheel, output_dir))
        should_resolve_requirement = (
            should_resolve_local_files
            or _should_resolve_local_file_requirement(
                requirement,
                resolvable_local_file_prefixes,
            )
        )
        if not should_resolve_requirement:
            continue
        wheel_requirement = _wheel_requirement_from_local_file_requirement(requirement)
        if wheel_requirement is None:
            continue
        resolved_local_file_requirements.append(wheel_requirement)
        if _requirement_key(wheel_requirement) in seen_requirements:
            continue
        requirements_to_download.append(wheel_requirement)
        seen_requirements.add(_requirement_key(wheel_requirement))
    _write_lines(
        output_dir / "resolved-local-file-requirements.txt",
        resolved_local_file_requirements,
    )
    _write_lines(output_dir / "copied-local-wheels.txt", sorted(set(copied_local_wheels)))

    failed: list[dict[str, str]] = []
    for index, requirement in enumerate(requirements_to_download, 1):
        print(f"[{index}/{len(requirements_to_download)}] {requirement}", flush=True)
        ok, output = _download_requirement(
            requirement,
            output_dir=output_dir,
            python_version=args.python_version,
            implementation=args.implementation,
            platforms=args.platform,
            abis=args.abi,
            index_url=args.index_url,
            extra_index_urls=args.extra_index_url,
            timeout_seconds=args.timeout_seconds,
        )
        if not ok:
            failed.append({"requirement": requirement, "pip_output": output})
            print(f"  failed: {requirement}", flush=True)

    downloaded = sorted(path.name for path in output_dir.glob("*.whl"))
    source_archives = sorted(path.name for path in output_dir.glob("*.tar.gz"))
    _write_lines(output_dir / "downloaded-wheels.txt", downloaded)
    _write_lines(output_dir / "source-archives.txt", source_archives)
    _write_lines(
        output_dir / "downloaded-artifacts.txt",
        sorted([*downloaded, *source_archives]),
    )
    _write_lines(
        output_dir / "failed-requirements.txt",
        [
            f"{item['requirement']}\n{item['pip_output']}\n---"
            for item in failed
        ],
    )

    manifest = ExportManifest(
        freeze_file=str(freeze_file),
        output_dir=str(output_dir),
        python_version=args.python_version,
        implementation=args.implementation,
        platforms=list(args.platform),
        abis=list(args.abi),
        downloaded=downloaded,
        source_archives=source_archives,
        failed=failed,
        extra_requirements=list(args.extra_requirement),
        local_file_requirements=local_file,
        copied_local_wheels=sorted(set(copied_local_wheels)),
        resolved_local_file_requirements=resolved_local_file_requirements,
        skipped_non_pinned_requirements=non_pinned,
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(asdict(manifest), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export the validated Ascend 910B vLLM embedding runtime wheelhouse "
            "from a pip freeze file."
        )
    )
    parser.add_argument(
        "--freeze-file",
        type=Path,
        default=DEFAULT_FREEZE_FILE,
        help=f"Freeze file to export from. Defaults to {DEFAULT_FREEZE_FILE}.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Wheelhouse output directory. Defaults to {DEFAULT_OUTPUT_DIR}.",
    )
    parser.add_argument("--python-version", default="310")
    parser.add_argument("--implementation", default="cp")
    parser.add_argument(
        "--platform",
        action="append",
        default=list(DEFAULT_PLATFORMS),
        help="Target wheel platform tag. May be repeated.",
    )
    parser.add_argument(
        "--abi",
        action="append",
        default=list(DEFAULT_ABIS),
        help="Target ABI tag. May be repeated.",
    )
    parser.add_argument("--index-url")
    parser.add_argument("--extra-index-url", action="append", default=[])
    parser.add_argument(
        "--local-wheel-dir",
        action="append",
        type=Path,
        default=[],
        help=(
            "Directory containing wheels referenced by freeze file:// entries. "
            "May be repeated. Existing file:// paths are copied automatically."
        ),
    )
    parser.add_argument(
        "--resolve-local-file-wheels",
        action="store_true",
        help=(
            "Also convert freeze file:// wheel entries back to package==version "
            "and try to download them from the configured indexes. By default "
            "these entries are recorded as image-provided dependencies."
        ),
    )
    parser.add_argument(
        "--resolvable-local-file-prefix",
        action="append",
        type=Path,
        default=list(DEFAULT_RESOLVABLE_LOCAL_FILE_PREFIXES),
        help=(
            "file:// wheel path prefix that should be resolved from package "
            "indexes by default. Defaults to /tmp/ragent-mep-test."
        ),
    )
    parser.add_argument(
        "--extra-requirement",
        action="append",
        default=list(DEFAULT_EXTRA_REQUIREMENTS),
        help=(
            "Additional exact requirement to download even if freeze recorded "
            "it as a file:// install. May be repeated."
        ),
    )
    parser.add_argument("--timeout-seconds", type=int, default=600)
    return parser.parse_args()


def main() -> None:
    manifest = export_wheelhouse(parse_args())
    print(
        json.dumps(
            {
                "output_dir": manifest.output_dir,
                "downloaded_count": len(manifest.downloaded),
                "source_archive_count": len(manifest.source_archives),
                "failed_count": len(manifest.failed),
                "local_file_requirement_count": len(
                    manifest.local_file_requirements
                ),
                "copied_local_wheel_count": len(manifest.copied_local_wheels),
                "resolved_local_file_requirement_count": len(
                    manifest.resolved_local_file_requirements
                ),
                "non_pinned_requirement_count": len(
                    manifest.skipped_non_pinned_requirements
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
