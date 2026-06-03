from __future__ import annotations

import asyncio
import json
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Iterable, Iterator
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ragent.base import BaseGraphStorage, BaseKVStorage, BaseVectorStorage, DocStatus
from ragent.operate import merge_nodes_and_edges
from ragent.utils import clean_text, compute_mdhash_id, get_content_summary


RAW_MERGE_UNIT_SCHEMA_VERSION = 1


@dataclass
class RawMergeUnit:
    """Serializable extraction output that can be replayed into final KG storage."""

    doc_id: str
    content: str
    chunks: dict[str, dict[str, Any]]
    chunk_results: list[Any]
    file_path: str = "unknown_source"
    doc_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    vector_chunks: dict[str, dict[str, Any]] | None = None
    source_group_key: str | None = None
    content_summary: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class OfflineReplayStats:
    units_seen: int = 0
    units_replayed: int = 0
    duplicate_docs_skipped: int = 0
    groups_replayed: int = 0
    groups_failed: int = 0
    groups_rolled_back: int = 0
    docs_written: int = 0
    chunks_written: int = 0
    chunk_result_groups: int = 0
    units_failed: int = 0


def _edge_key_to_pair(edge_key: Any) -> tuple[str, str]:
    if isinstance(edge_key, str):
        try:
            parsed = json.loads(edge_key)
        except json.JSONDecodeError as exc:
            raise ValueError(f"String edge key is not JSON encoded: {edge_key!r}") from exc
        edge_key = parsed

    if not isinstance(edge_key, (list, tuple)) or len(edge_key) != 2:
        raise ValueError(f"Edge key must be a 2-item tuple/list, got: {edge_key!r}")
    return str(edge_key[0]), str(edge_key[1])


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if hasattr(value, "tolist"):
        return _json_ready(value.tolist())
    if hasattr(value, "item"):
        return value.item()
    return value


def encode_chunk_results(chunk_results: list[Any]) -> list[dict[str, Any]]:
    encoded: list[dict[str, Any]] = []
    for chunk_result in chunk_results:
        if not isinstance(chunk_result, (list, tuple)) or len(chunk_result) != 2:
            raise ValueError(
                "Each chunk result must be a (maybe_nodes, maybe_edges) pair."
            )
        maybe_nodes, maybe_edges = chunk_result
        edges: list[dict[str, Any]] = []
        for edge_key, records in dict(maybe_edges).items():
            src_id, tgt_id = _edge_key_to_pair(edge_key)
            edges.append(
                {
                    "src_id": src_id,
                    "tgt_id": tgt_id,
                    "records": _json_ready(list(records)),
                }
            )
        encoded.append(
            {
                "nodes": {
                    str(entity_name): _json_ready(list(records))
                    for entity_name, records in dict(maybe_nodes).items()
                },
                "edges": edges,
            }
        )
    return encoded


def decode_chunk_results(
    payload: list[Any],
) -> list[tuple[dict[str, Any], dict[tuple[str, str], Any]]]:
    decoded: list[tuple[dict[str, Any], dict[tuple[str, str], Any]]] = []
    for item in payload:
        if isinstance(item, dict) and "nodes" in item and "edges" in item:
            maybe_nodes = {
                str(entity_name): list(records)
                for entity_name, records in dict(item["nodes"]).items()
            }
            maybe_edges: dict[tuple[str, str], Any] = {}
            for edge_item in item["edges"]:
                src_id = str(edge_item["src_id"])
                tgt_id = str(edge_item["tgt_id"])
                maybe_edges[(src_id, tgt_id)] = list(edge_item.get("records") or [])
            decoded.append((maybe_nodes, maybe_edges))
            continue

        if isinstance(item, (list, tuple)) and len(item) == 2:
            maybe_nodes, maybe_edges = item
            normalized_edges = {
                _edge_key_to_pair(edge_key): list(records)
                for edge_key, records in dict(maybe_edges).items()
            }
            decoded.append((dict(maybe_nodes), normalized_edges))
            continue

        raise ValueError(f"Unsupported chunk result payload: {item!r}")
    return decoded


def raw_merge_unit_to_json_obj(unit: RawMergeUnit) -> dict[str, Any]:
    payload = _json_ready(asdict(unit))
    payload["schema_version"] = RAW_MERGE_UNIT_SCHEMA_VERSION
    payload["chunk_results"] = encode_chunk_results(unit.chunk_results)
    return payload


