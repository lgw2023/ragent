import asyncio
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, final

from ragent.base import BaseKVStorage
from ragent.utils import load_json, logger


@final
@dataclass
class SQLiteKVStorage(BaseKVStorage):
    def __post_init__(self):
        working_dir = self.global_config["working_dir"]
        if self.workspace:
            workspace_dir = os.path.join(working_dir, self.workspace)
            os.makedirs(workspace_dir, exist_ok=True)
            base_dir = workspace_dir
        else:
            base_dir = working_dir

        self._file_name = os.path.join(base_dir, f"kv_store_{self.namespace}.sqlite")
        self._legacy_json_file = os.path.join(
            base_dir, f"kv_store_{self.namespace}.json"
        )
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
                CREATE TABLE IF NOT EXISTS kv_entries (
                    key TEXT PRIMARY KEY,
                    entry_json TEXT NOT NULL,
                    create_time INTEGER NOT NULL DEFAULT 0,
                    update_time INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_kv_entries_update_time ON kv_entries(update_time)"
            )
            self._conn.commit()

            await self._migrate_legacy_json_if_needed_locked()

    async def finalize(self):
        async with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("SQLiteKVStorage is not initialized")
        return self._conn

    def _coerce_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _is_text_chunks_namespace(self) -> bool:
        return "text_chunks" in self.namespace

    def _prepare_return_record(
        self, key: str, entry: dict[str, Any]
    ) -> dict[str, Any]:
        result = dict(entry)
        result.setdefault("create_time", 0)
        result.setdefault("update_time", 0)
        result["_id"] = key
        return result

    def _normalize_entry_for_storage(
        self,
        key: str,
        value: dict[str, Any] | Any,
        *,
        existing_create_time: int | None = None,
        now: int | None = None,
        preserve_update_time: bool = False,
    ) -> tuple[dict[str, Any], int, int]:
        entry = dict(value) if isinstance(value, dict) else {"return": value}
        entry.pop("_id", None)

        if self._is_text_chunks_namespace() and "llm_cache_list" not in entry:
            entry["llm_cache_list"] = []

        timestamp = now or int(time.time())
        if existing_create_time is not None and existing_create_time > 0:
            create_time = self._coerce_int(
                entry.get("create_time"), existing_create_time
            )
        else:
            create_time = self._coerce_int(entry.get("create_time"), timestamp)

        if preserve_update_time:
            update_time = self._coerce_int(entry.get("update_time"), create_time)
        elif existing_create_time is not None:
            update_time = timestamp
        else:
            update_time = self._coerce_int(entry.get("update_time"), create_time)

        entry["create_time"] = create_time
        entry["update_time"] = update_time
        return entry, create_time, update_time

    async def _migrate_legacy_json_if_needed_locked(self) -> None:
        conn = self._get_connection()
        count_row = conn.execute("SELECT COUNT(*) AS count FROM kv_entries").fetchone()
        existing_count = int(count_row["count"]) if count_row is not None else 0
        if existing_count > 0 or not os.path.exists(self._legacy_json_file):
            return

        legacy_data = load_json(self._legacy_json_file) or {}
        if not isinstance(legacy_data, dict) or not legacy_data:
            return

        migrated_count = await self._upsert_locked(
            legacy_data,
            preserve_update_time=True,
        )
        logger.info(
            "Migrated %s KV entries from %s to %s",
            migrated_count,
            self._legacy_json_file,
            self._file_name,
        )

    async def refresh_from_storage(self) -> bool:
        async with self._lock:
            return self._conn is not None

    async def get_all(self) -> dict[str, Any]:
        async with self._lock:
            conn = self._get_connection()
            rows = conn.execute("SELECT key, entry_json FROM kv_entries").fetchall()
            result: dict[str, Any] = {}
            for row in rows:
                entry = json.loads(row["entry_json"])
                if not isinstance(entry, dict):
                    entry = {"return": entry}
                result[str(row["key"])] = self._prepare_return_record(
                    str(row["key"]), entry
                )
            return result

    async def get_by_id(self, id: str) -> dict[str, Any] | None:
        async with self._lock:
            conn = self._get_connection()
            row = conn.execute(
                "SELECT entry_json FROM kv_entries WHERE key = ?",
                (id,),
            ).fetchone()
            if row is None:
                return None

            entry = json.loads(row["entry_json"])
            if not isinstance(entry, dict):
                entry = {"return": entry}
            return self._prepare_return_record(id, entry)

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []

        async with self._lock:
            conn = self._get_connection()
            placeholders = ",".join("?" for _ in ids)
            rows = conn.execute(
                f"SELECT key, entry_json FROM kv_entries WHERE key IN ({placeholders})",
                tuple(ids),
            ).fetchall()
            rows_by_key = {str(row["key"]): row for row in rows}

            results: list[dict[str, Any] | None] = []
            for item_id in ids:
                row = rows_by_key.get(item_id)
                if row is None:
                    results.append(None)
                    continue

                entry = json.loads(row["entry_json"])
                if not isinstance(entry, dict):
                    entry = {"return": entry}
                results.append(self._prepare_return_record(item_id, entry))
            return results

    async def filter_keys(self, keys: set[str]) -> set[str]:
        if not keys:
            return set()

        async with self._lock:
            conn = self._get_connection()
            placeholders = ",".join("?" for _ in keys)
            rows = conn.execute(
                f"SELECT key FROM kv_entries WHERE key IN ({placeholders})",
                tuple(keys),
            ).fetchall()
            existing = {str(row["key"]) for row in rows}
            return set(keys) - existing

    async def _load_existing_create_times_locked(
        self, keys: list[str]
    ) -> dict[str, int]:
        if not keys:
            return {}

        conn = self._get_connection()
        placeholders = ",".join("?" for _ in keys)
        rows = conn.execute(
            f"SELECT key, create_time FROM kv_entries WHERE key IN ({placeholders})",
            tuple(keys),
        ).fetchall()
        return {
            str(row["key"]): self._coerce_int(row["create_time"], 0) for row in rows
        }

    async def _upsert_locked(
        self,
        data: dict[str, dict[str, Any]],
        *,
        preserve_update_time: bool = False,
    ) -> int:
        if not data:
            return 0

        conn = self._get_connection()
        now = int(time.time())
        existing_create_times = await self._load_existing_create_times_locked(
            list(data.keys())
        )

        rows_to_write: list[tuple[Any, ...]] = []
        for key, value in data.items():
            entry, create_time, update_time = self._normalize_entry_for_storage(
                key,
                value,
                existing_create_time=existing_create_times.get(key),
                now=now,
                preserve_update_time=preserve_update_time,
            )
            rows_to_write.append(
                (
                    key,
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
            rows_to_write,
        )
        conn.commit()
        return len(rows_to_write)

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        async with self._lock:
            await self._upsert_locked(data)

    async def delete(self, ids: list[str]) -> None:
        if not ids:
            return

        async with self._lock:
            conn = self._get_connection()
            placeholders = ",".join("?" for _ in ids)
            conn.execute(
                f"DELETE FROM kv_entries WHERE key IN ({placeholders})",
                tuple(ids),
            )
            conn.commit()

    async def drop_cache_by_modes(self, modes: list[str] | None = None) -> bool:
        if not modes:
            return False

        async with self._lock:
            conn = self._get_connection()
            where_clause = " OR ".join("key LIKE ?" for _ in modes)
            params = tuple(f"{mode}:%" for mode in modes)
            conn.execute(f"DELETE FROM kv_entries WHERE {where_clause}", params)
            conn.commit()
        return True

    async def index_done_callback(self) -> None:
        async with self._lock:
            conn = self._get_connection()
            conn.commit()

    async def drop(self) -> dict[str, str]:
        try:
            async with self._lock:
                conn = self._get_connection()
                conn.execute("DELETE FROM kv_entries")
                conn.commit()
            return {"status": "success", "message": "data dropped"}
        except Exception as e:
            logger.error(f"Error dropping {self.namespace}: {e}")
            return {"status": "error", "message": str(e)}
