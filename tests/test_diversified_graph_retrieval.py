import unittest

from ragent.base import QueryParam
from ragent.operate import (
    _build_diversified_retrieval_queries,
    _chunk_file_group_key,
    _coerce_score,
    _is_low_signal_chunk_candidate,
    _is_normative_chunk_candidate,
    _query_graph_hit_vectors_with_shared_embedding,
    _select_hybrid_context_entries,
    _retrieval_only_rerank_disabled,
    _query_vector_storage_diversified,
)
import numpy as np


class _FakeVectorStorage:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    async def query(self, query, top_k, ids=None):
        self.calls.append((query, top_k, ids))
        return list(self._responses.get(query, []))


class _TimedFakeVectorStorage(_FakeVectorStorage):
    async def query(
        self,
        query,
        top_k,
        ids=None,
        *,
        timing_collector=None,
        stage_prefix=None,
    ):
        if timing_collector is not None:
            timing_collector.append(
                {
                    "stage": f"{stage_prefix}_fake_query",
                    "label": "fake query",
                    "seconds": 0.001,
                }
            )
        return await super().query(query, top_k, ids=ids)


class _BatchFakeVectorStorage(_FakeVectorStorage):
    async def query_many(
        self,
        queries,
        top_k,
        ids=None,
        *,
        timing_collector=None,
        stage_prefix=None,
    ):
        self.calls.append((tuple(queries), top_k, ids))
        if timing_collector is not None:
            timing_collector.append(
                {
                    "stage": f"{stage_prefix}_embedding",
                    "label": "fake batch embedding",
                    "seconds": 0.002,
                }
            )
        return [list(self._responses.get(query, [])) for query in queries]


class _SharedEmbeddingFunc:
    def __init__(self):
        self.calls = []

    async def __call__(self, queries, _priority=None):
        self.calls.append((list(queries), _priority))
        return list(queries)


class _EmbeddingBatchFakeVectorStorage:
    def __init__(self, responses, embedding_func):
        self._responses = responses
        self.embedding_func = embedding_func
        self.calls = []

    async def query_many_by_embeddings(
        self,
        embeddings,
        top_k,
        ids=None,
        *,
        timing_collector=None,
        stage_prefix=None,
    ):
        embedding_list = list(embeddings)
        self.calls.append((tuple(embedding_list), top_k, ids, stage_prefix))
        if timing_collector is not None:
            timing_collector.append(
                {
                    "stage": f"{stage_prefix}_index_search",
                    "label": "fake precomputed vector query",
                    "seconds": 0.001,
                }
            )
        return [list(self._responses.get(embedding, [])) for embedding in embedding_list]


