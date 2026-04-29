from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_MODEL_PACKAGE = "bge-m3"
DEFAULT_PLATFORM_TAG = "linux-arm64-py3.10"
DEFAULT_HF_MODEL_ID = "knowledgator/gliner-x-small"
DEFAULT_HF_MODEL_DIR_NAME = "knowledgator-gliner-x-small"
KEYWORD_MODEL_RELATIVE_DIR = (
    Path("data")
    / "models"
    / "keyword_extraction"
    / DEFAULT_HF_MODEL_DIR_NAME
)
KEYWORD_WHEELHOUSE_RELATIVE_DIR = Path("data") / "deps" / "keyword_wheelhouse"
DEFAULT_BINARY_REQUIREMENTS = (
    "gliner==0.2.26",
    "stanza==1.10.1",
    "onnxruntime==1.16.3",
    "coloredlogs==15.0.1",
    "flatbuffers==25.12.19",
    "humanfriendly==10.0",
    "emoji==2.14.1",
)
DEFAULT_PURE_WHEEL_REQUIREMENTS = ("langdetect==1.0.9",)
DEFAULT_MODEL_ALLOW_PATTERNS = (
    "README.md",
    "config.json",
    "gliner_config.json",
    "generation_config.json",
    "model.safetensors",
    "pytorch_model.bin",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.*",
    "merges.txt",
)
MODEL_WEIGHT_FILENAMES = (
    "model.safetensors",
    "pytorch_model.bin",
)
MODEL_MARKER_FILENAMES = (
    "gliner_config.json",
    "tokenizer_config.json",
)


def keyword_model_dir(model_dir_root: Path) -> Path:
    return model_dir_root / KEYWORD_MODEL_RELATIVE_DIR


