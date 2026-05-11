#!/usr/bin/env python3
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from ragent.constants import GRAPH_FIELD_SEP
except Exception:
    GRAPH_FIELD_SEP = "<SEP>"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def split_source_ids(value):
    if value in (None, "", [], {}, ()):
        return []

    if isinstance(value, str):
        parts = re.split(re.escape(GRAPH_FIELD_SEP), value)
        return [p.strip() for p in parts if p.strip()]

    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            result.extend(split_source_ids(item))
        return result

    return [str(value).strip()]


def short(text, limit=120):
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def resolve_row_sources(row, chunk_map):
    source_ids = split_source_ids(row.get("source_chunk_ids") or row.get("source_id"))
    resolved_chunk_ids = [cid for cid in source_ids if cid in chunk_map]

    docs = set()
    refs = []

    if resolved_chunk_ids:
        for cid in resolved_chunk_ids:
            chunk = chunk_map[cid]
            doc = chunk.get("file_path") or row.get("file_path") or "unknown"
            ref = chunk.get("source_ref") or doc
            docs.add(doc)
            refs.append(ref)
    else:
        doc = row.get("file_path") or "unknown"
        docs.add(doc)
        refs.append(doc)

    return {
        "source_ids": source_ids,
        "resolved_chunk_ids": resolved_chunk_ids,
        "docs": docs,
        "refs": refs,
    }


def analyze_rows(rows, chunk_map, kind):
    total_rows = len(rows)
    rows_with_ids = 0
    rows_resolved_to_chunks = 0

    unique_source_ids = set()
    unique_resolved_chunks = set()
    unique_docs = set()

    by_doc = defaultdict(lambda: {"entity_rows": 0, "relation_rows": 0, "chunks": set()})
    by_chunk = defaultdict(
        lambda: {
            "doc": "unknown",
            "source_ref": None,
            "entity_rows": 0,
            "relation_rows": 0,
            "preview": None,
        }
    )

    unresolved_examples = []

    for row in rows:
        resolved = resolve_row_sources(row, chunk_map)

        source_ids = resolved["source_ids"]
        chunk_ids = resolved["resolved_chunk_ids"]
        docs = resolved["docs"]

        if source_ids:
            rows_with_ids += 1
            unique_source_ids.update(source_ids)

        if chunk_ids:
            rows_resolved_to_chunks += 1
            unique_resolved_chunks.update(chunk_ids)
        elif source_ids and len(unresolved_examples) < 5:
            unresolved_examples.append(
                {
                    "name": row.get("entity_name")
                    or f"{row.get('src_id')} -> {row.get('tgt_id')}",
                    "source_ids": source_ids,
                }
            )

        unique_docs.update(docs)

        for doc in docs:
            if kind == "entity":
                by_doc[doc]["entity_rows"] += 1
            else:
                by_doc[doc]["relation_rows"] += 1
            by_doc[doc]["chunks"].update(chunk_ids)

        for cid in chunk_ids:
            chunk = chunk_map[cid]
            entry = by_chunk[cid]
            entry["doc"] = chunk.get("file_path") or "unknown"
            entry["source_ref"] = chunk.get("source_ref")
            entry["preview"] = short(chunk.get("content", ""))
            if kind == "entity":
                entry["entity_rows"] += 1
            else:
                entry["relation_rows"] += 1

    return {
        "total_rows": total_rows,
        "rows_with_ids": rows_with_ids,
        "rows_resolved_to_chunks": rows_resolved_to_chunks,
        "unique_source_ids": unique_source_ids,
        "unique_resolved_chunks": unique_resolved_chunks,
        "unique_docs": unique_docs,
        "by_doc": by_doc,
        "by_chunk": by_chunk,
        "unresolved_examples": unresolved_examples,
    }


def merge_doc_stats(entity_doc_stats, relation_doc_stats):
    all_docs = set(entity_doc_stats) | set(relation_doc_stats)
    merged = []
    for doc in all_docs:
        e = entity_doc_stats.get(doc, {"entity_rows": 0, "relation_rows": 0, "chunks": set()})
        r = relation_doc_stats.get(doc, {"entity_rows": 0, "relation_rows": 0, "chunks": set()})
        merged.append(
            {
                "doc": doc,
                "entity_rows": e["entity_rows"],
                "relation_rows": r["relation_rows"],
                "chunk_count": len(e["chunks"] | r["chunks"]),
            }
        )
    merged.sort(key=lambda x: (x["entity_rows"] + x["relation_rows"], x["chunk_count"]), reverse=True)
    return merged