class DiversifiedGraphRetrievalTests(unittest.IsolatedAsyncioTestCase):
    def test_build_diversified_queries_splits_multi_constraint_query(self):
        queries = _build_diversified_retrieval_queries("含糖饮料, 中速步行，爬楼")
        self.assertEqual(
            queries,
            [
                "含糖饮料, 中速步行,爬楼",
                "含糖饮料",
                "中速步行",
                "爬楼",
            ],
        )

    def test_build_diversified_queries_normalizes_fullwidth_punctuation(self):
        queries = _build_diversified_retrieval_queries("中速（5km/h）")
        self.assertEqual(queries, ["中速(5km/h)"])

    def test_coerce_score_supports_numpy_scalar(self):
        self.assertAlmostEqual(_coerce_score(np.float64(0.81)), 0.81)

    def test_quantitative_appendix_chunk_is_not_low_signal(self):
        metadata = {
            "section_path": "附录三 常见身体活动强度和能量消耗表",
            "source_ref": "中国居民膳食指南_2022.pdf | p.225-227 | 附录三 常见身体活动强度和能量消耗表",
        }
        content = (
            "步行 中速（5km/h） 中强度 3.5 38.5 32.7 "
            "上楼 高强度 8.0 88.0 74.7"
        )
        self.assertFalse(
            _is_low_signal_chunk_candidate(
                "/tmp/example.pdf",
                metadata,
                content,
            )
        )
        self.assertTrue(_is_normative_chunk_candidate(metadata, content))

    def test_chunk_group_key_prefers_source_ref(self):
        metadata = {"source_ref": "doc.pdf | p.225-227 | 附录三"}
        self.assertEqual(
            _chunk_file_group_key("/tmp/doc.pdf", metadata),
            "doc.pdf | p.225-227 | 附录三",
        )

    def test_retrieval_only_rerank_disable_is_explicit_opt_in(self):
        default_param = QueryParam(only_need_context=True)
        self.assertFalse(_retrieval_only_rerank_disabled(default_param, {}))

        disabled_param = QueryParam(only_need_context=True)
        disabled_param.disable_rerank_for_retrieval_only = True
        self.assertTrue(_retrieval_only_rerank_disabled(disabled_param, {}))

        answer_param = QueryParam(only_need_context=False)
        answer_param.disable_rerank_for_retrieval_only = True
        self.assertFalse(_retrieval_only_rerank_disabled(answer_param, {}))

    def test_final_chunk_selection_covers_atomic_query_variants(self):
        rerank_results = [{"index": 0}, {"index": 1}, {"index": 2}]
        results_text = [
            "含糖饮料 330ml 150kcal",
            "步行 中速（5km/h） 38.5",
            "上楼 8.0 88.0",
        ]
        results_file_paths = ["/tmp/doc.pdf"] * 3
        results_chunk_metadata = [
            {
                "source_ref": "doc.pdf | p.274",
                "matched_query_variants": ["含糖饮料"],
            },
            {
                "source_ref": "doc.pdf | p.225-227",
                "section_path": "附录三 常见身体活动强度和能量消耗表",
                "matched_query_variants": ["中速步行"],
            },
            {
                "source_ref": "doc.pdf | p.225-227",
                "section_path": "附录三 常见身体活动强度和能量消耗表",
                "matched_query_variants": ["爬楼"],
            },
        ]
        _, text_units_context = _select_hybrid_context_entries(
            rerank_results=rerank_results,
            results_text=results_text,
            results_file_paths=results_file_paths,
            results_chunk_metadata=results_chunk_metadata,
            query_param=QueryParam(chunk_top_k=3),
            query_variants=["含糖饮料", "中速步行", "爬楼"],
        )
        combined = "\n".join(item["content"] for item in text_units_context)
        self.assertIn("中速（5km/h）", combined)
        self.assertIn("上楼", combined)

    def test_quantitative_table_prefers_chunk_with_actual_variant_coverage(self):
        rerank_results = [
            {"index": 0},
            {"index": 1},
            {"index": 2},
            {"index": 3},
        ]
        results_text = [
            "游泳 爬泳（慢） 8.0 88.0 74.7",
            "步行 很快（7km/h） 下楼 上楼 8.0 88.0 74.7",
            "步行 慢速（3km/h） 中速（5km/h） 快速（5.5~6km/h） 38.5 32.7",
            "含糖饮料 330ml 150kcal",
        ]
        results_file_paths = ["/tmp/doc.pdf"] * 4
        results_chunk_metadata = [
            {
                "source_ref": "doc.pdf | p.225-227",
                "section_path": "附录三 常见身体活动强度和能量消耗表",
                "matched_query_variants": ["能量消耗"],
            },
            {
                "source_ref": "doc.pdf | p.225-227",
                "section_path": "附录三 常见身体活动强度和能量消耗表",
                "matched_query_variants": ["中速步行", "爬楼", "能量消耗"],
            },
            {
                "source_ref": "doc.pdf | p.225-227",
                "section_path": "附录三 常见身体活动强度和能量消耗表",
                "matched_query_variants": ["中速步行", "能量消耗"],
            },
            {
                "source_ref": "doc.pdf | p.274",
                "matched_query_variants": ["含糖饮料"],
            },
        ]
        _, text_units_context = _select_hybrid_context_entries(
            rerank_results=rerank_results,
            results_text=results_text,
            results_file_paths=results_file_paths,
            results_chunk_metadata=results_chunk_metadata,
            query_param=QueryParam(chunk_top_k=3),
            query_variants=["含糖饮料", "中速步行", "爬楼", "能量消耗"],
        )
        combined = "\n".join(item["content"] for item in text_units_context)
        self.assertIn("中速（5km/h）", combined)
        self.assertIn("上楼", combined)
        self.assertNotIn("游泳 爬泳（慢）", combined)

    async def test_diversified_query_preserves_specific_activity_entities(self):
        storage = _FakeVectorStorage(
            {
                "含糖饮料, 中速步行, 爬楼": [
                    {"entity_name": "含糖饮料", "distance": 0.83},
                    {"entity_name": "能量平衡", "distance": 0.79},
                ],
                "含糖饮料": [
                    {"entity_name": "含糖饮料", "distance": 0.84},
                ],
                "中速步行": [
                    {"entity_name": "中速(5km/h)", "distance": 0.81},
                    {"entity_name": "步行", "distance": 0.78},
                ],
                "爬楼": [
                    {"entity_name": "上楼", "distance": 0.82},
                ],
            }
        )

        results = await _query_vector_storage_diversified(
            "含糖饮料, 中速步行, 爬楼",
            storage,
            top_k=4,
        )

        names = [item["entity_name"] for item in results]
        self.assertIn("含糖饮料", names)
        self.assertIn("中速(5km/h)", names)
        self.assertIn("上楼", names)
        self.assertEqual(
            [query for query, _, _ in storage.calls],
            ["含糖饮料, 中速步行, 爬楼", "含糖饮料", "中速步行", "爬楼"],
        )

    async def test_diversified_query_records_optional_timing_stages(self):
        storage = _TimedFakeVectorStorage(
            {
                "含糖饮料, 中速步行": [{"entity_name": "含糖饮料", "distance": 0.83}],
                "含糖饮料": [{"entity_name": "含糖饮料", "distance": 0.84}],
                "中速步行": [{"entity_name": "中速(5km/h)", "distance": 0.81}],
            }
        )
        timings = []

        results = await _query_vector_storage_diversified(
            "含糖饮料, 中速步行",
            storage,
            top_k=2,
            timing_collector=timings,
            stage_prefix="unit_vector",
        )

        self.assertEqual(len(results), 2)
        stages = [item["stage"] for item in timings]
        self.assertIn("unit_vector_fake_query", stages)
        self.assertIn("unit_vector_merge", stages)

    async def test_diversified_query_uses_batch_query_when_supported(self):
        storage = _BatchFakeVectorStorage(
            {
                "含糖饮料, 中速步行": [{"entity_name": "含糖饮料", "distance": 0.83}],
                "含糖饮料": [{"entity_name": "含糖饮料", "distance": 0.84}],
                "中速步行": [{"entity_name": "中速(5km/h)", "distance": 0.81}],
            }
        )
        timings = []

        results = await _query_vector_storage_diversified(
            "含糖饮料, 中速步行",
            storage,
            top_k=2,
            timing_collector=timings,
            stage_prefix="unit_vector",
        )

        self.assertEqual([item["entity_name"] for item in results], ["含糖饮料", "中速(5km/h)"])
        self.assertEqual(
            storage.calls,
            [(("含糖饮料, 中速步行", "含糖饮料", "中速步行"), 12, None)],
        )
        stages = [item["stage"] for item in timings]
        self.assertIn("unit_vector_embedding", stages)
        self.assertIn("unit_vector_merge", stages)

    async def test_graph_hit_vectors_share_one_embedding_batch(self):
        embedding_func = _SharedEmbeddingFunc()
        entity_storage = _EmbeddingBatchFakeVectorStorage(
            {
                "含糖饮料, 中速步行": [
                    {"entity_name": "含糖饮料", "distance": 0.83}
                ],
                "含糖饮料": [{"entity_name": "含糖饮料", "distance": 0.84}],
                "中速步行": [{"entity_name": "中速(5km/h)", "distance": 0.81}],
            },
            embedding_func,
        )
        relation_storage = _EmbeddingBatchFakeVectorStorage(
            {
                "能量消耗": [
                    {
                        "src_id": "中速(5km/h)",
                        "tgt_id": "身体活动能量消耗",
                        "distance": 0.82,
                    }
                ]
            },
            embedding_func,
        )
        timings = []

        result = await _query_graph_hit_vectors_with_shared_embedding(
            "含糖饮料, 中速步行",
            "能量消耗",
            entity_storage,
            relation_storage,
            QueryParam(top_k=2),
            timings,
        )

        self.assertIsNotNone(result)
        entity_results, relation_results = result
        self.assertEqual(
            embedding_func.calls,
            [
                (
                    ["含糖饮料, 中速步行", "含糖饮料", "中速步行", "能量消耗"],
                    5,
                )
            ],
        )
        self.assertEqual(
            entity_storage.calls,
            [(("含糖饮料, 中速步行", "含糖饮料", "中速步行"), 12, None, "graph_entity_vector")],
        )
        self.assertEqual(
            relation_storage.calls,
            [(("能量消耗",), 2, None, "graph_relation_vector")],
        )
        self.assertEqual(
            [item["entity_name"] for item in entity_results],
            ["含糖饮料", "中速(5km/h)"],
        )
        self.assertEqual(relation_results[0]["src_id"], "中速(5km/h)")

        stages = [item["stage"] for item in timings]
        self.assertIn("graph_hit_vector_embedding", stages)
        self.assertIn("graph_entity_vector_index_search", stages)
        self.assertIn("graph_relation_vector_index_search", stages)
        self.assertIn("graph_entity_vector_merge", stages)

    async def test_diversified_query_timing_is_backward_compatible(self):
        storage = _FakeVectorStorage(
            {
                "含糖饮料": [{"entity_name": "含糖饮料", "distance": 0.84}],
            }
        )
        timings = []

        results = await _query_vector_storage_diversified(
            "含糖饮料",
            storage,
            top_k=1,
            timing_collector=timings,
            stage_prefix="unit_vector",
        )

        self.assertEqual([item["entity_name"] for item in results], ["含糖饮料"])
        self.assertEqual(timings, [])


if __name__ == "__main__":
    unittest.main()
