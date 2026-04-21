import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import ragent.ragent as ragent_module

Ragent = ragent_module.Ragent


async def _fake_llm(*args, **kwargs):
    return "ok"


async def _fake_embed(*args, **kwargs):
    return []


def _identity_priority_limit(*args, **kwargs):
    def _decorate(func):
        return func

    return _decorate


class QueryCacheBackendSelectionTests(unittest.TestCase):
    def _create_ragent(self, *, backend: str, requested_storage_names: list[str]):
        def _fake_get_storage_class(_self, storage_name: str):
            requested_storage_names.append(storage_name)

            def _factory(**kwargs):
                return SimpleNamespace(storage_name=storage_name, **kwargs)

            return _factory

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(
            Ragent,
            "_get_storage_class",
            autospec=True,
            side_effect=_fake_get_storage_class,
        ), patch.object(
            ragent_module,
            "priority_limit_async_func_call",
            side_effect=_identity_priority_limit,
        ), patch(
            "ragent.kg.shared_storage.initialize_share_data",
            return_value=None,
        ):
            rag = Ragent(
                working_dir=tmpdir,
                llm_model_name="unit-test-llm",
                llm_model_func=_fake_llm,
                embedding_func=_fake_embed,
                tokenizer=SimpleNamespace(encode=lambda text: list(str(text or ""))),
                query_cache_backend=backend,
                auto_manage_storages_states=False,
            )
        return rag

    def test_sqlite_backend_selects_sqlite_query_cache_storage(self):
        requested_storage_names: list[str] = []
        rag = self._create_ragent(
            backend="SQLITE",
            requested_storage_names=requested_storage_names,
        )

        self.assertEqual(rag.query_cache_backend, "sqlite")
        self.assertIn("SQLiteQueryCacheStorage", requested_storage_names)
        self.assertEqual(
            rag.llm_response_cache.storage_name,
            "SQLiteQueryCacheStorage",
        )

    def test_sqlite_query_cache_storage_alias_is_accepted(self):
        requested_storage_names: list[str] = []
        rag = self._create_ragent(
            backend="SQLiteQueryCacheStorage",
            requested_storage_names=requested_storage_names,
        )

        self.assertEqual(rag.query_cache_backend, "sqlite")
        self.assertIn("SQLiteQueryCacheStorage", requested_storage_names)
        self.assertEqual(
            rag.llm_response_cache.storage_name,
            "SQLiteQueryCacheStorage",
        )

    def test_non_sqlite_backend_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.object(
            ragent_module,
            "priority_limit_async_func_call",
            side_effect=_identity_priority_limit,
        ), patch(
            "ragent.kg.shared_storage.initialize_share_data",
            return_value=None,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Only 'sqlite' is supported",
            ):
                Ragent(
                    working_dir=tmpdir,
                    llm_model_name="unit-test-llm",
                    llm_model_func=_fake_llm,
                    embedding_func=_fake_embed,
                    tokenizer=SimpleNamespace(
                        encode=lambda text: list(str(text or ""))
                    ),
                    query_cache_backend="json",
                    auto_manage_storages_states=False,
                )


if __name__ == "__main__":
    unittest.main()
