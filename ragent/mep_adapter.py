from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .inference_runtime import (
    InferenceRequest,
    InferenceRuntimeSession,
    normalize_conversation_history,
    normalize_query_mode,
    parse_history_turns,
)
from .runtime_env import bootstrap_runtime_environment


bootstrap_runtime_environment()


_TRUE_VALUES = {"1", "true", "yes", "on"}
_RAGENT_SNAPSHOT_MARKERS = {
    "graph_chunk_entity_relation.graphml",
    "kv_store_text_chunks.json",
    "vdb_chunks.json",
}


@dataclass(frozen=True)
class ComponentBundlePaths:
    current_dir: Path
    parent_dir: Path
    data_dir: Path
    model_dir: Path


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


def _first_present(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping:
            return mapping.get(key)
    return None


def resolve_component_bundle_paths(
    process_file: str | os.PathLike[str],
    *,
    data_dir_override: str | os.PathLike[str] | None = None,
    model_dir_override: str | os.PathLike[str] | None = None,
) -> ComponentBundlePaths:
    current_dir = Path(process_file).expanduser().resolve().parent
    parent_dir = current_dir.parent
    data_dir = Path(
        os.getenv("RAGENT_MEP_DATA_DIR")
        or data_dir_override
        or (parent_dir / "data")
    ).expanduser().resolve()
    model_dir = Path(
        os.getenv("RAGENT_MEP_MODEL_DIR")
        or model_dir_override
        or (parent_dir / "model")
    ).expanduser().resolve()
    return ComponentBundlePaths(
        current_dir=current_dir,
        parent_dir=parent_dir,
        data_dir=data_dir,
        model_dir=model_dir,
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

    if is_ragent_project_snapshot(resolved_data_dir):
        return resolved_data_dir

    candidates = sorted(
        child
        for child in resolved_data_dir.iterdir()
        if child.is_dir() and is_ragent_project_snapshot(child)
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError(
            "No Ragent knowledge graph snapshot found under data/. "
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


def prepare_runtime_project_layout(
    *,
    data_dir: str | os.PathLike[str],
    model_dir: str | os.PathLike[str] | None = None,
    runtime_root: str | os.PathLike[str] | None = None,
) -> RuntimeProjectLayout:
    resolved_data_dir = Path(data_dir).expanduser().resolve()
    resolved_model_dir = (
        Path(model_dir).expanduser().resolve() if model_dir is not None else resolved_data_dir.parent / "model"
    )
    source_project_dir = resolve_single_snapshot_from_data_dir(resolved_data_dir)

    if _directory_is_writable(source_project_dir):
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


def normalize_mep_request(req_data: Any) -> NormalizedMepRequest:
    if req_data is None:
        raise ValueError("request data is missing")
    if not isinstance(req_data, dict):
        raise ValueError("request data must be a JSON object")

    data = req_data.get("data")
    if not isinstance(data, dict):
        raise ValueError("req_Data['data'] is required and must be a JSON object")

    raw_query_type = str(_first_present(data, "query_type", "queryType") or "").strip().lower()
    if raw_query_type not in {"onehop", "multihop", "chat"}:
        raise ValueError("query_type must be one of: onehop | multihop | chat")

    raw_query = _first_present(data, "query", "question")
    if not isinstance(raw_query, str) or not raw_query.strip():
        raise ValueError("query is required and must be a non-empty string")

    raw_history = _first_present(
        data,
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
        _first_present(data, "include_trace", "includeTrace", "trace", "debug"),
        field_name="include_trace",
    )

    inference_request = InferenceRequest(
        query_type=raw_query_type,  # type: ignore[arg-type]
        query=raw_query.strip(),
        mode=normalize_query_mode(_first_present(data, "mode") or "hybrid"),
        conversation_history=conversation_history,
        history_turns=parse_history_turns(
            _first_present(data, "history_turns", "historyTurns")
        ),
        enable_rerank=_parse_optional_bool(
            _first_present(data, "enable_rerank", "enableRerank"),
            field_name="enable_rerank",
        ),
        response_type=_first_present(data, "response_type", "responseType"),
        include_trace=bool(include_trace),
    )

    generate_path_value = _first_present(data, "generatePath")
    if generate_path_value is None:
        file_info = data.get("fileInfo")
        if isinstance(file_info, list) and file_info and isinstance(file_info[0], dict):
            generate_path_value = file_info[0].get("generatePath")

    generate_path = None
    if generate_path_value not in (None, ""):
        if not isinstance(generate_path_value, str):
            raise ValueError("generatePath must be a string when provided")
        generate_path = Path(generate_path_value).expanduser().resolve()

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
    ).strip()
    if not result_filename:
        raise ValueError("result filename must not be empty")

    return NormalizedMepRequest(
        inference_request=inference_request,
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
    payload: dict[str, Any] = {
        "answer": str(result.get("answer") or ""),
        "referenced_file_paths": list(result.get("referenced_file_paths") or []),
        "image_list": list(result.get("image_list") or []),
        "query_type": request.inference_request.query_type,
        "mode": str(result.get("mode") or request.inference_request.mode),
        "conversation_history_used_count": int(
            result.get(
                "conversation_history_used_count",
                len(request.inference_request.conversation_history or []),
            )
        ),
        "history_turns": result.get("history_turns"),
        "enable_rerank": result.get("enable_rerank"),
        "response_type": result.get("response_type"),
        "runtime_project_dir": str(runtime_layout.runtime_project_dir),
        "snapshot_source_dir": str(runtime_layout.source_project_dir),
        "copied_to_runtime_dir": runtime_layout.copied_to_runtime_dir,
    }

    if "decomposition" in result:
        payload["decomposition"] = result["decomposition"]
    if request.inference_request.include_trace:
        if result.get("trace") is not None:
            payload["trace"] = result["trace"]
        if result.get("steps") is not None:
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
    generate_path.mkdir(parents=True, exist_ok=True)
    output_path = generate_path / result_filename
    payload["result_file_path"] = str(output_path)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return output_path


def build_recommend_success(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "recommendResult": {
            "code": "0",
            "des": "success",
            "length": 1,
            "content": [payload],
        }
    }


def build_recommend_error(message: str, *, code: str = "3") -> dict[str, Any]:
    return {
        "recommendResult": {
            "code": str(code),
            "des": str(message),
            "length": 0,
            "content": [],
        }
    }


__all__ = [
    "AsyncLoopThread",
    "ComponentBundlePaths",
    "InferenceRequest",
    "InferenceRuntimeSession",
    "NormalizedMepRequest",
    "RuntimeProjectLayout",
    "cleanup_runtime_project_layout",
    "build_recommend_error",
    "build_recommend_success",
    "build_result_payload",
    "maybe_write_result_payload",
    "normalize_mep_request",
    "prepare_runtime_project_layout",
    "resolve_component_bundle_paths",
    "resolve_single_snapshot_from_data_dir",
]
