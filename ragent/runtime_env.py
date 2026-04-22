from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from dotenv import dotenv_values, find_dotenv, load_dotenv


_LOCAL_RUNTIME_VALUES = {"", "local", "cli", "dev", "development"}
_MEP_RUNTIME_VALUES = {"mep", "component", "platform"}
_TRUE_VALUES = {"1", "true", "yes", "on"}
_MISSING = object()


@dataclass(frozen=True)
class RuntimeBootstrapState:
    runtime_env: str
    dotenv_loaded: bool
    dotenv_path: str | None = None


_BOOTSTRAP_STATE: RuntimeBootstrapState | None = None
_BOOTSTRAP_KEY: tuple[str, str | None, str] | None = None
_BOOTSTRAP_ENV_BACKUP: dict[str, str | object] = {}
_BOOTSTRAP_LOCK = Lock()


def _normalize_runtime_env(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in _LOCAL_RUNTIME_VALUES:
        return "local"
    if normalized in _MEP_RUNTIME_VALUES:
        return "mep"
    raise ValueError(
        f"Unsupported runtime environment: {value!r}. Use one of: local | mep"
    )


def detect_runtime_environment(explicit_runtime_env: str | None = None) -> str:
    for candidate in (
        explicit_runtime_env,
        os.getenv("RAGENT_RUNTIME_ENV"),
        os.getenv("RAGENT_ENV"),
    ):
        if candidate is None:
            continue
        return _normalize_runtime_env(candidate)
    return "local"


def is_mep_runtime(explicit_runtime_env: str | None = None) -> bool:
    return detect_runtime_environment(explicit_runtime_env) == "mep"


def should_skip_dotenv(runtime_env: str | None = None) -> bool:
    resolved_runtime = (
        _normalize_runtime_env(runtime_env)
        if runtime_env is not None
        else detect_runtime_environment()
    )
    if resolved_runtime == "mep":
        return True
    raw_override = (os.getenv("RAGENT_SKIP_DOTENV") or "").strip().lower()
    return raw_override in _TRUE_VALUES


def _iter_dotenv_candidates(repo_root: Path | None = None):
    discovered_dotenv = find_dotenv(".env", usecwd=True)
    if discovered_dotenv:
        yield Path(discovered_dotenv)

    resolved_repo_root = repo_root
    if resolved_repo_root is None:
        resolved_repo_root = Path(__file__).resolve().parent.parent

    repo_dotenv = resolved_repo_root / ".env"
    if repo_dotenv.exists():
        yield repo_dotenv


def _normalize_repo_root(
    repo_root: str | os.PathLike[str] | None,
) -> Path | None:
    if repo_root is None:
        return None
    return Path(repo_root).expanduser().resolve()


def _build_bootstrap_key(runtime_env: str, repo_root: Path | None) -> tuple[str, str | None, str]:
    return (
        runtime_env,
        str(repo_root) if repo_root is not None else None,
        str(Path.cwd().resolve()),
    )


def _restore_bootstrap_environment() -> None:
    global _BOOTSTRAP_ENV_BACKUP

    for key, previous_value in _BOOTSTRAP_ENV_BACKUP.items():
        if previous_value is _MISSING:
            os.environ.pop(key, None)
            continue
        os.environ[key] = str(previous_value)
    _BOOTSTRAP_ENV_BACKUP = {}


def _remember_preexisting_environment(keys: set[str]) -> None:
    for key in keys:
        if key in _BOOTSTRAP_ENV_BACKUP:
            continue
        if key in os.environ:
            _BOOTSTRAP_ENV_BACKUP[key] = os.environ[key]
            continue
        _BOOTSTRAP_ENV_BACKUP[key] = _MISSING


def _load_dotenv_file(path: Path) -> set[str]:
    dotenv_entries = dotenv_values(path)
    loaded_keys = {str(key) for key in dotenv_entries.keys() if key}
    _remember_preexisting_environment(loaded_keys)
    load_dotenv(dotenv_path=path, override=True)
    return loaded_keys


def bootstrap_runtime_environment(
    *,
    explicit_runtime_env: str | None = None,
    repo_root: str | os.PathLike[str] | None = None,
    force: bool = False,
) -> RuntimeBootstrapState:
    global _BOOTSTRAP_KEY, _BOOTSTRAP_STATE

    runtime_env = detect_runtime_environment(explicit_runtime_env)
    normalized_repo_root = _normalize_repo_root(repo_root)
    bootstrap_key = _build_bootstrap_key(runtime_env, normalized_repo_root)

    with _BOOTSTRAP_LOCK:
        if _BOOTSTRAP_STATE is not None and _BOOTSTRAP_KEY == bootstrap_key and not force:
            if explicit_runtime_env:
                os.environ["RAGENT_RUNTIME_ENV"] = runtime_env
            return _BOOTSTRAP_STATE

        _restore_bootstrap_environment()
        _BOOTSTRAP_STATE = None
        _BOOTSTRAP_KEY = None

        if explicit_runtime_env:
            os.environ["RAGENT_RUNTIME_ENV"] = runtime_env

        if should_skip_dotenv(runtime_env):
            _BOOTSTRAP_STATE = RuntimeBootstrapState(
                runtime_env=runtime_env,
                dotenv_loaded=False,
                dotenv_path=None,
            )
            _BOOTSTRAP_KEY = bootstrap_key
            return _BOOTSTRAP_STATE

        loaded_path: str | None = None
        loaded = False
        seen_paths: set[Path] = set()
        for candidate in _iter_dotenv_candidates(normalized_repo_root):
            resolved = candidate.expanduser().resolve()
            if resolved in seen_paths or not resolved.exists():
                continue
            _load_dotenv_file(resolved)
            loaded_path = str(resolved)
            loaded = True
            seen_paths.add(resolved)

        _BOOTSTRAP_STATE = RuntimeBootstrapState(
            runtime_env=runtime_env,
            dotenv_loaded=loaded,
            dotenv_path=loaded_path,
        )
        _BOOTSTRAP_KEY = bootstrap_key
        return _BOOTSTRAP_STATE


def get_runtime_bootstrap_state() -> RuntimeBootstrapState | None:
    return _BOOTSTRAP_STATE
