#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ragent.constants import GRAPH_FIELD_SEP


GRAPH_FILE_NAME = "graph_chunk_entity_relation.graphml"
DOC_STATUS_FILE_NAME = "kv_store_doc_status.json"

VDB_FILE_NAMES = (
    "vdb_chunks.json",
    "vdb_entities.json",
    "vdb_relationships.json",
)

SQLITE_KV_NAMESPACES = (
    "full_docs",
    "text_chunks",
)

INDEX_METADATA_NAMESPACE = "index_metadata"
INDEX_METADATA_KEY = "corpus"
QUERY_CACHE_NAMESPACE = "llm_response_cache"


@dataclass
class MergeStats:
    sources: int = 0
    graph_input_nodes: int = 0
    graph_input_edges: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    vdb_records: dict[str, int] = field(default_factory=dict)
    kv_records: dict[str, int] = field(default_factory=dict)
    doc_status_records: int = 0
    dry_run: bool = False
    output_dir: str = ""


def _compute_mdhash_id(content: str, prefix: str = "") -> str:
    return prefix + hashlib.md5(content.encode()).hexdigest()


def _split_graph_field(value: Any) -> list[str]:
    if value in (None, "", [], {}, ()):
        return []
    if isinstance(value, str):
        values = value.split(GRAPH_FIELD_SEP)
    elif isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(_split_graph_field(item))
    else:
        values = [str(value)]
    return [item.strip() for item in values if str(item).strip()]


def _unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _merge_source_ids(*values: Any) -> str:
    merged: list[str] = []
    for value in values:
        merged.extend(_split_graph_field(value))
    return GRAPH_FIELD_SEP.join(_unique_in_order(merged))


def _merge_sorted_graph_field(*values: Any) -> str:
    merged: set[str] = set()
    for value in values:
        merged.update(_split_graph_field(value))
    return GRAPH_FIELD_SEP.join(sorted(merged))


def _split_keywords(value: Any) -> list[str]:
    keywords: list[str] = []
    for part in _split_graph_field(value):
        normalized = part.replace("，", ",")
        keywords.extend(item.strip() for item in normalized.split(",") if item.strip())
    return keywords


def _merge_keywords(*values: Any) -> str:
    merged: set[str] = set()
    for value in values:
        merged.update(_split_keywords(value))
    return ",".join(sorted(merged))


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _oldest_timestamp(*values: Any) -> int:
    timestamps = [_coerce_int(value, 0) for value in values]
    timestamps = [value for value in timestamps if value > 0]
    return min(timestamps) if timestamps else int(time.time())


def _is_empty_embedding(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() in {"", "[]", "None"}
    if isinstance(value, (list, tuple)):
        return len(value) == 0
    return False


def _choose_embedding(*values: Any) -> str:
    for value in values:
        if _is_empty_embedding(value):
            continue
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)
    return "[]"


def _choose_entity_type(*values: Any) -> str:
    ordered: list[str] = []
    for value in values:
        if value is None:
            continue
        entity_type = str(value).strip()
        if entity_type:
            ordered.append(entity_type)

    candidates = [value for value in ordered if value.upper() != "UNKNOWN"]
    if not candidates:
        return ordered[0] if ordered else "UNKNOWN"

    counts = {value: candidates.count(value) for value in candidates}
    return max(candidates, key=lambda value: counts[value])


def _merge_node_attrs(
    node_id: str, existing: dict[str, Any], incoming: dict[str, Any]
) -> dict[str, Any]:
    source_id = _merge_source_ids(
        existing.get("source_chunk_ids") or existing.get("source_id"),
        incoming.get("source_chunk_ids") or incoming.get("source_id"),
    )
    merged = {**existing, **incoming}
    merged.update(
        {
            "entity_id": node_id,
            "entity_type": _choose_entity_type(
                existing.get("entity_type"), incoming.get("entity_type")
            ),
            "description": _merge_sorted_graph_field(
                existing.get("description"), incoming.get("description")
            ),
            "source_id": source_id,
            "source_chunk_ids": source_id,
            "file_path": _merge_sorted_graph_field(
                existing.get("file_path"), incoming.get("file_path")
            ),
            "embeddings": _choose_embedding(
                existing.get("embeddings"), incoming.get("embeddings")
            ),
            "created_at": _oldest_timestamp(
                existing.get("created_at"), incoming.get("created_at")
            ),
        }
    )
    return merged


