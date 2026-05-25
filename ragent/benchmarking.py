from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from ragent.runtime_env import should_skip_dotenv


MANAGED_QUERY_MODES = ("graph", "hybrid")
QUERY_CACHE_TYPES = ("answer", "retrieval", "render", "prompt", "keyword_candidate")
SQLITE_CACHE_CORRUPTION_MARKERS = (
    "malformed",
    "not a database",
)
CACHE_HIT_STAGES = frozenset(
    {
        "answer_cache_hit",
        "retrieval_cache_hit",
        "render_cache_hit",
        "prompt_cache_hit",
        "keyword_candidate_cache_hit",
    }
)
BENCHMARK_SCENARIO_DESCRIPTIONS = {
    "first_request": (
        "Service process is already up, but the project session is unloaded and the "
        "query cache is cleared before each measured request."
    ),
    "steady_cold": (
        "Service process and project session stay warm, while the query cache is "
        "cleared before each measured request."
    ),
    "steady_retrieval_warm": (
        "Service process and project session stay warm, the target query is primed, "
        "and only answer-cache entries are cleared before each measured request so "
        "retrieval/render/prompt caches remain warm."
    ),
    "steady_answer_warm": (
        "Service process and project session stay warm, the target query is primed, "
        "and measured requests should hit the direct answer cache."
    ),
}


def normalize_project_dir(project_dir: str | os.PathLike[str]) -> Path:
    return Path(project_dir).expanduser().resolve()


def resolve_workspace_name(
    *,
    repo_root: Path | None = None,
    env_file: Path | None = None,
) -> str:
    raw_workspace = (os.getenv("WORKSPACE") or "").strip().strip('"').strip("'")
    if raw_workspace:
        return raw_workspace

    if should_skip_dotenv():
        return ""

    resolved_env_file = env_file
    if resolved_env_file is None and repo_root is not None:
        resolved_env_file = repo_root / ".env"

    if resolved_env_file is None or not resolved_env_file.exists():
        return ""

    env_values = dotenv_values(resolved_env_file)
    raw_workspace = str(env_values.get("WORKSPACE") or "").strip().strip('"').strip("'")
    return raw_workspace


def resolve_query_cache_paths(
    project_dir: str | os.PathLike[str],
    *,
    repo_root: Path | None = None,
    env_file: Path | None = None,
) -> list[Path]:
    normalized_project_dir = normalize_project_dir(project_dir)
    workspace_name = resolve_workspace_name(repo_root=repo_root, env_file=env_file)
    base_dir = normalized_project_dir / workspace_name if workspace_name else normalized_project_dir
    return [base_dir / "kv_store_llm_response_cache.sqlite"]


def is_sqlite_cache_corruption_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in SQLITE_CACHE_CORRUPTION_MARKERS)


def _query_cache_sidecar_paths(cache_path: Path) -> list[Path]:
    return [
        cache_path,
        Path(f"{cache_path}-wal"),
        Path(f"{cache_path}-shm"),
    ]