def raw_merge_unit_from_json_obj(payload: dict[str, Any]) -> RawMergeUnit:
    schema_version = int(payload.get("schema_version") or 1)
    if schema_version != RAW_MERGE_UNIT_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported raw merge unit schema version: "
            f"{schema_version}. Expected {RAW_MERGE_UNIT_SCHEMA_VERSION}."
        )

    return RawMergeUnit(
        doc_id=str(payload["doc_id"]),
        content=str(payload.get("content") or ""),
        chunks={
            str(chunk_id): dict(chunk)
            for chunk_id, chunk in dict(payload.get("chunks") or {}).items()
        },
        chunk_results=decode_chunk_results(list(payload.get("chunk_results") or [])),
        file_path=str(payload.get("file_path") or "unknown_source"),
        doc_name=payload.get("doc_name"),
        metadata=dict(payload.get("metadata") or {}),
        vector_chunks=(
            {
                str(chunk_id): dict(chunk)
                for chunk_id, chunk in dict(payload["vector_chunks"]).items()
            }
            if payload.get("vector_chunks") is not None
            else None
        ),
        source_group_key=payload.get("source_group_key"),
        content_summary=payload.get("content_summary"),
        created_at=payload.get("created_at"),
        updated_at=payload.get("updated_at"),
    )


def write_raw_merge_units_jsonl(
    units: Iterable[RawMergeUnit],
    path: str | Path,
) -> int:
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as file:
        for unit in units:
            file.write(
                json.dumps(raw_merge_unit_to_json_obj(unit), ensure_ascii=False)
                + "\n"
            )
            count += 1
    return count


def iter_raw_merge_unit_jsonl_paths(
    paths: Iterable[str | Path] | str | Path,
) -> Iterator[Path]:
    if isinstance(paths, (str, Path)):
        path_items: list[str | Path] = [paths]
    else:
        path_items = list(paths)

    for path_item in path_items:
        path = Path(path_item).expanduser().resolve()
        if path.is_dir():
            yield from sorted(path.glob("*.jsonl"))
            continue
        yield path


def iter_raw_merge_units_jsonl(paths: Iterable[str | Path] | str | Path) -> Iterator[RawMergeUnit]:
    for jsonl_path in iter_raw_merge_unit_jsonl_paths(paths):
        with jsonl_path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON in {jsonl_path}:{line_number}: {exc}"
                    ) from exc
                yield raw_merge_unit_from_json_obj(payload)


def raw_merge_unit_source_group_key(unit: RawMergeUnit) -> str:
    return str(unit.source_group_key or unit.file_path or unit.doc_id)


def iter_raw_merge_unit_groups_jsonl(
    paths: Iterable[str | Path] | str | Path,
    *,
    require_contiguous_source_groups: bool = True,
) -> Iterator[tuple[str, list[RawMergeUnit]]]:
    """Yield raw units grouped by contiguous source_group_key in JSONL order."""

    current_key: str | None = None
    current_units: list[RawMergeUnit] = []
    closed_keys: set[str] = set()

    for unit in iter_raw_merge_units_jsonl(paths):
        source_group_key = raw_merge_unit_source_group_key(unit)
        if current_key is None:
            current_key = source_group_key
            current_units = [unit]
            continue

        if source_group_key == current_key:
            current_units.append(unit)
            continue

        closed_keys.add(current_key)
        yield current_key, current_units

        if require_contiguous_source_groups and source_group_key in closed_keys:
            raise ValueError(
                "Raw merge units for source group "
                f"{source_group_key!r} are not contiguous in JSONL input order. "
                "Sort raw unit files and lines so each source_group_key appears in "
                "one contiguous block, or use the in-memory replay path for small "
                "debug datasets."
            )

        current_key = source_group_key
        current_units = [unit]

    if current_key is not None:
        yield current_key, current_units


def scan_raw_merge_units_jsonl(
    paths: Iterable[str | Path] | str | Path,
    *,
    require_contiguous_source_groups: bool = True,
) -> tuple[int, int]:
    """Return (units_seen, group_count) without retaining all raw units."""

    units_seen = 0
    group_count = 0
    for _source_group_key, group_units in iter_raw_merge_unit_groups_jsonl(
        paths,
        require_contiguous_source_groups=require_contiguous_source_groups,
    ):
        group_count += 1
        units_seen += len(group_units)
    return units_seen, group_count


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_chunks(unit: RawMergeUnit) -> dict[str, dict[str, Any]]:
    chunks: dict[str, dict[str, Any]] = {}
    for chunk_id, chunk in unit.chunks.items():
        chunk_record = dict(chunk)
        chunk_record.setdefault("full_doc_id", unit.doc_id)
        chunk_record.setdefault("file_path", unit.file_path)
        chunk_record.setdefault("llm_cache_list", [])
        chunks[str(chunk_id)] = chunk_record
    return chunks


