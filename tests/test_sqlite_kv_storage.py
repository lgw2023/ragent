import json
import tempfile
import unittest

from ragent.kg.sqlite_kv_impl import SQLiteKVStorage
from ragent.namespace import NameSpace


class SQLiteKVStorageTests(unittest.IsolatedAsyncioTestCase):
    async def _create_storage(
        self,
        *,
        working_dir: str,
        namespace: str = NameSpace.KV_STORE_INDEX_METADATA,
        workspace: str = "",
    ):
        storage = SQLiteKVStorage(
            namespace=namespace,
            workspace=workspace,
            global_config={"working_dir": working_dir},
            embedding_func=None,
        )
        await storage.initialize()
        self.addAsyncCleanup(storage.finalize)
        return storage

    async def test_initialize_migrates_legacy_json_kv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = await self._create_storage(working_dir=tmpdir)
            await storage.drop()

            legacy_path = f"{tmpdir}/kv_store_{NameSpace.KV_STORE_INDEX_METADATA}.json"
            with open(legacy_path, "w", encoding="utf-8") as file:
                json.dump(
                    {
                        "corpus": {
                            "corpus_revision": 2,
                            "index_digest": "rev-2",
                            "create_time": 11,
                            "update_time": 12,
                        }
                    },
                    file,
                    ensure_ascii=False,
                )

            await storage.finalize()
            await storage.initialize()

            record = await storage.get_by_id("corpus")
            self.assertIsNotNone(record)
            self.assertEqual(record["corpus_revision"], 2)
            self.assertEqual(record["index_digest"], "rev-2")
            self.assertEqual(record["create_time"], 11)
            self.assertEqual(record["update_time"], 12)

    async def test_refresh_from_storage_observes_updates_from_other_connection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = await self._create_storage(working_dir=tmpdir)
            second = await self._create_storage(working_dir=tmpdir)

            await first.upsert(
                {"corpus": {"corpus_revision": 1, "index_digest": None}}
            )
            await second.upsert(
                {"corpus": {"corpus_revision": 2, "index_digest": "rev-2"}}
            )

            self.assertTrue(await first.refresh_from_storage())
            record = await first.get_by_id("corpus")

            self.assertIsNotNone(record)
            self.assertEqual(record["corpus_revision"], 2)
            self.assertEqual(record["index_digest"], "rev-2")

    async def test_text_chunks_upsert_adds_llm_cache_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = await self._create_storage(
                working_dir=tmpdir,
                namespace=NameSpace.KV_STORE_TEXT_CHUNKS,
            )

            await storage.upsert(
                {
                    "chunk-1": {
                        "content": "chunk text",
                        "tokens": 3,
                        "full_doc_id": "doc-1",
                    }
                }
            )

            record = await storage.get_by_id("chunk-1")
            self.assertIsNotNone(record)
            self.assertEqual(record["llm_cache_list"], [])


if __name__ == "__main__":
    unittest.main()