def _initialize_empty_query_cache(cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(cache_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS query_cache_entries (
                key TEXT PRIMARY KEY,
                mode TEXT NOT NULL,
                cache_type TEXT NOT NULL,
                args_hash TEXT NOT NULL,
                entry_json TEXT NOT NULL,
                corpus_revision INTEGER NOT NULL DEFAULT 0,
                expires_at INTEGER,
                created_at INTEGER NOT NULL DEFAULT 0,
                last_accessed_at INTEGER NOT NULL DEFAULT 0,
                access_count INTEGER NOT NULL DEFAULT 0,
                is_query_cache INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_query_cache_mode_type ON query_cache_entries(mode, cache_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_query_cache_revision ON query_cache_entries(corpus_revision)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_query_cache_expires_at ON query_cache_entries(expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_query_cache_last_accessed_at ON query_cache_entries(last_accessed_at)"
        )
        conn.commit()


def recover_malformed_query_cache(cache_path: Path) -> list[str]:
    """Quarantine a corrupt query-cache DB and replace it with an empty cache.

    Query cache files are disposable. If SQLite reports corruption, selective
    deletion is no longer reliable, so the safest benchmark behavior is to
    replace the cache file and let subsequent requests repopulate it.
    """

    recovered_files: list[str] = []
    suffix = f".malformed.{int(time.time_ns())}"
    for path in _query_cache_sidecar_paths(cache_path):
        if not path.exists():
            continue
        target = path.with_name(f"{path.name}{suffix}")
        path.replace(target)
        recovered_files.append(str(target))

    _initialize_empty_query_cache(cache_path)
    return recovered_files


def extract_stage_seconds(stage_timings: list[dict[str, Any]] | None, stage_name: str) -> float | None:
    for item in reversed(stage_timings or []):
        if not isinstance(item, dict) or item.get("stage") != stage_name:
            continue
        value = item.get("seconds")
        if value is None:
            return None
        return float(value)
    return None


def collect_cache_hit_stages(stage_timings: list[dict[str, Any]] | None) -> list[str]:
    return sorted(
        {
            str(item.get("stage"))
            for item in (stage_timings or [])
            if isinstance(item, dict) and item.get("stage") in CACHE_HIT_STAGES
        }
    )


def clear_query_cache_entries(
    project_dir: str | os.PathLike[str],
    *,
    modes: list[str] | None = None,
    cache_types: list[str] | None = None,
    repo_root: Path | None = None,
    env_file: Path | None = None,
) -> dict[str, Any]:
    normalized_modes = [str(item) for item in (modes or MANAGED_QUERY_MODES) if str(item).strip()]
    normalized_cache_types = [
        str(item) for item in (cache_types or []) if str(item).strip()
    ]
    deleted_entry_count = 0
    touched_files: list[str] = []
    recovered_cache_files: list[str] = []

    for cache_path in resolve_query_cache_paths(
        project_dir,
        repo_root=repo_root,
        env_file=env_file,
    ):
        touched_files.append(str(cache_path))
        if not cache_path.exists():
            continue

        try:
            with sqlite3.connect(cache_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS query_cache_entries (
                        key TEXT PRIMARY KEY,
                        mode TEXT NOT NULL,
                        cache_type TEXT NOT NULL,
                        args_hash TEXT NOT NULL,
                        entry_json TEXT NOT NULL,
                        corpus_revision INTEGER NOT NULL DEFAULT 0,
                        expires_at INTEGER,
                        created_at INTEGER NOT NULL DEFAULT 0,
                        last_accessed_at INTEGER NOT NULL DEFAULT 0,
                        access_count INTEGER NOT NULL DEFAULT 0,
                        is_query_cache INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                clauses: list[str] = []
                parameters: list[str] = []

                if normalized_modes:
                    placeholders = ",".join("?" for _ in normalized_modes)
                    clauses.append(f"mode IN ({placeholders})")
                    parameters.extend(normalized_modes)
                if normalized_cache_types:
                    placeholders = ",".join("?" for _ in normalized_cache_types)
                    clauses.append(f"cache_type IN ({placeholders})")
                    parameters.extend(normalized_cache_types)

                if not clauses:
                    continue

                cursor = conn.execute(
                    "DELETE FROM query_cache_entries WHERE " + " AND ".join(clauses),
                    tuple(parameters),
                )
                conn.commit()
                deleted_entry_count += max(cursor.rowcount, 0)
        except sqlite3.DatabaseError as exc:
            if not is_sqlite_cache_corruption_error(exc):
                raise
            recovered_cache_files.extend(recover_malformed_query_cache(cache_path))

    return {
        "cache_files": touched_files,
        "deleted_entry_count": deleted_entry_count,
        "recovered_cache_files": recovered_cache_files,
        "modes": normalized_modes,
        "cache_types": normalized_cache_types,
    }
