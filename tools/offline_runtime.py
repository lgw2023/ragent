#!/usr/bin/env python3
"""Prepare and validate project-local offline runtime assets.

This script intentionally uses only the Python standard library so it can run
before the project dependencies are installed on an offline server.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_ROOT = PROJECT_ROOT / "vendor" / "mineru-models"
DEFAULT_RUNTIME_DIR = PROJECT_ROOT / ".runtime"
DEFAULT_MINERU_CONFIG = DEFAULT_RUNTIME_DIR / "mineru.json"
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"
MODEL_KEYS = ("pipeline", "vlm")


def _normalize_os() -> str:
    system = platform.system().lower()
    if system.startswith("linux"):
        return "linux"
    if system.startswith("darwin"):
        return "darwin"
    return system


def _normalize_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    return machine


def _platform_tag() -> str:
    py_tag = f"py{sys.version_info.major}.{sys.version_info.minor}"
    return f"{_normalize_os()}-{_normalize_arch()}-{py_tag}"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _read_env_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _quote_env_value(value: str) -> str:
    if not value:
        return '""'
    if any(ch.isspace() for ch in value) or "#" in value or '"' in value:
        return json.dumps(value, ensure_ascii=False)
    return value


def _upsert_env(path: Path, updates: dict[str, str]) -> None:
    lines = _read_env_lines(path)
    seen: set[str] = set()
    rewritten: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            rewritten.append(line)
            continue

        key = line.split("=", 1)[0].strip()
        if key in updates:
            rewritten.append(f"{key}={_quote_env_value(updates[key])}")
            seen.add(key)
        else:
            rewritten.append(line)

    if rewritten and rewritten[-1].strip():
        rewritten.append("")
    for key, value in updates.items():
        if key not in seen:
            rewritten.append(f"{key}={_quote_env_value(value)}")

    path.write_text("\n".join(rewritten).rstrip() + "\n", encoding="utf-8")


def _copy_dir(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"source model directory does not exist: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)

    rsync = shutil.which("rsync")
    if rsync:
        dst.mkdir(parents=True, exist_ok=True)
        cmd = [
            rsync,
            "-a",
            "--delete",
            "--exclude=.lock/",
            "--exclude=._____temp/",
            f"--exclude=/{src.name}",
            f"{src}/",
            f"{dst}/",
        ]
        subprocess.run(cmd, check=True)
        return

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(".lock", "._____temp", src.name),
        symlinks=True,
    )


def _resolve_source_model_dirs(config_path: Path) -> dict[str, Path]:
    config = _load_json(config_path)
    models_dir = config.get("models-dir") or {}
    missing = [key for key in MODEL_KEYS if not models_dir.get(key)]
    if missing:
        raise RuntimeError(
            f"{config_path} is missing models-dir entries: {', '.join(missing)}"
        )
    return {key: Path(models_dir[key]).expanduser().resolve() for key in MODEL_KEYS}


def _mineru_config_payload(model_root: Path) -> dict:
    return {
        "bucket_info": {
            "bucket-name-1": ["ak", "sk", "endpoint"],
            "bucket-name-2": ["ak", "sk", "endpoint"],
        },
        "latex-delimiter-config": {
            "display": {"left": "$$", "right": "$$"},
            "inline": {"left": "$", "right": "$"},
        },
        "llm-aided-config": {
            "title_aided": {
                "api_key": "your_api_key",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "qwen3-next-80b-a3b-instruct",
                "enable_thinking": False,
                "enable": False,
            }
        },
        "models-dir": {
            "pipeline": str((model_root / "pipeline").resolve()),
            "vlm": str((model_root / "vlm").resolve()),
        },
        "config_version": "1.3.1",
    }


def cmd_copy_models(args: argparse.Namespace) -> int:
    source_config = Path(args.source_config).expanduser().resolve()
    model_root = Path(args.model_root).expanduser().resolve()
    source_dirs = _resolve_source_model_dirs(source_config)

    for key in MODEL_KEYS:
        dst = model_root / key
        print(f"copy {key}: {source_dirs[key]} -> {dst}", flush=True)
        _copy_dir(source_dirs[key], dst)

    _write_json(DEFAULT_MINERU_CONFIG, _mineru_config_payload(model_root))
    print(f"wrote {DEFAULT_MINERU_CONFIG}")
    return 0


def cmd_configure(args: argparse.Namespace) -> int:
    model_root = Path(args.model_root).expanduser().resolve()
    config_path = Path(args.config).expanduser().resolve()
    payload = _mineru_config_payload(model_root)
    _write_json(config_path, payload)

    if args.update_env:
        env_path = Path(args.env).expanduser().resolve()
        relative_config = os.path.relpath(config_path, PROJECT_ROOT)
        _upsert_env(
            env_path,
            {
                "MINERU_MODEL_SOURCE": "local",
                "MINERU_TOOLS_CONFIG_JSON": relative_config,
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "TOKENIZERS_PARALLELISM": "false",
            },
        )
        print(f"updated {env_path}")

    print(f"wrote {config_path}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser().resolve()
    if not config_path.exists():
        print(f"missing MinerU config: {config_path}", file=sys.stderr)
        return 1

    config = _load_json(config_path)
    models_dir = config.get("models-dir") or {}
    failed = False
    for key in MODEL_KEYS:
        path = Path(models_dir.get(key, "")).expanduser()
        if not path.exists():
            print(f"missing {key} model dir: {path}", file=sys.stderr)
            failed = True
        else:
            print(f"ok {key}: {path}")

    wheelhouse_base = PROJECT_ROOT / "vendor" / "wheelhouse"
    wheelhouse = wheelhouse_base / _platform_tag()
    if wheelhouse.exists():
        wheels = list(wheelhouse.glob("*.whl"))
        print(f"wheelhouse: {wheelhouse} ({len(wheels)} wheels)")
    elif wheelhouse_base.exists() and list(wheelhouse_base.glob("*.whl")):
        wheels = list(wheelhouse_base.glob("*.whl"))
        print(f"wheelhouse: {wheelhouse_base} ({len(wheels)} wheels, legacy flat layout)")
    elif wheelhouse_base.exists():
        available = sorted(path.name for path in wheelhouse_base.iterdir() if path.is_dir())
        print(f"wheelhouse not found for current platform: {wheelhouse}")
        if available:
            print(f"available wheelhouses: {', '.join(available)}")
    else:
        print(f"wheelhouse not found: {wheelhouse_base}")

    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    copy_models = subparsers.add_parser("copy-models")
    copy_models.add_argument(
        "--source-config",
        default=str(Path.home() / "mineru.json"),
        help="MinerU config that currently points at downloaded local models.",
    )
    copy_models.add_argument("--model-root", default=str(DEFAULT_MODEL_ROOT))
    copy_models.set_defaults(func=cmd_copy_models)

    configure = subparsers.add_parser("configure")
    configure.add_argument("--model-root", default=str(DEFAULT_MODEL_ROOT))
    configure.add_argument("--config", default=str(DEFAULT_MINERU_CONFIG))
    configure.add_argument("--env", default=str(DEFAULT_ENV_PATH))
    configure.add_argument(
        "--no-update-env",
        dest="update_env",
        action="store_false",
        help="Only write the MinerU config; do not update .env.",
    )
    configure.set_defaults(func=cmd_configure, update_env=True)

    check = subparsers.add_parser("check")
    check.add_argument("--config", default=str(DEFAULT_MINERU_CONFIG))
    check.set_defaults(func=cmd_check)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
