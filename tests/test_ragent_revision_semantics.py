import asyncio
import importlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from ragent.base import DeletionResult, DocStatus, QueryParam
from ragent.kg.shared_storage import initialize_share_data
from ragent.utils import compute_mdhash_id


def _install_mineru_test_stubs() -> None:
    if "mineru" in sys.modules:
        return

    module_defs: dict[str, dict[str, object]] = {
        "mineru": {},
        "mineru.cli": {},
        "mineru.cli.common": {
            "convert_pdf_bytes_to_bytes": lambda *args, **kwargs: b"",
            "prepare_env": lambda *args, **kwargs: None,
            "read_fn": lambda *args, **kwargs: b"",
        },
        "mineru.utils": {},
        "mineru.utils.config_reader": {
            "get_local_models_dir": lambda: {},
        },
        "mineru.data": {},
        "mineru.data.data_reader_writer": {
            "FileBasedDataWriter": type("FileBasedDataWriter", (), {}),
        },
        "mineru.utils.draw_bbox": {
            "draw_layout_bbox": lambda *args, **kwargs: None,
            "draw_span_bbox": lambda *args, **kwargs: None,
        },
        "mineru.utils.enum_class": {
            "MakeMode": type(
                "MakeMode",
                (),
                {
                    "MM_MD": "MM_MD",
                    "CONTENT_LIST": "CONTENT_LIST",
                },
            ),
        },
        "mineru.backend": {},
        "mineru.backend.vlm": {},
        "mineru.backend.vlm.vlm_analyze": {
            "doc_analyze": lambda *args, **kwargs: None,
        },
        "mineru.backend.vlm.vlm_middle_json_mkcontent": {
            "union_make": lambda *args, **kwargs: None,
        },
        "mineru.backend.pipeline": {},
        "mineru.backend.pipeline.pipeline_analyze": {
            "doc_analyze": lambda *args, **kwargs: None,
            "doc_analyze_streaming": lambda *args, **kwargs: None,
        },
        "mineru.backend.pipeline.pipeline_middle_json_mkcontent": {
            "union_make": lambda *args, **kwargs: None,
        },
        "mineru.backend.pipeline.model_json_to_middle_json": {
            "result_to_middle_json": lambda *args, **kwargs: None,
        },
    }

    for module_name, attrs in module_defs.items():
        module = sys.modules.get(module_name)
        if module is None:
            module = type(sys)(module_name)
            sys.modules[module_name] = module
        for attr_name, attr_value in attrs.items():
            setattr(module, attr_name, attr_value)


_install_mineru_test_stubs()

ragent_module = importlib.import_module("ragent.ragent")
integrations_module = importlib.import_module("integrations")
Ragent = ragent_module.Ragent


class _FakeMetadataStorage:
    def __init__(self, in_memory: dict | None = None, persisted: dict | None = None):
        self.in_memory = dict(in_memory or {})
        self.persisted = dict(persisted or self.in_memory)
        self.refresh_calls = 0

    async def refresh_from_storage(self) -> bool:
        self.in_memory = dict(self.persisted)
        self.refresh_calls += 1
        return True

    async def get_by_id(self, key: str) -> dict | None:
        if key != "corpus":
            return None
        return dict(self.in_memory)


