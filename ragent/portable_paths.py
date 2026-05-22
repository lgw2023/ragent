from __future__ import annotations

import re
from typing import Any

from .constants import GRAPH_FIELD_SEP


_REPO_ROOT_MARKER = "/ragent/"
_PORTABLE_ROOT_MARKERS = ("example", "mep")
_PATH_KEYS = {
    "file_path",
    "file_paths",
    "referenced_file_paths",
    "image_list",
    "source_ref",
    "source_refs",
    "source_refs_display",
}
_URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


def _portable_single_path(value: str) -> str:
    path = value.strip().replace("\\", "/")
    if not path or path == "unknown_source" or _URL_RE.match(path):
        return path

    marker_index = path.rfind(_REPO_ROOT_MARKER)
    if marker_index >= 0:
        return path[marker_index + len(_REPO_ROOT_MARKER) :]

    for marker in _PORTABLE_ROOT_MARKERS:
        token = f"/{marker}/"
        token_index = path.find(token)
        if token_index >= 0:
            return path[token_index + 1 :]

    return path


def make_portable_file_path(value: Any) -> str:
    path = str(value or "").strip()
    if not path:
        return path
    if GRAPH_FIELD_SEP in path:
        return GRAPH_FIELD_SEP.join(
            _portable_single_path(item)
            for item in path.split(GRAPH_FIELD_SEP)
            if item.strip()
        )
    return _portable_single_path(path)


def _make_portable_source_ref(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return text

    if " ; " in text:
        return " ; ".join(_make_portable_source_ref(item) for item in text.split(" ; "))

    if " | " not in text:
        return make_portable_file_path(text)

    path, suffix = text.split(" | ", 1)
    return f"{make_portable_file_path(path)} | {suffix}"


def normalize_portable_file_paths(payload: Any, *, key: str | None = None) -> Any:
    if isinstance(payload, dict):
        return {
            item_key: normalize_portable_file_paths(item_value, key=str(item_key))
            for item_key, item_value in payload.items()
        }

    if isinstance(payload, list):
        return [
            normalize_portable_file_paths(item, key=key)
            for item in payload
        ]

    if isinstance(payload, tuple):
        return tuple(
            normalize_portable_file_paths(item, key=key)
            for item in payload
        )

    if isinstance(payload, str) and key in _PATH_KEYS:
        if key in {"source_ref", "source_refs", "source_refs_display"}:
            return _make_portable_source_ref(payload)
        return make_portable_file_path(payload)

    return payload
