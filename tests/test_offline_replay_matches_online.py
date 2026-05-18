from __future__ import annotations

import asyncio
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import ragent.offline_replay as offline_replay_module
from ragent.base import DocStatus
from ragent.constants import GRAPH_FIELD_SEP
from ragent.kg.shared_storage import finalize_share_data, initialize_share_data
from ragent.offline_replay import (
    RawMergeUnit,
    build_raw_merge_unit_from_text,
    iter_raw_merge_unit_groups_jsonl,
    iter_raw_merge_units_jsonl,
    replay_raw_merge_units,
    replay_raw_merge_units_jsonl,
    scan_raw_merge_units_jsonl,
    write_raw_merge_units_jsonl,
)
from ragent.operate import merge_nodes_and_edges
from ragent.utils import compute_mdhash_id, get_content_summary


class _FakeTokenizer:
    def encode(self, text: str) -> list[str]:
        return list(text)

    def decode(self, tokens: list[str]) -> str:
        return "".join(tokens)


class _FakeLLM:
    def __init__(self):
        self.calls: list[str] = []

    async def __call__(self, prompt: str, **_kwargs: Any) -> str:
        self.calls.append(prompt)
        return "summary:" + hashlib.md5(prompt.encode("utf-8")).hexdigest()


class _FakeEmbedding:
    embedding_dim = 4
    max_token_size = 8192

    async def __call__(self, texts: list[str], **_kwargs: Any) -> np.ndarray:
        rows = []
        for text in texts:
            digest = hashlib.md5(text.encode("utf-8")).digest()
            rows.append([digest[index] / 255.0 for index in range(4)])
        return np.asarray(rows, dtype=np.float32)


class _MemoryKVStorage:
    def __init__(self):
        self.data: dict[str, dict[str, Any]] = {}

    async def get_by_id(self, item_id: str) -> dict[str, Any] | None:
        return self.data.get(item_id)

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any] | None]:
        return [self.data.get(item_id) for item_id in ids]

    async def filter_keys(self, keys: set[str]) -> set[str]:
        return set(keys) - set(self.data)

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        self.data.update(deepcopy(data))

    async def delete(self, ids: list[str]) -> None:
        for item_id in ids:
            self.data.pop(item_id, None)

    async def index_done_callback(self) -> None:
        return None


class _MemoryVectorStorage:
    def __init__(self, embedding_func: _FakeEmbedding):
        self.embedding_func = embedding_func
        self.data: dict[str, dict[str, Any]] = {}
        self.vectors: dict[str, list[float]] = {}

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        pending_ids: list[str] = []
        pending_content: list[str] = []
        for item_id, record in data.items():
            record_copy = deepcopy(record)
            embedding = self._coerce_embedding(record_copy.get("embeddings"))
            if embedding is None:
                pending_ids.append(item_id)
                pending_content.append(record_copy["content"])
            else:
                record_copy["embeddings"] = embedding
                self.vectors[item_id] = embedding
            self.data[item_id] = record_copy

        if pending_content:
            embeddings = await self.embedding_func(pending_content)
            for item_id, embedding in zip(pending_ids, embeddings):
                self.vectors[item_id] = [float(value) for value in embedding]

    def _coerce_embedding(self, value: Any) -> list[float] | None:
        if hasattr(value, "tolist"):
            value = value.tolist()
        if value in (None, "", [], "[]", "None"):
            return None
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return None
        if not isinstance(value, list) or not value:
            return None
        return [float(item) for item in value]

    async def query(self, _query: str, _top_k: int, ids: list[str] | None = None):
        selected_ids = ids or list(self.data)
        return [self.data[item_id] for item_id in selected_ids if item_id in self.data]

    async def delete_entity(self, entity_name: str) -> None:
        await self.delete([compute_mdhash_id(entity_name, prefix="ent-")])

    async def delete_entity_relation(self, entity_name: str) -> None:
        ids = [
            item_id
            for item_id, record in self.data.items()
            if record.get("src_id") == entity_name or record.get("tgt_id") == entity_name
        ]
        await self.delete(ids)

    async def get_by_id(self, item_id: str) -> dict[str, Any] | None:
        if item_id not in self.data:
            return None
        return {**self.data[item_id], "__vector__": self.vectors[item_id]}

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        return [
            {**self.data[item_id], "__vector__": self.vectors[item_id]}
            for item_id in ids
            if item_id in self.data
        ]

    async def delete(self, ids: list[str]) -> None:
        for item_id in ids:
            self.data.pop(item_id, None)
            self.vectors.pop(item_id, None)

    async def index_done_callback(self) -> None:
        return None