def keyword_wheelhouse_dir(model_dir_root: Path, platform_tag: str) -> Path:
    return model_dir_root / KEYWORD_WHEELHOUSE_RELATIVE_DIR / platform_tag


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def _copy_visible_files(source_dir: Path, dest_dir: Path) -> list[str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source in sorted(source_dir.iterdir()):
        if not source.is_file() or source.name.startswith("._"):
            continue
        target = dest_dir / source.name
        shutil.copy2(source, target)
        copied.append(source.name)
    return copied


def _remove_existing_wheels(output_dir: Path) -> None:
    if not output_dir.is_dir():
        return
    for existing in output_dir.glob("*.whl"):
        if existing.is_file():
            existing.unlink()


def _distribution_name_from_wheel(wheel_name: str) -> str | None:
    if not wheel_name.endswith(".whl") or "-" not in wheel_name:
        return None
    distribution = wheel_name.split("-", 1)[0].replace("_", "-").lower()
    return distribution or None


def download_keyword_wheels(
    *,
    output_dir: Path,
    platform_tag: str,
    python_bin: str,
    binary_requirements: tuple[str, ...] = DEFAULT_BINARY_REQUIREMENTS,
    pure_wheel_requirements: tuple[str, ...] = DEFAULT_PURE_WHEEL_REQUIREMENTS,
) -> list[str]:
    if platform_tag != DEFAULT_PLATFORM_TAG:
        raise ValueError(
            "keyword fallback wheel export currently supports only "
            f"{DEFAULT_PLATFORM_TAG}: {platform_tag}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ragent_keyword_wheels_") as tmp:
        tmp_dir = Path(tmp)
        if binary_requirements:
            _run(
                [
                    python_bin,
                    "-m",
                    "pip",
                    "download",
                    "--dest",
                    str(tmp_dir),
                    "--only-binary=:all:",
                    "--platform",
                    "manylinux2014_aarch64",
                    "--python-version",
                    "310",
                    "--implementation",
                    "cp",
                    "--abi",
                    "cp310",
                    "--no-deps",
                    *binary_requirements,
                ]
            )
        if pure_wheel_requirements:
            _run(
                [
                    python_bin,
                    "-m",
                    "pip",
                    "wheel",
                    "--wheel-dir",
                    str(tmp_dir),
                    "--no-deps",
                    *pure_wheel_requirements,
                ]
            )
        _remove_existing_wheels(output_dir)
        copied = _copy_visible_files(tmp_dir, output_dir)

    manifest = {
        "platform_tag": platform_tag,
        "binary_requirements": list(binary_requirements),
        "pure_wheel_requirements": list(pure_wheel_requirements),
        "wheels": copied,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return copied


def download_keyword_model_snapshot(
    *,
    model_id: str,
    output_dir: Path,
    allow_patterns: tuple[str, ...] = DEFAULT_MODEL_ALLOW_PATTERNS,
) -> None:
    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:  # pragma: no cover - depends on local tooling
        raise RuntimeError(
            "huggingface_hub is required to export the GLiNER model snapshot"
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=model_id,
        local_dir=str(output_dir),
        allow_patterns=list(allow_patterns),
        ignore_patterns=[".git*", "*.msgpack"],
    )


def validate_keyword_fallback_assets(
    *,
    model_dir_root: Path,
    platform_tag: str,
) -> dict[str, Any]:
    model_dir = keyword_model_dir(model_dir_root)
    wheelhouse_dir = keyword_wheelhouse_dir(model_dir_root, platform_tag)
    if not model_dir.is_dir():
        raise FileNotFoundError(f"GLiNER keyword model directory is missing: {model_dir}")
    missing_markers = [
        name for name in MODEL_MARKER_FILENAMES if not (model_dir / name).is_file()
    ]
    if missing_markers:
        raise FileNotFoundError(
            "GLiNER keyword model snapshot is missing required files: "
            + ", ".join(missing_markers)
        )
    if not any((model_dir / name).is_file() for name in MODEL_WEIGHT_FILENAMES):
        raise FileNotFoundError(
            "GLiNER keyword model snapshot is missing model weights: "
            + ", ".join(MODEL_WEIGHT_FILENAMES)
        )
    if not wheelhouse_dir.is_dir():
        raise FileNotFoundError(f"keyword wheelhouse is missing: {wheelhouse_dir}")
    wheels = sorted(
        item.name
        for item in wheelhouse_dir.glob("*.whl")
        if item.is_file() and not item.name.startswith("._")
    )
    required_prefixes = (
        "gliner-",
        "stanza-",
        "onnxruntime-",
        "langdetect-",
    )
    missing_wheels = [
        prefix for prefix in required_prefixes if not any(name.startswith(prefix) for name in wheels)
    ]
    if missing_wheels:
        raise FileNotFoundError(
            "keyword wheelhouse is missing required wheels: "
            + ", ".join(missing_wheels)
        )
    wheels_by_distribution: dict[str, list[str]] = {}
    for wheel_name in wheels:
        distribution = _distribution_name_from_wheel(wheel_name)
        if distribution is not None:
            wheels_by_distribution.setdefault(distribution, []).append(wheel_name)
    required_distributions = ("gliner", "stanza", "onnxruntime", "langdetect")
    duplicate_required_wheels = {
        distribution: names
        for distribution, names in wheels_by_distribution.items()
        if distribution in required_distributions and len(names) != 1
    }
    if duplicate_required_wheels:
        details = "; ".join(
            f"{distribution}={names}"
            for distribution, names in sorted(duplicate_required_wheels.items())
        )
        raise ValueError(f"keyword wheelhouse has duplicate required wheels: {details}")
    return {
        "model_dir": str(model_dir),
        "wheelhouse_dir": str(wheelhouse_dir),
        "wheel_count": len(wheels),
        "wheels": wheels,
    }


def export_keyword_fallback_assets(
    *,
    repo_root: Path,
    model_package: str,
    platform_tag: str,
    python_bin: str,
    model_id: str,
    skip_model: bool = False,
    skip_wheels: bool = False,
) -> dict[str, Any]:
    model_dir_root = (
        repo_root / "mep" / "model_packages" / model_package / "modelDir"
    ).resolve()
    if not model_dir_root.is_dir():
        raise FileNotFoundError(f"MEP modelDir is missing: {model_dir_root}")

    model_dir = keyword_model_dir(model_dir_root)
    wheelhouse_dir = keyword_wheelhouse_dir(model_dir_root, platform_tag)
    if not skip_model:
        download_keyword_model_snapshot(model_id=model_id, output_dir=model_dir)
    if not skip_wheels:
        download_keyword_wheels(
            output_dir=wheelhouse_dir,
            platform_tag=platform_tag,
            python_bin=python_bin,
        )
    return validate_keyword_fallback_assets(
        model_dir_root=model_dir_root,
        platform_tag=platform_tag,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Export GLiNER keyword fallback dependencies and model snapshot into "
            "the MEP model package."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the parent of tools/.",
    )
    parser.add_argument(
        "--model-package",
        default=DEFAULT_MODEL_PACKAGE,
        help="Name under mep/model_packages/.",
    )
    parser.add_argument(
        "--platform-tag",
        default=DEFAULT_PLATFORM_TAG,
        help="Offline dependency platform tag.",
    )
    parser.add_argument(
        "--python-bin",
        default=sys.executable,
        help="Python executable used to run pip.",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_HF_MODEL_ID,
        help="Hugging Face model id to snapshot.",
    )
    parser.add_argument(
        "--skip-model",
        action="store_true",
        help="Only validate or export wheels; do not download the HF snapshot.",
    )
    parser.add_argument(
        "--skip-wheels",
        action="store_true",
        help="Only validate or export the model snapshot; do not download wheels.",
    )
    args = parser.parse_args()

    result = export_keyword_fallback_assets(
        repo_root=args.repo_root.expanduser().resolve(),
        model_package=args.model_package,
        platform_tag=args.platform_tag,
        python_bin=args.python_bin,
        model_id=args.model_id,
        skip_model=args.skip_model,
        skip_wheels=args.skip_wheels,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
