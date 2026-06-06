from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, final

import numpy as np

from ragent.base import BaseVectorStorage
from ragent.native_runtime_compat import ensure_faiss_import_compatibility
from ragent.utils import compute_mdhash_id, logger

ensure_faiss_import_compatibility()

if importlib.util.find_spec("faiss") is None:
    raise RuntimeError(
        "faiss-cpu or faiss-gpu is required for FaissSidecarVectorDBStorage. "
        "Install the standard ragent dependencies in the inference environment."
    )

import faiss  # type: ignore


MANIFEST_FILE_NAME = "manifest.json"
METADATA_TABLE = "vector_metadata"


def _sidecar_dir_from_config(global_config: dict[str, Any]) -> Path:
    kwargs = global_config.get("vector_db_storage_cls_kwargs") or {}
    configured_dir = kwargs.get("sidecar_dir") or os.getenv("RAG_VECTOR_SIDECAR_DIR")
    if not configured_dir:
        raise ValueError(
            "FaissSidecarVectorDBStorage requires RAG_VECTOR_SIDECAR_DIR "
            "or vector_db_storage_cls_kwargs['sidecar_dir']."
        )
    return Path(str(configured_dir)).expanduser().resolve()


def _load_manifest(sidecar_dir: Path) -> dict[str, Any]:
    manifest_path = sidecar_dir / MANIFEST_FILE_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"FAISS sidecar manifest not found: {manifest_path}")
    with manifest_path.open(encoding="utf-8") as file:
        manifest = json.load(file)
    if int(manifest.get("version") or 0) != 1:
        raise ValueError(f"Unsupported FAISS sidecar manifest version: {manifest_path}")
    return manifest


def _manifest_digest(manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True)
    return compute_mdhash_id(payload, prefix="sidecar-")


def _coerce_search_matrix(embeddings: Any, dim: int) -> np.ndarray:
    matrix = np.asarray(embeddings, dtype=np.float32)
    if matrix.size == 0:
        return matrix.reshape(0, dim)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    if matrix.ndim != 2 or matrix.shape[1] != dim:
        raise ValueError(
            f"Query embedding shape must be (n, {dim}), got {tuple(matrix.shape)}"
        )
    faiss.normalize_L2(matrix)
    return matrix


