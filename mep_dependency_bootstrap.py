from __future__ import annotations

import json
import os
import platform
import site
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Iterator

try:
    from importlib import metadata as importlib_metadata
except ImportError:  # pragma: no cover - Python < 3.8 is not supported here.
    import importlib_metadata  # type: ignore


_NATIVE_WHEEL_SUFFIXES = (".so", ".pyd", ".dll", ".dylib")
_KEYWORD_FALLBACK_MODEL_RELATIVE_DIR = (
    "models/keyword_extraction/knowledgator-gliner-x-small"
)
_OFFLINE_REQUIREMENTS_DONE: set[Path] = set()


def _maybe_json_loads(value: str):
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _resolve_component_runtime_data_dir(current_dir: Path) -> Path | None:
    for candidate in (current_dir, *current_dir.parents):
        if candidate.name == "component" and (candidate / "config.json").is_file():
            return (candidate.parent / "data").resolve()
    return None


def _resolve_sfs_data_dir() -> Path | None:
    raw_model_sfs = (os.getenv("MODEL_SFS") or "").strip()
    model_object_id = (os.getenv("MODEL_OBJECT_ID") or "").strip()
    if not raw_model_sfs or not model_object_id:
        return None
    payload = _maybe_json_loads(raw_model_sfs)
    if not isinstance(payload, dict):
        return None
    sfs_base_path = payload.get("sfsBasePath")
    if not isinstance(sfs_base_path, str) or not sfs_base_path.strip():
        return None
    return (Path(sfs_base_path).expanduser() / model_object_id / "data").resolve()


def iter_mep_data_dir_candidates(current_dir: Path) -> Iterator[Path]:
    explicit_data_dir = os.getenv("RAGENT_MEP_DATA_DIR")
    if explicit_data_dir:
        yield Path(explicit_data_dir).expanduser().resolve()

    runtime_data_dir = _resolve_component_runtime_data_dir(current_dir)
    if runtime_data_dir is not None:
        yield runtime_data_dir

    sfs_data_dir = _resolve_sfs_data_dir()
    if sfs_data_dir is not None:
        yield sfs_data_dir

    yield (current_dir / "data").resolve()


def _normalize_os_name(system: str | None = None) -> str:
    normalized = (system or platform.system()).strip().lower()
    if normalized.startswith("linux"):
        return "linux"
    if normalized.startswith("darwin"):
        return "darwin"
    return normalized or "unknown"


def _normalize_arch_name(machine: str | None = None) -> str:
    normalized = (machine or platform.machine()).strip().lower()
    if normalized in {"x86_64", "amd64"}:
        return "amd64"
    if normalized in {"aarch64", "arm64"}:
        return "arm64"
    return normalized or "unknown"


def _python_tag() -> str:
    return f"py{sys.version_info.major}.{sys.version_info.minor}"


def current_platform_tag() -> str:
    return f"{_normalize_os_name()}-{_normalize_arch_name()}-{_python_tag()}"


def iter_platform_tags() -> Iterator[str]:
    explicit_tag = (os.getenv("RAGENT_MEP_PLATFORM_TAG") or "").strip()
    if explicit_tag:
        yield explicit_tag

    os_name = _normalize_os_name()
    normalized_arch = _normalize_arch_name()
    raw_arch = (platform.machine() or "").strip().lower()
    py_tag = _python_tag()
    candidates = [f"{os_name}-{normalized_arch}-{py_tag}"]
    if raw_arch and raw_arch != normalized_arch:
        candidates.append(f"{os_name}-{raw_arch}-{py_tag}")

    seen: set[str] = {explicit_tag} if explicit_tag else set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate


