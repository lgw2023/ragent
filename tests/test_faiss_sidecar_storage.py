from __future__ import annotations

import asyncio
import base64
import importlib
import importlib.machinery
import pickle
import sqlite3
import sys
import types
from pathlib import Path

import numpy as np

from ragent.vector_sidecar_artifacts import (
    DEFAULT_SIDECAR_PROFILE,
    default_vector_sidecar_dir,
    validate_vector_sidecar_manifest,
)
from tools import build_vector_sidecars


class _FakeHnswParams:
    efConstruction = 0
    efSearch = 0


class _FakeFaissIndexFlatIP:
    def __init__(self, dim: int):
        self.dim = dim
        self.hnsw = _FakeHnswParams()
        self.vectors = np.array([], dtype=np.float32).reshape(0, dim)

    @property
    def ntotal(self):
        return self.vectors.shape[0]

    def add(self, vectors):
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.size == 0:
            return
        self.vectors = np.vstack([self.vectors, vectors.reshape(-1, self.dim)])

    def search(self, queries, top_k: int):
        queries = np.asarray(queries, dtype=np.float32).reshape(-1, self.dim)
        if self.vectors.shape[0] == 0:
            distances = np.zeros((queries.shape[0], top_k), dtype=np.float32)
            indices = np.full((queries.shape[0], top_k), -1, dtype=np.int64)
            return distances, indices
        scores = queries @ self.vectors.T
        order = np.argsort(scores, axis=1)[:, ::-1][:, :top_k]
        distances = np.take_along_axis(scores, order, axis=1)
        if order.shape[1] < top_k:
            pad = top_k - order.shape[1]
            order = np.pad(order, ((0, 0), (0, pad)), constant_values=-1)
            distances = np.pad(distances, ((0, 0), (0, pad)), constant_values=0.0)
        return distances.astype(np.float32), order.astype(np.int64)


class _FakeFaissIndexHNSWFlat(_FakeFaissIndexFlatIP):
    def __init__(self, dim: int, _m: int, _metric: int):
        super().__init__(dim)


def _normalize_l2(matrix):
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix[:] = matrix / norms


def _fake_write_index(index, path):
    with open(path, "wb") as file:
        pickle.dump(index, file)


def _fake_read_index(path):
    with open(path, "rb") as file:
        return pickle.load(file)


def _fake_faiss_module():
    module = types.ModuleType("faiss")
    module.IndexFlatIP = _FakeFaissIndexFlatIP
    module.IndexHNSWFlat = _FakeFaissIndexHNSWFlat
    module.IndexIVFFlat = lambda quantizer, dim, nlist, metric: _FakeFaissIndexFlatIP(dim)
    module.METRIC_INNER_PRODUCT = 0
    module.normalize_L2 = _normalize_l2
    module.write_index = _fake_write_index
    module.read_index = _fake_read_index
    return module