def _normalize_vector_chunks(
    unit: RawMergeUnit,
    chunks: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if unit.vector_chunks is None:
        return chunks

    vector_chunks: dict[str, dict[str, Any]] = {}
    for chunk_id, chunk in unit.vector_chunks.items():
        base_chunk = chunks.get(chunk_id, {})
        vector_chunk = {**base_chunk, **dict(chunk)}
        vector_chunk.setdefault("full_doc_id", unit.doc_id)
        vector_chunk.setdefault("file_path", unit.file_path)
        vector_chunk.setdefault("llm_cache_list", [])
        vector_chunks[str(chunk_id)] = vector_chunk
    return vector_chunks


def _build_doc_status_record(
    unit: RawMergeUnit,
    *,
    chunks: dict[str, dict[str, Any]],
    status: DocStatus,
    timestamp: str,
    error: str | None = None,
) -> dict[str, dict[str, Any]]:
    record: dict[str, Any] = {
        "status": status,
        "content": unit.content,
        "content_summary": unit.content_summary or get_content_summary(unit.content),
        "content_length": len(unit.content),
        "created_at": unit.created_at or timestamp,
        "updated_at": unit.updated_at or timestamp,
        "file_path": unit.file_path,
        "metadata": dict(unit.metadata or {}),
        "chunks_count": len(chunks),
        "chunks_list": list(chunks.keys()),
    }
    if error is not None:
        record["error"] = error
    return {unit.doc_id: record}


def _group_units_by_source(
    units: Iterable[RawMergeUnit],
) -> OrderedDict[str, list[RawMergeUnit]]:
    groups: OrderedDict[str, list[RawMergeUnit]] = OrderedDict()
    for unit in units:
        source_group_key = raw_merge_unit_source_group_key(unit)
        groups.setdefault(source_group_key, []).append(unit)
    return groups


async def _doc_already_seen(
    doc_status: BaseKVStorage,
    seen_doc_ids: set[str],
    doc_id: str,
) -> bool:
    if doc_id in seen_doc_ids:
        return True
    get_by_id = getattr(doc_status, "get_by_id", None)
    if callable(get_by_id):
        existing = await get_by_id(doc_id)
        if existing:
            if not isinstance(existing, dict):
                return True
            status = existing.get("status")
            if status is None:
                return True
            return status == DocStatus.PROCESSED or status == DocStatus.PROCESSED.value
    return False


def _collect_touched_graph_keys(
    chunk_results: list[Any],
) -> tuple[list[str], list[tuple[str, str]]]:
    node_ids: set[str] = set()
    edge_keys: set[tuple[str, str]] = set()
    for maybe_nodes, maybe_edges in chunk_results:
        for entity_name in dict(maybe_nodes):
            node_ids.add(str(entity_name))
        for edge_key in dict(maybe_edges):
            src_id, tgt_id = _edge_key_to_pair(edge_key)
            node_ids.add(src_id)
            node_ids.add(tgt_id)
            if src_id != tgt_id:
                edge_keys.add(tuple(sorted((src_id, tgt_id))))
    return sorted(node_ids), sorted(edge_keys)


def _sanitize_vector_record_for_upsert(record: dict[str, Any]) -> dict[str, Any]:
    restored = deepcopy(record)
    if "embeddings" not in restored and "__vector__" in restored:
        restored["embeddings"] = restored["__vector__"]
    for internal_key in (
        "__id__",
        "__metrics__",
        "__created_at__",
        "__vector__",
        "id",
        "distance",
        "created_at",
    ):
        restored.pop(internal_key, None)
    return restored


async def _snapshot_vector_records_from_client_storage(
    vector_storage: BaseVectorStorage,
    ids: set[str],
) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}

    try:
        client_storage = await vector_storage.client_storage  # type: ignore[attr-defined]
    except (AttributeError, NotImplementedError):
        return {}

    if not isinstance(client_storage, dict):
        return {}
    data = client_storage.get("data")
    matrix = client_storage.get("matrix")
    if not isinstance(data, list) or matrix is None:
        return {}

    snapshots: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(data):
        if not isinstance(record, dict):
            continue
        record_id = record.get("__id__")
        if record_id not in ids:
            continue
        restored = deepcopy(record)
        try:
            vector = matrix[index]
        except (IndexError, TypeError):
            continue
        restored["__vector__"] = vector.tolist() if hasattr(vector, "tolist") else vector
        snapshots[str(record_id)] = restored
    return snapshots