def merge_chunk_stats(entity_chunk_stats, relation_chunk_stats):
    all_chunks = set(entity_chunk_stats) | set(relation_chunk_stats)
    merged = []
    for cid in all_chunks:
        e = entity_chunk_stats.get(
            cid, {"doc": "unknown", "source_ref": None, "entity_rows": 0, "relation_rows": 0, "preview": None}
        )
        r = relation_chunk_stats.get(
            cid, {"doc": e["doc"], "source_ref": e["source_ref"], "entity_rows": 0, "relation_rows": 0, "preview": e["preview"]}
        )
        merged.append(
            {
                "chunk_id": cid,
                "doc": e["doc"] if e["doc"] != "unknown" else r["doc"],
                "source_ref": e["source_ref"] or r["source_ref"],
                "entity_rows": e["entity_rows"],
                "relation_rows": r["relation_rows"],
                "preview": e["preview"] or r["preview"],
            }
        )
    merged.sort(key=lambda x: (x["entity_rows"] + x["relation_rows"], x["entity_rows"]), reverse=True)
    return merged


def main():
    if len(sys.argv) != 2:
        print("Usage: python stats_provenance.py <kg_dir>")
        sys.exit(1)

    kg_dir = Path(sys.argv[1]).resolve()

    chunks_path = kg_dir / "kv_store_text_chunks.json"
    entities_path = kg_dir / "vdb_entities.json"
    relations_path = kg_dir / "vdb_relationships.json"

    if not chunks_path.exists():
        raise FileNotFoundError(f"Missing file: {chunks_path}")
    if not entities_path.exists():
        raise FileNotFoundError(f"Missing file: {entities_path}")
    if not relations_path.exists():
        raise FileNotFoundError(f"Missing file: {relations_path}")

    chunk_map = load_json(chunks_path)
    entity_rows = load_json(entities_path).get("data", [])
    relation_rows = load_json(relations_path).get("data", [])

    entity_stats = analyze_rows(entity_rows, chunk_map, kind="entity")
    relation_stats = analyze_rows(relation_rows, chunk_map, kind="relation")

    print("\n=== Summary ===")
    print(f"KG dir: {kg_dir}")
    print(f"Total chunks in store: {len(chunk_map)}")
    print(f"Total entities: {entity_stats['total_rows']}")
    print(f"Total relations: {relation_stats['total_rows']}")
    print(f"Entity source chunks (distinct, resolved): {len(entity_stats['unique_resolved_chunks'])}")
    print(f"Relation source chunks (distinct, resolved): {len(relation_stats['unique_resolved_chunks'])}")
    print(f"Entity source docs (distinct): {len(entity_stats['unique_docs'])}")
    print(f"Relation source docs (distinct): {len(relation_stats['unique_docs'])}")
    print(f"Combined source chunks (distinct): {len(entity_stats['unique_resolved_chunks'] | relation_stats['unique_resolved_chunks'])}")
    print(f"Combined source docs (distinct): {len(entity_stats['unique_docs'] | relation_stats['unique_docs'])}")

    print("\n=== Entity Stats ===")
    print(f"Rows with source ids: {entity_stats['rows_with_ids']}")
    print(f"Rows resolved to chunks: {entity_stats['rows_resolved_to_chunks']}")
    if entity_stats["unresolved_examples"]:
        print("Unresolved entity examples:")
        for item in entity_stats["unresolved_examples"]:
            print(f"  - {item}")

    print("\n=== Relation Stats ===")
    print(f"Rows with source ids: {relation_stats['rows_with_ids']}")
    print(f"Rows resolved to chunks: {relation_stats['rows_resolved_to_chunks']}")
    if relation_stats["unresolved_examples"]:
        print("Unresolved relation examples:")
        for item in relation_stats["unresolved_examples"]:
            print(f"  - {item}")

    print("\n=== By Document ===")
    for item in merge_doc_stats(entity_stats["by_doc"], relation_stats["by_doc"]):
        print(
            f"- doc={item['doc']}\n"
            f"  entity_rows={item['entity_rows']}, relation_rows={item['relation_rows']}, chunk_count={item['chunk_count']}"
        )

    print("\n=== By Chunk ===")
    for item in merge_chunk_stats(entity_stats["by_chunk"], relation_stats["by_chunk"]):
        print(
            f"- chunk_id={item['chunk_id']}\n"
            f"  doc={item['doc']}\n"
            f"  source_ref={item['source_ref']}\n"
            f"  entity_rows={item['entity_rows']}, relation_rows={item['relation_rows']}\n"
            f"  preview={item['preview']}"
        )


if __name__ == "__main__":
    main()

