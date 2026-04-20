import unittest
from unittest.mock import AsyncMock, patch

from ragent.base import QueryParam
from ragent.operate import (
    _QUERY_CACHE_TYPE_ANSWER,
    _QUERY_CACHE_TYPE_RENDER,
    _QUERY_CACHE_TYPE_RETRIEVAL,
    _QUERY_RESULT_KIND_ANSWER,
    _build_query_cache_payload,
    _build_query_request_fingerprint,
    _coerce_query_cache_payload,
    graph_query,
    hybrid_query,
)
from ragent.utils import compute_args_hash


class _FakeTokenizer:
    def encode(self, text):
        return list(str(text))


class _FakeKV:
    def __init__(self):
        self.global_config = {
            "enable_llm_cache": True,
            "enable_llm_cache_for_entity_extract": True,
        }
        self.store = {}

    async def get_by_id(self, key):
        return self.store.get(key)

    async def upsert(self, data):
        self.store.update(data)


class _Model:
    def __init__(self, response="cached answer"):
        self.response = response
        self.calls = []

    async def __call__(self, prompt, system_prompt=None, stream=False, **kwargs):
        self.calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "stream": stream,
                "kwargs": kwargs,
            }
        )
        return self.response


def _global_config(model):
    return {
        "llm_model_func": model,
        "llm_model_name": "unit-test-llm",
        "tokenizer": _FakeTokenizer(),
        "addon_params": {"language": "Chinese", "example_number": 1},
        "answer_prompt_mode": "single_prompt",
        "rerank_model_func": None,
        "tiktoken_model_name": "unit-test-tokenizer",
    }


def _hybrid_retrieval_debug():
    return {
        "high_level_keywords": ["指南"],
        "low_level_keywords": ["饮食"],
        "ll_keywords_str": "饮食",
        "hl_keywords_str": "指南",
        "graph_entities": [],
        "graph_relations": [],
        "vector_weights": {"c1": 1.0},
        "vector_texts": {"c1": "chunk text"},
        "vector_file_paths": {"c1": "/tmp/source.pdf"},
        "vector_metadata_map": {"c1": {"file_path": "/tmp/source.pdf"}},
        "graph_weights": {},
        "graph_texts": {},
        "graph_file_paths": {},
        "graph_metadata_map": {},
        "merged_candidates": [
            {
                "rank": 1,
                "source": "vector",
                "sources": ["vector"],
                "chunk_id": "c1",
                "score": 1.0,
                "file_path": "/tmp/source.pdf",
                "content": "chunk text",
            }
        ],
        "rerank_results": [{"index": 0, "relevance_score": 0.9}],
        "selected_candidate_indexes": [0],
        "results_text": ["chunk text"],
        "results_file_paths": ["/tmp/source.pdf"],
        "results_chunk_ids": ["c1"],
        "results_sources": [["vector"]],
        "results_source_labels": ["vector"],
        "results_chunk_metadata": [{"file_path": "/tmp/source.pdf"}],
        "text_units_context": [
            {
                "content": "chunk text",
                "file_path": "/tmp/source.pdf",
            }
        ],
        "referenced_file_paths": ["/tmp/source.pdf"],
        "stage_timings": [{"stage": "fake_retrieval", "label": "fake", "seconds": 0.1}],
    }


def _graph_retrieval_debug():
    return {
        "high_level_keywords": ["指南"],
        "low_level_keywords": ["饮食"],
        "graph_entities": [
            {
                "entity": "饮食",
                "type": "topic",
                "description": "desc",
                "file_path": "/tmp/graph.pdf",
            }
        ],
        "graph_relations": [],
        "entities_context": [
            {
                "entity": "饮食",
                "type": "topic",
                "description": "desc",
                "file_path": "/tmp/graph.pdf",
            }
        ],
        "relations_context": [],
        "text_units_context": [
            {
                "content": "graph chunk",
                "file_path": "/tmp/graph.pdf",
            }
        ],
        "referenced_file_paths": ["/tmp/graph.pdf"],
        "context_available": True,
        "stage_timings": [{"stage": "fake_graph", "label": "fake", "seconds": 0.1}],
    }