async def _snapshot_vector_records(
    vector_storage: BaseVectorStorage,
    ids: list[str],
) -> dict[str, dict[str, Any] | None]:
    direct_snapshots = await _snapshot_vector_records_from_client_storage(
        vector_storage,
        set(ids),
    )
    snapshots: dict[str, dict[str, Any] | None] = {}
    for record_id in ids:
        if record_id in direct_snapshots:
            snapshots[record_id] = direct_snapshots[record_id]
            continue
        record = await vector_storage.get_by_id(record_id)
        snapshots[record_id] = deepcopy(record) if record else None
    return snapshots


async def _restore_vector_records(
    vector_storage: BaseVectorStorage,
    snapshots: dict[str, dict[str, Any] | None],
) -> None:
    if not snapshots:
        return

    await vector_storage.delete(list(snapshots))
    restore_payload = {
        record_id: _sanitize_vector_record_for_upsert(record)
        for record_id, record in snapshots.items()
        if record is not None
    }
    if restore_payload:
        await vector_storage.upsert(restore_payload)


async def _snapshot_merge_state(
    chunk_results: list[Any],
    *,
    knowledge_graph_inst: BaseGraphStorage,
    entity_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
) -> dict[str, Any]:
    node_ids, edge_keys = _collect_touched_graph_keys(chunk_results)
    entity_vector_ids = [
        compute_mdhash_id(node_id, prefix="ent-") for node_id in node_ids
    ]
    relation_vector_ids = [
        compute_mdhash_id(src_id + tgt_id, prefix="rel-")
        for src_id, tgt_id in edge_keys
    ]

    return {
        "nodes": {
            node_id: deepcopy(await knowledge_graph_inst.get_node(node_id))
            for node_id in node_ids
        },
        "edges": {
            edge_key: deepcopy(await knowledge_graph_inst.get_edge(*edge_key))
            for edge_key in edge_keys
        },
        "entity_vdb": await _snapshot_vector_records(entity_vdb, entity_vector_ids),
        "relationships_vdb": await _snapshot_vector_records(
            relationships_vdb, relation_vector_ids
        ),
    }


async def _restore_merge_state(
    snapshot: dict[str, Any] | None,
    *,
    knowledge_graph_inst: BaseGraphStorage,
    entity_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
) -> None:
    if not snapshot:
        return

    edges_to_remove = [
        edge_key for edge_key, edge_data in snapshot["edges"].items() if edge_data is None
    ]
    nodes_to_remove = [
        node_id for node_id, node_data in snapshot["nodes"].items() if node_data is None
    ]

    if edges_to_remove:
        await knowledge_graph_inst.remove_edges(edges_to_remove)
    for edge_key, edge_data in snapshot["edges"].items():
        if edge_data is not None:
            await knowledge_graph_inst.upsert_edge(edge_key[0], edge_key[1], edge_data)

    if nodes_to_remove:
        await knowledge_graph_inst.remove_nodes(nodes_to_remove)
    for node_id, node_data in snapshot["nodes"].items():
        if node_data is not None:
            await knowledge_graph_inst.upsert_node(node_id, node_data)

    await _restore_vector_records(entity_vdb, snapshot["entity_vdb"])
    await _restore_vector_records(relationships_vdb, snapshot["relationships_vdb"])


