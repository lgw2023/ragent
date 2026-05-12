from __future__ import annotations

import importlib.util
import asyncio
import logging
from collections import deque
import json
import os
import platform
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
import requests

try:
    from importlib import metadata as importlib_metadata
except ImportError:  # pragma: no cover - Python < 3.8 is not supported here.
    import importlib_metadata  # type: ignore


logger = logging.getLogger("ragent.mep_embedding_runtime")

_TRUE_VALUES = {"1", "true", "yes", "on"}
_MANAGED_ENV_VARS = (
    "EMBEDDING_MODEL",
    "EMBEDDING_MODEL_KEY",
    "EMBEDDING_MODEL_URL",
    "EMBEDDING_PROVIDER",
    "EMBEDDING_DIMENSIONS",
)
_LOCAL_PROVIDER = "custom_openai"
_DEFAULT_MODEL_NAME = "BAAI/bge-m3"
_DEFAULT_API_KEY = "EMPTY"
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_BIND_HOST = _DEFAULT_HOST
_DEFAULT_RUNNER = "pooling"
_DEFAULT_STARTUP_TIMEOUT_SECONDS = 300.0
_MODEL_DIR_MARKERS = ("config.json", "tokenizer.json")
_DATA_CONFIG_FILENAMES = (
    "embedding.properties",
    "sysconfig.properties",
)
_DEFAULT_ASCEND_ENV_SCRIPTS = (
    "/usr/local/Ascend/ascend-toolkit/set_env.sh",
    "/usr/local/Ascend/ascend-toolkit/latest/set_env.sh",
    "/usr/local/Ascend/nnal/atb/set_env.sh",
    "/usr/local/Ascend/nnal/atb/latest/atb/set_env.sh",
)
_VLLM_SUBPROCESS_DEFAULT_ENV = {
    "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
}
_VLLM_ENV_PROPERTY_PREFIX = "vllm.env."
_EXACT_REQUIREMENT_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([^;\s]+)$")
_VLLM_DEPENDENCY_BOOTSTRAP_DONE: set[tuple[str, ...]] = set()


@dataclass(frozen=True)
class MepEmbeddingLaunchConfig:
    model_dir: Path
    model_path: Path
    served_model_name: str
    host: str
    bind_host: str
    port: int
    api_key: str
    runner: str
    startup_timeout_seconds: float
    dimensions: int | None = None
    max_token_size: int | None = None
    max_model_len: int | None = None
    extra_args: tuple[str, ...] = ()
    subprocess_env: tuple[tuple[str, str], ...] = ()
    install_requirements: tuple[str, ...] = ()
    uninstall_packages: tuple[str, ...] = ()
    install_no_deps: bool = True
    install_force_reinstall: bool = True
    install_all_wheelhouse_wheels: bool = False
    launch_mode: str = "auto"
    runtime: str = "vllm"
    device: str | None = None
    batch_size: int = 8
    pooling: str = "auto"
    normalize_embeddings: bool = True
    trust_remote_code: bool = True
    config_path: Path | None = None
    data_dir: Path | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}/v1"


@dataclass
class LocalEmbeddingRuntime:
    config: MepEmbeddingLaunchConfig
    process: subprocess.Popen[Any] | None
    launch_command: tuple[str, ...]
    log_path: Path
    cleanup_callback: Callable[[], None] | None = field(default=None, repr=False)
    _env_backup: dict[str, str | None] = field(default_factory=dict, repr=False)

    def apply_environment(self) -> None:
        if not self._env_backup:
            for key in _MANAGED_ENV_VARS:
                self._env_backup[key] = os.getenv(key)
        os.environ["EMBEDDING_MODEL"] = self.config.served_model_name
        if self.config.runtime == "vllm":
            os.environ["EMBEDDING_MODEL_KEY"] = self.config.api_key
            os.environ["EMBEDDING_MODEL_URL"] = self.config.base_url
            os.environ["EMBEDDING_PROVIDER"] = _LOCAL_PROVIDER
        if self.config.dimensions is not None:
            os.environ["EMBEDDING_DIMENSIONS"] = str(self.config.dimensions)

    def restore_environment(self) -> None:
        for key, previous_value in self._env_backup.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value
        self._env_backup.clear()

    def shutdown(self) -> None:
        self.restore_environment()

        if self.cleanup_callback is not None:
            self.cleanup_callback()
            self.cleanup_callback = None

        if self.process is None:
            return
        if self.process.poll() is not None:
            return

        self.process.terminate()
        try:
            self.process.wait(timeout=10)
            return
        except subprocess.TimeoutExpired:
            logger.warning(
                "Local vLLM embedding process did not exit after SIGTERM, sending SIGKILL. pid=%s",
                self.process.pid,
            )
        self.process.kill()
        self.process.wait(timeout=5)


def _read_properties_file(path: Path) -> dict[str, str]:
    properties: dict[str, str] = {}
    if not path.exists():
        return properties

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            key, value = line, ""
        properties[key.strip()] = value.strip()
    return properties


def _iter_embedding_config_candidates(
    *,
    model_dir: Path,
    data_dir: Path | None,
) -> list[Path]:
    candidates: list[Path] = []

    configured_path = _normalize_optional_str(
        os.getenv("RAGENT_MEP_EMBEDDING_CONFIG_PATH")
    )
    if configured_path is not None:
        candidate = Path(configured_path).expanduser()
        if not candidate.is_absolute():
            candidate = ((data_dir or model_dir) / candidate).resolve()
        else:
            candidate = candidate.resolve()
        candidates.append(candidate)

    if data_dir is not None:
        for filename in _DATA_CONFIG_FILENAMES:
            candidates.append((data_dir / "config" / filename).resolve())
        for filename in _DATA_CONFIG_FILENAMES:
            candidates.append((data_dir / filename).resolve())

    # Legacy compatibility: older local model packages stored component-readable
    # bootstrap config beside the HF model directory under model/.
    candidates.append((model_dir / "sysconfig.properties").resolve())

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        deduped.append(candidate)
        seen.add(candidate)
    return deduped