def _install_fake_faiss(monkeypatch):
    fake_faiss = _fake_faiss_module()
    original_find_spec = importlib.util.find_spec

    def fake_find_spec(name, package=None):
        if name == "faiss":
            return importlib.machinery.ModuleSpec(name, loader=None)
        return original_find_spec(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setitem(sys.modules, "faiss", fake_faiss)
    sys.modules.pop("ragent.kg.faiss_sidecar_impl", None)
    return importlib.import_module("ragent.kg.faiss_sidecar_impl")


def _write_vdb(path: Path, matrix: np.ndarray, records: list[dict]):
    payload = {
        "embedding_dim": matrix.shape[1],
        "data": records,
        "matrix": base64.b64encode(matrix.astype(np.float32).tobytes()).decode(),
    }
    path.write_text(
        __import__("json").dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_all_vdb_files(project_dir: Path):
    matrix = np.asarray(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    _write_vdb(
        project_dir / "vdb_chunks.json",
        matrix,
        [
            {"__id__": "chunk-a", "__created_at__": 1, "content": "apple"},
            {"__id__": "chunk-b", "__created_at__": 2, "content": "banana"},
        ],
    )
    _write_vdb(
        project_dir / "vdb_entities.json",
        matrix,
        [
            {"__id__": "entity-a", "entity_name": "apple"},
            {"__id__": "entity-b", "entity_name": "banana"},
        ],
    )
    _write_vdb(
        project_dir / "vdb_relationships.json",
        matrix,
        [
            {"__id__": "rel-a", "src_id": "entity-a", "tgt_id": "entity-b"},
            {"__id__": "rel-b", "src_id": "entity-b", "tgt_id": "entity-a"},
        ],
    )


class _EmbeddingFunc:
    embedding_dim = 3

    async def __call__(self, texts, _priority=None):
        lookup = {
            "apple": [1.0, 0.1, 0.0],
            "banana": [0.0, 1.0, 0.0],
        }
        return np.asarray([lookup[str(text)] for text in texts], dtype=np.float32)


def test_build_sidecar_and_query_exact_results(monkeypatch, tmp_path: Path):
    sidecar_module = _install_fake_faiss(monkeypatch)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    matrix = np.asarray(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    _write_vdb(
        project_dir / "vdb_chunks.json",
        matrix,
        [
            {"__id__": "chunk-a", "__created_at__": 1, "content": "apple"},
            {"__id__": "chunk-b", "__created_at__": 2, "content": "banana"},
            {"__id__": "chunk-c", "__created_at__": 3, "content": "citrus"},
        ],
    )

    sidecar_dir = tmp_path / "sidecar"
    manifest = build_vector_sidecars.build_sidecars(
        project_dir=project_dir,
        output_dir=sidecar_dir,
        namespaces=["chunks"],
        default_spec=build_vector_sidecars.IndexSpec(index_type="flat"),
    )
    assert manifest["profile"] == "custom"
    assert manifest["namespaces"]["chunks"]["count"] == 3
    assert (sidecar_dir / "faiss_index_chunks.index").exists()
    assert (sidecar_dir / "metadata_chunks.sqlite").exists()

    storage = sidecar_module.FaissSidecarVectorDBStorage(
        namespace="chunks",
        workspace="",
        global_config={
            "vector_db_storage_cls_kwargs": {
                "cosine_better_than_threshold": 0.0,
                "sidecar_dir": str(sidecar_dir),
            }
        },
        embedding_func=_EmbeddingFunc(),
    )
    timings: list[dict] = []
    results = asyncio.run(storage.query("apple", top_k=2, timing_collector=timings))
    assert [item["id"] for item in results] == ["chunk-a", "chunk-b"]
    assert results[0]["created_at"] == 1
    assert timings[-1]["index_type"] == "flat"

    record = asyncio.run(storage.get_by_id("chunk-b"))
    assert record["content"] == "banana"
    asyncio.run(storage.finalize())


def test_build_sidecar_allows_duplicate_external_ids(monkeypatch, capsys, tmp_path: Path):
    _install_fake_faiss(monkeypatch)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    matrix = np.asarray(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    _write_vdb(
        project_dir / "vdb_chunks.json",
        matrix,
        [
            {"__id__": "chunk-dup", "__created_at__": 1, "content": "apple"},
            {"__id__": "chunk-dup", "__created_at__": 2, "content": "banana"},
        ],
    )

    sidecar_dir = tmp_path / "sidecar"
    manifest = build_vector_sidecars.build_sidecars(
        project_dir=project_dir,
        output_dir=sidecar_dir,
        namespaces=["chunks"],
        default_spec=build_vector_sidecars.IndexSpec(index_type="flat"),
    )

    assert manifest["namespaces"]["chunks"]["count"] == 2
    warning = capsys.readouterr().err
    assert "duplicate vector external ids in chunks in vdb_chunks.json" in warning
    assert "1 duplicate id values" in warning
    assert "FAISS row_id remains authoritative" in warning
    assert "chunk-dup(2)" in warning

    conn = sqlite3.connect(sidecar_dir / "metadata_chunks.sqlite")
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM vector_metadata WHERE id = ?",
            ("chunk-dup",),
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 2


def test_build_sidecar_supports_entity_and_relationship_overrides(
    monkeypatch, tmp_path: Path
):
    _install_fake_faiss(monkeypatch)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    matrix = np.asarray(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    _write_vdb(
        project_dir / "vdb_chunks.json",
        matrix,
        [
            {"__id__": "chunk-a", "content": "apple"},
            {"__id__": "chunk-b", "content": "banana"},
        ],
    )
    _write_vdb(
        project_dir / "vdb_entities.json",
        matrix,
        [
            {"__id__": "entity-a", "entity_name": "apple"},
            {"__id__": "entity-b", "entity_name": "banana"},
        ],
    )
    _write_vdb(
        project_dir / "vdb_relationships.json",
        matrix,
        [
            {"__id__": "rel-a", "src_id": "entity-a", "tgt_id": "entity-b"},
            {"__id__": "rel-b", "src_id": "entity-b", "tgt_id": "entity-a"},
        ],
    )

    manifest = build_vector_sidecars.build_sidecars(
        project_dir=project_dir,
        output_dir=tmp_path / "sidecar",
        namespaces=["chunks", "entities", "relationships"],
        default_spec=build_vector_sidecars.IndexSpec(index_type="flat"),
        entities_spec=build_vector_sidecars.IndexSpec(
            index_type="hnsw",
            hnsw_ef_search=64,
        ),
        relationships_spec=build_vector_sidecars.IndexSpec(
            index_type="hnsw",
            hnsw_ef_search=128,
        ),
    )

    namespaces = manifest["namespaces"]
    assert namespaces["chunks"]["index_type"] == "flat"
    assert namespaces["chunks"]["search_params"] == {}
    assert namespaces["entities"]["index_type"] == "hnsw"
    assert namespaces["entities"]["search_params"] == {"ef_search": 64}
    assert namespaces["relationships"]["index_type"] == "hnsw"
    assert namespaces["relationships"]["search_params"] == {"ef_search": 128}


def test_build_profile_sidecars_uses_project_default_profile_dir(
    monkeypatch,
    tmp_path: Path,
):
    _install_fake_faiss(monkeypatch)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _write_all_vdb_files(project_dir)

    manifest = build_vector_sidecars.build_profile_sidecars(project_dir=project_dir)
    sidecar_dir = default_vector_sidecar_dir(project_dir)

    assert manifest["profile"] == DEFAULT_SIDECAR_PROFILE
    assert (sidecar_dir / "manifest.json").exists()
    assert manifest["namespaces"]["chunks"]["index_type"] == "flat"
    assert manifest["namespaces"]["chunks"]["search_params"] == {}
    assert manifest["namespaces"]["entities"]["index_type"] == "hnsw"
    assert manifest["namespaces"]["entities"]["search_params"] == {"ef_search": 128}
    assert manifest["namespaces"]["relationships"]["index_type"] == "hnsw"
    assert manifest["namespaces"]["relationships"]["search_params"] == {
        "ef_search": 128
    }

    validation = validate_vector_sidecar_manifest(
        project_dir,
        sidecar_dir,
        expected_profile=DEFAULT_SIDECAR_PROFILE,
    )
    assert validation["profile"] == DEFAULT_SIDECAR_PROFILE
    assert validation["sidecar_dir"] == str(sidecar_dir)
    assert validation["manifest_digest"]


def test_build_profile_sidecars_exact_profile_keeps_all_namespaces_flat(
    monkeypatch,
    tmp_path: Path,
):
    _install_fake_faiss(monkeypatch)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _write_all_vdb_files(project_dir)

    manifest = build_vector_sidecars.build_profile_sidecars(
        project_dir=project_dir,
        profile="exact",
    )

    assert manifest["profile"] == "exact"
    assert (project_dir / "vector_sidecars" / "exact" / "manifest.json").exists()
    assert {
        namespace_manifest["index_type"]
        for namespace_manifest in manifest["namespaces"].values()
    } == {"flat"}


def test_build_profile_sidecars_allows_namespace_subset(monkeypatch, tmp_path: Path):
    _install_fake_faiss(monkeypatch)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _write_vdb(
        project_dir / "vdb_chunks.json",
        np.asarray([[1.0, 0.0, 0.0]], dtype=np.float32),
        [{"__id__": "chunk-a", "content": "apple"}],
    )

    manifest = build_vector_sidecars.build_profile_sidecars(
        project_dir=project_dir,
        output_dir=tmp_path / "sidecar",
        namespaces=["chunks"],
    )

    assert set(manifest["namespaces"]) == {"chunks"}
    assert manifest["profile"] == DEFAULT_SIDECAR_PROFILE


def test_sidecar_dimension_mismatch_raises(monkeypatch, tmp_path: Path):
    sidecar_module = _install_fake_faiss(monkeypatch)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    _write_vdb(
        project_dir / "vdb_chunks.json",
        np.asarray([[1.0, 0.0, 0.0]], dtype=np.float32),
        [{"__id__": "chunk-a", "content": "apple"}],
    )
    sidecar_dir = tmp_path / "sidecar"
    build_vector_sidecars.build_sidecars(
        project_dir=project_dir,
        output_dir=sidecar_dir,
        namespaces=["chunks"],
        default_spec=build_vector_sidecars.IndexSpec(index_type="flat"),
    )

    class BadEmbeddingFunc:
        embedding_dim = 2

    try:
        sidecar_module.FaissSidecarVectorDBStorage(
            namespace="chunks",
            workspace="",
            global_config={
                "vector_db_storage_cls_kwargs": {
                    "cosine_better_than_threshold": 0.0,
                    "sidecar_dir": str(sidecar_dir),
                }
            },
            embedding_func=BadEmbeddingFunc(),
        )
    except ValueError as exc:
        assert "dimension mismatch" in str(exc)
    else:
        raise AssertionError("expected dimension mismatch")


def test_runtime_backend_env_selects_sidecar(monkeypatch):
    from ragent.ragent import _resolve_default_vector_storage

    monkeypatch.delenv("VECTOR_STORAGE", raising=False)
    monkeypatch.setenv("RAG_VECTOR_RUNTIME_BACKEND", "faiss_sidecar")
    assert _resolve_default_vector_storage() == "FaissSidecarVectorDBStorage"

    monkeypatch.setenv("VECTOR_STORAGE", "NanoVectorDBStorage")
    assert _resolve_default_vector_storage() == "NanoVectorDBStorage"