async def _rollback_staged_replay_group(
    *,
    full_docs: BaseKVStorage,
    text_chunks: BaseKVStorage,
    chunks_vdb: BaseVectorStorage,
    doc_status: BaseKVStorage,
    knowledge_graph_inst: BaseGraphStorage,
    entity_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    merge_snapshot: dict[str, Any] | None,
    replay_units: list[RawMergeUnit],
    normalized_chunks_by_doc: dict[str, dict[str, dict[str, Any]]],
    error: Exception,
) -> None:
    doc_ids = [unit.doc_id for unit in replay_units]
    chunk_ids = [
        chunk_id
        for chunks in normalized_chunks_by_doc.values()
        for chunk_id in chunks
    ]

    cleanup_tasks = []
    if doc_ids:
        cleanup_tasks.append(full_docs.delete(doc_ids))
    if chunk_ids:
        cleanup_tasks.append(text_chunks.delete(chunk_ids))
        cleanup_tasks.append(chunks_vdb.delete(chunk_ids))
    if cleanup_tasks:
        await asyncio.gather(*cleanup_tasks)

    await _restore_merge_state(
        merge_snapshot,
        knowledge_graph_inst=knowledge_graph_inst,
        entity_vdb=entity_vdb,
        relationships_vdb=relationships_vdb,
    )

    failed_timestamp = _utc_now_iso()
    failed_status_payload: dict[str, dict[str, Any]] = {}
    for unit in replay_units:
        failed_status_payload.update(
            _build_doc_status_record(
                unit,
                chunks=normalized_chunks_by_doc.get(unit.doc_id, {}),
                status=DocStatus.FAILED,
                timestamp=failed_timestamp,
                error=str(error),
            )
        )
    if failed_status_payload:
        await doc_status.upsert(failed_status_payload)


async def build_raw_merge_unit_from_text(
    rag: Any,
    *,
    text: str,
    doc_name: str,
    file_path: str,
    doc_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    source_group_key: str | None = None,
    split_by_character: str | None = None,
    split_by_character_only: bool = False,
    pipeline_status: dict[str, Any] | None = None,
    pipeline_status_lock: asyncio.Lock | None = None,
    clean_input: bool = True,
) -> RawMergeUnit:
    """Run chunk embedding and entity extraction, returning replayable raw output."""

    content = clean_text(text) if clean_input else text
    resolved_doc_id = doc_id or compute_mdhash_id(content, prefix="doc-")
    resolved_metadata = dict(metadata or {})
    resolved_metadata.setdefault("file_path", file_path)

    try:
        raw_chunks = rag.chunking_func(
            doc_name,
            rag.tokenizer,
            content,
            doc_metadata=resolved_metadata,
            split_by_character=split_by_character,
            split_by_character_only=split_by_character_only,
            overlap_token_size=rag.chunk_overlap_token_size,
            max_token_size=rag.chunk_token_size,
        )
    except TypeError:
        raw_chunks = rag.chunking_func(
            doc_name,
            rag.tokenizer,
            content,
            split_by_character,
            split_by_character_only,
            rag.chunk_overlap_token_size,
            rag.chunk_token_size,
        )

    chunks = {
        compute_mdhash_id(chunk["content"], prefix="chunk-"): {
            **chunk,
            "full_doc_id": resolved_doc_id,
            "file_path": file_path,
            "llm_cache_list": [],
        }
        for chunk in raw_chunks
    }
    vector_chunks, _chunk_embeddings = await rag._build_vector_chunks(chunks)

    if pipeline_status is None:
        pipeline_status = {"latest_message": "", "history_messages": []}
    pipeline_status.setdefault("history_messages", [])
    if pipeline_status_lock is None:
        pipeline_status_lock = asyncio.Lock()

    # Entity extraction reads chunk text from storage when recording cache keys.
    await rag.text_chunks.upsert(chunks)
    chunk_results = await rag._process_entity_relation_graph(
        vector_chunks or chunks,
        pipeline_status,
        pipeline_status_lock,
    )

    return RawMergeUnit(
        doc_id=resolved_doc_id,
        doc_name=doc_name,
        file_path=file_path,
        source_group_key=source_group_key,
        content=content,
        content_summary=get_content_summary(content),
        metadata=resolved_metadata,
        chunks=chunks,
        vector_chunks=vector_chunks,
        chunk_results=chunk_results,
    )