def _read_embedding_properties(
    *,
    model_dir: Path,
    data_dir: Path | None,
) -> tuple[dict[str, str], Path | None]:
    for candidate in _iter_embedding_config_candidates(
        model_dir=model_dir,
        data_dir=data_dir,
    ):
        if candidate.is_file():
            return _read_properties_file(candidate), candidate
    return {}, None


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _parse_optional_int(value: Any) -> int | None:
    normalized = _normalize_optional_str(value)
    if normalized is None:
        return None
    return int(normalized)


def _parse_optional_float(value: Any) -> float | None:
    normalized = _normalize_optional_str(value)
    if normalized is None:
        return None
    return float(normalized)


def _parse_optional_bool(value: Any) -> bool | None:
    normalized = _normalize_optional_str(value)
    if normalized is None:
        return None
    lowered = normalized.lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _resolve_subprocess_env(properties: dict[str, str]) -> tuple[tuple[str, str], ...]:
    resolved: list[tuple[str, str]] = []
    seen: set[str] = set()
    for key, value in properties.items():
        if not key.startswith(_VLLM_ENV_PROPERTY_PREFIX):
            continue
        env_name = key[len(_VLLM_ENV_PROPERTY_PREFIX) :].strip()
        if not env_name or env_name in seen:
            continue
        normalized_value = _normalize_optional_str(value)
        if normalized_value is None:
            continue
        seen.add(env_name)
        resolved.append((env_name, normalized_value))
    return tuple(resolved)


def _parse_string_list(value: Any) -> tuple[str, ...]:
    normalized = _normalize_optional_str(value)
    if normalized is None:
        return ()
    return tuple(
        item
        for item in shlex.split(normalized.replace(",", " "))
        if item.strip()
    )


def _has_complete_external_embedding_config() -> bool:
    return all(_normalize_optional_str(os.getenv(key)) for key in _MANAGED_ENV_VARS[:3])


def _resolve_property(
    properties: dict[str, str],
    env_var: str,
    *property_names: str,
) -> str | None:
    env_value = _normalize_optional_str(os.getenv(env_var))
    if env_value is not None:
        return env_value
    for property_name in property_names:
        property_value = _normalize_optional_str(properties.get(property_name))
        if property_value is not None:
            return property_value
    return None


def _should_pass_vllm_api_key(api_key: str) -> bool:
    normalized = api_key.strip()
    return bool(normalized) and normalized.lower() not in {"empty", "none", "null"}


def _find_available_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _looks_like_embedding_model_dir(candidate: Path) -> bool:
    return candidate.is_dir() and all((candidate / marker).exists() for marker in _MODEL_DIR_MARKERS)


_NESTED_EMBEDDING_MODEL_SCAN_MAX_DEPTH = 6


def _find_nested_embedding_model_directories(
    model_dir: Path, *, max_depth: int = _NESTED_EMBEDDING_MODEL_SCAN_MAX_DEPTH
) -> tuple[Path, ...]:
    """
    Breadth-first search for descendant directories that look like HuggingFace-style
    embedding snapshots (config.json + tokenizer.json).

    Used when the MEP model bundle root is not itself an HF directory and no *direct*
    child qualifies — e.g. weights live under modelDir/model/ inside the mount.
    """
    resolved_root = model_dir.resolve()
    found: list[Path] = []
    seen: set[Path] = set()
    queue: deque[tuple[Path, int]] = deque([(resolved_root, 0)])

    while queue:
        current, depth = queue.popleft()
        try:
            resolved = current.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            if not resolved.is_dir():
                continue
        except OSError:
            continue

        if resolved != resolved_root and _looks_like_embedding_model_dir(resolved):
            found.append(resolved)
            continue

        if depth >= max_depth:
            continue
        try:
            for child in resolved.iterdir():
                try:
                    if child.is_dir():
                        queue.append((child, depth + 1))
                except OSError:
                    continue
        except OSError:
            continue

    return tuple(sorted(set(found)))


def _normalize_model_dir_input(model_dir: Path) -> tuple[Path, Path | None]:
    resolved_input_dir = model_dir.expanduser().resolve()
    if (resolved_input_dir / "sysconfig.properties").exists():
        return resolved_input_dir, None
    if _looks_like_embedding_model_dir(resolved_input_dir):
        parent_dir = resolved_input_dir.parent
        if (parent_dir / "sysconfig.properties").exists():
            return parent_dir.resolve(), resolved_input_dir
        return resolved_input_dir, resolved_input_dir
    return resolved_input_dir, None


