from __future__ import annotations

import importlib.util
import logging
import os
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests


logger = logging.getLogger("ragent.mep_embedding_runtime")

_TRUE_VALUES = {"1", "true", "yes", "on"}
_MANAGED_ENV_VARS = (
    "EMBEDDING_MODEL",
    "EMBEDDING_MODEL_KEY",
    "EMBEDDING_MODEL_URL",
    "EMBEDDING_PROVIDER",
)
_LOCAL_PROVIDER = "custom_openai"
_DEFAULT_MODEL_NAME = "BAAI/bge-m3"
_DEFAULT_API_KEY = "EMPTY"
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_RUNNER = "pooling"
_DEFAULT_STARTUP_TIMEOUT_SECONDS = 300.0
_MODEL_DIR_MARKERS = ("config.json", "tokenizer.json")


@dataclass(frozen=True)
class MepEmbeddingLaunchConfig:
    model_dir: Path
    model_path: Path
    served_model_name: str
    host: str
    port: int
    api_key: str
    runner: str
    startup_timeout_seconds: float
    dimensions: int | None = None
    max_token_size: int | None = None
    max_model_len: int | None = None
    extra_args: tuple[str, ...] = ()
    launch_mode: str = "auto"

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}/v1"


@dataclass
class LocalEmbeddingRuntime:
    config: MepEmbeddingLaunchConfig
    process: subprocess.Popen[Any]
    launch_command: tuple[str, ...]
    log_path: Path
    _env_backup: dict[str, str | None] = field(default_factory=dict, repr=False)

    def apply_environment(self) -> None:
        if not self._env_backup:
            for key in _MANAGED_ENV_VARS:
                self._env_backup[key] = os.getenv(key)
        os.environ["EMBEDDING_MODEL"] = self.config.served_model_name
        os.environ["EMBEDDING_MODEL_KEY"] = self.config.api_key
        os.environ["EMBEDDING_MODEL_URL"] = self.config.base_url
        os.environ["EMBEDDING_PROVIDER"] = _LOCAL_PROVIDER

    def restore_environment(self) -> None:
        for key, previous_value in self._env_backup.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value
        self._env_backup.clear()

    def shutdown(self) -> None:
        self.restore_environment()

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


def _find_available_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _looks_like_embedding_model_dir(candidate: Path) -> bool:
    return candidate.is_dir() and all((candidate / marker).exists() for marker in _MODEL_DIR_MARKERS)


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
        candidate = Path(configured_path).expanduser()
        if not candidate.is_absolute():
            candidate = (model_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if not _looks_like_embedding_model_dir(candidate):
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
        raise FileNotFoundError(
            "No embedding model directory found under model/. "
            f"Checked: {model_dir}"
        )
    raise RuntimeError(
        "Multiple embedding model directories found under model/. "
        f"Please set RAGENT_MEP_EMBEDDING_MODEL_PATH explicitly. Candidates: {', '.join(str(item) for item in candidates)}"
    )


def resolve_embedding_launch_config(
    model_dir: str | os.PathLike[str],
) -> MepEmbeddingLaunchConfig:
    resolved_model_dir_input = Path(model_dir).expanduser().resolve()
    resolved_model_dir, preferred_model_path = _normalize_model_dir_input(
        resolved_model_dir_input
    )
    if not resolved_model_dir.exists():
        raise FileNotFoundError(f"MEP model directory does not exist: {resolved_model_dir}")
    if not resolved_model_dir.is_dir():
        raise ValueError(f"MEP model path is not a directory: {resolved_model_dir}")

    properties = _read_properties_file(resolved_model_dir / "sysconfig.properties")
    model_path = _resolve_model_path(
        resolved_model_dir,
        properties,
        preferred_model_path=preferred_model_path,
    )
    host = _resolve_property(
        properties,
        "RAGENT_MEP_EMBEDDING_HOST",
        "vllm.host",
    ) or _DEFAULT_HOST
    configured_port = _parse_optional_int(
        _resolve_property(
            properties,
            "RAGENT_MEP_EMBEDDING_PORT",
            "vllm.port",
        )
    )
    port = configured_port if configured_port not in (None, 0) else _find_available_port(host)
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

    logger.info(
        "Resolved embedding launch config. input_model_dir=%s bundle_model_dir=%s "
        "model_path=%s path_appendix=%s sysconfig_present=%s",
        resolved_model_dir_input,
        resolved_model_dir,
        model_path,
        _normalize_optional_str(os.getenv("path_appendix")),
        (resolved_model_dir / "sysconfig.properties").exists(),
    )

    return MepEmbeddingLaunchConfig(
        model_dir=resolved_model_dir,
        model_path=model_path,
        served_model_name=served_model_name,
        host=host,
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
        launch_mode=launch_mode,
    )


def build_vllm_command_candidates(
    config: MepEmbeddingLaunchConfig,
) -> list[tuple[str, ...]]:
    common_args = [
        "--host",
        config.host,
        "--port",
        str(config.port),
        "--api-key",
        config.api_key,
        "--served-model-name",
        config.served_model_name,
    ]
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
            module_args.extend(
                [
                    "--task",
                    "embed" if config.runner == "pooling" else config.runner,
                ]
            )
        candidates.append(tuple(module_args))

    if not candidates:
        raise RuntimeError(
            "vLLM is not available in the current runtime. "
            "Expected either the `vllm` CLI on PATH or the Python `vllm` package."
        )
    return candidates


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
            env=os.environ.copy(),
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


def bootstrap_local_embedding_runtime(
    model_dir: str | os.PathLike[str],
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

    config = resolve_embedding_launch_config(model_dir)
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
    "resolve_embedding_launch_config",
]
