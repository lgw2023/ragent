from __future__ import annotations

import asyncio
import json
import os
import shutil
import sqlite3
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

from .inference_runtime import (
    InferenceRequest,
    InferenceRuntimeSession,
    normalize_conversation_history,
    normalize_query_mode,
    parse_history_turns,
)
from .runtime_env import bootstrap_runtime_environment, is_mep_runtime


bootstrap_runtime_environment()


_TRUE_VALUES = {"1", "true", "yes", "on"}
_RAGENT_SNAPSHOT_MARKERS = {
    "graph_chunk_entity_relation.graphml",
    "kv_store_text_chunks.json",
    "vdb_chunks.json",
}
_SQLITE_KV_NAMESPACES_FROM_JSON = ("full_docs", "text_chunks")


@dataclass(frozen=True)
class ComponentBundlePaths:
    current_dir: Path
    parent_dir: Path
    data_dir: Path
    model_dir: Path
    meta_dir: Path
    data_source: str
    model_source: str
    meta_source: str
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeProjectLayout:
    data_dir: Path
    model_dir: Path
    source_project_dir: Path
    runtime_project_dir: Path
    copied_to_runtime_dir: bool
    runtime_temp_root: Path | None = None


@dataclass(frozen=True)
class NormalizedMepRequest:
    inference_request: InferenceRequest
    action: str | None
    task_id: str | None
    base_path: Path | None
    generate_path: Path | None
    result_filename: str
    raw_data: dict[str, Any]


class AsyncLoopThread:
    def __init__(self, name: str = "ragent-mep-runtime"):
        self._loop = asyncio.new_event_loop()
        self._started = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name=name,
            daemon=True,
        )
        self._thread.start()
        self._started.wait()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._started.set()
        self._loop.run_forever()
        pending = asyncio.all_tasks(self._loop)
        if pending:
            for task in pending:
                task.cancel()
            self._loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )
        self._loop.close()

    def run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def close(self) -> None:
        if not self._loop.is_running():
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)


def _parse_optional_bool(value: Any, *, field_name: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized in _TRUE_VALUES:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"Invalid boolean value for {field_name}: {value!r}")


def _parse_string_list(value: Any, *, field_name: str) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple)):
        result: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                result.append(text)
        return result
    raise ValueError(f"Invalid list value for {field_name}: {value!r}")


