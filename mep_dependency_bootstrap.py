from __future__ import annotations

import json
import os
import site
import sys
from pathlib import Path
from typing import Iterator


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
        yield (deps_dir / relative_dir).resolve()

    wheelhouse_dir = deps_dir / "wheelhouse"
    if wheelhouse_dir.is_dir():
        yield from sorted(wheelhouse_dir.glob("*.whl"))


def _prepend_import_path(path: Path) -> bool:
    if not path.exists():
        return False
    path_text = str(path)
    if path.is_dir():
        site.addsitedir(path_text)
    if path_text in sys.path:
        sys.path.remove(path_text)
    sys.path.insert(0, path_text)
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
        for dependency_path in iter_mep_dependency_paths(data_dir):
            if dependency_path in seen_dependency_paths:
                continue
            seen_dependency_paths.add(dependency_path)
            if _prepend_import_path(dependency_path):
                added_paths.append(str(dependency_path))
    if added_paths:
        os.environ["RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH"] = os.pathsep.join(
            added_paths
        )
    return tuple(added_paths)


__all__ = [
    "bootstrap_mep_data_dependencies",
    "iter_mep_data_dir_candidates",
    "iter_mep_dependency_paths",
]