class _MemoryGraphStorage:
    def __init__(self):
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[tuple[str, str], dict[str, Any]] = {}

    def _edge_key(self, src_id: str, tgt_id: str) -> tuple[str, str]:
        return tuple(sorted((src_id, tgt_id)))

    async def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes

    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        return self._edge_key(source_node_id, target_node_id) in self.edges

    async def get_node(self, node_id: str) -> dict[str, Any] | None:
        return self.nodes.get(node_id)

    async def get_edge(
        self, source_node_id: str, target_node_id: str
    ) -> dict[str, Any] | None:
        return self.edges.get(self._edge_key(source_node_id, target_node_id))

    async def upsert_node(self, node_id: str, node_data: dict[str, Any]) -> None:
        self.nodes[node_id] = deepcopy(node_data)

    async def upsert_edge(
        self, source_node_id: str, target_node_id: str, edge_data: dict[str, Any]
    ) -> None:
        self.edges[self._edge_key(source_node_id, target_node_id)] = deepcopy(edge_data)

    async def remove_nodes(self, nodes: list[str]) -> None:
        for node_id in nodes:
            self.nodes.pop(node_id, None)
        self.edges = {
            edge_key: edge
            for edge_key, edge in self.edges.items()
            if edge_key[0] not in nodes and edge_key[1] not in nodes
        }

    async def remove_edges(self, edges: list[tuple[str, str]]) -> None:
        for src_id, tgt_id in edges:
            self.edges.pop(self._edge_key(src_id, tgt_id), None)


class _ReplayEnv:
    def __init__(self):
        self.embedding = _FakeEmbedding()
        self.llm = _FakeLLM()
        self.full_docs = _MemoryKVStorage()
        self.text_chunks = _MemoryKVStorage()
        self.doc_status = _MemoryKVStorage()
        self.chunks_vdb = _MemoryVectorStorage(self.embedding)
        self.entities_vdb = _MemoryVectorStorage(self.embedding)
        self.relationships_vdb = _MemoryVectorStorage(self.embedding)
        self.graph = _MemoryGraphStorage()
        self.pipeline_status = {"latest_message": "", "history_messages": []}
        self.pipeline_status_lock = asyncio.Lock()

    def global_config(self) -> dict[str, Any]:
        return {
            "force_llm_summary_on_merge": 3,
            "llm_model_func": self.llm,
            "llm_model_max_async": 1,
            "llm_model_max_token_size": 8192,
            "tokenizer": _FakeTokenizer(),
            "addon_params": {"language": "English"},
            "workspace": "",
        }


