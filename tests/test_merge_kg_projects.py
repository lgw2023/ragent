from __future__ import annotations

import base64
import json
import sqlite3
from pathlib import Path

import networkx as nx
import numpy as np

from ragent.constants import GRAPH_FIELD_SEP
from tools.merge_kg_projects import (
    GRAPH_FILE_NAME,
    _compute_mdhash_id,
    _decode_matrix,
    merge_projects,
)


def _write_graph(path: Path, graph: nx.Graph) -> None:
    nx.write_graphml(graph, path / GRAPH_FILE_NAME)


def _write_vdb(
    path: Path,
    file_name: str,
    data: list[dict],
    rows: list[list[float]],
    *,
    embedding_dim: int = 2,
) -> None:
    matrix = (
        np.asarray(rows, dtype=np.float32)
        if rows
        else np.array([], dtype=np.float32).reshape(0, embedding_dim)
    )
    payload = {
        "embedding_dim": embedding_dim,
        "data": data,
        "matrix": base64.b64encode(matrix.tobytes()).decode(),
    }
    (path / file_name).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def _write_sqlite_kv(path: Path, namespace: str, rows: dict[str, dict]) -> None:
    conn = sqlite3.connect(path / f"kv_store_{namespace}.sqlite")
    conn.execute(
        """
        CREATE TABLE kv_entries (
            key TEXT PRIMARY KEY,
            entry_json TEXT NOT NULL,
            create_time INTEGER NOT NULL DEFAULT 0,
            update_time INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.executemany(
        "INSERT INTO kv_entries (key, entry_json, create_time, update_time) VALUES (?, ?, ?, ?)",
        [
            (
                key,
                json.dumps(value, ensure_ascii=False),
                value.get("create_time", 1),
                value.get("update_time", 1),
            )
            for key, value in rows.items()
        ],
    )
    conn.commit()
    conn.close()


def _read_sqlite_kv(path: Path, namespace: str) -> dict[str, dict]:
    conn = sqlite3.connect(path / f"kv_store_{namespace}.sqlite")
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT key, entry_json FROM kv_entries").fetchall()
    conn.close()
    return {row["key"]: json.loads(row["entry_json"]) for row in rows}


def _read_vdb(path: Path, file_name: str) -> tuple[list[dict], np.ndarray]:
    payload = json.loads((path / file_name).read_text(encoding="utf-8"))
    return payload["data"], _decode_matrix(payload["matrix"], payload["embedding_dim"])


def test_merge_projects_merges_graph_fields_and_avoids_unknown_override(tmp_path: Path):
    source_a = tmp_path / "source_a"
    source_b = tmp_path / "source_b"
    output = tmp_path / "merged"
    source_a.mkdir()
    source_b.mkdir()

    graph_a = nx.Graph()
    graph_a.add_node(
        "A",
        entity_id="A",
        entity_type="UNKNOWN",
        description="desc-a",
        source_id="chunk-a",
        source_chunk_ids="chunk-a",
        file_path="/docs/a.pdf",
        embeddings="[]",
        created_at=20,
    )
    graph_a.add_node(
        "B",
        entity_id="B",
        entity_type="category",
        description="desc-b",
        source_id="chunk-a",
        source_chunk_ids="chunk-a",
        file_path="/docs/a.pdf",
        embeddings="[]",
        created_at=20,
    )
    graph_a.add_edge(
        "A",
        "B",
        weight=1.5,
        description="edge-a",
        keywords="shared,k1",
        source_id="chunk-a",
        source_chunk_ids="chunk-a",
        file_path="/docs/a.pdf",
        created_at=20,
    )
    _write_graph(source_a, graph_a)

    graph_b = nx.Graph()
    graph_b.add_node(
        "A",
        entity_id="A",
        entity_type="organization",
        description="desc-c",
        source_id="chunk-b",
        source_chunk_ids="chunk-b",
        file_path="/docs/b.pdf",
        embeddings="[0.2, 0.8]",
        created_at=10,
    )
    graph_b.add_node(
        "B",
        entity_id="B",
        entity_type="category",
        description="desc-b",
        source_id="chunk-b",
        source_chunk_ids="chunk-b",
        file_path="/docs/b.pdf",
        embeddings="[]",
        created_at=10,
    )
    graph_b.add_edge(
        "B",
        "A",
        weight=2.5,
        description="edge-b",
        keywords=f"k2{GRAPH_FIELD_SEP}shared,k3",
        source_id="chunk-b",
        source_chunk_ids="chunk-b",
        file_path="/docs/b.pdf",
        created_at=10,
    )
    _write_graph(source_b, graph_b)

    _write_vdb(source_a, "vdb_entities.json", [], [])
    _write_vdb(source_b, "vdb_entities.json", [], [])
    _write_vdb(source_a, "vdb_relationships.json", [], [])
    _write_vdb(source_b, "vdb_relationships.json", [], [])
    _write_vdb(source_a, "vdb_chunks.json", [], [])
    _write_vdb(source_b, "vdb_chunks.json", [], [])

    merge_projects([source_a, source_b], output)

    graph = nx.read_graphml(output / GRAPH_FILE_NAME)
    assert graph.nodes["A"]["entity_type"] == "organization"
    assert graph.nodes["A"]["description"] == f"desc-a{GRAPH_FIELD_SEP}desc-c"
    assert graph.nodes["A"]["source_chunk_ids"] == f"chunk-a{GRAPH_FIELD_SEP}chunk-b"
    assert graph.nodes["A"]["file_path"] == f"/docs/a.pdf{GRAPH_FIELD_SEP}/docs/b.pdf"
    assert graph.nodes["A"]["embeddings"] == "[0.2, 0.8]"
    assert graph.nodes["A"]["created_at"] == 10

    edge = graph.edges[("A", "B")]
    assert edge["weight"] == 4.0
    assert edge["description"] == f"edge-a{GRAPH_FIELD_SEP}edge-b"
    assert edge["keywords"] == "k1,k2,k3,shared"
    assert edge["source_chunk_ids"] == f"chunk-a{GRAPH_FIELD_SEP}chunk-b"


def test_merge_projects_preserves_vdb_data_matrix_alignment(tmp_path: Path):
    source_a = tmp_path / "source_a"
    source_b = tmp_path / "source_b"
    output = tmp_path / "merged"
    source_a.mkdir()
    source_b.mkdir()
    _write_graph(source_a, nx.Graph())
    _write_graph(source_b, nx.Graph())

    _write_vdb(
        source_a,
        "vdb_chunks.json",
        [
            {"__id__": "chunk-1", "__created_at__": 1, "content": "one"},
            {"__id__": "chunk-2", "__created_at__": 1, "content": "two"},
        ],
        [[1.0, 0.0], [0.0, 1.0]],
    )
    _write_vdb(
        source_b,
        "vdb_chunks.json",
        [
            {"__id__": "chunk-2", "__created_at__": 2, "content": "two-updated"},
            {"__id__": "chunk-3", "__created_at__": 2, "content": "three"},
        ],
        [[0.5, 0.5], [0.25, 0.75]],
    )
    for name in ("vdb_entities.json", "vdb_relationships.json"):
        _write_vdb(source_a, name, [], [])
        _write_vdb(source_b, name, [], [])

    merge_projects([source_a, source_b], output)

    data, matrix = _read_vdb(output, "vdb_chunks.json")
    assert [record["__id__"] for record in data] == ["chunk-1", "chunk-2", "chunk-3"]
    assert data[1]["content"] == "two-updated"
    np.testing.assert_allclose(matrix[0], np.array([1.0, 0.0], dtype=np.float32))
    np.testing.assert_allclose(matrix[1], np.array([0.5, 0.5], dtype=np.float32))
    np.testing.assert_allclose(matrix[2], np.array([0.25, 0.75], dtype=np.float32))


def test_merge_projects_merges_sqlite_kv_and_doc_status_json(tmp_path: Path):
    source_a = tmp_path / "source_a"
    source_b = tmp_path / "source_b"
    output = tmp_path / "merged"
    source_a.mkdir()
    source_b.mkdir()
    _write_graph(source_a, nx.Graph())
    _write_graph(source_b, nx.Graph())
    for name in ("vdb_chunks.json", "vdb_entities.json", "vdb_relationships.json"):
        _write_vdb(source_a, name, [], [])
        _write_vdb(source_b, name, [], [])

    _write_sqlite_kv(
        source_a,
        "full_docs",
        {
            "doc-a": {"content": "old", "create_time": 1, "update_time": 1},
            "doc-b": {"content": "b", "create_time": 1, "update_time": 1},
        },
    )
    _write_sqlite_kv(
        source_b,
        "full_docs",
        {
            "doc-a": {"content": "new", "create_time": 2, "update_time": 3},
        },
    )
    _write_sqlite_kv(
        source_a,
        "text_chunks",
        {"chunk-a": {"content": "chunk", "create_time": 1, "update_time": 1}},
    )
    _write_sqlite_kv(source_b, "text_chunks", {})

    (source_a / "kv_store_doc_status.json").write_text(
        json.dumps({"doc-a": {"status": "processed"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (source_b / "kv_store_doc_status.json").write_text(
        json.dumps(
            {"doc-c": {"status": "processed", "chunks_list": ["chunk-c"]}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    merge_projects([source_a, source_b], output)

    full_docs = _read_sqlite_kv(output, "full_docs")
    assert set(full_docs) == {"doc-a", "doc-b"}
    assert full_docs["doc-a"]["content"] == "new"
    assert full_docs["doc-a"]["create_time"] == 2
    assert full_docs["doc-a"]["update_time"] == 3

    text_chunks = _read_sqlite_kv(output, "text_chunks")
    assert text_chunks["chunk-a"]["llm_cache_list"] == []

    doc_status = json.loads(
        (output / "kv_store_doc_status.json").read_text(encoding="utf-8")
    )
    assert doc_status["doc-a"]["chunks_list"] == []
    assert doc_status["doc-c"]["chunks_list"] == ["chunk-c"]

    index_metadata = _read_sqlite_kv(output, "index_metadata")
    assert index_metadata["corpus"]["corpus_revision"] == 1
    assert index_metadata["corpus"]["index_digest"] is None

    conn = sqlite3.connect(output / "kv_store_llm_response_cache.sqlite")
    assert conn.execute("SELECT count(*) FROM query_cache_entries").fetchone()[0] == 0
    conn.close()


def test_merge_projects_refreshes_entity_and_relationship_vdb_metadata_from_graph(tmp_path: Path):
    source_a = tmp_path / "source_a"
    source_b = tmp_path / "source_b"
    output = tmp_path / "merged"
    source_a.mkdir()
    source_b.mkdir()

    graph_a = nx.Graph()
    graph_a.add_node(
        "A",
        entity_id="A",
        entity_type="category",
        description="desc-a",
        source_id="chunk-a",
        source_chunk_ids="chunk-a",
        file_path="/docs/a.pdf",
        embeddings="[]",
        created_at=1,
    )
    graph_a.add_node(
        "B",
        entity_id="B",
        entity_type="category",
        description="desc-b",
        source_id="chunk-a",
        source_chunk_ids="chunk-a",
        file_path="/docs/a.pdf",
        embeddings="[]",
        created_at=1,
    )
    graph_a.add_edge(
        "A",
        "B",
        weight=1,
        description="edge-a",
        keywords="k1",
        source_id="chunk-a",
        source_chunk_ids="chunk-a",
        file_path="/docs/a.pdf",
        created_at=1,
    )
    _write_graph(source_a, graph_a)

    graph_b = nx.Graph()
    graph_b.add_node(
        "A",
        entity_id="A",
        entity_type="category",
        description="desc-c",
        source_id="chunk-b",
        source_chunk_ids="chunk-b",
        file_path="/docs/b.pdf",
        embeddings="[]",
        created_at=2,
    )
    graph_b.add_node(
        "B",
        entity_id="B",
        entity_type="category",
        description="desc-b",
        source_id="chunk-b",
        source_chunk_ids="chunk-b",
        file_path="/docs/b.pdf",
        embeddings="[]",
        created_at=2,
    )
    graph_b.add_edge(
        "B",
        "A",
        weight=1,
        description="edge-c",
        keywords="k2",
        source_id="chunk-b",
        source_chunk_ids="chunk-b",
        file_path="/docs/b.pdf",
        created_at=2,
    )
    _write_graph(source_b, graph_b)

    ent_a_id = _compute_mdhash_id("A", prefix="ent-")
    rel_id = _compute_mdhash_id("A" + "B", prefix="rel-")
    _write_vdb(
        source_a,
        "vdb_entities.json",
        [
            {
                "__id__": ent_a_id,
                "__created_at__": 5,
                "entity_name": "A",
                "content": "stale",
            }
        ],
        [[1.0, 0.0]],
    )
    _write_vdb(
        source_b,
        "vdb_entities.json",
        [
            {
                "__id__": ent_a_id,
                "__created_at__": 6,
                "entity_name": "A",
                "content": "stale-new",
            }
        ],
        [[0.0, 1.0]],
    )
    _write_vdb(
        source_a,
        "vdb_relationships.json",
        [
            {
                "__id__": rel_id,
                "__created_at__": 7,
                "src_id": "A",
                "tgt_id": "B",
                "content": "stale",
            }
        ],
        [[1.0, 1.0]],
    )
    _write_vdb(source_b, "vdb_relationships.json", [], [])
    _write_vdb(source_a, "vdb_chunks.json", [], [])
    _write_vdb(source_b, "vdb_chunks.json", [], [])

    merge_projects([source_a, source_b], output)

    entity_data, entity_matrix = _read_vdb(output, "vdb_entities.json")
    assert entity_data[0]["content"] == f"A\ndesc-a{GRAPH_FIELD_SEP}desc-c"
    assert entity_data[0]["source_chunk_ids"] == f"chunk-a{GRAPH_FIELD_SEP}chunk-b"
    np.testing.assert_allclose(
        entity_matrix[0], np.array([0.0, 1.0], dtype=np.float32)
    )

    relationship_data, _ = _read_vdb(output, "vdb_relationships.json")
    assert relationship_data[0]["__id__"] == rel_id
    assert relationship_data[0]["src_id"] == "A"
    assert relationship_data[0]["tgt_id"] == "B"
    assert relationship_data[0]["content"] == f"A\tB\nk1,k2\nedge-a{GRAPH_FIELD_SEP}edge-c"