def _merge_edge_attrs(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    source_id = _merge_source_ids(
        existing.get("source_chunk_ids") or existing.get("source_id"),
        incoming.get("source_chunk_ids") or incoming.get("source_id"),
    )
    merged = {**existing, **incoming}
    merged.update(
        {
            "weight": _coerce_float(existing.get("weight"), 0.0)
            + _coerce_float(incoming.get("weight"), 0.0),
            "description": _merge_sorted_graph_field(
                existing.get("description"), incoming.get("description")
            ),
            "keywords": _merge_keywords(
                existing.get("keywords"), incoming.get("keywords")
            ),
            "source_id": source_id,
            "source_chunk_ids": source_id,
            "file_path": _merge_sorted_graph_field(
                existing.get("file_path"), incoming.get("file_path")
            ),
            "created_at": _oldest_timestamp(
                existing.get("created_at"), incoming.get("created_at")
            ),
        }
    )
    return merged


def _load_graph(path: Path) -> nx.Graph:
    if not path.exists():
        return nx.Graph()
    marker = path.read_bytes()[:64].strip()
    if marker in {b"", b"{}"}:
        return nx.Graph()
    return nx.read_graphml(path)


def _merge_graphs(source_dirs: list[Path], stats: MergeStats) -> nx.Graph:
    merged = nx.Graph()

    for source_dir in source_dirs:
        graph_path = source_dir / GRAPH_FILE_NAME
        if not graph_path.exists():
            continue
        graph = _load_graph(graph_path)
        stats.graph_input_nodes += graph.number_of_nodes()
        stats.graph_input_edges += graph.number_of_edges()

        for node_id, node_attrs in graph.nodes(data=True):
            node_key = str(node_id)
            incoming = dict(node_attrs)
            if merged.has_node(node_key):
                merged.nodes[node_key].update(
                    _merge_node_attrs(node_key, dict(merged.nodes[node_key]), incoming)
                )
            else:
                merged.add_node(node_key, **_merge_node_attrs(node_key, {}, incoming))

        for src_id, tgt_id, edge_attrs in graph.edges(data=True):
            if str(src_id) == str(tgt_id):
                continue
            edge_key = tuple(sorted((str(src_id), str(tgt_id))))
            for node_id in edge_key:
                if not merged.has_node(node_id):
                    merged.add_node(
                        node_id,
                        **_merge_node_attrs(
                            node_id,
                            {},
                            {
                                "entity_id": node_id,
                                "entity_type": "UNKNOWN",
                                "description": edge_attrs.get("description", ""),
                                "source_id": edge_attrs.get("source_id", ""),
                                "source_chunk_ids": edge_attrs.get(
                                    "source_chunk_ids", ""
                                ),
                                "file_path": edge_attrs.get("file_path", ""),
                            },
                        ),
                    )

            incoming = dict(edge_attrs)
            if merged.has_edge(*edge_key):
                merged.edges[edge_key].update(
                    _merge_edge_attrs(dict(merged.edges[edge_key]), incoming)
                )
            else:
                merged.add_edge(*edge_key, **_merge_edge_attrs({}, incoming))

    stats.graph_nodes = merged.number_of_nodes()
    stats.graph_edges = merged.number_of_edges()
    return merged


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


def _encode_matrix(matrix: np.ndarray) -> str:
    return base64.b64encode(matrix.astype(np.float32).tobytes()).decode()


def _load_vdb(path: Path) -> tuple[int, list[dict[str, Any]], np.ndarray, dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    embedding_dim = int(payload["embedding_dim"])
    data = [dict(item) for item in payload.get("data", [])]
    matrix = _decode_matrix(payload.get("matrix", ""), embedding_dim)
    if len(data) != matrix.shape[0]:
        raise ValueError(
            f"{path} has {len(data)} data records but {matrix.shape[0]} vectors"
        )
    additional_data = dict(payload.get("additional_data") or {})
    return embedding_dim, data, matrix, additional_data


def _merge_vdbs(
    source_dirs: list[Path],
    file_name: str,
) -> tuple[int | None, list[dict[str, Any]], list[np.ndarray], dict[str, Any]]:
    embedding_dim: int | None = None
    merged_data: list[dict[str, Any]] = []
    merged_rows: list[np.ndarray] = []
    id_to_index: dict[str, int] = {}
    merged_additional_data: dict[str, Any] = {}

    for source_dir in source_dirs:
        path = source_dir / file_name
        if not path.exists():
            continue
        current_dim, current_data, current_matrix, current_additional_data = _load_vdb(
            path
        )
        if embedding_dim is None:
            embedding_dim = current_dim
        elif embedding_dim != current_dim:
            raise ValueError(
                f"Embedding dimension mismatch for {file_name}: "
                f"{embedding_dim} != {current_dim} in {path}"
            )
        merged_additional_data.update(current_additional_data)

        for record, row in zip(current_data, current_matrix):
            record_id = str(record.get("__id__") or "")
            if not record_id:
                record_id = hashlib.md5(
                    np.asarray(row, dtype=np.float32).tobytes()
                ).hexdigest()
                record["__id__"] = record_id

            if record_id in id_to_index:
                index = id_to_index[record_id]
                merged_data[index] = dict(record)
                merged_rows[index] = np.asarray(row, dtype=np.float32)
                continue

            id_to_index[record_id] = len(merged_data)
            merged_data.append(dict(record))
            merged_rows.append(np.asarray(row, dtype=np.float32))

    return embedding_dim, merged_data, merged_rows, merged_additional_data


def _refresh_entities_vdb_from_graph(
    data: list[dict[str, Any]], graph: nx.Graph
) -> None:
    id_to_record = {str(record.get("__id__")): record for record in data}
    for node_id, attrs in graph.nodes(data=True):
        record_id = _compute_mdhash_id(str(node_id), prefix="ent-")
        record = id_to_record.get(record_id)
        if record is None:
            continue
        description = str(attrs.get("description") or "")
        source_id = str(attrs.get("source_chunk_ids") or attrs.get("source_id") or "")
        created_at = _coerce_int(record.get("__created_at__"), 0) or _coerce_int(
            attrs.get("created_at"), int(time.time())
        )
        record.clear()
        record.update(
            {
                "__id__": record_id,
                "__created_at__": created_at,
                "entity_name": str(node_id),
                "content": f"{node_id}\n{description}",
                "source_id": source_id,
                "source_chunk_ids": source_id,
                "file_path": str(attrs.get("file_path") or "unknown_source"),
            }
        )


def _refresh_relationships_vdb_from_graph(
    data: list[dict[str, Any]], graph: nx.Graph
) -> None:
    id_to_record = {str(record.get("__id__")): record for record in data}
    for src_id, tgt_id, attrs in graph.edges(data=True):
        source_id, target_id = sorted((str(src_id), str(tgt_id)))
        canonical_id = _compute_mdhash_id(source_id + target_id, prefix="rel-")
        reverse_id = _compute_mdhash_id(target_id + source_id, prefix="rel-")
        record = id_to_record.get(canonical_id) or id_to_record.get(reverse_id)
        if record is None:
            continue
        description = str(attrs.get("description") or "")
        keywords = str(attrs.get("keywords") or "")
        source_chunk_ids = str(
            attrs.get("source_chunk_ids") or attrs.get("source_id") or ""
        )
        created_at = _coerce_int(record.get("__created_at__"), 0) or _coerce_int(
            attrs.get("created_at"), int(time.time())
        )
        record.clear()
        record.update(
            {
                "__id__": canonical_id,
                "__created_at__": created_at,
                "src_id": source_id,
                "tgt_id": target_id,
                "content": f"{source_id}\t{target_id}\n{keywords}\n{description}",
                "source_id": source_chunk_ids,
                "source_chunk_ids": source_chunk_ids,
                "file_path": str(attrs.get("file_path") or "unknown_source"),
            }
        )


def _write_vdb(
    output_dir: Path,
    file_name: str,
    embedding_dim: int | None,
    data: list[dict[str, Any]],
    rows: list[np.ndarray],
    additional_data: dict[str, Any],
) -> None:
    if embedding_dim is None:
        return
    matrix = (
        np.vstack(rows).astype(np.float32)
        if rows
        else np.array([], dtype=np.float32).reshape(0, embedding_dim)
    )
    payload: dict[str, Any] = {
        "embedding_dim": embedding_dim,
        "data": data,
        "matrix": _encode_matrix(matrix),
    }
    if additional_data:
        payload["additional_data"] = additional_data
    with (output_dir / file_name).open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False)


def _open_sqlite_kv(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS kv_entries (
            key TEXT PRIMARY KEY,
            entry_json TEXT NOT NULL,
            create_time INTEGER NOT NULL DEFAULT 0,
            update_time INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_kv_entries_update_time ON kv_entries(update_time)"
    )
    conn.commit()
    return conn


def _read_sqlite_kv(path: Path) -> dict[str, tuple[dict[str, Any], int, int]]:
    if not path.exists():
        return {}
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT key, entry_json, create_time, update_time FROM kv_entries"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()

    result: dict[str, tuple[dict[str, Any], int, int]] = {}
    for row in rows:
        entry = json.loads(row["entry_json"])
        if not isinstance(entry, dict):
            entry = {"return": entry}
        entry.pop("_id", None)
        create_time = _coerce_int(
            row["create_time"], _coerce_int(entry.get("create_time"), 0)
        )
        update_time = _coerce_int(
            row["update_time"], _coerce_int(entry.get("update_time"), create_time)
        )
        entry["create_time"] = create_time
        entry["update_time"] = update_time
        result[str(row["key"])] = (entry, create_time, update_time)
    return result


def _merge_kv_namespace(
    source_dirs: list[Path], namespace: str
) -> dict[str, tuple[dict[str, Any], int, int]]:
    merged: dict[str, tuple[dict[str, Any], int, int]] = {}
    for source_dir in source_dirs:
        for key, (entry, create_time, update_time) in _read_sqlite_kv(
            source_dir / f"kv_store_{namespace}.sqlite"
        ).items():
            normalized_entry = dict(entry)
            if namespace == "text_chunks":
                normalized_entry.setdefault("llm_cache_list", [])
            merged[key] = (normalized_entry, create_time, update_time)
    return merged


def _write_kv_namespace(
    output_dir: Path,
    namespace: str,
    rows: dict[str, tuple[dict[str, Any], int, int]],
) -> None:
    conn = _open_sqlite_kv(output_dir / f"kv_store_{namespace}.sqlite")
    conn.executemany(
        """
        INSERT INTO kv_entries (key, entry_json, create_time, update_time)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            entry_json = excluded.entry_json,
            create_time = excluded.create_time,
            update_time = excluded.update_time
        """,
        [
            (
                key,
                json.dumps(entry, ensure_ascii=False, default=str),
                create_time,
                update_time,
            )
            for key, (entry, create_time, update_time) in rows.items()
        ],
    )
    conn.commit()
    conn.close()


def _merge_doc_status(source_dirs: list[Path]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for source_dir in source_dirs:
        path = source_dir / DOC_STATUS_FILE_NAME
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as file:
            payload = json.load(file)
        for key, value in payload.items():
            entry = dict(value) if isinstance(value, dict) else {"return": value}
            entry.setdefault("chunks_list", [])
            merged[str(key)] = entry
    return merged


def _write_index_metadata(output_dir: Path) -> None:
    now = int(time.time())
    rows = {
        INDEX_METADATA_KEY: (
            {
                "corpus_revision": 1,
                "index_digest": None,
                "updated_at": now,
                "last_reason": "merged_kg_projects",
                "affected_chunk_ids": [],
                "create_time": now,
                "update_time": now,
            },
            now,
            now,
        )
    }
    _write_kv_namespace(output_dir, INDEX_METADATA_NAMESPACE, rows)


def _write_empty_query_cache(output_dir: Path) -> None:
    conn = sqlite3.connect(output_dir / f"kv_store_{QUERY_CACHE_NAMESPACE}.sqlite")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS query_cache_entries (
            key TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            cache_type TEXT NOT NULL,
            args_hash TEXT NOT NULL,
            entry_json TEXT NOT NULL,
            corpus_revision INTEGER NOT NULL DEFAULT 0,
            expires_at INTEGER,
            created_at INTEGER NOT NULL DEFAULT 0,
            last_accessed_at INTEGER NOT NULL DEFAULT 0,
            access_count INTEGER NOT NULL DEFAULT 0,
            is_query_cache INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_query_cache_mode_type ON query_cache_entries(mode, cache_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_query_cache_revision ON query_cache_entries(corpus_revision)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_query_cache_expires_at ON query_cache_entries(expires_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_query_cache_last_accessed_at ON query_cache_entries(last_accessed_at)"
    )
    conn.commit()
    conn.close()


def _prepare_output_dir(output_dir: Path, source_dirs: list[Path], overwrite: bool, dry_run: bool) -> None:
    resolved_output = output_dir.resolve()
    for source_dir in source_dirs:
        resolved_source = source_dir.resolve()
        if (
            resolved_output == resolved_source
            or resolved_output in resolved_source.parents
            or resolved_source in resolved_output.parents
        ):
            raise ValueError("Output directory must not overlap source project dirs")

    if dry_run:
        return

    if output_dir.exists():
        if overwrite:
            shutil.rmtree(output_dir)
        elif any(output_dir.iterdir()):
            raise FileExistsError(f"Output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)


def merge_projects(
    source_dirs: list[str | Path],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> MergeStats:
    sources = [Path(source_dir).expanduser().resolve() for source_dir in source_dirs]
    if len(sources) < 1:
        raise ValueError("At least one source project dir is required")
    for source_dir in sources:
        if not source_dir.is_dir():
            raise FileNotFoundError(f"Source project dir does not exist: {source_dir}")

    output_path = Path(output_dir).expanduser().resolve()
    _prepare_output_dir(output_path, sources, overwrite=overwrite, dry_run=dry_run)

    stats = MergeStats(sources=len(sources), dry_run=dry_run, output_dir=str(output_path))
    graph = _merge_graphs(sources, stats)

    vdb_outputs: dict[str, tuple[int | None, list[dict[str, Any]], list[np.ndarray], dict[str, Any]]] = {}
    for file_name in VDB_FILE_NAMES:
        embedding_dim, data, rows, additional_data = _merge_vdbs(sources, file_name)
        if file_name == "vdb_entities.json":
            _refresh_entities_vdb_from_graph(data, graph)
        elif file_name == "vdb_relationships.json":
            _refresh_relationships_vdb_from_graph(data, graph)
        stats.vdb_records[file_name] = len(data)
        vdb_outputs[file_name] = (embedding_dim, data, rows, additional_data)

    kv_outputs: dict[str, dict[str, tuple[dict[str, Any], int, int]]] = {}
    for namespace in SQLITE_KV_NAMESPACES:
        rows = _merge_kv_namespace(sources, namespace)
        stats.kv_records[namespace] = len(rows)
        kv_outputs[namespace] = rows

    doc_status = _merge_doc_status(sources)
    stats.doc_status_records = len(doc_status)

    if dry_run:
        return stats

    nx.write_graphml(graph, output_path / GRAPH_FILE_NAME)

    for file_name, (embedding_dim, data, rows, additional_data) in vdb_outputs.items():
        _write_vdb(output_path, file_name, embedding_dim, data, rows, additional_data)

    for namespace, rows in kv_outputs.items():
        _write_kv_namespace(output_path, namespace, rows)

    with (output_path / DOC_STATUS_FILE_NAME).open("w", encoding="utf-8") as file:
        json.dump(doc_status, file, ensure_ascii=False, indent=2)

    _write_index_metadata(output_path)
    _write_empty_query_cache(output_path)
    return stats


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge multiple independently built Ragent KG project dirs."
    )
    parser.add_argument(
        "sources",
        nargs="+",
        help="Source KG project directories to merge, in upsert precedence order.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Final project_dir to write.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the output directory if it already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute merge statistics without writing the output directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    stats = merge_projects(
        args.sources,
        args.output,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    print(json.dumps(asdict(stats), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