def _env_flag_enabled(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_flag_disabled(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"0", "false", "no", "off"}


def _wheel_has_native_extensions(wheel_path: Path) -> bool:
    try:
        with zipfile.ZipFile(wheel_path) as wheel:
            return any(
                name.lower().endswith(_NATIVE_WHEEL_SUFFIXES)
                for name in wheel.namelist()
            )
    except zipfile.BadZipFile:
        return False


def _distribution_and_version_from_wheel(wheel_path: Path) -> tuple[str, str] | None:
    wheel_name = wheel_path.name
    if not wheel_name.endswith(".whl") or "-" not in wheel_name:
        return None
    parts = wheel_name[:-4].split("-")
    if len(parts) < 2:
        return None
    distribution = parts[0].replace("_", "-").lower()
    version = parts[1]
    if not distribution or not version:
        return None
    return distribution, version


def _wheel_should_be_added(wheel_path: Path) -> bool:
    if _wheel_has_native_extensions(wheel_path) and not _env_flag_enabled(
        "RAGENT_MEP_ALLOW_NATIVE_WHEEL_ZIPIMPORT"
    ):
        return False

    if _env_flag_enabled("RAGENT_MEP_FORCE_WHEELHOUSE"):
        return True

    parsed = _distribution_and_version_from_wheel(wheel_path)
    if parsed is None:
        return True
    distribution, wheel_version = parsed
    try:
        installed_version = importlib_metadata.version(distribution)
    except importlib_metadata.PackageNotFoundError:
        return True
    return installed_version != wheel_version


def _iter_existing_platform_dirs(root: Path) -> Iterator[Path]:
    for tag in iter_platform_tags():
        candidate = root / tag
        if candidate.is_dir():
            yield candidate


def _iter_wheelhouse_dirs(
    deps_dir: Path,
    root_name: str = "wheelhouse",
) -> Iterator[Path]:
    wheelhouse_root = deps_dir / root_name
    if not wheelhouse_root.is_dir():
        return

    yielded: set[Path] = set()
    for candidate in _iter_existing_platform_dirs(wheelhouse_root):
        resolved = candidate.resolve()
        yielded.add(resolved)
        yield resolved

    legacy_flat_dir = wheelhouse_root.resolve()
    if legacy_flat_dir not in yielded:
        yield legacy_flat_dir


def _iter_platform_named_files(
    deps_dir: Path,
    *,
    prefix: str,
    suffix: str = ".txt",
) -> Iterator[Path]:
    seen: set[Path] = set()
    for tag in iter_platform_tags():
        candidate = deps_dir / f"{prefix}-{tag}{suffix}"
        if candidate.is_file():
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield resolved


def _resolve_constraints_file(deps_dir: Path) -> Path | None:
    return next(
        _iter_platform_named_files(
            deps_dir,
            prefix="constraints",
        ),
        None,
    )


def _iter_offline_requirements_files(deps_dir: Path) -> Iterator[Path]:
    yield from _iter_platform_named_files(
        deps_dir,
        prefix="requirements",
    )


def _run_offline_pip_install(
    *,
    requirements_file: Path,
    constraints_file: Path | None,
    wheelhouse_dirs: tuple[Path, ...],
) -> None:
    _validate_wheelhouse_wheels(wheelhouse_dirs)

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-index",
    ]
    for wheelhouse_dir in wheelhouse_dirs:
        command.extend(["--find-links", str(wheelhouse_dir)])
    if constraints_file is not None:
        command.extend(["-c", str(constraints_file)])
    command.extend(["-r", str(requirements_file)])

    completed = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "offline MEP dependency installation failed with exit_code="
            f"{completed.returncode}: {' '.join(command)}\n{completed.stdout}"
        )


def _validate_wheelhouse_wheels(wheelhouse_dirs: tuple[Path, ...]) -> None:
    invalid_wheels: list[str] = []
    for wheelhouse_dir in wheelhouse_dirs:
        for wheel_path in sorted(wheelhouse_dir.glob("*.whl")):
            try:
                with zipfile.ZipFile(wheel_path) as wheel:
                    corrupt_member = wheel.testzip()
            except (OSError, zipfile.BadZipFile) as exc:
                invalid_wheels.append(f"{wheel_path}: {exc}")
                continue
            if corrupt_member is not None:
                invalid_wheels.append(
                    f"{wheel_path}: corrupt archive member {corrupt_member}"
                )

    if invalid_wheels:
        raise RuntimeError(
            "offline MEP wheelhouse contains invalid wheel file(s):\n"
            + "\n".join(f"- {detail}" for detail in invalid_wheels)
        )


def _refresh_site_paths() -> None:
    try:
        site.addsitedir(site.getusersitepackages())
    except Exception:
        pass
    try:
        for site_package_dir in site.getsitepackages():
            site.addsitedir(site_package_dir)
    except Exception:
        pass