def _resolve_model_path(
    model_dir: Path,
    properties: dict[str, str],
    *,
    preferred_model_path: Path | None = None,
) -> Path:
    configured_path = _resolve_property(
        properties,
        "RAGENT_MEP_EMBEDDING_MODEL_PATH",
        "embedding.model_path",
        "model.path",
        "embedding.model_relative_path",
        "model.relative_path",
    )
    if configured_path is not None:
        configured_path_obj = Path(configured_path).expanduser()
        candidate = configured_path_obj
        if not candidate.is_absolute():
            candidate = (model_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if not _looks_like_embedding_model_dir(candidate):
            if (
                not configured_path_obj.is_absolute()
                and preferred_model_path is not None
                and _looks_like_embedding_model_dir(preferred_model_path)
                and (
                    str(configured_path_obj) == "."
                    or configured_path_obj.parts == (preferred_model_path.name,)
                )
            ):
                return preferred_model_path.resolve()
            raise FileNotFoundError(
                f"Configured embedding model path is invalid: {candidate}"
            )
        return candidate

    if preferred_model_path is not None and _looks_like_embedding_model_dir(
        preferred_model_path
    ):
        return preferred_model_path.resolve()

    path_appendix = _normalize_optional_str(os.getenv("path_appendix"))
    if path_appendix is not None:
        appendix_candidate = Path(path_appendix).expanduser()
        if not appendix_candidate.is_absolute():
            appendix_candidate = (model_dir / appendix_candidate).resolve()
        else:
            appendix_candidate = appendix_candidate.resolve()
        if _looks_like_embedding_model_dir(appendix_candidate):
            return appendix_candidate

    if _looks_like_embedding_model_dir(model_dir):
        return model_dir

    candidates = sorted(
        child.resolve()
        for child in model_dir.iterdir()
        if _looks_like_embedding_model_dir(child)
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        nested = _find_nested_embedding_model_directories(model_dir)
        if len(nested) == 1:
            return nested[0]
        if len(nested) > 1:
            raise RuntimeError(
                "Multiple embedding model directories found under model/ (nested). "
                "Please set RAGENT_MEP_EMBEDDING_MODEL_PATH explicitly. "
                f"Candidates: {', '.join(str(item) for item in nested)}"
            )
        raise FileNotFoundError(
            "No embedding model directory found under model/. "
            f"Checked: {model_dir}"
        )
    raise RuntimeError(
        "Multiple embedding model directories found under model/. "
        "Please set RAGENT_MEP_EMBEDDING_MODEL_PATH explicitly. "
        f"Candidates: {', '.join(str(item) for item in candidates)}"
    )


def resolve_embedding_launch_config(
    model_dir: str | os.PathLike[str],
    *,
    data_dir: str | os.PathLike[str] | None = None,
) -> MepEmbeddingLaunchConfig:
    resolved_model_dir_input = Path(model_dir).expanduser().resolve()
    resolved_model_dir, preferred_model_path = _normalize_model_dir_input(
        resolved_model_dir_input
    )
    resolved_data_dir = (
        Path(data_dir).expanduser().resolve() if data_dir is not None else None
    )
    if not resolved_model_dir.exists():
        raise FileNotFoundError(f"MEP model directory does not exist: {resolved_model_dir}")
    if not resolved_model_dir.is_dir():
        raise ValueError(f"MEP model path is not a directory: {resolved_model_dir}")

    properties, config_path = _read_embedding_properties(
        model_dir=resolved_model_dir,
        data_dir=resolved_data_dir,
    )
    model_path = _resolve_model_path(
        resolved_model_dir,
        properties,
        preferred_model_path=preferred_model_path,
    )
    legacy_host = _resolve_property(
        properties,
        "RAGENT_MEP_EMBEDDING_HOST",
        "vllm.host",
    )
    host = (
        _resolve_property(
            properties,
            "RAGENT_MEP_EMBEDDING_CLIENT_HOST",
            "vllm.client_host",
            "embedding.host",
        )
        or legacy_host
        or _DEFAULT_HOST
    )
    bind_host = (
        _resolve_property(
            properties,
            "RAGENT_MEP_VLLM_BIND_HOST",
            "vllm.bind_host",
            "vllm.listen_host",
        )
        or legacy_host
        or _DEFAULT_BIND_HOST
    )
    configured_port = _parse_optional_int(
        _resolve_property(
            properties,
            "RAGENT_MEP_EMBEDDING_PORT",
            "vllm.port",
        )
    )
    port = (
        configured_port
        if configured_port not in (None, 0)
        else _find_available_port(bind_host)
    )
    startup_timeout_seconds = _parse_optional_float(
        _resolve_property(
            properties,
            "RAGENT_MEP_EMBEDDING_STARTUP_TIMEOUT_SECONDS",
            "vllm.startup_timeout_seconds",
        )
    )
    served_model_name = _resolve_property(
        properties,
        "RAGENT_MEP_EMBEDDING_MODEL_NAME",
        "vllm.served_model_name",
        "embedding.served_model_name",
        "model.name",
    ) or _DEFAULT_MODEL_NAME
    api_key = _resolve_property(
        properties,
        "RAGENT_MEP_EMBEDDING_API_KEY",
        "vllm.api_key",
    ) or _DEFAULT_API_KEY
    runner = _resolve_property(
        properties,
        "RAGENT_MEP_VLLM_RUNNER",
        "vllm.runner",
    ) or _DEFAULT_RUNNER
    launch_mode = (
        _resolve_property(
            properties,
            "RAGENT_MEP_VLLM_LAUNCH_MODE",
            "vllm.launch_mode",
        )
        or "auto"
    ).lower()
    runtime = (
        _resolve_property(
            properties,
            "RAGENT_MEP_EMBEDDING_RUNTIME",
            "embedding.runtime",
        )
        or "vllm"
    ).lower()
    extra_args = tuple(
        shlex.split(
            _resolve_property(
                properties,
                "RAGENT_MEP_VLLM_EXTRA_ARGS",
                "vllm.extra_args",
            )
            or ""
        )
    )
    install_no_deps_value = _resolve_property(
        properties,
        "RAGENT_MEP_VLLM_INSTALL_NO_DEPS",
        "vllm.install_no_deps",
    )
    install_force_reinstall_value = _resolve_property(
        properties,
        "RAGENT_MEP_VLLM_INSTALL_FORCE_REINSTALL",
        "vllm.install_force_reinstall",
    )
    install_all_wheelhouse_wheels_value = _resolve_property(
        properties,
        "RAGENT_MEP_VLLM_INSTALL_ALL_WHEELHOUSE_WHEELS",
        "vllm.install_all_wheelhouse_wheels",
    )

    logger.info(
        "Resolved embedding launch config. input_model_dir=%s bundle_model_dir=%s "
        "data_dir=%s model_path=%s runtime=%s bind_host=%s client_host=%s port=%s "
        "path_appendix=%s config_path=%s legacy_sysconfig_present=%s",
        resolved_model_dir_input,
        resolved_model_dir,
        resolved_data_dir,
        model_path,
        runtime,
        bind_host,
        host,
        port,
        _normalize_optional_str(os.getenv("path_appendix")),
        config_path,
        (resolved_model_dir / "sysconfig.properties").exists(),
    )

    return MepEmbeddingLaunchConfig(
        model_dir=resolved_model_dir,
        model_path=model_path,
        served_model_name=served_model_name,
        host=host,
        bind_host=bind_host,
        port=port,
        api_key=api_key,
        runner=runner,
        startup_timeout_seconds=(
            startup_timeout_seconds or _DEFAULT_STARTUP_TIMEOUT_SECONDS
        ),
        dimensions=_parse_optional_int(properties.get("embedding.dimensions")),
        max_token_size=_parse_optional_int(properties.get("embedding.max_token_size")),
        max_model_len=_parse_optional_int(
            _resolve_property(
                properties,
                "RAGENT_MEP_VLLM_MAX_MODEL_LEN",
                "vllm.max_model_len",
                "embedding.max_model_len",
            )
        ),
        extra_args=extra_args,
        subprocess_env=_resolve_subprocess_env(properties),
        install_requirements=_parse_string_list(
            _resolve_property(
                properties,
                "RAGENT_MEP_VLLM_INSTALL_REQUIREMENTS",
                "vllm.install_requirements",
            )
        ),
        uninstall_packages=_parse_string_list(
            _resolve_property(
                properties,
                "RAGENT_MEP_VLLM_UNINSTALL_PACKAGES",
                "vllm.uninstall_packages",
            )
        ),
        install_no_deps=(
            _parse_optional_bool(install_no_deps_value)
            if install_no_deps_value is not None
            else True
        ),
        install_force_reinstall=(
            _parse_optional_bool(install_force_reinstall_value)
            if install_force_reinstall_value is not None
            else True
        ),
        install_all_wheelhouse_wheels=(
            _parse_optional_bool(install_all_wheelhouse_wheels_value)
            if install_all_wheelhouse_wheels_value is not None
            else False
        ),
        launch_mode=launch_mode,
        runtime=runtime,
        device=_resolve_property(
            properties,
            "RAGENT_MEP_EMBEDDING_DEVICE",
            "embedding.device",
        ),
        batch_size=(
            _parse_optional_int(
                _resolve_property(
                    properties,
                    "RAGENT_MEP_EMBEDDING_BATCH_SIZE",
                    "embedding.batch_size",
                )
            )
            or 8
        ),
        pooling=(
            _resolve_property(
                properties,
                "RAGENT_MEP_EMBEDDING_POOLING",
                "embedding.pooling",
            )
            or "auto"
        ).lower(),
        normalize_embeddings=(
            _parse_optional_bool(
                _resolve_property(
                    properties,
                    "RAGENT_MEP_EMBEDDING_NORMALIZE",
                    "embedding.normalize",
                    "embedding.normalize_embeddings",
                )
            )
            if _resolve_property(
                properties,
                "RAGENT_MEP_EMBEDDING_NORMALIZE",
                "embedding.normalize",
                "embedding.normalize_embeddings",
            )
            is not None
            else True
        ),
        trust_remote_code=(
            _parse_optional_bool(
                _resolve_property(
                    properties,
                    "RAGENT_MEP_EMBEDDING_TRUST_REMOTE_CODE",
                    "embedding.trust_remote_code",
                )
            )
            if _resolve_property(
                properties,
                "RAGENT_MEP_EMBEDDING_TRUST_REMOTE_CODE",
                "embedding.trust_remote_code",
            )
            is not None
            else True
        ),
        config_path=config_path,
        data_dir=resolved_data_dir,
    )


def build_vllm_command_candidates(
    config: MepEmbeddingLaunchConfig,
) -> list[tuple[str, ...]]:
    common_args = [
        "--host",
        config.bind_host,
        "--port",
        str(config.port),
        "--served-model-name",
        config.served_model_name,
    ]
    if _should_pass_vllm_api_key(config.api_key):
        common_args.extend(["--api-key", config.api_key])
    if config.max_model_len is not None:
        common_args.extend(["--max-model-len", str(config.max_model_len)])
    common_args.extend(config.extra_args)

    launch_mode = config.launch_mode
    if launch_mode not in {"auto", "cli", "module"}:
        raise ValueError(
            f"Unsupported vLLM launch mode: {config.launch_mode!r}. "
            "Use one of: auto | cli | module"
        )

    candidates: list[tuple[str, ...]] = []
    cli_available = shutil.which("vllm") is not None
    module_available = importlib.util.find_spec("vllm") is not None

    if launch_mode in {"auto", "cli"} and cli_available:
        cli_args = [
            "vllm",
            "serve",
            str(config.model_path),
            *common_args,
        ]
        if config.runner:
            cli_args.extend(["--runner", config.runner])
        candidates.append(tuple(cli_args))

    if launch_mode in {"auto", "module"} and module_available:
        module_args = [
            sys.executable,
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--model",
            str(config.model_path),
            *common_args,
        ]
        if config.runner:
            module_args.extend(["--runner", config.runner])
        candidates.append(tuple(module_args))

    if not candidates:
        raise RuntimeError(
            "vLLM is not available in the current runtime. "
            "Expected either the `vllm` CLI on PATH or the Python `vllm` package."
        )
    return candidates


def _split_env_script_list(value: str) -> tuple[str, ...]:
    raw_parts: list[str] = []
    for chunk in value.replace(",", os.pathsep).split(os.pathsep):
        normalized = chunk.strip()
        if normalized:
            raw_parts.append(normalized)
    return tuple(raw_parts)


def _resolve_ascend_env_scripts() -> tuple[Path, ...]:
    configured_single = _normalize_optional_str(os.getenv("RAGENT_ASCEND_SET_ENV_SH"))
    configured_multi = _normalize_optional_str(os.getenv("RAGENT_ASCEND_ENV_SHS"))
    if configured_single is not None:
        raw_scripts = (configured_single,)
    elif configured_multi is not None:
        raw_scripts = _split_env_script_list(configured_multi)
    else:
        raw_scripts = _DEFAULT_ASCEND_ENV_SCRIPTS

    resolved: list[Path] = []
    seen: set[Path] = set()
    for raw_script in raw_scripts:
        candidate = Path(raw_script).expanduser()
        if not candidate.is_file():
            continue
        resolved_candidate = candidate.resolve()
        if resolved_candidate in seen:
            continue
        resolved.append(resolved_candidate)
        seen.add(resolved_candidate)
    return tuple(resolved)


def _load_env_after_sourcing_scripts(
    script_paths: tuple[Path, ...],
    base_env: dict[str, str],
) -> dict[str, str]:
    source_commands = "; ".join(
        f"source {shlex.quote(str(script_path))} >/dev/null 2>&1 || true"
        for script_path in script_paths
    )
    command = f"{source_commands}; env -0"
    completed = subprocess.run(
        ["bash", "-lc", command],
        check=False,
        env=base_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        script_list = ", ".join(str(path) for path in script_paths)
        raise RuntimeError(
            f"failed to source Ascend environment scripts: {script_list}; {stderr}"
        )

    sourced_env: dict[str, str] = {}
    for raw_item in completed.stdout.split(b"\0"):
        if not raw_item or b"=" not in raw_item:
            continue
        key, value = raw_item.split(b"=", 1)
        sourced_env[key.decode("utf-8", errors="surrogateescape")] = value.decode(
            "utf-8",
            errors="surrogateescape",
        )
    return sourced_env


def _prepend_env_path(env: dict[str, str], key: str, raw_prefix: str | None) -> None:
    if not raw_prefix:
        return
    existing_parts = [part for part in env.get(key, "").split(os.pathsep) if part]
    prefix_parts = [part for part in raw_prefix.split(os.pathsep) if part]
    if not prefix_parts:
        return

    merged: list[str] = []
    seen: set[str] = set()
    for part in (*prefix_parts, *existing_parts):
        if part in seen:
            continue
        seen.add(part)
        merged.append(part)
    env[key] = os.pathsep.join(merged)


def _prepend_bootstrapped_pythonpath(env: dict[str, str]) -> None:
    _prepend_env_path(
        env,
        "PYTHONPATH",
        os.getenv("RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH"),
    )


def build_vllm_subprocess_env(
    config: MepEmbeddingLaunchConfig | None = None,
) -> dict[str, str]:
    env = os.environ.copy()
    for key, value in _VLLM_SUBPROCESS_DEFAULT_ENV.items():
        env.setdefault(key, value)
    _prepend_bootstrapped_pythonpath(env)

    ascend_env_scripts = _resolve_ascend_env_scripts()
    if ascend_env_scripts:
        try:
            sourced_env = _load_env_after_sourcing_scripts(ascend_env_scripts, env)
        except Exception as exc:
            logger.warning("Unable to load Ascend CANN environment: %s", exc)
        else:
            # Keep explicit runtime overrides from the platform or caller, but
            # merge the CANN library/path additions that set_env.sh contributes.
            for key, value in sourced_env.items():
                if key in os.environ and key not in {
                    "PATH",
                    "LD_LIBRARY_PATH",
                    "PYTHONPATH",
                }:
                    continue
                env[key] = value
    for key, value in _VLLM_SUBPROCESS_DEFAULT_ENV.items():
        env.setdefault(key, value)
    _prepend_bootstrapped_pythonpath(env)
    if config is not None:
        for key, value in config.subprocess_env:
            env[key] = value
    return env


def _normalize_distribution_name(name: str) -> str:
    return name.replace("_", "-").lower()


def _requirement_name_and_version(requirement: str) -> tuple[str, str]:
    match = _EXACT_REQUIREMENT_RE.match(requirement.strip())
    if match is None:
        raise ValueError(
            "vLLM runtime install requirements must be exact pins, "
            f"got: {requirement!r}"
        )
    return _normalize_distribution_name(match.group(1)), match.group(2)


def _install_artifact_name_and_version(path: Path) -> tuple[str, str] | None:
    if path.suffix == ".whl":
        parts = path.name[:-4].split("-")
        if len(parts) < 2:
            return None
        return _normalize_distribution_name(parts[0]), parts[1]

    if path.name.endswith(".tar.gz"):
        stem = path.name[:-7]
    elif path.suffix == ".zip":
        stem = path.name[:-4]
    else:
        return None

    if "-" not in stem:
        return None
    name, version = stem.rsplit("-", 1)
    if not name or not version:
        return None
    return _normalize_distribution_name(name), version


def _distribution_is_loaded_from_wheel(dist: importlib_metadata.Distribution) -> bool:
    try:
        location = Path(str(dist.locate_file("")))
    except Exception:
        return False
    return any(part.endswith(".whl") for part in location.parts) or location.name.endswith(
        ".whl"
    )


def _installed_requirements_satisfied(requirements: tuple[str, ...]) -> bool:
    for requirement in requirements:
        name, expected_version = _requirement_name_and_version(requirement)
        try:
            distribution = importlib_metadata.distribution(name)
        except importlib_metadata.PackageNotFoundError:
            return False
        if _distribution_is_loaded_from_wheel(distribution):
            return False
        installed_version = distribution.version
        if installed_version != expected_version:
            return False
    return True


def _iter_runtime_platform_tags() -> tuple[str, ...]:
    try:
        from mep_dependency_bootstrap import iter_platform_tags
    except Exception:
        os_name = platform.system().strip().lower()
        if os_name.startswith("linux"):
            os_name = "linux"
        elif os_name.startswith("darwin"):
            os_name = "darwin"
        arch = platform.machine().strip().lower()
        if arch in {"x86_64", "amd64"}:
            arch = "amd64"
        elif arch in {"aarch64", "arm64"}:
            arch = "arm64"
        return (f"{os_name or 'unknown'}-{arch or 'unknown'}-py{sys.version_info.major}.{sys.version_info.minor}",)
    return tuple(iter_platform_tags())


def _iter_vllm_wheelhouse_dirs(config: MepEmbeddingLaunchConfig) -> tuple[Path, ...]:
    env_value = _normalize_optional_str(os.getenv("RAGENT_MEP_WHEELHOUSE_DIRS"))
    if env_value is not None:
        dirs = [
            Path(raw_path).expanduser().resolve()
            for raw_path in env_value.split(os.pathsep)
            if raw_path.strip()
        ]
        return tuple(path for path in dirs if path.is_dir())

    if config.data_dir is None:
        return ()

    wheelhouse_root = config.data_dir / "deps" / "wheelhouse"
    if not wheelhouse_root.is_dir():
        return ()

    resolved_dirs: list[Path] = []
    seen: set[Path] = set()
    for tag in _iter_runtime_platform_tags():
        candidate = (wheelhouse_root / tag).resolve()
        if candidate.is_dir() and candidate not in seen:
            seen.add(candidate)
            resolved_dirs.append(candidate)
    legacy_dir = wheelhouse_root.resolve()
    if legacy_dir not in seen:
        resolved_dirs.append(legacy_dir)
    return tuple(resolved_dirs)


def _validate_install_artifacts_exist(
    requirements: tuple[str, ...],
    wheelhouse_dirs: tuple[Path, ...],
) -> None:
    available = {
        parsed
        for wheelhouse_dir in wheelhouse_dirs
        for artifact_path in wheelhouse_dir.iterdir()
        if (parsed := _install_artifact_name_and_version(artifact_path)) is not None
    }
    missing: list[str] = []
    for requirement in requirements:
        if _requirement_name_and_version(requirement) not in available:
            missing.append(requirement)
    if missing:
        raise FileNotFoundError(
            "Configured vLLM runtime install requirements are missing "
            "installable artifacts from "
            f"wheelhouse: {', '.join(missing)}"
        )


def _iter_installable_wheelhouse_wheels(
    wheelhouse_dirs: tuple[Path, ...],
) -> tuple[Path, ...]:
    wheels: list[Path] = []
    seen: set[Path] = set()
    for wheelhouse_dir in wheelhouse_dirs:
        for wheel_path in sorted(wheelhouse_dir.glob("*.whl")):
            if wheel_path.name.startswith("._"):
                continue
            resolved = wheel_path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            wheels.append(resolved)
    return tuple(wheels)


def _run_pip_command(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        output = completed.stdout.strip()
        raise RuntimeError(
            f"pip command failed with exit_code={completed.returncode}: "
            f"{' '.join(command)}\n{output}"
        )


def _ensure_vllm_runtime_dependencies(config: MepEmbeddingLaunchConfig) -> None:
    if not config.install_requirements and not config.install_all_wheelhouse_wheels:
        return
    if (
        config.install_requirements
        and not config.install_all_wheelhouse_wheels
        and _installed_requirements_satisfied(config.install_requirements)
    ):
        return

    install_key = (
        "all-wheelhouse-wheels" if config.install_all_wheelhouse_wheels else "requirements",
        *config.install_requirements,
    )
    if install_key in _VLLM_DEPENDENCY_BOOTSTRAP_DONE:
        return

    wheelhouse_dirs = _iter_vllm_wheelhouse_dirs(config)
    if not wheelhouse_dirs:
        raise FileNotFoundError(
            "vLLM runtime install requirements are configured, but no matching "
            "data/deps/wheelhouse directory was found."
        )
    if config.install_requirements:
        _validate_install_artifacts_exist(config.install_requirements, wheelhouse_dirs)
    install_targets: list[str]
    if config.install_all_wheelhouse_wheels:
        wheelhouse_wheels = _iter_installable_wheelhouse_wheels(wheelhouse_dirs)
        if not wheelhouse_wheels:
            raise FileNotFoundError(
                "vLLM runtime is configured to install all wheelhouse wheels, "
                "but no .whl files were found."
            )
        install_targets = [str(wheel_path) for wheel_path in wheelhouse_wheels]
    else:
        install_targets = list(config.install_requirements)

    if config.uninstall_packages:
        uninstall_command = [
            sys.executable,
            "-m",
            "pip",
            "uninstall",
            *config.uninstall_packages,
            "-y",
        ]
        logger.info("Uninstalling image-provided vLLM packages: %s", " ".join(uninstall_command))
        _run_pip_command(uninstall_command)

    install_command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--no-index",
    ]
    for wheelhouse_dir in wheelhouse_dirs:
        install_command.extend(["--find-links", str(wheelhouse_dir)])
    if config.install_no_deps or config.install_all_wheelhouse_wheels:
        install_command.append("--no-deps")
    if config.install_force_reinstall:
        install_command.append("--force-reinstall")
    install_command.extend(install_targets)
    logger.info("Installing validated vLLM runtime packages: %s", " ".join(install_command))
    _run_pip_command(install_command)
    importlib.invalidate_caches()
    _VLLM_DEPENDENCY_BOOTSTRAP_DONE.add(install_key)


def _read_log_tail(path: Path, max_chars: int = 4000) -> str:
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace")
    if len(content) <= max_chars:
        return content
    return content[-max_chars:]


def _is_server_ready(config: MepEmbeddingLaunchConfig) -> bool:
    headers = {"Authorization": f"Bearer {config.api_key}"}
    response = requests.get(
        f"{config.base_url}/models",
        headers=headers,
        timeout=5,
    )
    if response.status_code != 200:
        return False
    payload = response.json()
    data = payload.get("data") or []
    available_ids = {
        item.get("id")
        for item in data
        if isinstance(item, dict) and item.get("id")
    }
    if not available_ids:
        return True
    return any(
        candidate in available_ids
        for candidate in (
            config.served_model_name,
            config.model_path.name,
            str(config.model_path),
        )
    )


def _launch_candidate(
    config: MepEmbeddingLaunchConfig,
    command: tuple[str, ...],
) -> LocalEmbeddingRuntime:
    log_file = tempfile.NamedTemporaryFile(
        prefix="ragent_mep_vllm_",
        suffix=".log",
        delete=False,
    )
    log_path = Path(log_file.name).resolve()
    log_file.close()

    with log_path.open("a", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            list(command),
            cwd=str(config.model_dir),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env=build_vllm_subprocess_env(config),
        )

    started_at = time.monotonic()
    last_error: Exception | None = None
    while time.monotonic() - started_at < config.startup_timeout_seconds:
        exit_code = process.poll()
        if exit_code is not None:
            log_tail = _read_log_tail(log_path)
            raise RuntimeError(
                "Local vLLM embedding process exited before becoming ready. "
                f"exit_code={exit_code}, command={' '.join(command)}, log_tail={log_tail}"
            )
        try:
            if _is_server_ready(config):
                return LocalEmbeddingRuntime(
                    config=config,
                    process=process,
                    launch_command=command,
                    log_path=log_path,
                )
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(1)

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    log_tail = _read_log_tail(log_path)
    raise RuntimeError(
        "Timed out waiting for local vLLM embedding service to become ready. "
        f"base_url={config.base_url}, command={' '.join(command)}, "
        f"last_error={last_error}, log_tail={log_tail}"
    )


def _apply_embedding_function_attributes(config: MepEmbeddingLaunchConfig) -> None:
    from .llm import openai as openai_module

    if config.dimensions is not None:
        openai_module.openai_embed.embedding_dim = config.dimensions
    if config.max_token_size is not None:
        openai_module.openai_embed.max_token_size = config.max_token_size


def _apply_ascend_env_to_current_process(config: MepEmbeddingLaunchConfig) -> None:
    env = build_vllm_subprocess_env(config)
    for key, value in env.items():
        if key in os.environ and key not in {
            "PATH",
            "LD_LIBRARY_PATH",
            "PYTHONPATH",
        }:
            continue
        if key.startswith(("ASCEND_", "HCCL_", "ATB_", "NPU_")) or key in {
            "PATH",
            "LD_LIBRARY_PATH",
            "PYTHONPATH",
        }:
            os.environ[key] = value


def _resolve_sentence_transformers_pooling(model_path: Path) -> str:
    pooling_config_path = model_path / "1_Pooling" / "config.json"
    if not pooling_config_path.is_file():
        return "cls"
    try:
        payload = json.loads(pooling_config_path.read_text(encoding="utf-8"))
    except Exception:
        return "cls"
    if payload.get("pooling_mode_cls_token") is True:
        return "cls"
    if payload.get("pooling_mode_mean_tokens") is True:
        return "mean"
    if payload.get("pooling_mode_max_tokens") is True:
        return "max"
    return "cls"


class _LocalTransformersEmbeddingModel:
    def __init__(self, config: MepEmbeddingLaunchConfig) -> None:
        self.config = config
        self._lock = threading.Lock()
        self._loaded = False
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._torch: Any | None = None
        self._device = "cpu"
        self._pooling = (
            _resolve_sentence_transformers_pooling(config.model_path)
            if config.pooling in {"", "auto"}
            else config.pooling
        )

    @property
    def output_dimensions(self) -> int:
        return self.config.dimensions or 1024

    def _load(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            _apply_ascend_env_to_current_process(self.config)

            import torch
            try:
                import torch_npu  # noqa: F401
            except Exception as exc:
                logger.warning("torch_npu import failed, using CPU if available: %s", exc)
            from transformers import AutoModel, AutoTokenizer

            has_npu = hasattr(torch, "npu") and torch.npu.is_available()
            configured_device = (self.config.device or "").strip()
            device = configured_device or ("npu:0" if has_npu else "cpu")
            if device.startswith("npu") and not has_npu:
                raise RuntimeError(
                    f"Configured embedding device {device!r}, but torch.npu is not available."
                )

            tokenizer = AutoTokenizer.from_pretrained(
                str(self.config.model_path),
                local_files_only=True,
                use_fast=True,
            )
            model = AutoModel.from_pretrained(
                str(self.config.model_path),
                local_files_only=True,
                trust_remote_code=self.config.trust_remote_code,
            )
            model.to(device)
            model.eval()

            self._torch = torch
            self._tokenizer = tokenizer
            self._model = model
            self._device = device
            self._loaded = True
            logger.info(
                "Loaded local transformers embedding model. model_path=%s device=%s "
                "pooling=%s dimensions=%s batch_size=%s",
                self.config.model_path,
                self._device,
                self._pooling,
                self.output_dimensions,
                self.config.batch_size,
            )

    def _pool(self, outputs: Any, attention_mask: Any) -> Any:
        torch = self._torch
        if torch is None:
            raise RuntimeError("local transformers embedding model is not loaded")

        last_hidden = outputs.last_hidden_state.float()
        if self._pooling == "cls":
            return last_hidden[:, 0]
        if self._pooling == "max":
            mask = attention_mask.unsqueeze(-1).to(last_hidden.dtype)
            masked = last_hidden.masked_fill(mask == 0, -1e9)
            return masked.max(dim=1).values

        mask = attention_mask.unsqueeze(-1).to(last_hidden.dtype)
        return (last_hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)

    def embed(self, texts: list[str]) -> np.ndarray:
        self._load()
        if not texts:
            return np.empty((0, self.output_dimensions), dtype=float)

        torch = self._torch
        tokenizer = self._tokenizer
        model = self._model
        if torch is None or tokenizer is None or model is None:
            raise RuntimeError("local transformers embedding model is not loaded")

        max_length = self.config.max_token_size or self.config.max_model_len or 8192
        batch_size = max(1, self.config.batch_size)
        chunks: list[np.ndarray] = []
        for offset in range(0, len(texts), batch_size):
            batch_texts = texts[offset : offset + batch_size]
            batch = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            )
            batch = {key: value.to(self._device) for key, value in batch.items()}

            with torch.inference_mode():
                outputs = model(**batch)
                if self._device.startswith("npu"):
                    torch.npu.synchronize()
                embeddings = self._pool(outputs, batch["attention_mask"])
                if self.config.dimensions is not None:
                    embeddings = embeddings[:, : self.config.dimensions]
                if self.config.normalize_embeddings:
                    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            chunks.append(embeddings.detach().cpu().numpy().astype(float))
        return np.concatenate(chunks, axis=0)

    def close(self) -> None:
        self._model = None
        self._tokenizer = None
        self._torch = None
        self._loaded = False


def _install_local_transformers_embedding_function(
    config: MepEmbeddingLaunchConfig,
) -> Callable[[], None]:
    from .llm import openai as openai_module

    previous_openai_embed = openai_module.openai_embed
    embedder = _LocalTransformersEmbeddingModel(config)

    async def local_transformers_embed(
        texts: list[str],
        *_args: Any,
        **_kwargs: Any,
    ) -> np.ndarray:
        return await asyncio.to_thread(embedder.embed, list(texts))

    local_transformers_embed.embedding_dim = embedder.output_dimensions  # type: ignore[attr-defined]
    local_transformers_embed.max_token_size = (  # type: ignore[attr-defined]
        config.max_token_size or config.max_model_len or 8192
    )
    openai_module.openai_embed = local_transformers_embed

    def cleanup() -> None:
        openai_module.openai_embed = previous_openai_embed
        embedder.close()

    return cleanup


def _bootstrap_local_transformers_embedding_runtime(
    config: MepEmbeddingLaunchConfig,
) -> LocalEmbeddingRuntime:
    cleanup_callback = _install_local_transformers_embedding_function(config)
    runtime = LocalEmbeddingRuntime(
        config=config,
        process=None,
        launch_command=("local-transformers", str(config.model_path)),
        log_path=Path(os.devnull),
        cleanup_callback=cleanup_callback,
    )
    runtime.apply_environment()
    logger.info(
        "Local transformers embedding runtime is ready. model=%s model_path=%s device=%s",
        config.served_model_name,
        config.model_path,
        config.device or "auto",
    )
    return runtime


def bootstrap_local_embedding_runtime(
    model_dir: str | os.PathLike[str],
    *,
    data_dir: str | os.PathLike[str] | None = None,
) -> LocalEmbeddingRuntime | None:
    autostart_enabled = _parse_optional_bool(
        os.getenv("RAGENT_MEP_EMBEDDING_AUTOSTART", "1")
    )
    if autostart_enabled is False:
        if _has_complete_external_embedding_config():
            return None
        raise RuntimeError(
            "Embedding autostart is disabled by RAGENT_MEP_EMBEDDING_AUTOSTART=0, "
            "but EMBEDDING_MODEL/EMBEDDING_MODEL_URL/EMBEDDING_MODEL_KEY are incomplete."
        )

    if _has_complete_external_embedding_config():
        logger.info(
            "Detected external embedding API config. Skip local vLLM bootstrap."
        )
        return None

    config = resolve_embedding_launch_config(model_dir, data_dir=data_dir)
    if config.runtime in {"transformers", "local_transformers", "local-transformers"}:
        return _bootstrap_local_transformers_embedding_runtime(config)
    if config.runtime != "vllm":
        raise ValueError(
            f"Unsupported embedding runtime: {config.runtime!r}. "
            "Use one of: vllm | transformers"
        )

    _ensure_vllm_runtime_dependencies(config)
    launch_errors: list[str] = []
    for command in build_vllm_command_candidates(config):
        logger.info(
            "Bootstrapping local embedding service via vLLM. model_path=%s base_url=%s command=%s",
            config.model_path,
            config.base_url,
            " ".join(command),
        )
        try:
            runtime = _launch_candidate(config, command)
        except Exception as exc:
            logger.warning("Failed to launch vLLM candidate: %s", exc)
            launch_errors.append(str(exc))
            continue
        runtime.apply_environment()
        _apply_embedding_function_attributes(config)
        logger.info(
            "Local embedding service is ready. model=%s base_url=%s log_path=%s",
            config.served_model_name,
            config.base_url,
            runtime.log_path,
        )
        return runtime

    joined_errors = "\n---\n".join(launch_errors)
    raise RuntimeError(
        "Unable to bootstrap local vLLM embedding service from model package.\n"
        f"{joined_errors}"
    )


__all__ = [
    "LocalEmbeddingRuntime",
    "MepEmbeddingLaunchConfig",
    "bootstrap_local_embedding_runtime",
    "build_vllm_command_candidates",
    "build_vllm_subprocess_env",
    "resolve_embedding_launch_config",
]