async def replay_raw_merge_unit_groups(
    unit_groups: Iterable[tuple[str, list[RawMergeUnit]]],
    *,
    full_docs: BaseKVStorage,
    text_chunks: BaseKVStorage,
    chunks_vdb: BaseVectorStorage,
    doc_status: BaseKVStorage,
    knowledge_graph_inst: BaseGraphStorage,
    entity_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    global_config: dict[str, Any],
    pipeline_status: dict[str, Any] | None = None,
    pipeline_status_lock: asyncio.Lock | None = None,
    llm_response_cache: BaseKVStorage | None = None,
    group_done_callback: Callable[[list[str]], Awaitable[None]] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    total_groups: int | None = None,
    units_seen: int | None = None,
    rollback_staged_data_on_error: bool = True,
    continue_on_group_error: bool = False,
) -> OfflineReplayStats:
    """Replay grouped raw extraction units through the online graph merge function."""

    stats = OfflineReplayStats()
    if units_seen is not None:
        stats.units_seen = units_seen

    if pipeline_status is None:
        pipeline_status = {"latest_message": "", "history_messages": []}
    pipeline_status.setdefault("history_messages", [])
    if pipeline_status_lock is None:
        pipeline_status_lock = asyncio.Lock()

    seen_doc_ids: set[str] = set()
    for group_index, (source_group_key, group_units) in enumerate(unit_groups, start=1):
        if units_seen is None:
            stats.units_seen += len(group_units)

        replay_units: list[RawMergeUnit] = []
        for unit in group_units:
            if await _doc_already_seen(doc_status, seen_doc_ids, unit.doc_id):
                stats.duplicate_docs_skipped += 1
                continue
            replay_units.append(unit)
            seen_doc_ids.add(unit.doc_id)

        if not replay_units:
            continue

        normalized_chunks_by_doc: dict[str, dict[str, dict[str, Any]]] = {}
        affected_chunk_ids: list[str] = []
        full_doc_payload: dict[str, dict[str, Any]] = {}
        text_chunk_payload: dict[str, dict[str, Any]] = {}
        chunk_vdb_payload: dict[str, dict[str, Any]] = {}
        processing_status_payload: dict[str, dict[str, Any]] = {}
        combined_chunk_results: list[Any] = []
        merge_snapshot: dict[str, Any] | None = None
        timestamp = _utc_now_iso()

        try:
            for unit in replay_units:
                chunks = _normalize_chunks(unit)
                vector_chunks = _normalize_vector_chunks(unit, chunks)
                normalized_chunks_by_doc[unit.doc_id] = chunks
                affected_chunk_ids.extend(chunks.keys())
                full_doc_payload[unit.doc_id] = {"content": unit.content}
                text_chunk_payload.update(chunks)
                chunk_vdb_payload.update(vector_chunks)
                processing_status_payload.update(
                    _build_doc_status_record(
                        unit,
                        chunks=chunks,
                        status=DocStatus.PROCESSING,
                        timestamp=timestamp,
                    )
                )

            async with pipeline_status_lock:
                total_groups_for_log = total_groups if total_groups is not None else 0
                log_message = (
                    f"Offline replay stage {group_index}/{total_groups_for_log}: "
                    f"{source_group_key}"
                )
                pipeline_status["latest_message"] = log_message
                pipeline_status["history_messages"].append(log_message)

            await asyncio.gather(
                doc_status.upsert(processing_status_payload),
                chunks_vdb.upsert(chunk_vdb_payload),
                full_docs.upsert(full_doc_payload),
                text_chunks.upsert(text_chunk_payload),
            )

            combined_chunk_results = [
                chunk_result
                for unit in replay_units
                for chunk_result in unit.chunk_results
            ]
            if rollback_staged_data_on_error:
                merge_snapshot = await _snapshot_merge_state(
                    combined_chunk_results,
                    knowledge_graph_inst=knowledge_graph_inst,
                    entity_vdb=entity_vdb,
                    relationships_vdb=relationships_vdb,
                )

            await merge_nodes_and_edges(
                chunk_results=combined_chunk_results,
                knowledge_graph_inst=knowledge_graph_inst,
                entity_vdb=entity_vdb,
                relationships_vdb=relationships_vdb,
                global_config=global_config,
                pipeline_status=pipeline_status,
                pipeline_status_lock=pipeline_status_lock,
                llm_response_cache=llm_response_cache,
                current_file_number=group_index,
                total_files=total_groups if total_groups is not None else 0,
                file_path=source_group_key,
                progress_callback=progress_callback,
            )

            processed_status_payload: dict[str, dict[str, Any]] = {}
            processed_timestamp = _utc_now_iso()
            for unit in replay_units:
                processed_status_payload.update(
                    _build_doc_status_record(
                        unit,
                        chunks=normalized_chunks_by_doc[unit.doc_id],
                        status=DocStatus.PROCESSED,
                        timestamp=processed_timestamp,
                    )
                )
            await doc_status.upsert(processed_status_payload)

            stats.groups_replayed += 1
            stats.units_replayed += len(replay_units)
            stats.docs_written += len(full_doc_payload)
            stats.chunks_written += len(text_chunk_payload)
            stats.chunk_result_groups += len(combined_chunk_results)

            if group_done_callback is not None:
                await group_done_callback(affected_chunk_ids)
        except Exception as exc:
            stats.groups_failed += 1
            stats.units_failed += len(replay_units)
            error_message = (
                f"Offline replay failed in source group {group_index}/"
                f"{total_groups if total_groups is not None else 0}: "
                f"{source_group_key}: {exc}"
            )
            async with pipeline_status_lock:
                pipeline_status["latest_message"] = error_message
                pipeline_status["history_messages"].append(error_message)

            if rollback_staged_data_on_error:
                await _rollback_staged_replay_group(
                    full_docs=full_docs,
                    text_chunks=text_chunks,
                    chunks_vdb=chunks_vdb,
                    doc_status=doc_status,
                    knowledge_graph_inst=knowledge_graph_inst,
                    entity_vdb=entity_vdb,
                    relationships_vdb=relationships_vdb,
                    merge_snapshot=merge_snapshot,
                    replay_units=replay_units,
                    normalized_chunks_by_doc=normalized_chunks_by_doc,
                    error=exc,
                )
                stats.groups_rolled_back += 1

            if llm_response_cache is not None:
                await llm_response_cache.index_done_callback()

            if continue_on_group_error:
                continue
            raise

    return stats