def ensure_mep_offline_requirements(
    current_dir: str | os.PathLike[str],
) -> tuple[str, ...]:
    if _env_flag_disabled("RAGENT_MEP_OFFLINE_PIP_INSTALL"):
        return ()

    resolved_current_dir = Path(current_dir).expanduser().resolve()
    installed_from: list[str] = []
    seen_data_dirs: set[Path] = set()
    for data_dir in iter_mep_data_dir_candidates(resolved_current_dir):
        if data_dir in seen_data_dirs:
            continue
        seen_data_dirs.add(data_dir)
        deps_dir = data_dir / "deps"
        if not deps_dir.is_dir():
            continue

        wheelhouse_dirs = tuple(
            wheelhouse_dir
            for wheelhouse_dir in _iter_wheelhouse_dirs(deps_dir)
            if wheelhouse_dir.is_dir() and any(wheelhouse_dir.glob("*.whl"))
        )
        if not wheelhouse_dirs:
            continue

        constraints_file = _resolve_constraints_file(deps_dir)
        for requirements_file in _iter_offline_requirements_files(deps_dir):
            if requirements_file in _OFFLINE_REQUIREMENTS_DONE:
                continue
            _run_offline_pip_install(
                requirements_file=requirements_file,
                constraints_file=constraints_file,
                wheelhouse_dirs=wheelhouse_dirs,
            )
            _OFFLINE_REQUIREMENTS_DONE.add(requirements_file)
            installed_from.append(str(requirements_file))

    if installed_from:
        _refresh_site_paths()
    return tuple(installed_from)


def iter_mep_dependency_paths(data_dir: Path) -> Iterator[Path]:
    deps_dir = data_dir / "deps"
    extra_pythonpath = os.getenv("RAGENT_MEP_EXTRA_PYTHONPATH") or ""
    for env_path in extra_pythonpath.split(os.pathsep):
        if env_path.strip():
            yield Path(env_path).expanduser().resolve()

    for relative_dir in (
        "pythonpath",
        "site-packages",
        "python",
    ):
        root = deps_dir / relative_dir
        for platform_dir in _iter_existing_platform_dirs(root):
            yield platform_dir.resolve()
        yield root.resolve()

    for wheelhouse_dir in _iter_wheelhouse_dirs(deps_dir, "keyword_wheelhouse"):
        for wheel_path in sorted(wheelhouse_dir.glob("*.whl")):
            if _wheel_should_be_added(wheel_path):
                yield wheel_path.resolve()

    for wheelhouse_dir in _iter_wheelhouse_dirs(deps_dir):
        for wheel_path in sorted(wheelhouse_dir.glob("*.whl")):
            if _wheel_should_be_added(wheel_path):
                yield wheel_path.resolve()


def _configure_keyword_fallback_model(data_dir: Path) -> None:
    model_dir = (data_dir / _KEYWORD_FALLBACK_MODEL_RELATIVE_DIR).resolve()
    if not model_dir.is_dir():
        return
    if not (os.getenv("RAG_KEYWORD_FALLBACK_MODEL") or "").strip():
        os.environ["RAG_KEYWORD_FALLBACK_MODEL"] = str(model_dir)
    if not (os.getenv("RAG_KEYWORD_FALLBACK_DEVICE") or "").strip():
        os.environ["RAG_KEYWORD_FALLBACK_DEVICE"] = "cpu"


def _prepend_import_path(path: Path, *, index: int = 0) -> bool:
    if not path.exists():
        return False
    path_text = str(path)
    if path.is_dir():
        site.addsitedir(path_text)
    if path_text in sys.path:
        sys.path.remove(path_text)
    sys.path.insert(index, path_text)
    return True


def bootstrap_mep_data_dependencies(current_dir: str | os.PathLike[str]) -> tuple[str, ...]:
    resolved_current_dir = Path(current_dir).expanduser().resolve()
    added_paths: list[str] = []
    seen_data_dirs: set[Path] = set()
    seen_dependency_paths: set[Path] = set()
    for data_dir in iter_mep_data_dir_candidates(resolved_current_dir):
        if data_dir in seen_data_dirs:
            continue
        seen_data_dirs.add(data_dir)
        if not data_dir.is_dir():
            continue
        _configure_keyword_fallback_model(data_dir)
        for dependency_path in iter_mep_dependency_paths(data_dir):
            if dependency_path in seen_dependency_paths:
                continue
            seen_dependency_paths.add(dependency_path)
            if _prepend_import_path(dependency_path, index=len(added_paths)):
                added_paths.append(str(dependency_path))
    if added_paths:
        os.environ["RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH"] = os.pathsep.join(
            added_paths
        )
    else:
        os.environ.pop("RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH", None)
    return tuple(added_paths)


__all__ = [
    "bootstrap_mep_data_dependencies",
    "current_platform_tag",
    "ensure_mep_offline_requirements",
    "iter_mep_data_dir_candidates",
    "iter_mep_dependency_paths",
    "iter_platform_tags",
]
