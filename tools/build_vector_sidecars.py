#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import importlib.util
import json
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

VDB_NAMESPACES = {
    "chunks": "vdb_chunks.json",
    "entities": "vdb_entities.json",
    "relationships": "vdb_relationships.json",
}

MANIFEST_FILE_NAME = "manifest.json"
METADATA_TABLE = "vector_metadata"
OMIT_METADATA_FIELDS = {"__vector__", "vector", "embedding", "embeddings"}


@dataclass(frozen=True)
class IndexSpec:
    index_type: Literal["flat", "hnsw", "ivf_flat"]
    hnsw_m: int = 16
    hnsw_ef_construction: int = 200
    hnsw_ef_search: int = 128
    ivf_nlist: int = 4096
    ivf_nprobe: int = 32


def _require_faiss():
    if importlib.util.find_spec("faiss") is None:
        raise RuntimeError(
            "faiss-cpu or faiss-gpu is required. Install ragent with the "
            "'faiss' extra before building sidecars."
        )
    import faiss  # type: ignore

    return faiss


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decode_matrix(value: Any, embedding_dim: int) -> np.ndarray:
    if value in (None, ""):
        return np.array([], dtype=np.float32).reshape(0, embedding_dim)
    if isinstance(value, str):
        array = np.frombuffer(base64.b64decode(value), dtype=np.float32)
    else:
        array = np.asarray(value, dtype=np.float32)

    if array.size == 0:
        return array.reshape(0, embedding_dim)
    return array.reshape(-1, embedding_dim)


def load_vdb(path: Path) -> tuple[int, list[dict[str, Any]], np.ndarray]:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    embedding_dim = int(payload["embedding_dim"])
    data = [dict(item) for item in payload.get("data", [])]
    matrix = _decode_matrix(payload.get("matrix", ""), embedding_dim)
    if len(data) != matrix.shape[0]:
        raise ValueError(
            f"{path} has {len(data)} data records but {matrix.shape[0]} vectors"
        )
    return embedding_dim, data, matrix


def _metadata_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key not in OMIT_METADATA_FIELDS}


def _external_id(record: dict[str, Any]) -> str:
    return str(record.get("__id__") or record.get("id") or "")


def _warn_duplicate_external_ids(records: list[dict[str, Any]], *, context: str) -> None:
    counts = Counter(_external_id(record) for record in records)
    duplicates = [
        (external_id, count)
        for external_id, count in counts.items()
        if external_id and count > 1
    ]
    if not duplicates:
        return

    duplicates.sort(key=lambda item: (-item[1], item[0]))
    samples = ", ".join(
        f"{external_id}({count})" for external_id, count in duplicates[:5]
    )
    more = len(duplicates) - 5
    if more > 0:
        samples = f"{samples} (+{more} more)"
    print(
        f"Warning: duplicate vector external ids in {context}: "
        f"{len(duplicates)} duplicate id values; "
        f"FAISS row_id remains authoritative. Samples: {samples}",
        file=sys.stderr,
    )


