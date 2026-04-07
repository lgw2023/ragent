import unittest

from ragent.base import QueryParam
from ragent.operate import (
    _build_diversified_retrieval_queries,
    _chunk_file_group_key,
    _coerce_score,
    _is_low_signal_chunk_candidate,
    _is_normative_chunk_candidate,
    _select_hybrid_context_entries,
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


if __name__ == "__main__":
    unittest.main()
