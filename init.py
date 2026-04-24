from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


_TRUE_VALUES = {"1", "true", "yes", "on", "y", "t"}
_FALSE_VALUES = {"0", "false", "no", "off", "n", "f"}


def strtobool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(f"Invalid truth value: {value!r}")


def getenv_or_default(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key)
    if value is None:
        return default
    normalized = value.strip()
    if not normalized or normalized.lower() in {"null", "none"}:
        return default
    return normalized


def getint_or_default(key: str, default: int | None = None) -> int | None:
    value = getenv_or_default(key)
    if value is None:
        return default
    return int(value)


def getfloat_or_default(key: str, default: float | None = None) -> float | None:
    value = getenv_or_default(key)
    if value is None:
        return default
    return float(value)


def getbool_or_default(key: str, default: bool | None = None) -> bool | None:
    value = getenv_or_default(key)
    if value is None:
        return default
    return strtobool(value)


def _parse_model_sfs_base_dir() -> str:
    raw_model_sfs = getenv_or_default("MODEL_SFS")
    model_object_id = getenv_or_default("MODEL_OBJECT_ID")
    if raw_model_sfs is None or model_object_id is None:
        return ""

    try:
        payload = json.loads(raw_model_sfs)
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict):
        return ""

    sfs_base_path = payload.get("sfsBasePath")
    if not isinstance(sfs_base_path, str) or not sfs_base_path.strip():
        return ""
    return str(Path(sfs_base_path).expanduser() / model_object_id)


COMPONENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = COMPONENT_DIR.parent
MODEL_DIR = ROOT_DIR / "model"
DATA_DIR = ROOT_DIR / "data"
META_DIR = ROOT_DIR / "meta"

MODEL_SFS_BASE_DIR = _parse_model_sfs_base_dir()
MODEL_ABSOLUTE_DIR = getenv_or_default("MODEL_ABSOLUTE_DIR", "")
MODEL_RELATIVE_DIR = getenv_or_default("MODEL_RELATIVE_DIR", "")
SFS_MODEL_DIR = (
    str(Path(MODEL_SFS_BASE_DIR) / MODEL_RELATIVE_DIR)
    if MODEL_SFS_BASE_DIR and MODEL_RELATIVE_DIR
    else ""
)
PATH_APPENDIX = getenv_or_default("path_appendix", "")
RAGENT_MEP_MODEL_DIR = getenv_or_default("RAGENT_MEP_MODEL_DIR", "")
RAGENT_MEP_DATA_DIR = getenv_or_default("RAGENT_MEP_DATA_DIR", "")


def build_runtime_probe() -> dict[str, Any]:
    return {
        "cwd": str(Path.cwd().resolve()),
        "component_dir": str(COMPONENT_DIR),
        "root_dir": str(ROOT_DIR),
        "model_dir": str(MODEL_DIR),
        "model_dir_exists": MODEL_DIR.exists(),
        "data_dir": str(DATA_DIR),
        "data_dir_exists": DATA_DIR.exists(),
        "meta_dir": str(META_DIR),
        "meta_dir_exists": META_DIR.exists(),
        "model_sfs_base_dir": MODEL_SFS_BASE_DIR,
        "model_absolute_dir": MODEL_ABSOLUTE_DIR,
        "model_relative_dir": MODEL_RELATIVE_DIR,
        "sfs_model_dir": SFS_MODEL_DIR,
        "path_appendix": PATH_APPENDIX,
        "ragent_mep_model_dir": RAGENT_MEP_MODEL_DIR,
        "ragent_mep_data_dir": RAGENT_MEP_DATA_DIR,
    }


__all__ = [
    "COMPONENT_DIR",
    "DATA_DIR",
    "META_DIR",
    "MODEL_ABSOLUTE_DIR",
    "MODEL_DIR",
    "MODEL_RELATIVE_DIR",
    "MODEL_SFS_BASE_DIR",
    "PATH_APPENDIX",
    "RAGENT_MEP_DATA_DIR",
    "RAGENT_MEP_MODEL_DIR",
    "ROOT_DIR",
    "SFS_MODEL_DIR",
    "build_runtime_probe",
    "getbool_or_default",
    "getenv_or_default",
    "getfloat_or_default",
    "getint_or_default",
    "strtobool",
]