def write_metadata_db(path: Path, records: list[dict[str, Any]]) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute(
            f"""
            CREATE TABLE {METADATA_TABLE} (
                row_id INTEGER PRIMARY KEY,
                id TEXT NOT NULL,
                created_at INTEGER,
                record_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"CREATE INDEX idx_{METADATA_TABLE}_id ON {METADATA_TABLE}(id)"
        )
        rows = []
        for row_id, record in enumerate(records):
            external_id = _external_id(record)
            if not external_id:
                raise ValueError(f"Missing vector record id at row {row_id}")
            metadata = _metadata_record(record)
            rows.append(
                (
                    row_id,
                    external_id,
                    int(record.get("__created_at__") or record.get("created_at") or 0),
                    json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                )
            )
        conn.executemany(
            f"""
            INSERT INTO {METADATA_TABLE}
                (row_id, id, created_at, record_json)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def _build_faiss_index(matrix: np.ndarray, spec: IndexSpec):
    faiss = _require_faiss()
    vectors = np.asarray(matrix, dtype=np.float32).copy()
    if vectors.ndim != 2:
        raise ValueError(f"Expected 2D vector matrix, got shape {vectors.shape}")
    dim = vectors.shape[1]
    faiss.normalize_L2(vectors)

    if spec.index_type == "flat":
        index = faiss.IndexFlatIP(dim)
    elif spec.index_type == "hnsw":
        index = faiss.IndexHNSWFlat(dim, spec.hnsw_m, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = spec.hnsw_ef_construction
        index.hnsw.efSearch = spec.hnsw_ef_search
    elif spec.index_type == "ivf_flat":
        quantizer = faiss.IndexFlatIP(dim)
        index = faiss.IndexIVFFlat(
            quantizer,
            dim,
            spec.ivf_nlist,
            faiss.METRIC_INNER_PRODUCT,
        )
        if vectors.shape[0] > 0:
            index.train(vectors)
        index.nprobe = spec.ivf_nprobe
    else:
        raise ValueError(f"Unsupported FAISS index type: {spec.index_type}")

    if vectors.shape[0] > 0:
        index.add(vectors)
    return index


def _write_faiss_index(path: Path, matrix: np.ndarray, spec: IndexSpec) -> None:
    faiss = _require_faiss()
    index = _build_faiss_index(matrix, spec)
    faiss.write_index(index, str(path))


def _search_params(spec: IndexSpec) -> dict[str, int]:
    if spec.index_type == "hnsw":
        return {"ef_search": spec.hnsw_ef_search}
    if spec.index_type == "ivf_flat":
        return {"nprobe": spec.ivf_nprobe}
    return {}


def _build_namespace_sidecar(
    *,
    project_dir: Path,
    output_dir: Path,
    namespace: str,
    file_name: str,
    spec: IndexSpec,
) -> dict[str, Any]:
    source_path = project_dir / file_name
    if not source_path.exists():
        raise FileNotFoundError(f"Vector DB file not found: {source_path}")

    embedding_dim, records, matrix = load_vdb(source_path)
    _warn_duplicate_external_ids(
        records,
        context=f"{namespace} in {source_path.name}",
    )
    index_file = f"faiss_index_{namespace}.index"
    metadata_file = f"metadata_{namespace}.sqlite"
    index_path = output_dir / index_file
    metadata_path = output_dir / metadata_file

    _write_faiss_index(index_path, matrix, spec)
    write_metadata_db(metadata_path, records)

    return {
        "namespace": namespace,
        "source_file": file_name,
        "source_sha256": _sha256(source_path),
        "source_size_bytes": source_path.stat().st_size,
        "embedding_dim": embedding_dim,
        "count": len(records),
        "index_type": spec.index_type,
        "index_file": index_file,
        "metadata_file": metadata_file,
        "search_params": _search_params(spec),
    }


def build_sidecars(
    *,
    project_dir: Path,
    output_dir: Path,
    namespaces: list[str],
    default_spec: IndexSpec,
    entities_spec: IndexSpec | None = None,
    relationships_spec: IndexSpec | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "version": 1,
        "created_at": int(time.time()),
        "source_project_dir": str(project_dir.resolve()),
        "namespaces": {},
    }
    for namespace in namespaces:
        if namespace not in VDB_NAMESPACES:
            raise ValueError(
                f"Unknown namespace {namespace!r}. Expected one of {sorted(VDB_NAMESPACES)}"
            )
        spec = default_spec
        if namespace == "entities" and entities_spec:
            spec = entities_spec
        elif namespace == "relationships" and relationships_spec:
            spec = relationships_spec
        manifest["namespaces"][namespace] = _build_namespace_sidecar(
            project_dir=project_dir,
            output_dir=output_dir,
            namespace=namespace,
            file_name=VDB_NAMESPACES[namespace],
            spec=spec,
        )

    manifest_path = output_dir / MANIFEST_FILE_NAME
    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2, sort_keys=True)
    return manifest


def _parse_namespaces(raw_namespaces: list[str]) -> list[str]:
    namespaces: list[str] = []
    for raw in raw_namespaces:
        for item in raw.split(","):
            namespace = item.strip()
            if namespace:
                namespaces.append(namespace)
    return namespaces or list(VDB_NAMESPACES)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build read-only FAISS vector sidecars from existing Ragent vdb JSON files."
    )
    parser.add_argument("--project-dir", required=True, help="Existing Ragent project directory.")
    parser.add_argument("--output-dir", required=True, help="Directory for generated sidecars.")
    parser.add_argument(
        "--namespaces",
        nargs="*",
        default=list(VDB_NAMESPACES),
        help="Namespaces to build: chunks, entities, relationships. Comma-separated values are accepted.",
    )
    parser.add_argument(
        "--index-type",
        choices=["flat", "hnsw", "ivf_flat"],
        default="flat",
        help="Default index type for selected namespaces.",
    )
    parser.add_argument(
        "--relationships-index-type",
        choices=["flat", "hnsw", "ivf_flat"],
        default=None,
        help="Override index type for relationships only.",
    )
    parser.add_argument(
        "--entities-index-type",
        choices=["flat", "hnsw", "ivf_flat"],
        default=None,
        help="Override index type for entities only.",
    )
    parser.add_argument("--hnsw-m", type=int, default=16)
    parser.add_argument("--hnsw-ef-construction", type=int, default=200)
    parser.add_argument("--hnsw-ef-search", type=int, default=128)
    parser.add_argument(
        "--entities-hnsw-ef-search",
        type=int,
        default=None,
        help="Override HNSW efSearch for entities only.",
    )
    parser.add_argument(
        "--relationships-hnsw-ef-search",
        type=int,
        default=None,
        help="Override HNSW efSearch for relationships only.",
    )
    parser.add_argument("--ivf-nlist", type=int, default=4096)
    parser.add_argument("--ivf-nprobe", type=int, default=32)
    parser.add_argument(
        "--entities-ivf-nprobe",
        type=int,
        default=None,
        help="Override IVF nprobe for entities only.",
    )
    parser.add_argument(
        "--relationships-ivf-nprobe",
        type=int,
        default=None,
        help="Override IVF nprobe for relationships only.",
    )
    return parser.parse_args(argv)