async def replay_raw_merge_units(
    units: Iterable[RawMergeUnit],
    *,
    full_docs: BaseKVStorage,
    text_chunks: BaseKVStorage,
    chunks_vdb: BaseVectorStorage,
    doc_status: BaseKVStorage,
    knowledge_graph_inst: BaseGraphStorage,
    entity_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    global_config: dict[str, Any],
    pipeline_status: dict[str, Any] | None = None,
    pipeline_status_lock: asyncio.Lock | None = None,
    llm_response_cache: BaseKVStorage | None = None,
    group_done_callback: Callable[[list[str]], Awaitable[None]] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    rollback_staged_data_on_error: bool = True,
    continue_on_group_error: bool = False,
) -> OfflineReplayStats:
    """Replay raw extraction units, grouping by source_group_key in memory."""

    groups = _group_units_by_source(units)
    units_seen = sum(len(group_units) for group_units in groups.values())
    return await replay_raw_merge_unit_groups(
        groups.items(),
        full_docs=full_docs,
        text_chunks=text_chunks,
        chunks_vdb=chunks_vdb,
        doc_status=doc_status,
        knowledge_graph_inst=knowledge_graph_inst,
        entity_vdb=entity_vdb,
        relationships_vdb=relationships_vdb,
        global_config=global_config,
        pipeline_status=pipeline_status,
        pipeline_status_lock=pipeline_status_lock,
        llm_response_cache=llm_response_cache,
        group_done_callback=group_done_callback,
        progress_callback=progress_callback,
        total_groups=len(groups),
        units_seen=units_seen,
        rollback_staged_data_on_error=rollback_staged_data_on_error,
        continue_on_group_error=continue_on_group_error,
    )


async def replay_raw_merge_units_jsonl(
    paths: Iterable[str | Path] | str | Path,
    *,
    full_docs: BaseKVStorage,
    text_chunks: BaseKVStorage,
    chunks_vdb: BaseVectorStorage,
    doc_status: BaseKVStorage,
    knowledge_graph_inst: BaseGraphStorage,
    entity_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    global_config: dict[str, Any],
    pipeline_status: dict[str, Any] | None = None,
    pipeline_status_lock: asyncio.Lock | None = None,
    llm_response_cache: BaseKVStorage | None = None,
    group_done_callback: Callable[[list[str]], Awaitable[None]] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    require_contiguous_source_groups: bool = True,
    rollback_staged_data_on_error: bool = True,
    continue_on_group_error: bool = False,
) -> OfflineReplayStats:
    """Replay raw unit JSONL without materializing the entire input set."""

    jsonl_paths = list(iter_raw_merge_unit_jsonl_paths(paths))
    units_seen, total_groups = scan_raw_merge_units_jsonl(
        jsonl_paths,
        require_contiguous_source_groups=require_contiguous_source_groups,
    )
    return await replay_raw_merge_unit_groups(
        iter_raw_merge_unit_groups_jsonl(
            jsonl_paths,
            require_contiguous_source_groups=require_contiguous_source_groups,
        ),
        full_docs=full_docs,
        text_chunks=text_chunks,
        chunks_vdb=chunks_vdb,
        doc_status=doc_status,
        knowledge_graph_inst=knowledge_graph_inst,
        entity_vdb=entity_vdb,
        relationships_vdb=relationships_vdb,
        global_config=global_config,
        pipeline_status=pipeline_status,
        pipeline_status_lock=pipeline_status_lock,
        llm_response_cache=llm_response_cache,
        group_done_callback=group_done_callback,
        progress_callback=progress_callback,
        total_groups=total_groups,
        units_seen=units_seen,
        rollback_staged_data_on_error=rollback_staged_data_on_error,
        continue_on_group_error=continue_on_group_error,
    )