class _FakeRawBuilderRag:
    def __init__(self):
        self.tokenizer = _FakeTokenizer()
        self.chunk_overlap_token_size = 0
        self.chunk_token_size = 80
        self.text_chunks = _MemoryKVStorage()
        self.embedding = _FakeEmbedding()

    def chunking_func(
        self,
        doc_name: str,
        tokenizer: _FakeTokenizer,
        content: str,
        doc_metadata: dict[str, Any] | None = None,
        **_kwargs: Any,
    ) -> list[dict[str, Any]]:
        chunks = []
        for index, part in enumerate(content.split("\n\n")):
            text = part.strip()
            if not text:
                continue
            chunks.append(
                {
                    "tokens": len(tokenizer.encode(text)),
                    "content": text,
                    "chunk_order_index": index,
                    "section_path": doc_metadata.get("section_path", "")
                    if doc_metadata
                    else "",
                }
            )
        return chunks

    async def _build_vector_chunks(
        self,
        chunks: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        chunk_ids = list(chunks)
        embeddings = await self.embedding(
            [chunks[chunk_id]["content"] for chunk_id in chunk_ids]
        )
        chunk_embeddings = {
            chunk_id: embeddings[index] for index, chunk_id in enumerate(chunk_ids)
        }
        return (
            {
                chunk_id: {
                    **chunks[chunk_id],
                    "embeddings": chunk_embeddings[chunk_id],
                }
                for chunk_id in chunk_ids
            },
            chunk_embeddings,
        )

    async def _process_entity_relation_graph(
        self,
        chunks: dict[str, dict[str, Any]],
        _pipeline_status=None,
        _pipeline_status_lock=None,
    ) -> list:
        chunk_results = []
        for chunk_id, chunk in chunks.items():
            file_path = chunk["file_path"]
            chunk_results.append(
                (
                    {
                        "ALPHA": [
                            _entity(
                                "ALPHA",
                                "sample",
                                f"alpha from {chunk_id}",
                                chunk_id,
                                file_path,
                            )
                        ],
                        "BETA": [
                            _entity(
                                "BETA",
                                "sample",
                                f"beta from {chunk_id}",
                                chunk_id,
                                file_path,
                            )
                        ],
                    },
                    {
                        ("ALPHA", "BETA"): [
                            _relationship(
                                "ALPHA",
                                "BETA",
                                f"alpha beta from {chunk_id}",
                                "sample",
                                1.0,
                                chunk_id,
                                file_path,
                            )
                        ]
                    },
                )
            )
        return chunk_results


def _entity(
    name: str,
    entity_type: str,
    description: str,
    chunk_id: str,
    file_path: str,
) -> dict[str, Any]:
    return {
        "entity_name": name,
        "entity_type": entity_type,
        "description": description,
        "source_id": chunk_id,
        "source_chunk_ids": chunk_id,
        "file_path": file_path,
    }


def _relationship(
    src_id: str,
    tgt_id: str,
    description: str,
    keywords: str,
    weight: float,
    chunk_id: str,
    file_path: str,
) -> dict[str, Any]:
    return {
        "src_id": src_id,
        "tgt_id": tgt_id,
        "description": description,
        "keywords": keywords,
        "weight": weight,
        "source_id": chunk_id,
        "source_chunk_ids": chunk_id,
        "file_path": file_path,
    }


def _unit(
    doc_id: str,
    chunk_id: str,
    *,
    alpha_type: str,
    alpha_description: str,
    relation_description: str,
    relation_keywords: str,
    relation_weight: float,
) -> RawMergeUnit:
    file_path = f"/docs/{doc_id}.md"
    content = f"{doc_id} content"
    chunk = {
        "tokens": 3,
        "content": content,
        "full_doc_id": doc_id,
        "chunk_order_index": 0,
        "file_path": file_path,
        "llm_cache_list": [],
    }
    return RawMergeUnit(
        doc_id=doc_id,
        doc_name=doc_id,
        file_path=file_path,
        source_group_key="combined-source",
        content=content,
        content_summary=get_content_summary(content),
        metadata={"file_path": file_path},
        chunks={chunk_id: chunk},
        vector_chunks={
            chunk_id: {
                **chunk,
                "embeddings": np.asarray([0.9, 0.8, 0.7, 0.6], dtype=np.float32),
            }
        },
        chunk_results=[
            (
                {
                    "ALPHA": [
                        _entity(
                            "ALPHA",
                            alpha_type,
                            alpha_description,
                            chunk_id,
                            file_path,
                        )
                    ],
                    "BETA": [
                        _entity("BETA", "concept", "beta desc", chunk_id, file_path)
                    ],
                },
                {
                    ("ALPHA", "BETA"): [
                        _relationship(
                            "ALPHA",
                            "BETA",
                            relation_description,
                            relation_keywords,
                            relation_weight,
                            chunk_id,
                            file_path,
                        )
                    ]
                },
            )
        ],
    )


def _sample_units() -> list[RawMergeUnit]:
    unit_a = _unit(
        "doc-a",
        "chunk-a",
        alpha_type="standard",
        alpha_description="alpha desc 1",
        relation_description="rel desc 1",
        relation_keywords="shared,k1",
        relation_weight=1.0,
    )
    unit_b = _unit(
        "doc-b",
        "chunk-b",
        alpha_type="standard",
        alpha_description="alpha desc 2",
        relation_description="rel desc 2",
        relation_keywords="k2",
        relation_weight=2.0,
    )
    unit_c = _unit(
        "doc-c",
        "chunk-c",
        alpha_type="other",
        alpha_description="alpha desc 3",
        relation_description="rel desc 3",
        relation_keywords="shared,k3",
        relation_weight=3.0,
    )
    duplicate_doc = deepcopy(unit_c)
    return [unit_a, unit_b, unit_c, duplicate_doc]


async def _run_online_reference(units: list[RawMergeUnit]) -> _ReplayEnv:
    env = _ReplayEnv()
    seen_doc_ids: set[str] = set()
    replay_units = []
    for unit in units:
        if unit.doc_id in seen_doc_ids:
            continue
        seen_doc_ids.add(unit.doc_id)
        replay_units.append(unit)

    full_docs = {unit.doc_id: {"content": unit.content} for unit in replay_units}
    chunks = {
        chunk_id: chunk
        for unit in replay_units
        for chunk_id, chunk in unit.chunks.items()
    }
    vector_chunks = {
        chunk_id: chunk
        for unit in replay_units
        for chunk_id, chunk in (unit.vector_chunks or unit.chunks).items()
    }
    doc_status = {
        unit.doc_id: {
            "status": DocStatus.PROCESSED,
            "content": unit.content,
            "content_summary": unit.content_summary,
            "content_length": len(unit.content),
            "created_at": "reference",
            "updated_at": "reference",
            "file_path": unit.file_path,
            "metadata": unit.metadata,
            "chunks_count": len(unit.chunks),
            "chunks_list": list(unit.chunks),
        }
        for unit in replay_units
    }
    await asyncio.gather(
        env.full_docs.upsert(full_docs),
        env.text_chunks.upsert(chunks),
        env.chunks_vdb.upsert(vector_chunks),
        env.doc_status.upsert(doc_status),
    )
    await merge_nodes_and_edges(
        chunk_results=[
            chunk_result
            for unit in replay_units
            for chunk_result in unit.chunk_results
        ],
        knowledge_graph_inst=env.graph,
        entity_vdb=env.entities_vdb,
        relationships_vdb=env.relationships_vdb,
        global_config=env.global_config(),
        pipeline_status=env.pipeline_status,
        pipeline_status_lock=env.pipeline_status_lock,
        llm_response_cache=None,
        current_file_number=1,
        total_files=1,
        file_path="combined-source",
    )
    return env


def _stable_graph_snapshot(graph: _MemoryGraphStorage) -> dict[str, Any]:
    def strip_created_at(payload: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in payload.items() if key != "created_at"}

    return {
        "nodes": {
            node_id: strip_created_at(node)
            for node_id, node in sorted(graph.nodes.items())
        },
        "edges": {
            f"{src_id}->{tgt_id}": strip_created_at(edge)
            for (src_id, tgt_id), edge in sorted(graph.edges.items())
        },
    }


def _assert_vectors_match(left: _MemoryVectorStorage, right: _MemoryVectorStorage):
    assert left.data == right.data
    assert set(left.vectors) == set(right.vectors)
    for item_id in left.vectors:
        np.testing.assert_allclose(left.vectors[item_id], right.vectors[item_id])


def test_offline_replay_matches_online_reference_with_jsonl_artifacts(tmp_path: Path):
    async def run() -> None:
        initialize_share_data()
        try:
            units = _sample_units()
            artifact_path = tmp_path / "raw_units.jsonl"
            assert write_raw_merge_units_jsonl(units, artifact_path) == 4
            decoded_units = list(iter_raw_merge_units_jsonl(artifact_path))

            reference = await _run_online_reference(units)
            replay = _ReplayEnv()
            stats = await replay_raw_merge_units(
                decoded_units,
                full_docs=replay.full_docs,
                text_chunks=replay.text_chunks,
                chunks_vdb=replay.chunks_vdb,
                doc_status=replay.doc_status,
                knowledge_graph_inst=replay.graph,
                entity_vdb=replay.entities_vdb,
                relationships_vdb=replay.relationships_vdb,
                global_config=replay.global_config(),
                pipeline_status=replay.pipeline_status,
                pipeline_status_lock=replay.pipeline_status_lock,
                llm_response_cache=None,
            )

            assert stats.units_seen == 4
            assert stats.units_replayed == 3
            assert stats.duplicate_docs_skipped == 1
            assert stats.groups_replayed == 1
            assert stats.docs_written == 3
            assert stats.chunks_written == 3
            assert stats.chunk_result_groups == 3

            assert _stable_graph_snapshot(replay.graph) == _stable_graph_snapshot(
                reference.graph
            )
            _assert_vectors_match(replay.entities_vdb, reference.entities_vdb)
            _assert_vectors_match(
                replay.relationships_vdb, reference.relationships_vdb
            )
            _assert_vectors_match(replay.chunks_vdb, reference.chunks_vdb)

            assert replay.full_docs.data == reference.full_docs.data
            assert replay.text_chunks.data == reference.text_chunks.data
            assert set(replay.doc_status.data) == set(reference.doc_status.data)
            assert replay.llm.calls == reference.llm.calls

            alpha = replay.graph.nodes["ALPHA"]
            assert alpha["entity_type"] == "standard"
            assert alpha["source_chunk_ids"] == (
                f"chunk-a{GRAPH_FIELD_SEP}chunk-b{GRAPH_FIELD_SEP}chunk-c"
            )

            edge = replay.graph.edges[("ALPHA", "BETA")]
            assert edge["weight"] == 6.0
            assert edge["keywords"] == "k1,k2,k3,shared"
            assert edge["source_chunk_ids"] == (
                f"chunk-a{GRAPH_FIELD_SEP}chunk-b{GRAPH_FIELD_SEP}chunk-c"
            )

            entity_id = compute_mdhash_id("ALPHA", prefix="ent-")
            entity_record = replay.entities_vdb.data[entity_id]
            assert entity_record["content"] == f"ALPHA\n{alpha['description']}"
            expected_entity_vector = await replay.embedding([entity_record["content"]])
            np.testing.assert_allclose(
                replay.entities_vdb.vectors[entity_id],
                expected_entity_vector[0],
            )

            relation_id = compute_mdhash_id("ALPHABETA", prefix="rel-")
            relation_record = replay.relationships_vdb.data[relation_id]
            assert relation_record["content"] == (
                f"ALPHA\tBETA\n{edge['keywords']}\n{edge['description']}"
            )
            expected_relation_vector = await replay.embedding(
                [relation_record["content"]]
            )
            np.testing.assert_allclose(
                replay.relationships_vdb.vectors[relation_id],
                expected_relation_vector[0],
            )
        finally:
            finalize_share_data()

    asyncio.run(run())


def test_streaming_jsonl_replay_matches_in_memory_replay(tmp_path: Path):
    async def run() -> None:
        initialize_share_data()
        try:
            units = _sample_units()
            artifact_path = tmp_path / "raw_units.jsonl"
            write_raw_merge_units_jsonl(units, artifact_path)

            in_memory = _ReplayEnv()
            in_memory_stats = await replay_raw_merge_units(
                list(iter_raw_merge_units_jsonl(artifact_path)),
                full_docs=in_memory.full_docs,
                text_chunks=in_memory.text_chunks,
                chunks_vdb=in_memory.chunks_vdb,
                doc_status=in_memory.doc_status,
                knowledge_graph_inst=in_memory.graph,
                entity_vdb=in_memory.entities_vdb,
                relationships_vdb=in_memory.relationships_vdb,
                global_config=in_memory.global_config(),
                pipeline_status=in_memory.pipeline_status,
                pipeline_status_lock=in_memory.pipeline_status_lock,
                llm_response_cache=None,
            )

            streaming = _ReplayEnv()
            streaming_stats = await replay_raw_merge_units_jsonl(
                artifact_path,
                full_docs=streaming.full_docs,
                text_chunks=streaming.text_chunks,
                chunks_vdb=streaming.chunks_vdb,
                doc_status=streaming.doc_status,
                knowledge_graph_inst=streaming.graph,
                entity_vdb=streaming.entities_vdb,
                relationships_vdb=streaming.relationships_vdb,
                global_config=streaming.global_config(),
                pipeline_status=streaming.pipeline_status,
                pipeline_status_lock=streaming.pipeline_status_lock,
                llm_response_cache=None,
            )

            assert streaming_stats == in_memory_stats
            assert _stable_graph_snapshot(streaming.graph) == _stable_graph_snapshot(
                in_memory.graph
            )
            _assert_vectors_match(streaming.entities_vdb, in_memory.entities_vdb)
            _assert_vectors_match(
                streaming.relationships_vdb, in_memory.relationships_vdb
            )
            _assert_vectors_match(streaming.chunks_vdb, in_memory.chunks_vdb)
        finally:
            finalize_share_data()

    asyncio.run(run())


def test_jsonl_source_groups_are_streamed_in_input_order(tmp_path: Path):
    units = _sample_units()[:3]
    units[0].source_group_key = "group-a"
    units[1].source_group_key = "group-a"
    units[2].source_group_key = "group-b"
    artifact_path = tmp_path / "raw_units.jsonl"
    write_raw_merge_units_jsonl(units, artifact_path)

    assert scan_raw_merge_units_jsonl(artifact_path) == (3, 2)
    groups = list(iter_raw_merge_unit_groups_jsonl(artifact_path))
    assert [group_key for group_key, _ in groups] == ["group-a", "group-b"]
    assert [[unit.doc_id for unit in group_units] for _, group_units in groups] == [
        ["doc-a", "doc-b"],
        ["doc-c"],
    ]


def test_streaming_jsonl_rejects_non_contiguous_source_groups(tmp_path: Path):
    units = _sample_units()[:3]
    units[0].source_group_key = "group-a"
    units[1].source_group_key = "group-b"
    units[2].source_group_key = "group-a"
    artifact_path = tmp_path / "raw_units.jsonl"
    write_raw_merge_units_jsonl(units, artifact_path)

    with pytest.raises(ValueError, match="not contiguous"):
        scan_raw_merge_units_jsonl(artifact_path)


def test_replay_rolls_back_staged_group_data_on_merge_failure(monkeypatch):
    async def run() -> None:
        env = _ReplayEnv()
        unit = _sample_units()[0]

        async def failing_merge_nodes_and_edges(**kwargs):
            await kwargs["knowledge_graph_inst"].upsert_node(
                "ALPHA",
                {
                    "entity_id": "ALPHA",
                    "entity_type": "corrupt",
                    "description": "partial",
                    "source_id": "chunk-a",
                    "source_chunk_ids": "chunk-a",
                    "file_path": "/partial",
                },
            )
            await kwargs["entity_vdb"].upsert(
                {
                    compute_mdhash_id("ALPHA", prefix="ent-"): {
                        "entity_name": "ALPHA",
                        "entity_type": "corrupt",
                        "content": "partial",
                        "source_id": "chunk-a",
                        "source_chunk_ids": "chunk-a",
                        "file_path": "/partial",
                    }
                }
            )
            raise RuntimeError("forced merge failure")

        monkeypatch.setattr(
            offline_replay_module,
            "merge_nodes_and_edges",
            failing_merge_nodes_and_edges,
        )

        stats = await replay_raw_merge_units(
            [unit],
            full_docs=env.full_docs,
            text_chunks=env.text_chunks,
            chunks_vdb=env.chunks_vdb,
            doc_status=env.doc_status,
            knowledge_graph_inst=env.graph,
            entity_vdb=env.entities_vdb,
            relationships_vdb=env.relationships_vdb,
            global_config=env.global_config(),
            pipeline_status=env.pipeline_status,
            pipeline_status_lock=env.pipeline_status_lock,
            llm_response_cache=None,
            continue_on_group_error=True,
        )

        assert stats.groups_failed == 1
        assert stats.groups_rolled_back == 1
        assert stats.units_failed == 1
        assert stats.groups_replayed == 0
        assert env.full_docs.data == {}
        assert env.text_chunks.data == {}
        assert env.chunks_vdb.data == {}
        assert env.graph.nodes == {}
        assert env.entities_vdb.data == {}
        assert env.doc_status.data[unit.doc_id]["status"] == DocStatus.FAILED
        assert "forced merge failure" in env.doc_status.data[unit.doc_id]["error"]

    asyncio.run(run())


def test_raw_builder_jsonl_streaming_replay_small_markdown_sample(tmp_path: Path):
    async def run() -> None:
        raw_builder = _FakeRawBuilderRag()
        md_text = (
            "# Sample\n"
            "Alpha is connected to Beta in the first paragraph.\n\n"
            "Alpha repeats the Beta relation in the second paragraph."
        )
        unit = await build_raw_merge_unit_from_text(
            raw_builder,
            text=md_text,
            doc_name="sample.md",
            file_path=str(tmp_path / "sample.md"),
            source_group_key="sample",
            metadata={"file_path": str(tmp_path / "sample.md")},
        )
        artifact_path = tmp_path / "sample.raw-units.jsonl"
        write_raw_merge_units_jsonl([unit], artifact_path)

        replay = _ReplayEnv()
        stats = await replay_raw_merge_units_jsonl(
            artifact_path,
            full_docs=replay.full_docs,
            text_chunks=replay.text_chunks,
            chunks_vdb=replay.chunks_vdb,
            doc_status=replay.doc_status,
            knowledge_graph_inst=replay.graph,
            entity_vdb=replay.entities_vdb,
            relationships_vdb=replay.relationships_vdb,
            global_config=replay.global_config(),
            pipeline_status=replay.pipeline_status,
            pipeline_status_lock=replay.pipeline_status_lock,
            llm_response_cache=None,
        )

        assert stats.units_seen == 1
        assert stats.groups_replayed == 1
        assert stats.chunk_result_groups == 2
        assert replay.doc_status.data[unit.doc_id]["status"] == DocStatus.PROCESSED
        assert len(replay.text_chunks.data) == 2
        assert replay.graph.nodes["ALPHA"]["source_chunk_ids"]
        assert replay.graph.edges[("ALPHA", "BETA")]["weight"] == 2.0
        assert replay.entities_vdb.data[
            compute_mdhash_id("ALPHA", prefix="ent-")
        ]["content"].startswith("ALPHA\n")

    asyncio.run(run())
