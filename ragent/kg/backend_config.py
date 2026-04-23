from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import Any


def load_backend_config(*backend_env_names: str) -> configparser.ConfigParser:
    """Load optional backend config from the first configured env path."""
    config = configparser.ConfigParser()
    for env_name in (*backend_env_names, "RAGENT_KG_CONFIG_FILE"):
        config_path = os.getenv(env_name)
        if not config_path:
            continue
        config.read(Path(config_path).expanduser(), encoding="utf-8")
        break
    return config


def get_backend_config_value(
    config: configparser.ConfigParser,
    section: str,
    option: str,
    *,
    env_var: str,
    fallback: Any = None,
) -> Any:
    env_value = os.environ.get(env_var)
    if env_value is not None:
        return env_value
    return config.get(section, option, fallback=fallback)