async def replay_raw_merge_units_to_rag(
    rag: Any,
    units: Iterable[RawMergeUnit],
    *,
    pipeline_status: dict[str, Any] | None = None,
    pipeline_status_lock: asyncio.Lock | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    rollback_staged_data_on_error: bool = True,
    continue_on_group_error: bool = False,
) -> OfflineReplayStats:
    if pipeline_status is None:
        pipeline_status = {"latest_message": "", "history_messages": []}
    if pipeline_status_lock is None:
        pipeline_status_lock = asyncio.Lock()

    async def _persist_group(affected_chunk_ids: list[str]) -> None:
        await rag._insert_done(pipeline_status, pipeline_status_lock)
        await rag._try_bump_corpus_revision(
            "offline_replay",
            affected_chunk_ids=affected_chunk_ids,
        )

    if hasattr(rag, "_build_runtime_global_config"):
        global_config = await rag._build_runtime_global_config()
    else:
        global_config = asdict(rag)

    return await replay_raw_merge_units(
        units,
        full_docs=rag.full_docs,
        text_chunks=rag.text_chunks,
        chunks_vdb=rag.chunks_vdb,
        doc_status=rag.doc_status,
        knowledge_graph_inst=rag.chunk_entity_relation_graph,
        entity_vdb=rag.entities_vdb,
        relationships_vdb=rag.relationships_vdb,
        global_config=global_config,
        pipeline_status=pipeline_status,
        pipeline_status_lock=pipeline_status_lock,
        llm_response_cache=rag.llm_response_cache,
        group_done_callback=_persist_group,
        progress_callback=progress_callback,
        rollback_staged_data_on_error=rollback_staged_data_on_error,
        continue_on_group_error=continue_on_group_error,
    )


async def replay_raw_merge_units_jsonl_to_rag(
    rag: Any,
    paths: Iterable[str | Path] | str | Path,
    *,
    pipeline_status: dict[str, Any] | None = None,
    pipeline_status_lock: asyncio.Lock | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    require_contiguous_source_groups: bool = True,
    rollback_staged_data_on_error: bool = True,
    continue_on_group_error: bool = False,
) -> OfflineReplayStats:
    if pipeline_status is None:
        pipeline_status = {"latest_message": "", "history_messages": []}
    if pipeline_status_lock is None:
        pipeline_status_lock = asyncio.Lock()

    async def _persist_group(affected_chunk_ids: list[str]) -> None:
        await rag._insert_done(pipeline_status, pipeline_status_lock)
        await rag._try_bump_corpus_revision(
            "offline_replay",
            affected_chunk_ids=affected_chunk_ids,
        )

    if hasattr(rag, "_build_runtime_global_config"):
        global_config = await rag._build_runtime_global_config()
    else:
        global_config = asdict(rag)

    return await replay_raw_merge_units_jsonl(
        paths,
        full_docs=rag.full_docs,
        text_chunks=rag.text_chunks,
        chunks_vdb=rag.chunks_vdb,
        doc_status=rag.doc_status,
        knowledge_graph_inst=rag.chunk_entity_relation_graph,
        entity_vdb=rag.entities_vdb,
        relationships_vdb=rag.relationships_vdb,
        global_config=global_config,
        pipeline_status=pipeline_status,
        pipeline_status_lock=pipeline_status_lock,
        llm_response_cache=rag.llm_response_cache,
        group_done_callback=_persist_group,
        progress_callback=progress_callback,
        require_contiguous_source_groups=require_contiguous_source_groups,
        rollback_staged_data_on_error=rollback_staged_data_on_error,
        continue_on_group_error=continue_on_group_error,
    )