def _first_present(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping:
            return mapping.get(key)
    return None


def _has_value(value: Any) -> bool:
    return value is not None and value != ""


def _first_with_fallback(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    tertiary: dict[str, Any],
    *keys: str,
) -> Any:
    for source in (primary, secondary, tertiary):
        for key in keys:
            if key in source and _has_value(source.get(key)):
                return source.get(key)
    return None


def _extract_first_file_info(data: dict[str, Any]) -> dict[str, Any]:
    file_info = data.get("fileInfo")
    if isinstance(file_info, list) and file_info and isinstance(file_info[0], dict):
        return file_info[0]
    return {}


def _maybe_json_loads(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _merge_process_spec_item(target: dict[str, Any], item: Any) -> None:
    if isinstance(item, str):
        parsed = _maybe_json_loads(item.strip())
        if parsed is not None:
            _merge_process_spec_item(target, parsed)
        elif "=" in item:
            key, value = item.split("=", 1)
            key = key.strip()
            if key:
                target[key] = value.strip()
        return

    if isinstance(item, list):
        for nested_item in item:
            _merge_process_spec_item(target, nested_item)
        return

    if not isinstance(item, dict):
        return

    for key_name in ("key", "name", "field", "fieldName", "paramName"):
        if key_name in item and "value" in item:
            key = str(item[key_name]).strip()
            if key:
                target[key] = item.get("value")
            return
    for key_name, value_name in (
        ("key", "val"),
        ("name", "val"),
        ("fieldName", "fieldValue"),
        ("paramName", "paramValue"),
    ):
        if key_name in item and value_name in item:
            key = str(item[key_name]).strip()
            if key:
                target[key] = item.get(value_name)
            return

    for key, value in item.items():
        if key in {"processSpec", "params", "parameters"}:
            _merge_process_spec_item(target, value)
        else:
            target[key] = value


def _normalize_process_spec(process_spec: Any) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    _merge_process_spec_item(normalized, process_spec)
    return normalized


def _resolve_source_json_path(file_info: dict[str, Any]) -> Path | None:
    source_image = file_info.get("sourceImage")
    source_path = file_info.get("sourcePath")
    if not isinstance(source_image, str) or not source_image.strip():
        return None

    image_path = Path(source_image).expanduser()
    if not image_path.is_absolute():
        if not isinstance(source_path, str) or not source_path.strip():
            return None
        image_path = Path(source_path).expanduser() / image_path
    image_path = image_path.resolve()
    if image_path.suffix.lower() != ".json" or not image_path.is_file():
        return None
    return image_path


def _load_source_json_fallback(file_info: dict[str, Any]) -> dict[str, Any]:
    source_json_path = _resolve_source_json_path(file_info)
    if source_json_path is None:
        return {}

    with source_json_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"input JSON must be an object: {source_json_path}")
    data_payload = payload.get("data")
    if isinstance(data_payload, dict):
        return data_payload
    return payload


def _resolve_optional_path(value: Any, *, field_name: str) -> Path | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string when provided")
    return Path(value).expanduser().resolve()


def _normalize_action(data: dict[str, Any]) -> str | None:
    action = _first_present(data, "action")
    if action in (None, ""):
        return None
    if not isinstance(action, str):
        raise ValueError("action must be a string when provided")
    normalized = action.strip().lower()
    if normalized not in {"create", "query"}:
        raise ValueError("action must be one of: create | query")
    return normalized


def get_mep_action(req_data: Any) -> str | None:
    if not isinstance(req_data, dict):
        return None
    data = req_data.get("data")
    if not isinstance(data, dict):
        return None
    return _normalize_action(data)


def _resolve_env_path(value: str | os.PathLike[str] | None) -> Path | None:
    if value in (None, ""):
        return None
    return Path(value).expanduser().resolve()


def _parse_model_sfs_object_root() -> tuple[Path | None, tuple[str, ...]]:
    diagnostics: list[str] = []
    raw_model_sfs = (os.getenv("MODEL_SFS") or "").strip()
    model_object_id = (os.getenv("MODEL_OBJECT_ID") or "").strip()
    if not raw_model_sfs:
        diagnostics.append("MODEL_SFS is not set")
        return None, tuple(diagnostics)
    if not model_object_id:
        diagnostics.append("MODEL_OBJECT_ID is not set")
        return None, tuple(diagnostics)

    payload = _maybe_json_loads(raw_model_sfs)
    if not isinstance(payload, dict):
        diagnostics.append("MODEL_SFS is not valid JSON")
        return None, tuple(diagnostics)

    sfs_base_path = payload.get("sfsBasePath")
    if not isinstance(sfs_base_path, str) or not sfs_base_path.strip():
        diagnostics.append("MODEL_SFS.sfsBasePath is missing")
        return None, tuple(diagnostics)

    object_root = (Path(sfs_base_path).expanduser() / model_object_id).resolve()
    diagnostics.append(f"SFS object root candidate={object_root}")
    return object_root, tuple(diagnostics)


def _looks_like_model_bundle_dir(candidate: Path) -> bool:
    return candidate.name == "model" or (candidate / "sysconfig.properties").exists()


def _build_runtime_root_candidates(runtime_root: Path) -> dict[str, Path]:
    resolved_runtime_root = runtime_root.expanduser().resolve()
    return {
        "model": resolved_runtime_root / "model",
        "data": resolved_runtime_root / "data",
        "meta": resolved_runtime_root / "meta",
    }


def _resolve_runtime_root_from_model_path(model_path: Path) -> Path | None:
    resolved_model_path = model_path.expanduser().resolve()
    if _looks_like_model_bundle_dir(resolved_model_path):
        return resolved_model_path.parent
    parent_dir = resolved_model_path.parent
    if _looks_like_model_bundle_dir(parent_dir):
        return parent_dir.parent
    return None


def _build_model_root_candidates(model_root: Path) -> dict[str, Path]:
    resolved_model_root = model_root.expanduser().resolve()
    if _looks_like_model_bundle_dir(resolved_model_root):
        candidates = _build_runtime_root_candidates(resolved_model_root.parent)
        candidates["model"] = resolved_model_root
        return candidates
    return _build_runtime_root_candidates(resolved_model_root)


def _is_component_package_dir(candidate: Path) -> bool:
    return candidate.name == "component" and (candidate / "config.json").is_file()


def _resolve_component_runtime_root(current_dir: Path) -> Path | None:
    resolved_current_dir = current_dir.expanduser().resolve()
    for candidate in (resolved_current_dir, *resolved_current_dir.parents):
        if _is_component_package_dir(candidate):
            return candidate.parent.resolve()
    return None


def _select_component_bundle_path(
    name: str,
    candidates: list[tuple[str, Path | None]],
) -> tuple[Path, str, tuple[str, ...]]:
    diagnostics: list[str] = []
    first_candidate: tuple[str, Path] | None = None
    seen_paths: set[Path] = set()

    for source, raw_path in candidates:
        resolved_path = _resolve_env_path(raw_path)
        if resolved_path is None:
            continue
        if resolved_path in seen_paths:
            continue
        seen_paths.add(resolved_path)

        exists = resolved_path.exists()
        diagnostics.append(
            f"{name} candidate source={source} path={resolved_path} exists={exists}"
        )
        if first_candidate is None:
            first_candidate = (source, resolved_path)
        if exists:
            diagnostics.append(
                f"{name} selected source={source} path={resolved_path}"
            )
            return resolved_path, source, tuple(diagnostics)

    if first_candidate is None:
        raise RuntimeError(f"No candidate paths configured for {name}")

    diagnostics.append(
        f"{name} selected fallback source={first_candidate[0]} path={first_candidate[1]}"
    )
    return (
        first_candidate[1],
        f"{first_candidate[0]} (missing)",
        tuple(diagnostics),
    )


def resolve_component_bundle_paths(
    process_file: str | os.PathLike[str],
    *,
    data_dir_override: str | os.PathLike[str] | None = None,
    model_dir_override: str | os.PathLike[str] | None = None,
    model_root: str | os.PathLike[str] | None = None,
) -> ComponentBundlePaths:
    current_dir = Path(process_file).expanduser().resolve().parent
    parent_dir = current_dir.parent
    diagnostics: list[str] = []

    component_runtime_root = _resolve_component_runtime_root(current_dir)
    component_runtime_candidates = (
        _build_runtime_root_candidates(component_runtime_root)
        if component_runtime_root is not None
        else None
    )
    if component_runtime_root is not None:
        diagnostics.append(f"component runtime root={component_runtime_root}")
    else:
        diagnostics.append("component runtime root not detected from process_file")

    sfs_object_root, sfs_diagnostics = _parse_model_sfs_object_root()
    diagnostics.extend(sfs_diagnostics)

    model_root_candidates = (
        _build_model_root_candidates(Path(model_root))
        if model_root is not None
        else None
    )
    if model_root_candidates is not None:
        diagnostics.append(
            "model_root candidates="
            f"model={model_root_candidates['model']} "
            f"data={model_root_candidates['data']} "
            f"meta={model_root_candidates['meta']}"
        )

    model_absolute_dir = _resolve_env_path(os.getenv("MODEL_ABSOLUTE_DIR"))
    model_relative_dir = (
        os.getenv("MODEL_RELATIVE_DIR") or ""
    ).strip() or "model"
    model_absolute_runtime_root = (
        _resolve_runtime_root_from_model_path(model_absolute_dir)
        if model_absolute_dir is not None
        else None
    )
    model_absolute_sibling_candidates = (
        _build_runtime_root_candidates(model_absolute_runtime_root)
        if model_absolute_runtime_root is not None
        else None
    )

    data_dir, data_source, data_diagnostics = _select_component_bundle_path(
        "data",
        [
            ("explicit_data_dir_override", data_dir_override),
            (
                "runtime_sibling_data_dir",
                None
                if component_runtime_candidates is None
                else component_runtime_candidates["data"],
            ),
            (
                "sfs_object_data_dir",
                None if sfs_object_root is None else sfs_object_root / "data",
            ),
            (
                "model_absolute_data_dir",
                None
                if model_absolute_sibling_candidates is None
                else model_absolute_sibling_candidates["data"],
            ),
            (
                "model_root_data_dir",
                None if model_root_candidates is None else model_root_candidates["data"],
            ),
            ("local_env_data_dir", os.getenv("RAGENT_MEP_DATA_DIR")),
            ("legacy_current_dir_data_dir", current_dir / "data"),
        ],
    )
    model_dir, model_source, model_diagnostics = _select_component_bundle_path(
        "model",
        [
            ("explicit_model_dir_override", model_dir_override),
            (
                "runtime_sibling_model_dir",
                None
                if component_runtime_candidates is None
                else component_runtime_candidates["model"],
            ),
            ("sfs_model_absolute_dir", model_absolute_dir),
            (
                "sfs_model_relative_dir",
                None
                if sfs_object_root is None
                else sfs_object_root / model_relative_dir,
            ),
            (
                "sfs_default_model_dir",
                None if sfs_object_root is None else sfs_object_root / "model",
            ),
            (
                "model_root_model_dir",
                None
                if model_root_candidates is None
                else model_root_candidates["model"],
            ),
            ("local_env_model_dir", os.getenv("RAGENT_MEP_MODEL_DIR")),
            ("legacy_current_dir_model_dir", current_dir / "model"),
        ],
    )
    meta_dir, meta_source, meta_diagnostics = _select_component_bundle_path(
        "meta",
        [
            (
                "runtime_sibling_meta_dir",
                None
                if component_runtime_candidates is None
                else component_runtime_candidates["meta"],
            ),
            (
                "sfs_object_meta_dir",
                None if sfs_object_root is None else sfs_object_root / "meta",
            ),
            (
                "model_absolute_meta_dir",
                None
                if model_absolute_sibling_candidates is None
                else model_absolute_sibling_candidates["meta"],
            ),
            (
                "model_root_meta_dir",
                None if model_root_candidates is None else model_root_candidates["meta"],
            ),
            ("legacy_current_dir_meta_dir", current_dir / "meta"),
        ],
    )

    diagnostics.extend(data_diagnostics)
    diagnostics.extend(model_diagnostics)
    diagnostics.extend(meta_diagnostics)
    return ComponentBundlePaths(
        current_dir=current_dir,
        parent_dir=parent_dir,
        data_dir=data_dir,
        model_dir=model_dir,
        meta_dir=meta_dir,
        data_source=data_source,
        model_source=model_source,
        meta_source=meta_source,
        diagnostics=tuple(diagnostics),
    )


def is_ragent_project_snapshot(path: str | os.PathLike[str]) -> bool:
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_dir():
        return False
    return sum(1 for marker in _RAGENT_SNAPSHOT_MARKERS if (candidate / marker).exists()) >= 2


def resolve_single_snapshot_from_data_dir(data_dir: str | os.PathLike[str]) -> Path:
    resolved_data_dir = Path(data_dir).expanduser().resolve()
    if not resolved_data_dir.exists():
        raise FileNotFoundError(f"MEP data directory does not exist: {resolved_data_dir}")
    if not resolved_data_dir.is_dir():
        raise ValueError(f"MEP data path is not a directory: {resolved_data_dir}")

    snapshot_override = os.getenv("RAGENT_MEP_KG_DIR") or os.getenv("RAGENT_MEP_SNAPSHOT_DIR")
    if snapshot_override:
        override_path = Path(snapshot_override).expanduser()
        if not override_path.is_absolute():
            override_path = (resolved_data_dir / override_path).resolve()
        else:
            override_path = override_path.resolve()
        if not is_ragent_project_snapshot(override_path):
            raise ValueError(
                "Configured Ragent knowledge graph snapshot is invalid: "
                f"{override_path}"
            )
        return override_path

    if is_ragent_project_snapshot(resolved_data_dir):
        return resolved_data_dir

    candidates: list[Path] = []
    for container in (
        resolved_data_dir / "kg",
        resolved_data_dir / "snapshots",
    ):
        if is_ragent_project_snapshot(container):
            candidates.append(container)
        elif container.is_dir():
            candidates.extend(
                child
                for child in container.iterdir()
                if child.is_dir() and is_ragent_project_snapshot(child)
            )

    # Legacy compatibility: older local packages placed the one KG snapshot
    # directly under data/.
    candidates.extend(
        child
        for child in resolved_data_dir.iterdir()
        if child.is_dir() and is_ragent_project_snapshot(child)
    )
    candidates = sorted(set(candidates))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError(
            "No Ragent knowledge graph snapshot found under data/ or data/kg/. "
            f"Checked: {resolved_data_dir}"
        )
    raise ValueError(
        "Multiple Ragent knowledge graph snapshots found under data/. "
        "Initial MEP adapter only supports one built-in snapshot: "
        + ", ".join(str(item) for item in candidates)
    )


def _directory_is_writable(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    try:
        fd, probe_path = tempfile.mkstemp(prefix=".ragent_write_probe_", dir=path)
        os.close(fd)
        os.unlink(probe_path)
        return True
    except OSError:
        return False


def _env_flag_enabled(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in _TRUE_VALUES


def _normalize_legacy_kv_json_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("legacy KV JSON payload must be an object")
    if isinstance(payload.get("data"), dict):
        return dict(payload["data"])
    return dict(payload)


def _coerce_kv_timestamp(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _materialize_sqlite_kv_from_json(
    project_dir: Path,
    *,
    namespace: str,
) -> int:
    json_path = project_dir / f"kv_store_{namespace}.json"
    if not json_path.is_file():
        return 0

    sqlite_path = project_dir / f"kv_store_{namespace}.sqlite"
    raw_payload = json.loads(json_path.read_text(encoding="utf-8"))
    records = _normalize_legacy_kv_json_payload(raw_payload)
    if not records:
        return 0

    conn = sqlite3.connect(sqlite_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kv_entries (
                key TEXT PRIMARY KEY,
                entry_json TEXT NOT NULL,
                create_time INTEGER NOT NULL DEFAULT 0,
                update_time INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kv_entries_update_time ON kv_entries(update_time)"
        )
        now = int(time.time())
        rows = []
        for key, value in records.items():
            entry = dict(value) if isinstance(value, dict) else {"return": value}
            entry.pop("_id", None)
            if namespace == "text_chunks":
                entry.setdefault("llm_cache_list", [])
            create_time = _coerce_kv_timestamp(entry.get("create_time"), now)
            update_time = _coerce_kv_timestamp(entry.get("update_time"), create_time)
            entry["create_time"] = create_time
            entry["update_time"] = update_time
            rows.append(
                (
                    str(key),
                    json.dumps(entry, ensure_ascii=False, default=str),
                    create_time,
                    update_time,
                )
            )

        conn.executemany(
            """
            INSERT INTO kv_entries (
                key,
                entry_json,
                create_time,
                update_time
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                entry_json = excluded.entry_json,
                create_time = excluded.create_time,
                update_time = excluded.update_time
            """,
            rows,
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def materialize_sqlite_kv_stores_from_snapshot(project_dir: Path) -> dict[str, int]:
    return {
        namespace: _materialize_sqlite_kv_from_json(project_dir, namespace=namespace)
        for namespace in _SQLITE_KV_NAMESPACES_FROM_JSON
    }


def prepare_runtime_project_layout(
    *,
    data_dir: str | os.PathLike[str],
    model_dir: str | os.PathLike[str] | None = None,
    runtime_root: str | os.PathLike[str] | None = None,
) -> RuntimeProjectLayout:
    resolved_data_dir = Path(data_dir).expanduser().resolve()
    resolved_model_dir = (
        Path(model_dir).expanduser().resolve()
        if model_dir is not None
        else resolved_data_dir.parent / "model"
    )
    source_project_dir = resolve_single_snapshot_from_data_dir(resolved_data_dir)

    use_source_snapshot = _directory_is_writable(source_project_dir)
    if is_mep_runtime() and not _env_flag_enabled("RAGENT_MEP_USE_SOURCE_SNAPSHOT"):
        use_source_snapshot = False

    if use_source_snapshot:
        return RuntimeProjectLayout(
            data_dir=resolved_data_dir,
            model_dir=resolved_model_dir,
            source_project_dir=source_project_dir,
            runtime_project_dir=source_project_dir,
            copied_to_runtime_dir=False,
            runtime_temp_root=None,
        )

    runtime_root_base = os.getenv("RAGENT_MEP_RUNTIME_ROOT") or runtime_root
    if runtime_root_base is not None:
        runtime_root_base_path = Path(runtime_root_base).expanduser().resolve()
        runtime_root_base_path.mkdir(parents=True, exist_ok=True)
        runtime_temp_root = Path(
            tempfile.mkdtemp(prefix="ragent_mep_runtime_", dir=runtime_root_base_path)
        ).resolve()
    else:
        runtime_temp_root = Path(tempfile.mkdtemp(prefix="ragent_mep_runtime_")).resolve()
    target_project_dir = runtime_temp_root / source_project_dir.name
    shutil.copytree(source_project_dir, target_project_dir)
    materialize_sqlite_kv_stores_from_snapshot(target_project_dir)

    return RuntimeProjectLayout(
        data_dir=resolved_data_dir,
        model_dir=resolved_model_dir,
        source_project_dir=source_project_dir,
        runtime_project_dir=target_project_dir,
        copied_to_runtime_dir=True,
        runtime_temp_root=runtime_temp_root,
    )


def cleanup_runtime_project_layout(layout: RuntimeProjectLayout | None) -> None:
    if (
        layout is None
        or not layout.copied_to_runtime_dir
        or layout.runtime_temp_root is None
    ):
        return

    shutil.rmtree(layout.runtime_temp_root, ignore_errors=True)


def _normalize_result_filename(value: Any) -> str:
    result_filename = str(value).strip()
    if not result_filename:
        raise ValueError("result filename must not be empty")
    if "\x00" in result_filename:
        raise ValueError("result filename must be a plain file name")
    if result_filename in {".", ".."}:
        raise ValueError("result filename must be a plain file name")
    if "/" in result_filename or "\\" in result_filename:
        raise ValueError("result filename must be a plain file name")
    windows_path = PureWindowsPath(result_filename)
    if Path(result_filename).is_absolute() or windows_path.is_absolute():
        raise ValueError("result filename must be a plain file name")
    if windows_path.drive or windows_path.root:
        raise ValueError("result filename must be a plain file name")
    return result_filename


def normalize_mep_request(req_data: Any) -> NormalizedMepRequest:
    if req_data is None:
        raise ValueError("request data is missing")
    if not isinstance(req_data, dict):
        raise ValueError("request data must be a JSON object")

    data = req_data.get("data")
    if not isinstance(data, dict):
        raise ValueError("req_Data['data'] is required and must be a JSON object")

    action = _normalize_action(data)
    task_id_value = _first_present(data, "taskId", "task_id")
    task_id = str(task_id_value).strip() if task_id_value not in (None, "") else None
    base_path = _resolve_optional_path(
        _first_present(data, "basePath", "base_path"),
        field_name="basePath",
    )

    file_info = _extract_first_file_info(data)
    process_spec = _normalize_process_spec(file_info.get("processSpec"))
    source_json = _load_source_json_fallback(file_info)

    raw_query_type = str(
        _first_with_fallback(data, process_spec, source_json, "query_type", "queryType")
        or ""
    ).strip().lower()
    if raw_query_type not in {"onehop", "multihop", "chat"}:
        raise ValueError("query_type must be one of: onehop | multihop | chat")

    raw_query = _first_with_fallback(data, process_spec, source_json, "query", "question")
    if not isinstance(raw_query, str) or not raw_query.strip():
        raise ValueError("query is required and must be a non-empty string")

    raw_history = _first_with_fallback(
        data,
        process_spec,
        source_json,
        "conversation_history",
        "conversationHistory",
        "history",
    )
    conversation_history = (
        normalize_conversation_history(raw_history, source_name="conversation_history")
        if raw_history is not None
        else []
    )

    include_trace = _parse_optional_bool(
        _first_with_fallback(
            data,
            process_spec,
            source_json,
            "include_trace",
            "includeTrace",
            "trace",
            "debug",
        ),
        field_name="include_trace",
    )
    retrieval_only = _parse_optional_bool(
        _first_with_fallback(
            data,
            process_spec,
            source_json,
            "retrieval_only",
            "retrievalOnly",
        ),
        field_name="retrieval_only",
    )
    only_need_context = _parse_optional_bool(
        _first_with_fallback(
            data,
            process_spec,
            source_json,
            "only_need_context",
            "onlyNeedContext",
        ),
        field_name="only_need_context",
    )
    retrieval_only_default = retrieval_only is None and only_need_context is None
    # MEP deployments may not inject LLM config; default to retrieval-only unless
    # the request explicitly opts into answer generation.
    retrieval_only_enabled = (
        retrieval_only_default or bool(retrieval_only) or bool(only_need_context)
    )

    inference_request = InferenceRequest(
        query_type=raw_query_type,  # type: ignore[arg-type]
        query=raw_query.strip(),
        mode=normalize_query_mode(
            _first_with_fallback(data, process_spec, source_json, "mode") or "hybrid"
        ),
        conversation_history=conversation_history,
        history_turns=parse_history_turns(
            _first_with_fallback(
                data,
                process_spec,
                source_json,
                "history_turns",
                "historyTurns",
            )
        ),
        enable_rerank=_parse_optional_bool(
            _first_with_fallback(
                data,
                process_spec,
                source_json,
                "enable_rerank",
                "enableRerank",
            ),
            field_name="enable_rerank",
        ),
        response_type=_first_with_fallback(
            data,
            process_spec,
            source_json,
            "response_type",
            "responseType",
        ),
        include_trace=bool(include_trace) or retrieval_only_enabled,
        retrieval_only=retrieval_only_enabled,
        only_need_context=bool(only_need_context) or retrieval_only_enabled,
        high_level_keywords=_parse_string_list(
            _first_with_fallback(
                data,
                process_spec,
                source_json,
                "high_level_keywords",
                "highLevelKeywords",
                "hl_keywords",
                "hlKeywords",
            ),
            field_name="high_level_keywords",
        ),
        low_level_keywords=_parse_string_list(
            _first_with_fallback(
                data,
                process_spec,
                source_json,
                "low_level_keywords",
                "lowLevelKeywords",
                "ll_keywords",
                "llKeywords",
            ),
            field_name="low_level_keywords",
        ),
    )

    generate_path_value = _first_present(data, "generatePath")
    if generate_path_value in (None, ""):
        generate_path_value = file_info.get("generatePath")

    generate_path = None
    if generate_path_value not in (None, ""):
        if not isinstance(generate_path_value, str):
            raise ValueError("generatePath must be a string when provided")
        generate_path = Path(generate_path_value).expanduser().resolve()

    if action in {"create", "query"}:
        result_filename = "gen.json"
    else:
        result_filename = str(
            _first_present(
                data,
                "result_filename",
                "resultFilename",
                "resultFileName",
                "output_filename",
            )
            or os.getenv("RAGENT_MEP_RESULT_FILENAME")
            or "gen.json"
        )
    result_filename = _normalize_result_filename(result_filename)

    return NormalizedMepRequest(
        inference_request=inference_request,
        action=action,
        task_id=task_id,
        base_path=base_path,
        generate_path=generate_path,
        result_filename=result_filename,
        raw_data=data,
    )


def build_result_payload(
    *,
    request: NormalizedMepRequest,
    result: dict[str, Any],
    runtime_layout: RuntimeProjectLayout,
    written_result_path: Path | None = None,
) -> dict[str, Any]:
    retrieval_only = bool(
        result.get(
            "retrieval_only",
            request.inference_request.retrieval_only
            or request.inference_request.only_need_context,
        )
    )
    payload: dict[str, Any] = {
        "code": "0",
        "des": "success",
        "taskId": request.task_id,
        "query": request.inference_request.query,
        "query_type": request.inference_request.query_type,
        "mode": str(result.get("mode") or request.inference_request.mode),
        "retrieval_only": retrieval_only,
        "only_need_context": bool(
            result.get(
                "only_need_context",
                request.inference_request.only_need_context or retrieval_only,
            )
        ),
        "answer": str(result.get("answer") or ""),
        "referenced_file_paths": list(result.get("referenced_file_paths") or []),
        "image_list": list(result.get("image_list") or []),
        "conversation_history_used_count": int(
            result.get(
                "conversation_history_used_count",
                len(request.inference_request.conversation_history or []),
            )
        ),
        "history_turns": result.get(
            "history_turns",
            request.inference_request.history_turns,
        ),
        "enable_rerank": result.get(
            "enable_rerank",
            request.inference_request.enable_rerank,
        ),
        "response_type": result.get(
            "response_type",
            request.inference_request.response_type,
        ),
        "trace": (
            result.get("trace") if request.inference_request.include_trace else None
        ),
        "runtime": {
            "runtime_project_dir": str(runtime_layout.runtime_project_dir),
            "snapshot_source_dir": str(runtime_layout.source_project_dir),
            "copied_to_runtime_dir": runtime_layout.copied_to_runtime_dir,
        },
    }

    if "decomposition" in result:
        payload["decomposition"] = result["decomposition"]
    if retrieval_only or result.get("retrieval_result") is not None:
        payload["retrieval_result"] = result.get("retrieval_result") or {}
    if "retrieval_only_degraded_from" in result:
        payload["retrieval_only_degraded_from"] = result[
            "retrieval_only_degraded_from"
        ]
    if request.inference_request.include_trace and result.get("steps") is not None:
        payload["steps"] = result["steps"]
    if written_result_path is not None:
        payload["result_file_path"] = str(written_result_path)
    return payload


def maybe_write_result_payload(
    payload: dict[str, Any],
    *,
    generate_path: Path | None,
    result_filename: str,
) -> Path | None:
    if generate_path is None:
        return None
    result_filename = _normalize_result_filename(result_filename)
    generate_path.mkdir(parents=True, exist_ok=True)
    output_path = generate_path / result_filename
    payload["result_file_path"] = str(output_path)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return output_path


def build_recommend_result(
    *,
    code: str,
    des: str,
    content: list[Any] | None = None,
) -> dict[str, Any]:
    normalized_content = content or []
    return {
        "recommendResult": {
            "code": str(code),
            "des": str(des),
            "length": len(normalized_content),
            "content": normalized_content,
        }
    }


def build_recommend_success(
    payload: dict[str, Any] | None = None,
    *,
    include_content: bool = False,
) -> dict[str, Any]:
    content = [payload] if include_content and payload is not None else []
    return build_recommend_result(code="0", des="success", content=content)


def build_recommend_error(message: str, *, code: str = "3") -> dict[str, Any]:
    return build_recommend_result(code=code, des=str(message), content=[])


def _candidate_result_paths_from_data(data: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []

    generate_path = _first_present(data, "generatePath")
    if isinstance(generate_path, str) and generate_path.strip():
        candidates.append(Path(generate_path).expanduser().resolve() / "gen.json")

    file_info = _extract_first_file_info(data)
    file_generate_path = file_info.get("generatePath")
    if isinstance(file_generate_path, str) and file_generate_path.strip():
        candidates.append(Path(file_generate_path).expanduser().resolve() / "gen.json")

    base_path = _first_present(data, "basePath", "base_path")
    if isinstance(base_path, str) and base_path.strip():
        resolved_base_path = Path(base_path).expanduser().resolve()
        candidates.append(resolved_base_path / "gen.json")
        candidates.append(resolved_base_path / "generatePath" / "gen.json")

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped


def build_action_query_response(req_data: Any) -> dict[str, Any]:
    if not isinstance(req_data, dict):
        return build_recommend_error("request data must be a JSON object", code="4")
    data = req_data.get("data")
    if not isinstance(data, dict):
        return build_recommend_error(
            "req_Data['data'] is required and must be a JSON object",
            code="4",
        )

    candidates = _candidate_result_paths_from_data(data)
    if not candidates:
        return build_recommend_error("generatePath or basePath is required", code="4")

    for candidate in candidates:
        if candidate.is_file():
            return build_recommend_success()

    if any(candidate.parent.exists() for candidate in candidates):
        return build_recommend_result(code="2", des="processing", content=[])
    return build_recommend_error("task result path does not exist", code="4")


__all__ = [
    "AsyncLoopThread",
    "ComponentBundlePaths",
    "InferenceRequest",
    "InferenceRuntimeSession",
    "NormalizedMepRequest",
    "RuntimeProjectLayout",
    "cleanup_runtime_project_layout",
    "build_action_query_response",
    "build_recommend_error",
    "build_recommend_result",
    "build_recommend_success",
    "build_result_payload",
    "get_mep_action",
    "maybe_write_result_payload",
    "normalize_mep_request",
    "prepare_runtime_project_layout",
    "resolve_component_bundle_paths",
    "resolve_single_snapshot_from_data_dir",
]
