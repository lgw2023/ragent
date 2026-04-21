import tempfile
import unittest

from ragent.kg.sqlite_query_cache_impl import SQLiteQueryCacheStorage
from ragent.namespace import NameSpace
from ragent.operate import _QUERY_RESULT_KIND_ANSWER, _build_query_cache_payload


class SQLiteQueryCacheStorageTests(unittest.IsolatedAsyncioTestCase):
    async def _create_storage(self, *, ttl_seconds=0, max_entries=0):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        storage = SQLiteQueryCacheStorage(
            namespace=NameSpace.KV_STORE_LLM_RESPONSE_CACHE,
            workspace="",
            global_config={
                "working_dir": temp_dir.name,
                "query_cache_ttl_seconds": ttl_seconds,
                "query_cache_max_entries": max_entries,
            },
            embedding_func=None,
        )
        await storage.initialize()
        self.addAsyncCleanup(storage.finalize)
        return storage, temp_dir.name

    async def test_ttl_expires_only_query_cache_entries(self):
        storage, _ = await self._create_storage(ttl_seconds=1)
        expired_payload = _build_query_cache_payload(
            result_kind=_QUERY_RESULT_KIND_ANSWER,
            answer="expired",
            created_at=10,
            last_accessed_at=10,
            access_count=1,
        )

        await storage.upsert(
            {
                "hybrid:answer:expired": {"return": expired_payload},
                "default:extract:keep": {"return": "keep-me"},
            }
        )

        self.assertIsNone(await storage.get_by_id("hybrid:answer:expired"))
        self.assertEqual(
            (await storage.get_by_id("default:extract:keep"))["return"],
            "keep-me",
        )

    async def test_lru_prunes_oldest_query_cache_entries(self):
        storage, _ = await self._create_storage(max_entries=2)

        await storage.upsert(
            {
                "hybrid:answer:a": {
                    "return": _build_query_cache_payload(
                        result_kind=_QUERY_RESULT_KIND_ANSWER,
                        answer="a",
                        created_at=1,
                        last_accessed_at=1,
                        access_count=1,
                    )
                },
                "hybrid:answer:b": {
                    "return": _build_query_cache_payload(
                        result_kind=_QUERY_RESULT_KIND_ANSWER,
                        answer="b",
                        created_at=2,
                        last_accessed_at=2,
                        access_count=1,
                    )
                },
                "default:extract:keep": {"return": "keep-me"},
            }
        )
        await storage.upsert(
            {
                "graph:answer:c": {
                    "return": _build_query_cache_payload(
                        result_kind=_QUERY_RESULT_KIND_ANSWER,
                        answer="c",
                        created_at=3,
                        last_accessed_at=3,
                        access_count=1,
                    )
                }
            }
        )

        self.assertIsNone(await storage.get_by_id("hybrid:answer:a"))
        self.assertEqual(
            (await storage.get_by_id("hybrid:answer:b"))["return"]["answer"],
            "b",
        )
        self.assertEqual(
            (await storage.get_by_id("graph:answer:c"))["return"]["answer"],
            "c",
        )
        self.assertEqual(
            (await storage.get_by_id("default:extract:keep"))["return"],
            "keep-me",
        )

    async def test_drop_cache_by_modes_removes_requested_query_modes(self):
        storage, _ = await self._create_storage()
        await storage.upsert(
            {
                "hybrid:answer:a": {
                    "return": _build_query_cache_payload(
                        result_kind=_QUERY_RESULT_KIND_ANSWER,
                        answer="hybrid",
                    )
                },
                "graph:answer:b": {
                    "return": _build_query_cache_payload(
                        result_kind=_QUERY_RESULT_KIND_ANSWER,
                        answer="graph",
                    )
                },
                "default:extract:c": {"return": "keep-me"},
            }
        )

        self.assertTrue(await storage.drop_cache_by_modes(["hybrid"]))
        self.assertIsNone(await storage.get_by_id("hybrid:answer:a"))
        self.assertEqual(
            (await storage.get_by_id("graph:answer:b"))["return"]["answer"],
            "graph",
        )
        self.assertEqual(
            (await storage.get_by_id("default:extract:c"))["return"],
            "keep-me",
        )

if __name__ == "__main__":
    unittest.main()
