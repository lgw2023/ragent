import asyncio
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, final

from ragent.base import BaseKVStorage


_QUERY_CACHE_MANAGED_MODES = {"graph", "hybrid"}


@final
@dataclass
class SQLiteQueryCacheStorage(BaseKVStorage):
    def __post_init__(self):
        working_dir = self.global_config["working_dir"]
        if self.workspace:
            workspace_dir = os.path.join(working_dir, self.workspace)
            os.makedirs(workspace_dir, exist_ok=True)
            base_dir = workspace_dir
        else:
            base_dir = working_dir

        self._file_name = os.path.join(base_dir, f"kv_store_{self.namespace}.sqlite")
        self._conn: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        async with self._lock:
            if self._conn is not None:
                return

            self._conn = sqlite3.connect(self._file_name, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute(
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
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_query_cache_mode_type ON query_cache_entries(mode, cache_type)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_query_cache_revision ON query_cache_entries(corpus_revision)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_query_cache_expires_at ON query_cache_entries(expires_at)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_query_cache_last_accessed_at ON query_cache_entries(last_accessed_at)"
            )
            self._conn.commit()

            await self._prune_locked()

    async def finalize(self):
        async with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("SQLiteQueryCacheStorage is not initialized")
        return self._conn

    def _parse_flattened_cache_key(self, key: str) -> tuple[str, str, str] | None:
        parts = str(key).split(":", 2)
        if len(parts) != 3:
            return None
        return parts[0], parts[1], parts[2]

    def _query_cache_ttl_seconds(self) -> int:
        try:
            return max(
                0, int(self.global_config.get("query_cache_ttl_seconds") or 0)
            )
        except (TypeError, ValueError):
            return 0

    def _query_cache_max_entries(self) -> int:
        try:
            return max(
                0, int(self.global_config.get("query_cache_max_entries") or 0)
            )
        except (TypeError, ValueError):
            return 0

    def _is_query_cache_key(self, key: str) -> bool:
        parsed = self._parse_flattened_cache_key(key)
        return bool(parsed and parsed[0] in _QUERY_CACHE_MANAGED_MODES)

    def _extract_entry_metadata(
        self, key: str, entry: dict[str, Any]
    ) -> dict[str, Any]:
        now = int(time.time())
        parsed = self._parse_flattened_cache_key(key)
        mode = parsed[0] if parsed else ""
        cache_type = parsed[1] if parsed else ""
        args_hash = parsed[2] if parsed else str(key)

        is_query_cache = mode in _QUERY_CACHE_MANAGED_MODES
        corpus_revision = 0
        created_at = int(entry.get("create_time") or 0)
        last_accessed_at = int(entry.get("update_time") or created_at or 0)
        access_count = 0
        expires_at = None

        if is_query_cache:
            payload = entry.get("return")
            if isinstance(payload, dict):
                corpus_revision = int(payload.get("corpus_revision") or 0)
                created_at = int(payload.get("created_at") or created_at or now)
                last_accessed_at = int(
                    payload.get("last_accessed_at") or last_accessed_at or created_at
                )
                access_count = max(0, int(payload.get("access_count") or 0))
            else:
                created_at = int(
                    entry.get("_query_cache_created_at") or created_at or now
                )
                last_accessed_at = int(
                    entry.get("_query_cache_last_accessed_at")
                    or last_accessed_at
                    or created_at
                )
                access_count = max(
                    0, int(entry.get("_query_cache_access_count") or 0)
                )

            ttl_seconds = self._query_cache_ttl_seconds()
            if ttl_seconds > 0:
                expires_at = created_at + ttl_seconds

        return {
            "mode": mode,
            "cache_type": cache_type,
            "args_hash": args_hash,
            "entry_json": json.dumps(entry, ensure_ascii=False, default=str),
            "corpus_revision": corpus_revision,
            "expires_at": expires_at,
            "created_at": created_at,
            "last_accessed_at": last_accessed_at,
            "access_count": access_count,
            "is_query_cache": 1 if is_query_cache else 0,
        }

    async def _get_by_id_locked(
        self, id: str, *, touch: bool
    ) -> dict[str, Any] | None:
        conn = self._get_connection()
        row = conn.execute(
            """
            SELECT entry_json, expires_at, created_at, last_accessed_at, access_count, is_query_cache
            FROM query_cache_entries
            WHERE key = ?
            """,
            (id,),
        ).fetchone()
        if row is None:
            return None

        now = int(time.time())
        expires_at = row["expires_at"]
        if row["is_query_cache"] and expires_at is not None and int(expires_at) <= now:
            conn.execute("DELETE FROM query_cache_entries WHERE key = ?", (id,))
            conn.commit()
            return None

        entry = json.loads(row["entry_json"])
        if not isinstance(entry, dict):
            entry = {"return": entry}

        if row["is_query_cache"] and touch:
            created_at = int(row["created_at"] or now)
            access_count = int(row["access_count"] or 0) + 1
            payload = entry.get("return")
            if isinstance(payload, dict):
                payload["created_at"] = int(payload.get("created_at") or created_at)
                payload["last_accessed_at"] = now
                payload["access_count"] = access_count
            else:
                entry["_query_cache_created_at"] = int(
                    entry.get("_query_cache_created_at") or created_at
                )
                entry["_query_cache_last_accessed_at"] = now
                entry["_query_cache_access_count"] = access_count

            conn.execute(
                """
                UPDATE query_cache_entries
                SET entry_json = ?, last_accessed_at = ?, access_count = ?
                WHERE key = ?
                """,
                (
                    json.dumps(entry, ensure_ascii=False, default=str),
                    now,
                    access_count,
                    id,
                ),
            )
            conn.commit()

        entry["_id"] = id
        return entry

    async def get_by_id(self, id: str) -> dict[str, Any] | None:
        async with self._lock:
            return await self._get_by_id_locked(id, touch=True)

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        async with self._lock:
            results: list[dict[str, Any] | None] = []
            for item_id in ids:
                results.append(await self._get_by_id_locked(item_id, touch=True))
            return results

    async def filter_keys(self, keys: set[str]) -> set[str]:
        if not keys:
            return set()

        async with self._lock:
            conn = self._get_connection()
            placeholders = ",".join("?" for _ in keys)
            rows = conn.execute(
                f"SELECT key FROM query_cache_entries WHERE key IN ({placeholders})",
                tuple(keys),
            ).fetchall()
            existing = {str(row["key"]) for row in rows}
            return set(keys) - existing

    async def _upsert_locked(
        self, data: dict[str, dict[str, Any]], *, prune: bool = True
    ) -> int:
        if not data:
            return 0

        conn = self._get_connection()
        rows_to_write: list[tuple[Any, ...]] = []
        for key, value in data.items():
            entry = dict(value) if isinstance(value, dict) else {"return": value}
            metadata = self._extract_entry_metadata(key, entry)
            rows_to_write.append(
                (
                    key,
                    metadata["mode"],
                    metadata["cache_type"],
                    metadata["args_hash"],
                    metadata["entry_json"],
                    metadata["corpus_revision"],
                    metadata["expires_at"],
                    metadata["created_at"],
                    metadata["last_accessed_at"],
                    metadata["access_count"],
                    metadata["is_query_cache"],
                )
            )

        conn.executemany(
            """
            INSERT INTO query_cache_entries (
                key,
                mode,
                cache_type,
                args_hash,
                entry_json,
                corpus_revision,
                expires_at,
                created_at,
                last_accessed_at,
                access_count,
                is_query_cache
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                mode = excluded.mode,
                cache_type = excluded.cache_type,
                args_hash = excluded.args_hash,
                entry_json = excluded.entry_json,
                corpus_revision = excluded.corpus_revision,
                expires_at = excluded.expires_at,
                created_at = excluded.created_at,
                last_accessed_at = excluded.last_accessed_at,
                access_count = excluded.access_count,
                is_query_cache = excluded.is_query_cache
            """,
            rows_to_write,
        )
        if prune:
            await self._prune_locked()
        else:
            conn.commit()
        return len(rows_to_write)

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        async with self._lock:
            await self._upsert_locked(data, prune=True)

    async def delete(self, ids: list[str]) -> None:
        if not ids:
            return

        async with self._lock:
            conn = self._get_connection()
            placeholders = ",".join("?" for _ in ids)
            conn.execute(
                f"DELETE FROM query_cache_entries WHERE key IN ({placeholders})",
                tuple(ids),
            )
            conn.commit()

    async def drop_cache_by_modes(self, modes: list[str] | None = None) -> bool:
        return await self.drop_cache_entries(modes=modes)

    async def drop_cache_entries(
        self,
        modes: list[str] | None = None,
        cache_types: list[str] | None = None,
    ) -> bool:
        normalized_modes = [str(item) for item in (modes or _QUERY_CACHE_MANAGED_MODES)]
        normalized_cache_types = [str(item) for item in (cache_types or [])]

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
            return False

        async with self._lock:
            conn = self._get_connection()
            conn.execute(
                "DELETE FROM query_cache_entries WHERE " + " AND ".join(clauses),
                tuple(parameters),
            )
            conn.commit()
        return True

    async def _prune_locked(self) -> None:
        conn = self._get_connection()
        ttl_seconds = self._query_cache_ttl_seconds()
        now = int(time.time())

        if ttl_seconds > 0:
            conn.execute(
                """
                DELETE FROM query_cache_entries
                WHERE is_query_cache = 1
                  AND expires_at IS NOT NULL
                  AND expires_at <= ?
                """,
                (now,),
            )

        max_entries = self._query_cache_max_entries()
        if max_entries > 0:
            count_row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM query_cache_entries
                WHERE is_query_cache = 1
                """
            ).fetchone()
            current_count = int(count_row["count"]) if count_row is not None else 0
            overflow = current_count - max_entries
            if overflow > 0:
                rows = conn.execute(
                    """
                    SELECT key
                    FROM query_cache_entries
                    WHERE is_query_cache = 1
                    ORDER BY last_accessed_at ASC, created_at ASC, key ASC
                    LIMIT ?
                    """,
                    (overflow,),
                ).fetchall()
                keys_to_delete = [str(row["key"]) for row in rows]
                if keys_to_delete:
                    placeholders = ",".join("?" for _ in keys_to_delete)
                    conn.execute(
                        f"DELETE FROM query_cache_entries WHERE key IN ({placeholders})",
                        tuple(keys_to_delete),
                    )

        conn.commit()

    async def index_done_callback(self) -> None:
        async with self._lock:
            await self._prune_locked()

    async def drop(self) -> dict[str, str]:
        try:
            async with self._lock:
                conn = self._get_connection()
                conn.execute("DELETE FROM query_cache_entries")
                conn.commit()
            return {"status": "success", "message": "data dropped"}
        except Exception as e:
            logger.error(f"Error dropping {self.namespace}: {e}")
            return {"status": "error", "message": str(e)}
