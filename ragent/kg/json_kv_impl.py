import os
import time
from dataclasses import dataclass
from typing import Any, final

from ragent.base import (
    BaseKVStorage,
)
from ragent.namespace import NameSpace
from ragent.utils import (
    load_json,
    logger,
    write_json,
)
from .shared_storage import (
    get_namespace_data,
    get_storage_lock,
    get_data_init_lock,
    get_update_flag,
    set_all_update_flags,
    clear_all_update_flags,
    try_initialize_namespace,
)

_QUERY_CACHE_MANAGED_MODES = {"graph", "hybrid"}


@final
@dataclass
class JsonKVStorage(BaseKVStorage):
    def __post_init__(self):
        working_dir = self.global_config["working_dir"]
        if self.workspace:
            # Include workspace in the file path for data isolation
            workspace_dir = os.path.join(working_dir, self.workspace)
            os.makedirs(workspace_dir, exist_ok=True)
            self._file_name = os.path.join(
                workspace_dir, f"kv_store_{self.namespace}.json"
            )
        else:
            # Default behavior when workspace is empty
            self._file_name = os.path.join(
                working_dir, f"kv_store_{self.namespace}.json"
            )
        self._data = None
        self._storage_lock = None
        self.storage_updated = None

    def _should_manage_query_cache(self) -> bool:
        backend = str(self.global_config.get("query_cache_backend") or "json").lower()
        return (
            self.namespace == NameSpace.KV_STORE_LLM_RESPONSE_CACHE
            and backend == "json"
        )

    def _parse_flattened_cache_key(self, key: str) -> tuple[str, str, str] | None:
        parts = str(key).split(":", 2)
        if len(parts) != 3:
            return None
        return parts[0], parts[1], parts[2]

    def _is_managed_query_cache_key(self, key: str) -> bool:
        parsed = self._parse_flattened_cache_key(key)
        return bool(parsed and parsed[0] in _QUERY_CACHE_MANAGED_MODES)

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

    def _get_query_cache_created_at(self, value: dict[str, Any]) -> int:
        payload = value.get("return")
        if isinstance(payload, dict):
            try:
                return max(0, int(payload.get("created_at") or value.get("create_time") or 0))
            except (TypeError, ValueError):
                return max(0, int(value.get("create_time") or 0))
        try:
            return max(
                0,
                int(value.get("_query_cache_created_at") or value.get("create_time") or 0),
            )
        except (TypeError, ValueError):
            return max(0, int(value.get("create_time") or 0))

    def _get_query_cache_last_accessed_at(self, value: dict[str, Any]) -> int:
        payload = value.get("return")
        created_at = self._get_query_cache_created_at(value)
        if isinstance(payload, dict):
            try:
                return max(
                    0,
                    int(
                        payload.get("last_accessed_at")
                        or value.get("update_time")
                        or created_at
                    ),
                )
            except (TypeError, ValueError):
                return max(0, int(value.get("update_time") or created_at))
        try:
            return max(
                0,
                int(
                    value.get("_query_cache_last_accessed_at")
                    or value.get("update_time")
                    or created_at
                ),
            )
        except (TypeError, ValueError):
            return max(0, int(value.get("update_time") or created_at))

    def _is_query_cache_expired(self, key: str, value: dict[str, Any], now: int) -> bool:
        if not self._should_manage_query_cache() or not self._is_managed_query_cache_key(
            key
        ):
            return False

        ttl_seconds = self._query_cache_ttl_seconds()
        if ttl_seconds <= 0:
            return False

        created_at = self._get_query_cache_created_at(value)
        return created_at > 0 and created_at + ttl_seconds <= now

    def _touch_query_cache_entry(
        self, key: str, value: dict[str, Any], now: int
    ) -> dict[str, Any] | None:
        if not self._should_manage_query_cache() or not self._is_managed_query_cache_key(
            key
        ):
            return value

        if self._is_query_cache_expired(key, value, now):
            return None

        updated_value = dict(value)
        payload = updated_value.get("return")
        if isinstance(payload, dict):
            payload = dict(payload)
            payload["created_at"] = self._get_query_cache_created_at(updated_value) or now
            payload["last_accessed_at"] = now
            payload["access_count"] = max(0, int(payload.get("access_count") or 0)) + 1
            updated_value["return"] = payload
        else:
            updated_value["_query_cache_created_at"] = (
                self._get_query_cache_created_at(updated_value) or now
            )
            updated_value["_query_cache_last_accessed_at"] = now
            updated_value["_query_cache_access_count"] = (
                max(0, int(updated_value.get("_query_cache_access_count") or 0)) + 1
            )

        updated_value["update_time"] = now
        return updated_value

    async def _prune_query_cache_entries(self) -> bool:
        if not self._should_manage_query_cache():
            return False

        now = int(time.time())
        keys_to_delete = [
            key
            for key, value in list(self._data.items())
            if isinstance(value, dict) and self._is_query_cache_expired(key, value, now)
        ]
        for key in keys_to_delete:
            self._data.pop(key, None)

        max_entries = self._query_cache_max_entries()
        if max_entries > 0:
            managed_entries = []
            for key, value in list(self._data.items()):
                if not isinstance(value, dict) or not self._is_managed_query_cache_key(key):
                    continue
                managed_entries.append(
                    (
                        self._get_query_cache_last_accessed_at(value),
                        self._get_query_cache_created_at(value),
                        key,
                    )
                )

            overflow = len(managed_entries) - max_entries
            if overflow > 0:
                managed_entries.sort(key=lambda item: (item[0], item[1], item[2]))
                for _, _, key in managed_entries[:overflow]:
                    self._data.pop(key, None)
                    if key not in keys_to_delete:
                        keys_to_delete.append(key)

        return bool(keys_to_delete)

    def _prepare_return_record(
        self, key: str, value: dict[str, Any]
    ) -> dict[str, Any]:
        result = dict(value)
        result.setdefault("create_time", 0)
        result.setdefault("update_time", 0)
        result["_id"] = key
        return result

    async def initialize(self):
        """Initialize storage data"""
        self._storage_lock = get_storage_lock()
        self.storage_updated = await get_update_flag(self.namespace)
        async with get_data_init_lock():
            # check need_init must before get_namespace_data
            need_init = await try_initialize_namespace(self.namespace)
            self._data = await get_namespace_data(self.namespace)
            if need_init:
                loaded_data = load_json(self._file_name) or {}
                async with self._storage_lock:
                    # Migrate legacy cache structure if needed
                    if self.namespace.endswith("_cache"):
                        loaded_data = await self._migrate_legacy_cache_structure(
                            loaded_data
                        )

                    self._data.update(loaded_data)
                    await self._prune_query_cache_entries()
                    data_count = len(loaded_data)

                    logger.info(
                        f"Process {os.getpid()} KV load {self.namespace} with {data_count} records"
                    )

    async def refresh_from_storage(self) -> bool:
        """Reload the latest persisted namespace data into memory.

        This is primarily used by metadata readers that must observe writes from
        other long-lived processes, even when this process does not share the
        in-memory update flag registry.
        """
        if self._storage_lock is None or self._data is None:
            return False

        loaded_data = load_json(self._file_name) or {}

        async with self._storage_lock:
            if self.namespace.endswith("_cache"):
                loaded_data = await self._migrate_legacy_cache_structure(loaded_data)

            self._data.clear()
            self._data.update(loaded_data)
            await self._prune_query_cache_entries()

            if self.storage_updated is not None:
                self.storage_updated.value = False

        return True

    async def index_done_callback(self) -> None:
        async with self._storage_lock:
            if self.storage_updated.value:
                await self._prune_query_cache_entries()
                data_dict = (
                    dict(self._data) if hasattr(self._data, "_getvalue") else self._data
                )

                # Calculate data count - all data is now flattened
                data_count = len(data_dict)

                logger.debug(
                    f"Process {os.getpid()} KV writting {data_count} records to {self.namespace}"
                )
                write_json(data_dict, self._file_name)
                await clear_all_update_flags(self.namespace)

    async def get_all(self) -> dict[str, Any]:
        """Get all data from storage

        Returns:
            Dictionary containing all stored data
        """
        async with self._storage_lock:
            result = {}
            for key, value in self._data.items():
                if value:
                    # Create a copy to avoid modifying the original data
                    data = dict(value)
                    # Ensure time fields are present, provide default values for old data
                    data.setdefault("create_time", 0)
                    data.setdefault("update_time", 0)
                    result[key] = data
                else:
                    result[key] = value
            return result

    async def get_by_id(self, id: str) -> dict[str, Any] | None:
        async with self._storage_lock:
            result = self._data.get(id)
            if result:
                if isinstance(result, dict):
                    touched_result = self._touch_query_cache_entry(
                        id, result, int(time.time())
                    )
                    if touched_result is None:
                        self._data.pop(id, None)
                        await set_all_update_flags(self.namespace)
                        return None
                    result = touched_result
                    self._data[id] = result
                    if self._is_managed_query_cache_key(id):
                        await set_all_update_flags(self.namespace)
                result = self._prepare_return_record(id, result)
            return result

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        async with self._storage_lock:
            results = []
            for id in ids:
                data = self._data.get(id, None)
                if data:
                    if isinstance(data, dict):
                        touched_data = self._touch_query_cache_entry(
                            id, data, int(time.time())
                        )
                        if touched_data is None:
                            self._data.pop(id, None)
                            await set_all_update_flags(self.namespace)
                            results.append(None)
                            continue
                        data = touched_data
                        self._data[id] = data
                        if self._is_managed_query_cache_key(id):
                            await set_all_update_flags(self.namespace)
                    results.append(self._prepare_return_record(id, data))
                else:
                    results.append(None)
            return results

    async def filter_keys(self, keys: set[str]) -> set[str]:
        async with self._storage_lock:
            return set(keys) - set(self._data.keys())

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        """
        Importance notes for in-memory storage:
        1. Changes will be persisted to disk during the next index_done_callback
        2. update flags to notify other processes that data persistence is needed
        """
        if not data:
            return

        current_time = int(time.time())  # Get current Unix timestamp

        logger.debug(f"Inserting {len(data)} records to {self.namespace}")
        async with self._storage_lock:
            # Add timestamps to data based on whether key exists
            for k, v in data.items():
                # For text_chunks namespace, ensure llm_cache_list field exists
                if "text_chunks" in self.namespace:
                    if "llm_cache_list" not in v:
                        v["llm_cache_list"] = []

                # Add timestamps based on whether key exists
                if k in self._data:  # Key exists, only update update_time
                    v["update_time"] = current_time
                else:  # New key, set both create_time and update_time
                    v["create_time"] = current_time
                    v["update_time"] = current_time

                v["_id"] = k

            self._data.update(data)
            await self._prune_query_cache_entries()
            await set_all_update_flags(self.namespace)

    async def delete(self, ids: list[str]) -> None:
        """Delete specific records from storage by their IDs

        Importance notes for in-memory storage:
        1. Changes will be persisted to disk during the next index_done_callback
        2. update flags to notify other processes that data persistence is needed

        Args:
            ids (list[str]): List of document IDs to be deleted from storage

        Returns:
            None
        """
        async with self._storage_lock:
            any_deleted = False
            for doc_id in ids:
                result = self._data.pop(doc_id, None)
                if result is not None:
                    any_deleted = True

            if any_deleted:
                await set_all_update_flags(self.namespace)

    async def drop_cache_by_modes(self, modes: list[str] | None = None) -> bool:
        """Delete specific records from storage by cache mode

        Importance notes for in-memory storage:
        1. Changes will be persisted to disk during the next index_done_callback
        2. update flags to notify other processes that data persistence is needed

        Args:
            modes (list[str]): List of cache modes to be dropped from storage

        Returns:
             True: if the cache drop successfully
             False: if the cache drop failed
        """
        if not modes:
            return False

        try:
            async with self._storage_lock:
                keys_to_delete = []
                modes_set = set(modes)  # Convert to set for efficient lookup

                for key in list(self._data.keys()):
                    # Parse flattened cache key: mode:cache_type:hash
                    parts = key.split(":", 2)
                    if len(parts) == 3 and parts[0] in modes_set:
                        keys_to_delete.append(key)

                # Batch delete
                for key in keys_to_delete:
                    self._data.pop(key, None)

                if keys_to_delete:
                    await set_all_update_flags(self.namespace)
                    logger.info(
                        f"Dropped {len(keys_to_delete)} cache entries for modes: {modes}"
                    )

            return True
        except Exception as e:
            logger.error(f"Error dropping cache by modes: {e}")
            return False

    # async def drop_cache_by_chunk_ids(self, chunk_ids: list[str] | None = None) -> bool:
    #     """Delete specific cache records from storage by chunk IDs

    #     Importance notes for in-memory storage:
    #     1. Changes will be persisted to disk during the next index_done_callback
    #     2. update flags to notify other processes that data persistence is needed

    #     Args:
    #         chunk_ids (list[str]): List of chunk IDs to be dropped from storage

    #     Returns:
    #          True: if the cache drop successfully
    #          False: if the cache drop failed
    #     """
    #     if not chunk_ids:
    #         return False

    #     try:
    #         async with self._storage_lock:
    #             # Iterate through all cache modes to find entries with matching chunk_ids
    #             for mode_key, mode_data in list(self._data.items()):
    #                 if isinstance(mode_data, dict):
    #                     # Check each cached entry in this mode
    #                     for cache_key, cache_entry in list(mode_data.items()):
    #                         if (
    #                             isinstance(cache_entry, dict)
    #                             and cache_entry.get("chunk_id") in chunk_ids
    #                         ):
    #                             # Remove this cache entry
    #                             del mode_data[cache_key]
    #                             logger.debug(
    #                                 f"Removed cache entry {cache_key} for chunk {cache_entry.get('chunk_id')}"
    #                             )

    #                     # If the mode is now empty, remove it entirely
    #                     if not mode_data:
    #                         del self._data[mode_key]

    #             # Set update flags to notify persistence is needed
    #             await set_all_update_flags(self.namespace)

    #         logger.info(f"Cleared cache for {len(chunk_ids)} chunk IDs")
    #         return True
    #     except Exception as e:
    #         logger.error(f"Error clearing cache by chunk IDs: {e}")
    #         return False

    async def drop(self) -> dict[str, str]:
        """Drop all data from storage and clean up resources
           This action will persistent the data to disk immediately.

        This method will:
        1. Clear all data from memory
        2. Update flags to notify other processes
        3. Trigger index_done_callback to save the empty state

        Returns:
            dict[str, str]: Operation status and message
            - On success: {"status": "success", "message": "data dropped"}
            - On failure: {"status": "error", "message": "<error details>"}
        """
        try:
            async with self._storage_lock:
                self._data.clear()
                await set_all_update_flags(self.namespace)

            await self.index_done_callback()
            logger.info(f"Process {os.getpid()} drop {self.namespace}")
            return {"status": "success", "message": "data dropped"}
        except Exception as e:
            logger.error(f"Error dropping {self.namespace}: {e}")
            return {"status": "error", "message": str(e)}

    async def _migrate_legacy_cache_structure(self, data: dict) -> dict:
        """Migrate legacy nested cache structure to flattened structure

        Args:
            data: Original data dictionary that may contain legacy structure

        Returns:
            Migrated data dictionary with flattened cache keys
        """
        from ragent.utils import generate_cache_key

        # Early return if data is empty
        if not data:
            return data

        # Check first entry to see if it's already in new format
        first_key = next(iter(data.keys()))
        if ":" in first_key and len(first_key.split(":")) == 3:
            # Already in flattened format, return as-is
            return data

        migrated_data = {}
        migration_count = 0

        for key, value in data.items():
            # Check if this is a legacy nested cache structure
            if isinstance(value, dict) and all(
                isinstance(v, dict) and "return" in v for v in value.values()
            ):
                # This looks like a legacy cache mode with nested structure
                mode = key
                for cache_hash, cache_entry in value.items():
                    cache_type = cache_entry.get("cache_type", "extract")
                    flattened_key = generate_cache_key(mode, cache_type, cache_hash)
                    migrated_data[flattened_key] = cache_entry
                    migration_count += 1
            else:
                # Keep non-cache data or already flattened cache data as-is
                migrated_data[key] = value

        if migration_count > 0:
            logger.info(
                f"Migrated {migration_count} legacy cache entries to flattened structure"
            )
            # Persist migrated data immediately
            write_json(migrated_data, self._file_name)

        return migrated_data

    async def finalize(self):
        """Finalize storage resources
        Persistence cache data to disk before exiting
        """
        if self.namespace.endswith("_cache"):
            await self.index_done_callback()