def _make_storage(**overrides):
    defaults = {
        "upsert": AsyncMock(),
        "get_by_id": AsyncMock(return_value={}),
        "get_by_ids": AsyncMock(return_value=[]),
        "get_docs_by_status": AsyncMock(return_value={}),
        "filter_keys": AsyncMock(return_value=set()),
        "delete": AsyncMock(),
        "index_done_callback": AsyncMock(),
        "upsert_node": AsyncMock(),
        "upsert_edge": AsyncMock(),
        "has_node": AsyncMock(return_value=True),
        "has_edge": AsyncMock(return_value=True),
        "get_node": AsyncMock(return_value={}),
        "get_edge": AsyncMock(return_value={}),
        "get_node_edges": AsyncMock(return_value=[]),
        "delete_node": AsyncMock(),
        "remove_edges": AsyncMock(),
        "delete_entity": AsyncMock(),
        "delete_entity_relation": AsyncMock(),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_ragent(
    metadata_storage: _FakeMetadataStorage | None = None,
) -> Ragent:
    rag = object.__new__(Ragent)
    rag.corpus_revision = 1
    rag.index_digest = None
    rag.index_metadata = metadata_storage or _FakeMetadataStorage(
        in_memory={"corpus_revision": 1, "index_digest": None},
        persisted={"corpus_revision": 1, "index_digest": None},
    )
    rag.chunk_entity_relation_graph = _make_storage()
    rag.entities_vdb = _make_storage()
    rag.relationships_vdb = _make_storage()
    rag.text_chunks = _make_storage()
    rag.chunks_vdb = _make_storage()
    rag.full_docs = _make_storage()
    rag.doc_status = _make_storage()
    rag.llm_response_cache = _make_storage()
    rag.tokenizer = SimpleNamespace(encode=lambda text: list(str(text or "")))
    rag.chunking_func = lambda *args, **kwargs: [{"content": "chunk text", "tokens": 2}]
    rag.chunk_overlap_token_size = 0
    rag.chunk_token_size = 128
    rag.max_parallel_insert = 1
    rag.llm_model_max_async = 1
    rag._query_done = AsyncMock()
    rag._insert_done = AsyncMock()
    rag._try_bump_corpus_revision = AsyncMock()
    rag._rollback_staged_group_data = AsyncMock()
    rag._process_entity_relation_graph = AsyncMock(return_value=[({"node": []}, [])])
    rag._build_vector_chunks = AsyncMock(side_effect=lambda chunks: (chunks, {}))
    return rag


class RagentRevisionSemanticsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        initialize_share_data()
        self.asdict_patch = patch.object(
            ragent_module,
            "asdict",
            side_effect=lambda rag: {
                "corpus_revision": getattr(rag, "corpus_revision", 0),
                "index_digest": getattr(rag, "index_digest", None),
            },
        )
        self.asdict_patch.start()

    def tearDown(self):
        self.asdict_patch.stop()

    async def test_aquery_refreshes_revision_before_graph_query(self):
        metadata = _FakeMetadataStorage(
            in_memory={"corpus_revision": 1, "index_digest": None},
            persisted={"corpus_revision": 2, "index_digest": "rev-2"},
        )
        rag = _make_ragent(metadata)

        graph_query = AsyncMock(return_value=("answer", ["/tmp/source.pdf"]))
        with patch.object(ragent_module, "graph_query", graph_query):
            answer, refs = await rag.aquery("q", QueryParam(mode="graph"))

        self.assertEqual(answer, "answer")
        self.assertEqual(refs, ["/tmp/source.pdf"])
        self.assertEqual(metadata.refresh_calls, 1)
        self.assertEqual(rag.corpus_revision, 2)
        self.assertEqual(rag.index_digest, "rev-2")
        self.assertEqual(graph_query.await_args.args[6]["corpus_revision"], 2)
        self.assertEqual(graph_query.await_args.args[6]["index_digest"], "rev-2")
        rag._query_done.assert_awaited_once()

    async def test_aquery_with_separate_keyword_extraction_refreshes_revision(self):
        metadata = _FakeMetadataStorage(
            in_memory={"corpus_revision": 3, "index_digest": None},
            persisted={"corpus_revision": 4, "index_digest": "rev-4"},
        )
        rag = _make_ragent(metadata)

        query_with_keywords = AsyncMock(return_value="answer")
        with patch.object(ragent_module, "query_with_keywords", query_with_keywords):
            answer = await rag.aquery_with_separate_keyword_extraction(
                "q",
                "prompt",
                QueryParam(mode="hybrid"),
            )

        self.assertEqual(answer, "answer")
        self.assertEqual(metadata.refresh_calls, 1)
        self.assertEqual(rag.corpus_revision, 4)
        self.assertEqual(
            query_with_keywords.await_args.kwargs["global_config"]["corpus_revision"],
            4,
        )
        self.assertEqual(
            query_with_keywords.await_args.kwargs["global_config"]["index_digest"],
            "rev-4",
        )
        rag._query_done.assert_awaited_once()

    async def test_one_hop_query_refreshes_revision_before_hybrid_query(self):
        metadata = _FakeMetadataStorage(
            in_memory={"corpus_revision": 5, "index_digest": None},
            persisted={"corpus_revision": 6, "index_digest": "rev-6"},
        )
        rag = _make_ragent(metadata)

        hybrid_query = AsyncMock(return_value=("answer", ["/tmp/source.pdf"]))
        with patch.object(integrations_module, "hybrid_query", hybrid_query):
            result = await integrations_module._run_one_hop_with_rag(
                rag,
                "q",
                "hybrid",
            )

        self.assertEqual(result["answer"], "answer")
        self.assertEqual(result["referenced_file_paths"], ["/tmp/source.pdf"])
        self.assertEqual(metadata.refresh_calls, 1)
        self.assertEqual(hybrid_query.await_args.args[7]["corpus_revision"], 6)
        self.assertEqual(hybrid_query.await_args.args[7]["index_digest"], "rev-6")
        rag._query_done.assert_awaited_once()

    async def test_ainsert_delegates_to_enqueue_and_process(self):
        rag = _make_ragent()
        rag.apipeline_enqueue_documents = AsyncMock()
        rag.apipeline_process_enqueue_documents = AsyncMock()

        await rag.ainsert("content", doc_name="doc.txt")

        rag.apipeline_enqueue_documents.assert_awaited_once()
        rag.apipeline_process_enqueue_documents.assert_awaited_once()

    async def test_apipeline_process_enqueue_documents_bumps_revision_on_success(self):
        rag = _make_ragent()
        status_doc = SimpleNamespace(
            content="doc.txt#######body",
            content_summary="summary",
            content_length=4,
            created_at="2024-01-01T00:00:00+00:00",
            file_path="/tmp/doc.txt",
            metadata={},
            chunks_count=0,
            chunks_list=[],
        )
        rag.doc_status.get_docs_by_status = AsyncMock(
            side_effect=[{}, {}, {"doc-1": status_doc}]
        )

        pipeline_status = {"history_messages": []}
        merge_nodes = AsyncMock(return_value=None)
        with patch.object(ragent_module, "get_namespace_data", AsyncMock(return_value=pipeline_status)), patch.object(
            ragent_module, "get_pipeline_status_lock", return_value=asyncio.Lock()
        ), patch.object(ragent_module, "merge_nodes_and_edges", merge_nodes):
            await rag.apipeline_process_enqueue_documents(doc_name="doc.txt")

        expected_chunk_id = compute_mdhash_id("chunk text", prefix="chunk-")
        rag._try_bump_corpus_revision.assert_awaited_once_with(
            "insert",
            affected_chunk_ids=[expected_chunk_id],
        )
        rag._insert_done.assert_awaited_once()
        self.assertFalse(pipeline_status["busy"])

    async def test_apipeline_process_enqueue_documents_skips_bump_when_no_docs(self):
        rag = _make_ragent()
        rag.doc_status.get_docs_by_status = AsyncMock(side_effect=[{}, {}, {}])

        pipeline_status = {"history_messages": []}
        with patch.object(ragent_module, "get_namespace_data", AsyncMock(return_value=pipeline_status)), patch.object(
            ragent_module, "get_pipeline_status_lock", return_value=asyncio.Lock()
        ):
            await rag.apipeline_process_enqueue_documents()

        rag._try_bump_corpus_revision.assert_not_awaited()
        rag._insert_done.assert_not_awaited()

    async def test_apipeline_process_enqueue_documents_does_not_bump_on_merge_failure(self):
        rag = _make_ragent()
        status_doc = SimpleNamespace(
            content="doc.txt#######body",
            content_summary="summary",
            content_length=4,
            created_at="2024-01-01T00:00:00+00:00",
            file_path="/tmp/doc.txt",
            metadata={},
            chunks_count=0,
            chunks_list=[],
        )
        rag.doc_status.get_docs_by_status = AsyncMock(
            side_effect=[{}, {}, {"doc-1": status_doc}]
        )

        pipeline_status = {"history_messages": []}
        with patch.object(ragent_module, "get_namespace_data", AsyncMock(return_value=pipeline_status)), patch.object(
            ragent_module, "get_pipeline_status_lock", return_value=asyncio.Lock()
        ), patch.object(
            ragent_module,
            "merge_nodes_and_edges",
            AsyncMock(side_effect=RuntimeError("merge failed")),
        ):
            with self.assertRaisesRegex(RuntimeError, "merge failed"):
                await rag.apipeline_process_enqueue_documents(doc_name="doc.txt")

        rag._try_bump_corpus_revision.assert_not_awaited()
        rag.llm_response_cache.index_done_callback.assert_awaited()

    async def test_ingest_prebuilt_chunk_graph_bumps_revision_on_success(self):
        rag = _make_ragent()
        chunks = {
            "chunk-1": {
                "content": "chunk text",
                "full_doc_id": "doc-1",
                "file_path": "/tmp/doc.txt",
            }
        }

        with patch.object(ragent_module, "get_namespace_data", AsyncMock(return_value={"history_messages": []})), patch.object(
            ragent_module, "get_pipeline_status_lock", return_value=asyncio.Lock()
        ), patch.object(ragent_module, "merge_nodes_and_edges", AsyncMock(return_value=None)):
            await rag._ingest_prebuilt_chunk_graph(
                doc_id="doc-1",
                doc_content="body",
                file_path="/tmp/doc.txt",
                chunks=chunks,
                chunk_results=[],
            )

        rag._insert_done.assert_awaited_once()
        rag._try_bump_corpus_revision.assert_awaited_once_with(
            "structured_import",
            affected_chunk_ids=["chunk-1"],
        )

    async def test_ingest_prebuilt_chunk_graph_does_not_bump_on_failure(self):
        rag = _make_ragent()
        chunks = {
            "chunk-1": {
                "content": "chunk text",
                "full_doc_id": "doc-1",
                "file_path": "/tmp/doc.txt",
            }
        }

        with patch.object(ragent_module, "get_namespace_data", AsyncMock(return_value={"history_messages": []})), patch.object(
            ragent_module, "get_pipeline_status_lock", return_value=asyncio.Lock()
        ), patch.object(
            ragent_module,
            "merge_nodes_and_edges",
            AsyncMock(side_effect=RuntimeError("boom")),
        ):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                await rag._ingest_prebuilt_chunk_graph(
                    doc_id="doc-1",
                    doc_content="body",
                    file_path="/tmp/doc.txt",
                    chunks=chunks,
                    chunk_results=[],
                )

        rag._try_bump_corpus_revision.assert_not_awaited()
        rag.llm_response_cache.index_done_callback.assert_awaited_once()

    async def test_ainsert_wide_table_processed_document_is_noop(self):
        rag = _make_ragent()
        rag.doc_status.get_by_ids = AsyncMock(
            return_value=[{"status": DocStatus.PROCESSED}]
        )
        rag._ingest_prebuilt_chunk_graph = AsyncMock()

        prepared_import = SimpleNamespace(
            doc_content="table content",
            file_path="/tmp/table.csv",
        )
        with patch.object(
            ragent_module,
            "prepare_wide_table_import",
            return_value=prepared_import,
        ):
            await rag.ainsert_wide_table(
                source="ignored",
                config=object(),
                doc_id="doc-table",
                doc_name="table.csv",
            )

        rag._ingest_prebuilt_chunk_graph.assert_not_called()
        rag._try_bump_corpus_revision.assert_not_awaited()

    async def test_ainsert_custom_kg_bumps_revision_when_data_is_inserted(self):
        rag = _make_ragent()

        custom_kg = {
            "chunks": [
                {
                    "content": "chunk body",
                    "source_id": "source-1",
                    "file_path": "/tmp/source.pdf",
                }
            ],
            "entities": [],
            "relationships": [],
        }

        await rag.ainsert_custom_kg(custom_kg, full_doc_id="doc-1")

        expected_chunk_id = compute_mdhash_id("chunk body", prefix="chunk-")
        rag._insert_done.assert_awaited_once()
        rag._try_bump_corpus_revision.assert_awaited_once_with(
            "custom_kg",
            affected_chunk_ids=[expected_chunk_id],
        )

    async def test_ainsert_custom_kg_empty_payload_does_not_bump_revision(self):
        rag = _make_ragent()

        await rag.ainsert_custom_kg(
            {"chunks": [], "entities": [], "relationships": []},
            full_doc_id="doc-1",
        )

        rag._insert_done.assert_not_awaited()
        rag._try_bump_corpus_revision.assert_not_awaited()

    async def test_aedit_entity_noop_does_not_bump_revision(self):
        rag = _make_ragent()
        rag.chunk_entity_relation_graph.get_node = AsyncMock(
            return_value={
                "entity_id": "Entity",
                "description": "same",
                "entity_type": "TYPE",
                "source_id": "chunk-1",
            }
        )

        result = await rag.aedit_entity("Entity", {"description": "same"})

        self.assertFalse(result["mutation_applied"])
        rag.chunk_entity_relation_graph.upsert_node.assert_not_awaited()
        rag.entities_vdb.upsert.assert_not_awaited()
        rag._try_bump_corpus_revision.assert_not_awaited()

    async def test_aedit_relation_noop_does_not_bump_revision(self):
        rag = _make_ragent()
        rag.chunk_entity_relation_graph.get_edge = AsyncMock(
            return_value={
                "description": "same",
                "keywords": "k",
                "source_id": "chunk-1",
                "weight": 1.0,
            }
        )

        result = await rag.aedit_relation("A", "B", {"description": "same"})

        self.assertFalse(result["mutation_applied"])
        rag.chunk_entity_relation_graph.upsert_edge.assert_not_awaited()
        rag.relationships_vdb.delete.assert_not_awaited()
        rag.relationships_vdb.upsert.assert_not_awaited()
        rag._try_bump_corpus_revision.assert_not_awaited()

    async def test_delete_methods_bump_revision_on_success(self):
        cases = [
            (
                "adelete_by_entity",
                "ragent.utils_graph.adelete_by_entity",
                ("Entity",),
                "delete_entity",
                {
                    "get_node": AsyncMock(
                        return_value={"source_chunk_ids": ["chunk-entity"]}
                    ),
                    "get_node_edges": AsyncMock(return_value=[("Entity", "Other")]),
                    "get_edge": AsyncMock(
                        return_value={"source_chunk_ids": ["chunk-relation"]}
                    ),
                },
                ["chunk-entity", "chunk-relation"],
                DeletionResult(
                    status="success",
                    doc_id="Entity",
                    message="deleted",
                ),
            ),
            (
                "adelete_by_relation",
                "ragent.utils_graph.adelete_by_relation",
                ("A", "B"),
                "delete_relation",
                {
                    "get_edge": AsyncMock(
                        return_value={"source_chunk_ids": ["chunk-relation"]}
                    ),
                },
                ["chunk-relation"],
                DeletionResult(
                    status="success",
                    doc_id="A -> B",
                    message="deleted",
                ),
            ),
        ]

        for method_name, patch_target, args, reason, graph_overrides, chunk_ids, result in cases:
            with self.subTest(method=method_name):
                rag = _make_ragent()
                for attr_name, override in graph_overrides.items():
                    setattr(rag.chunk_entity_relation_graph, attr_name, override)

                with patch(patch_target, new=AsyncMock(return_value=result)):
                    returned = await getattr(rag, method_name)(*args)

                self.assertEqual(returned, result)
                rag._try_bump_corpus_revision.assert_awaited_once_with(
                    reason,
                    affected_chunk_ids=chunk_ids,
                )

    async def test_delete_methods_do_not_bump_revision_when_not_found(self):
        cases = [
            (
                "adelete_by_entity",
                "ragent.utils_graph.adelete_by_entity",
                ("Entity",),
                DeletionResult(
                    status="not_found",
                    doc_id="Entity",
                    message="missing",
                    status_code=404,
                ),
            ),
            (
                "adelete_by_relation",
                "ragent.utils_graph.adelete_by_relation",
                ("A", "B"),
                DeletionResult(
                    status="not_found",
                    doc_id="A -> B",
                    message="missing",
                    status_code=404,
                ),
            ),
        ]

        for method_name, patch_target, args, result in cases:
            with self.subTest(method=method_name):
                rag = _make_ragent()
                rag.chunk_entity_relation_graph.get_node = AsyncMock(return_value=None)
                rag.chunk_entity_relation_graph.get_node_edges = AsyncMock(
                    return_value=[]
                )
                rag.chunk_entity_relation_graph.get_edge = AsyncMock(return_value=None)

                with patch(patch_target, new=AsyncMock(return_value=result)):
                    returned = await getattr(rag, method_name)(*args)

                self.assertEqual(returned, result)
                rag._try_bump_corpus_revision.assert_not_awaited()

    async def test_graph_mutation_methods_bump_revision_on_success(self):
        cases = [
            (
                "aedit_entity",
                "ragent.utils_graph.aedit_entity",
                ("Entity", {"description": "new"}, True),
                "edit_entity",
            ),
            (
                "aedit_relation",
                "ragent.utils_graph.aedit_relation",
                ("A", "B", {"description": "new"}),
                "edit_relation",
            ),
            (
                "acreate_entity",
                "ragent.utils_graph.acreate_entity",
                ("Entity", {"description": "new"}),
                "create_entity",
            ),
            (
                "acreate_relation",
                "ragent.utils_graph.acreate_relation",
                ("A", "B", {"description": "new"}),
                "create_relation",
            ),
            (
                "amerge_entities",
                "ragent.utils_graph.amerge_entities",
                (["A", "B"], "Merged", None, None),
                "merge_entities",
            ),
        ]

        for method_name, patch_target, args, reason in cases:
            with self.subTest(method=method_name):
                rag = _make_ragent()
                result = {"source_chunk_ids": ["chunk-1"]}

                with patch(patch_target, new=AsyncMock(return_value=result)):
                    returned = await getattr(rag, method_name)(*args)

                self.assertEqual(returned, result)
                rag._try_bump_corpus_revision.assert_awaited_once_with(
                    reason,
                    affected_chunk_ids=["chunk-1"],
                )

    async def test_graph_mutation_methods_do_not_bump_revision_on_failure(self):
        cases = [
            ("aedit_entity", "ragent.utils_graph.aedit_entity", ("Entity", {"description": "new"}, True)),
            ("aedit_relation", "ragent.utils_graph.aedit_relation", ("A", "B", {"description": "new"})),
            ("acreate_entity", "ragent.utils_graph.acreate_entity", ("Entity", {"description": "new"})),
            ("acreate_relation", "ragent.utils_graph.acreate_relation", ("A", "B", {"description": "new"})),
            ("amerge_entities", "ragent.utils_graph.amerge_entities", (["A", "B"], "Merged", None, None)),
        ]

        for method_name, patch_target, args in cases:
            with self.subTest(method=method_name):
                rag = _make_ragent()
                with patch(
                    patch_target,
                    new=AsyncMock(side_effect=RuntimeError("boom")),
                ):
                    with self.assertRaisesRegex(RuntimeError, "boom"):
                        await getattr(rag, method_name)(*args)

                rag._try_bump_corpus_revision.assert_not_awaited()
