#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path

import networkx as nx

from ragent.llm.openai import openai_embed
from ragent.operate import _coerce_embedding_list, _generate_chunk_text_embeddings
from ragent.utils import get_configured_embedding_dim, get_env_value


DEFAULT_GRAPH_FILE_NAME = "graph_chunk_entity_relation.graphml"
DEFAULT_VDB_FILE_NAME = "vdb_chunks.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill missing chunk_text node embeddings in a persisted Ragent graph."
        )
    )
    parser.add_argument(
        "--storage-dir",
        help=(
            "Directory containing graph_chunk_entity_relation.graphml. "
            "Example: example/demo_diet_kg"
        ),
    )
    parser.add_argument(
        "--working-dir",
        help="Working directory used by Ragent when --storage-dir is not provided.",
    )
    parser.add_argument(
        "--workspace",
        default="",
        help="Workspace name under --working-dir.",
    )
    parser.add_argument(
        "--graph-file-name",
        default=DEFAULT_GRAPH_FILE_NAME,
        help=f"GraphML file name inside the storage directory. Default: {DEFAULT_GRAPH_FILE_NAME}",
    )
    parser.add_argument(
        "--vdb-file-name",
        default=DEFAULT_VDB_FILE_NAME,
        help=f"Chunk vector DB file name inside the storage directory. Default: {DEFAULT_VDB_FILE_NAME}",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=get_env_value("EMBEDDING_BATCH_NUM", 10, int),
        help="Embedding batch size. Default follows EMBEDDING_BATCH_NUM or falls back to 10.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Only backfill the first N invalid chunk_text nodes.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect and compute stats only. Do not write the graph file.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a timestamped .bak copy before overwriting the graph.",
    )
    parser.add_argument(
        "--force-dimension-mismatch",
        action="store_true",
        help="Allow writing even if current embedding dim differs from persisted graph/vdb dim.",
    )
    args = parser.parse_args()
    if not args.storage_dir and not args.working_dir:
        parser.error("Provide either --storage-dir or --working-dir.")
    if args.batch_size <= 0:
        parser.error("--batch-size must be > 0.")
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be > 0.")
    return args


def _resolve_storage_dir(args: argparse.Namespace) -> Path:
    if args.storage_dir:
        return Path(args.storage_dir).expanduser().resolve()
    working_dir = Path(args.working_dir).expanduser().resolve()
    if args.workspace:
        return working_dir / args.workspace
    return working_dir


def _load_graph(graph_path: Path) -> nx.Graph:
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")
    return nx.read_graphml(graph_path)


def _load_vdb_embedding_dim(vdb_path: Path) -> int | None:
    if not vdb_path.exists():
        return None
    with vdb_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    embedding_dim = data.get("embedding_dim")
    return embedding_dim if isinstance(embedding_dim, int) and embedding_dim > 0 else None


def _detect_graph_embedding_dim(graph: nx.Graph) -> int | None:
    dims: set[int] = set()
    for _, node_data in graph.nodes(data=True):
        embedding = _coerce_embedding_list(node_data.get("embeddings"))
        if embedding is not None:
            dims.add(len(embedding))
            if len(dims) > 1:
                raise ValueError(
                    f"Found multiple embedding dimensions in graph nodes: {sorted(dims)}"
                )
    return next(iter(dims), None) if dims else None


def _collect_backfill_candidates(
    graph: nx.Graph,
) -> tuple[list[tuple[str, str]], dict[str, int], list[str]]:
    candidates: list[tuple[str, str]] = []
    stats = {
        "chunk_text_total": 0,
        "already_valid": 0,
        "missing_or_invalid": 0,
        "missing_description": 0,
    }
    missing_description_ids: list[str] = []

    for node_id, node_data in graph.nodes(data=True):
        if node_data.get("entity_type") != "chunk_text":
            continue

        stats["chunk_text_total"] += 1
        embedding = _coerce_embedding_list(node_data.get("embeddings"))
        if embedding is not None:
            stats["already_valid"] += 1
            continue

        stats["missing_or_invalid"] += 1
        description = (node_data.get("description") or "").strip()
        if not description:
            stats["missing_description"] += 1
            missing_description_ids.append(str(node_id))
            continue
        candidates.append((str(node_id), description))

    return candidates, stats, missing_description_ids