class QueryCacheSemanticsTests(unittest.IsolatedAsyncioTestCase):
    def test_compute_args_hash_uses_structured_json(self):
        self.assertEqual(
            compute_args_hash({"b": 2, "a": 1}),
            compute_args_hash({"a": 1, "b": 2}),
        )
        self.assertNotEqual(
            compute_args_hash({"a": 1, "b": 2}),
            compute_args_hash({"a": 1, "b": 3}),
        )

    def test_fingerprint_changes_for_result_related_params(self):
        model = _Model()
        config = _global_config(model)
        base = QueryParam(mode="hybrid", response_type="Multiple Paragraphs")
        changed_response = QueryParam(mode="hybrid", response_type="Bullet Points")
        changed_rerank = QueryParam(mode="hybrid", enable_rerank=False)

        base_key = _build_query_request_fingerprint(
            scope=_QUERY_CACHE_TYPE_ANSWER,
            query="q",
            query_param=base,
            global_config=config,
            answer_prompt_mode="single_prompt",
        )
        self.assertNotEqual(
            base_key,
            _build_query_request_fingerprint(
                scope=_QUERY_CACHE_TYPE_ANSWER,
                query="q",
                query_param=changed_response,
                global_config=config,
                answer_prompt_mode="single_prompt",
            ),
        )
        self.assertNotEqual(
            _build_query_request_fingerprint(
                scope=_QUERY_CACHE_TYPE_RETRIEVAL,
                query="q",
                query_param=base,
                global_config=config,
                answer_prompt_mode="single_prompt",
            ),
            _build_query_request_fingerprint(
                scope=_QUERY_CACHE_TYPE_RETRIEVAL,
                query="q",
                query_param=changed_rerank,
                global_config=config,
                answer_prompt_mode="single_prompt",
            ),
        )

    def test_payload_schema_round_trip_defaults(self):
        payload = _build_query_cache_payload(
            result_kind=_QUERY_RESULT_KIND_ANSWER,
            answer="answer",
            referenced_file_paths=["unknown_source", "/tmp/a.pdf", "/tmp/a.pdf"],
        )
        restored = _coerce_query_cache_payload(
            payload,
            expected_result_kind=_QUERY_RESULT_KIND_ANSWER,
        )
        self.assertEqual(restored["answer"], "answer")
        self.assertEqual(restored["referenced_file_paths"], ["/tmp/a.pdf"])
        self.assertIn("debug_payload_cacheable", restored)
        self.assertIn("final_context_document_chunks", restored)

    async def test_hybrid_answer_cache_short_circuits_warm_run(self):
        model = _Model("hybrid answer")
        config = _global_config(model)
        cache = _FakeKV()
        param = QueryParam(mode="hybrid")

        with patch(
            "ragent.operate._build_hybrid_retrieval_debug_data",
            new_callable=AsyncMock,
            return_value=_hybrid_retrieval_debug(),
        ) as retrieval_mock:
            answer, refs = await hybrid_query(
                "q",
                None,
                None,
                None,
                None,
                None,
                param,
                config,
                cache,
            )
            self.assertEqual(answer, "hybrid answer")
            self.assertEqual(refs, ["/tmp/source.pdf"])
            self.assertEqual(retrieval_mock.await_count, 1)
            self.assertEqual(len(model.calls), 1)

            retrieval_mock.reset_mock()
            retrieval_mock.side_effect = AssertionError("retrieval should short-circuit")
            answer, refs = await hybrid_query(
                "q",
                None,
                None,
                None,
                None,
                None,
                QueryParam(mode="hybrid"),
                config,
                cache,
            )
            self.assertEqual(answer, "hybrid answer")
            self.assertEqual(refs, ["/tmp/source.pdf"])
            self.assertEqual(retrieval_mock.await_count, 0)
            self.assertEqual(len(model.calls), 1)

        key_prefixes = {":".join(key.split(":", 2)[:2]) for key in cache.store}
        self.assertIn("hybrid:answer", key_prefixes)
        self.assertIn("hybrid:retrieval", key_prefixes)
        self.assertIn("hybrid:render", key_prefixes)

    async def test_hybrid_debug_reuses_retrieval_render_and_answer_caches(self):
        model = _Model("hybrid answer")
        config = _global_config(model)
        cache = _FakeKV()

        with patch(
            "ragent.operate._build_hybrid_retrieval_debug_data",
            new_callable=AsyncMock,
            return_value=_hybrid_retrieval_debug(),
        ):
            await hybrid_query(
                "q",
                None,
                None,
                None,
                None,
                None,
                QueryParam(mode="hybrid"),
                config,
                cache,
            )

        with patch(
            "ragent.operate._build_hybrid_retrieval_debug_data",
            new_callable=AsyncMock,
            side_effect=AssertionError("retrieval should come from cache"),
        ):
            answer, refs, debug = await hybrid_query(
                "q",
                None,
                None,
                None,
                None,
                None,
                QueryParam(mode="hybrid"),
                config,
                cache,
                return_debug=True,
            )

        self.assertEqual(answer, "hybrid answer")
        self.assertEqual(refs, ["/tmp/source.pdf"])
        stages = {item["stage"] for item in debug["stage_timings"]}
        self.assertIn("retrieval_cache_hit", stages)
        self.assertIn("render_cache_hit", stages)
        self.assertIn("prompt_cache_hit", stages)
        self.assertIn("answer_cache_hit", stages)
        self.assertEqual(len(model.calls), 1)

    async def test_graph_answer_cache_short_circuits_warm_run(self):
        model = _Model("graph answer")
        config = _global_config(model)
        cache = _FakeKV()

        with patch(
            "ragent.operate._build_graph_retrieval_debug_data",
            new_callable=AsyncMock,
            return_value=_graph_retrieval_debug(),
        ) as retrieval_mock:
            answer, refs = await graph_query(
                "q",
                None,
                None,
                None,
                None,
                QueryParam(mode="graph"),
                config,
                cache,
            )
            self.assertEqual(answer, "graph answer")
            self.assertEqual(refs, ["/tmp/graph.pdf"])
            self.assertEqual(retrieval_mock.await_count, 1)

            retrieval_mock.reset_mock()
            retrieval_mock.side_effect = AssertionError("retrieval should short-circuit")
            answer, refs = await graph_query(
                "q",
                None,
                None,
                None,
                None,
                QueryParam(mode="graph"),
                config,
                cache,
            )
            self.assertEqual(answer, "graph answer")
            self.assertEqual(refs, ["/tmp/graph.pdf"])
            self.assertEqual(retrieval_mock.await_count, 0)

    async def test_only_need_context_render_cache_short_circuits_retrieval(self):
        model = _Model("unused")
        config = _global_config(model)
        cache = _FakeKV()
        param = QueryParam(mode="hybrid", only_need_context=True)

        with patch(
            "ragent.operate._build_hybrid_retrieval_debug_data",
            new_callable=AsyncMock,
            return_value=_hybrid_retrieval_debug(),
        ) as retrieval_mock:
            first_context = await hybrid_query(
                "q",
                None,
                None,
                None,
                None,
                None,
                param,
                config,
                cache,
            )
            self.assertIn("Document Chunks", first_context)
            self.assertEqual(retrieval_mock.await_count, 1)

            retrieval_mock.reset_mock()
            retrieval_mock.side_effect = AssertionError("retrieval should come from cache")
            second_context = await hybrid_query(
                "q",
                None,
                None,
                None,
                None,
                None,
                QueryParam(mode="hybrid", only_need_context=True),
                config,
                cache,
            )
            self.assertEqual(second_context, first_context)
            self.assertEqual(retrieval_mock.await_count, 0)
            self.assertEqual(model.calls, [])

    async def test_conflicting_render_flags_raise(self):
        with self.assertRaises(ValueError):
            await hybrid_query(
                "q",
                None,
                None,
                None,
                None,
                None,
                QueryParam(
                    mode="hybrid",
                    only_need_context=True,
                    only_need_prompt=True,
                ),
                _global_config(_Model()),
                _FakeKV(),
            )


if __name__ == "__main__":
    unittest.main()