def _spec_from_args(
    args: argparse.Namespace,
    index_type: str,
    *,
    hnsw_ef_search: int | None = None,
    ivf_nprobe: int | None = None,
) -> IndexSpec:
    return IndexSpec(
        index_type=index_type,
        hnsw_m=args.hnsw_m,
        hnsw_ef_construction=args.hnsw_ef_construction,
        hnsw_ef_search=(
            hnsw_ef_search if hnsw_ef_search is not None else args.hnsw_ef_search
        ),
        ivf_nlist=args.ivf_nlist,
        ivf_nprobe=ivf_nprobe if ivf_nprobe is not None else args.ivf_nprobe,
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    project_dir = Path(args.project_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    namespaces = _parse_namespaces(args.namespaces)
    default_spec = _spec_from_args(args, args.index_type)
    entities_spec = (
        _spec_from_args(
            args,
            args.entities_index_type,
            hnsw_ef_search=args.entities_hnsw_ef_search,
            ivf_nprobe=args.entities_ivf_nprobe,
        )
        if args.entities_index_type
        else None
    )
    relationships_spec = (
        _spec_from_args(
            args,
            args.relationships_index_type,
            hnsw_ef_search=args.relationships_hnsw_ef_search,
            ivf_nprobe=args.relationships_ivf_nprobe,
        )
        if args.relationships_index_type
        else None
    )
    manifest = build_sidecars(
        project_dir=project_dir,
        output_dir=output_dir,
        namespaces=namespaces,
        default_spec=default_spec,
        entities_spec=entities_spec,
        relationships_spec=relationships_spec,
    )
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "namespaces": {
                    name: {
                        "count": item["count"],
                        "embedding_dim": item["embedding_dim"],
                        "index_type": item["index_type"],
                        "search_params": item["search_params"],
                    }
                    for name, item in manifest["namespaces"].items()
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