def _build_backup_path(graph_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return graph_path.with_suffix(f"{graph_path.suffix}.bak.{timestamp}")


async def _backfill_embeddings(args: argparse.Namespace) -> None:
    storage_dir = _resolve_storage_dir(args)
    graph_path = storage_dir / args.graph_file_name
    vdb_path = storage_dir / args.vdb_file_name

    graph = _load_graph(graph_path)
    candidates, stats, missing_description_ids = _collect_backfill_candidates(graph)

    graph_embedding_dim = _detect_graph_embedding_dim(graph)
    vdb_embedding_dim = _load_vdb_embedding_dim(vdb_path)
    expected_embedding_dim = graph_embedding_dim or vdb_embedding_dim

    graph_vdb_dim_mismatch = (
        graph_embedding_dim is not None
        and vdb_embedding_dim is not None
        and graph_embedding_dim != vdb_embedding_dim
    )
    current_embedding_dim = get_configured_embedding_dim(
        getattr(openai_embed, "embedding_dim", 1024)
    )
    runtime_dim_mismatch = (
        expected_embedding_dim is not None
        and current_embedding_dim is not None
        and expected_embedding_dim != current_embedding_dim
    )

    original_candidate_count = len(candidates)
    if args.limit is not None:
        candidates = candidates[: args.limit]

    print(f"storage_dir={storage_dir}")
    print(f"graph_path={graph_path}")
    print(f"chunk_text_total={stats['chunk_text_total']}")
    print(f"already_valid={stats['already_valid']}")
    print(f"missing_or_invalid={stats['missing_or_invalid']}")
    print(f"missing_description={stats['missing_description']}")
    print(f"graph_embedding_dim={graph_embedding_dim}")
    print(f"vdb_embedding_dim={vdb_embedding_dim}")
    print(f"current_embedding_dim={current_embedding_dim}")
    print(f"batch_size={args.batch_size}")
    print(f"candidates_to_backfill={len(candidates)}")
    if args.limit is not None:
        print(f"candidate_limit_applied_from={original_candidate_count}")
    if missing_description_ids:
        preview = ", ".join(missing_description_ids[:5])
        print(f"missing_description_preview={preview}")

    if not candidates:
        print("No backfill candidates found.")
        return

    if graph_vdb_dim_mismatch:
        raise ValueError(
            "Graph embedding dim and chunk VDB embedding dim do not match: "
            f"{graph_embedding_dim} != {vdb_embedding_dim}"
        )

    if runtime_dim_mismatch and args.dry_run and not args.force_dimension_mismatch:
        print(
            "Dry run warning: current embedding function dim does not match persisted "
            f"storage dim: {current_embedding_dim} != {expected_embedding_dim}"
        )
        print(
            "Set the correct embedding env or rerun with --force-dimension-mismatch "
            "before writing."
        )
        print("Dry run enabled. No graph file was modified.")
        return

    if runtime_dim_mismatch and not args.force_dimension_mismatch:
        raise ValueError(
            "Current embedding function dim does not match persisted storage dim: "
            f"{current_embedding_dim} != {expected_embedding_dim}. "
            "Set the correct embedding env or rerun with --force-dimension-mismatch."
        )

    if args.dry_run:
        print("Dry run enabled. No graph file was modified.")
        return

    if not args.no_backup:
        backup_path = _build_backup_path(graph_path)
        shutil.copy2(graph_path, backup_path)
        print(f"backup_path={backup_path}")

    total_updated = 0
    for batch_index, start in enumerate(range(0, len(candidates), args.batch_size), start=1):
        batch = candidates[start : start + args.batch_size]
        embeddings_by_entity = await _generate_chunk_text_embeddings(
            batch,
            {"embedding_func": openai_embed},
        )

        for node_id, _ in batch:
            embedding = embeddings_by_entity[node_id]
            if (
                expected_embedding_dim is not None
                and len(embedding) != expected_embedding_dim
                and not args.force_dimension_mismatch
            ):
                raise ValueError(
                    f"Generated embedding dim mismatch for {node_id}: "
                    f"{len(embedding)} != {expected_embedding_dim}"
                )
            graph.nodes[node_id]["embeddings"] = str(embedding)
            total_updated += 1

        print(f"batch={batch_index} updated={total_updated}/{len(candidates)}")

    nx.write_graphml(graph, graph_path)
    print(f"Backfill complete. updated={total_updated} graph_path={graph_path}")


def main() -> None:
    args = _parse_args()
    asyncio.run(_backfill_embeddings(args))


if __name__ == "__main__":
    main()