@final
@dataclass
class FaissSidecarVectorDBStorage(BaseVectorStorage):
    """Read-only FAISS sidecar vector storage for versioned inference projects."""

    def __post_init__(self):
        kwargs = self.global_config.get("vector_db_storage_cls_kwargs", {})
        cosine_threshold = kwargs.get("cosine_better_than_threshold")
        if cosine_threshold is None:
            raise ValueError(
                "cosine_better_than_threshold must be specified in vector_db_storage_cls_kwargs"
            )
        self.cosine_better_than_threshold = cosine_threshold
        self._dim = int(self.embedding_func.embedding_dim)

        self._sidecar_dir = _sidecar_dir_from_config(self.global_config)
        self._manifest_path = self._sidecar_dir / MANIFEST_FILE_NAME
        self._manifest = _load_manifest(self._sidecar_dir)
        self.sidecar_manifest_digest = _manifest_digest(self._manifest)

        namespaces = self._manifest.get("namespaces") or {}
        namespace_key = str(self.namespace)
        namespace_manifest = namespaces.get(namespace_key)
        if not isinstance(namespace_manifest, dict):
            raise KeyError(
                f"Namespace {namespace_key!r} is missing from FAISS sidecar manifest."
            )
        self._namespace_manifest = namespace_manifest
        self.sidecar_index_type = str(namespace_manifest.get("index_type") or "unknown")
        self.sidecar_manifest_path = str(self._manifest_path)

        manifest_dim = int(namespace_manifest.get("embedding_dim") or 0)
        if manifest_dim != self._dim:
            raise ValueError(
                f"FAISS sidecar dimension mismatch for {namespace_key}: "
                f"manifest={manifest_dim}, runtime={self._dim}"
            )

        self._index_path = self._sidecar_dir / str(namespace_manifest["index_file"])
        self._metadata_path = self._sidecar_dir / str(
            namespace_manifest["metadata_file"]
        )
        if not self._index_path.exists():
            raise FileNotFoundError(f"FAISS sidecar index not found: {self._index_path}")
        if not self._metadata_path.exists():
            raise FileNotFoundError(
                f"FAISS sidecar metadata DB not found: {self._metadata_path}"
            )

        self._index = faiss.read_index(str(self._index_path))
        self._apply_search_params()
        self._conn = sqlite3.connect(str(self._metadata_path))
        self._conn.row_factory = sqlite3.Row

        ntotal = int(getattr(self._index, "ntotal", 0))
        expected_count = int(namespace_manifest.get("count") or 0)
        if ntotal != expected_count:
            raise ValueError(
                f"FAISS sidecar count mismatch for {namespace_key}: "
                f"index={ntotal}, manifest={expected_count}"
            )
        logger.info(
            "Loaded FAISS sidecar namespace=%s index_type=%s count=%s path=%s",
            namespace_key,
            self.sidecar_index_type,
            ntotal,
            self._index_path,
        )

    def _apply_search_params(self) -> None:
        params = self._namespace_manifest.get("search_params") or {}
        nprobe = params.get("nprobe")
        if nprobe is not None and hasattr(self._index, "nprobe"):
            self._index.nprobe = int(nprobe)
        ef_search = params.get("ef_search")
        hnsw = getattr(self._index, "hnsw", None)
        if ef_search is not None and hnsw is not None and hasattr(hnsw, "efSearch"):
            hnsw.efSearch = int(ef_search)

    async def initialize(self):
        return None

    async def finalize(self):
        conn = getattr(self, "_conn", None)
        if conn is not None:
            conn.close()
            self._conn = None

    async def _search(self, embeddings: Any, top_k: int) -> tuple[Any, Any]:
        query_matrix = _coerce_search_matrix(embeddings, self._dim)
        if query_matrix.shape[0] == 0:
            return [], []
        return await asyncio.to_thread(self._index.search, query_matrix, top_k)

    def _fetch_records_by_row_ids(self, row_ids: list[int]) -> dict[int, dict[str, Any]]:
        if not row_ids:
            return {}
        placeholders = ",".join("?" for _ in row_ids)
        rows = self._conn.execute(
            f"SELECT row_id, record_json FROM {METADATA_TABLE} "
            f"WHERE row_id IN ({placeholders})",
            row_ids,
        ).fetchall()
        return {
            int(row["row_id"]): json.loads(str(row["record_json"])) for row in rows
        }

    def _format_result_sets(self, distances: Any, indices: Any) -> list[list[dict[str, Any]]]:
        row_ids = [
            int(index)
            for index in np.asarray(indices).reshape(-1).tolist()
            if int(index) >= 0
        ]
        records_by_row_id = self._fetch_records_by_row_ids(row_ids)

        result_sets: list[list[dict[str, Any]]] = []
        for row_distances, row_indices in zip(distances, indices):
            result_set: list[dict[str, Any]] = []
            for distance, index in zip(row_distances, row_indices):
                row_id = int(index)
                if row_id < 0:
                    continue
                score = float(distance)
                if score < self.cosine_better_than_threshold:
                    break
                record = records_by_row_id.get(row_id)
                if record is None:
                    continue
                result_set.append(
                    {
                        **record,
                        "id": record.get("__id__") or record.get("id"),
                        "distance": score,
                        "created_at": record.get("__created_at__")
                        or record.get("created_at"),
                    }
                )
            result_sets.append(result_set)
        return result_sets

    async def query(
        self,
        query: str,
        top_k: int,
        ids: list[str] | None = None,
        *,
        timing_collector: list[dict[str, Any]] | None = None,
        stage_prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        prefix = stage_prefix or self.namespace
        stage_started_at = time.perf_counter()
        embedding = await self.embedding_func([query], _priority=5)
        if timing_collector is not None:
            timing_collector.append(
                {
                    "stage": f"{prefix}_embedding",
                    "label": f"{self.namespace} query embedding",
                    "seconds": round(max(time.perf_counter() - stage_started_at, 0.0), 3),
                }
            )
        result_sets = await self.query_many_by_embeddings(
            embedding,
            top_k=top_k,
            ids=ids,
            timing_collector=timing_collector,
            stage_prefix=stage_prefix,
        )
        return result_sets[0] if result_sets else []

    async def query_many(
        self,
        queries: list[str],
        top_k: int,
        ids: list[str] | None = None,
        *,
        timing_collector: list[dict[str, Any]] | None = None,
        stage_prefix: str | None = None,
    ) -> list[list[dict[str, Any]]]:
        query_list = [str(query) for query in queries]
        if not query_list:
            return []

        prefix = stage_prefix or self.namespace
        stage_started_at = time.perf_counter()
        embeddings = await self.embedding_func(query_list, _priority=5)
        if timing_collector is not None:
            timing_collector.append(
                {
                    "stage": f"{prefix}_embedding",
                    "label": f"{self.namespace} batch query embedding",
                    "seconds": round(max(time.perf_counter() - stage_started_at, 0.0), 3),
                    "query_count": len(query_list),
                }
            )
        return await self.query_many_by_embeddings(
            embeddings,
            top_k=top_k,
            ids=ids,
            timing_collector=timing_collector,
            stage_prefix=stage_prefix,
        )

    async def query_many_by_embeddings(
        self,
        embeddings: Any,
        top_k: int,
        ids: list[str] | None = None,
        *,
        timing_collector: list[dict[str, Any]] | None = None,
        stage_prefix: str | None = None,
    ) -> list[list[dict[str, Any]]]:
        prefix = stage_prefix or self.namespace
        stage_started_at = time.perf_counter()
        distances, indices = await self._search(embeddings, top_k)
        if timing_collector is not None:
            timing_collector.append(
                {
                    "stage": f"{prefix}_index_search",
                    "label": f"{self.namespace} FAISS sidecar vector search",
                    "seconds": round(max(time.perf_counter() - stage_started_at, 0.0), 3),
                    "query_count": len(embeddings),
                    "index_type": self.sidecar_index_type,
                    "manifest_digest": self.sidecar_manifest_digest,
                }
            )
        return self._format_result_sets(distances, indices)

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        raise RuntimeError("FaissSidecarVectorDBStorage is read-only.")

    async def delete(self, ids: list[str]):
        raise RuntimeError("FaissSidecarVectorDBStorage is read-only.")

    async def delete_entity(self, entity_name: str) -> None:
        raise RuntimeError("FaissSidecarVectorDBStorage is read-only.")

    async def delete_entity_relation(self, entity_name: str) -> None:
        raise RuntimeError("FaissSidecarVectorDBStorage is read-only.")

    async def index_done_callback(self) -> bool:
        return True

    async def get_by_id(self, id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            f"SELECT record_json FROM {METADATA_TABLE} WHERE id = ?",
            (id,),
        ).fetchone()
        if row is None:
            return None
        record = json.loads(str(row["record_json"]))
        return {
            **record,
            "id": record.get("__id__") or record.get("id"),
            "created_at": record.get("__created_at__") or record.get("created_at"),
        }

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for record_id in ids:
            record = await self.get_by_id(record_id)
            if record is not None:
                results.append(record)
        return results

    @property
    async def client_storage(self):
        return {
            "sidecar_dir": str(self._sidecar_dir),
            "namespace": str(self.namespace),
            "index_type": self.sidecar_index_type,
            "manifest_digest": self.sidecar_manifest_digest,
            "count": int(self._namespace_manifest.get("count") or 0),
        }

    async def drop(self) -> dict[str, str]:
        return {
            "status": "error",
            "message": "FaissSidecarVectorDBStorage is read-only.",
        }
