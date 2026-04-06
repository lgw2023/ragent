from __future__ import annotations
from functools import partial

import asyncio
import ast
import json
import math
import os
import re
import numpy as np
from typing import Any, AsyncIterator, Callable
from collections import Counter, defaultdict
from ragent.rerank import rerank_from_env
from .llm.openai import openai_embed
from .utils import (
    logger,
    clean_str,
    compute_mdhash_id,
    Tokenizer,
    is_float_regex,
    normalize_extracted_info,
    pack_user_ass_to_openai_messages,
    split_string_by_multi_markers,
    truncate_list_by_token_size,
    process_combine_contexts,
    compute_args_hash,
    handle_cache,
    save_to_cache,
    CacheData,
    get_conversation_turns,
    use_llm_func_with_cache,
    update_chunk_cache_list,
    remove_think_tags,
)
from .base import (
    BaseGraphStorage,
    BaseKVStorage,
    BaseVectorStorage,
    TextChunkSchema,
    QueryParam,
)
from .prompt import PROMPTS
from .constants import (
    GRAPH_FIELD_SEP,
    DEFAULT_MAX_ENTITY_TOKENS,
    DEFAULT_MAX_RELATION_TOKENS,
    DEFAULT_MAX_TOTAL_TOKENS,
    DEFAULT_RELATED_CHUNK_NUMBER,
)
from .kg.shared_storage import get_storage_keyed_lock
import time


def _append_stage_timing(
    stage_timings: list[dict[str, Any]],
    stage: str,
    label: str,
    seconds: float,
):
    stage_timings.append(
        {
            "stage": stage,
            "label": label,
            "seconds": round(max(seconds, 0.0), 3),
        }
    )


def _record_stage_timing(
    stage_timings: list[dict[str, Any]],
    stage: str,
    label: str,
    started_at: float,
):
    _append_stage_timing(stage_timings, stage, label, time.perf_counter() - started_at)


def _coerce_embedding_array(embedding: Any) -> np.ndarray | None:
    if embedding is None:
        return None

    parsed_embedding = embedding
    if isinstance(parsed_embedding, str):
        stripped = parsed_embedding.strip()
        if stripped in {"", "None", "[]"}:
            return None
        try:
            parsed_embedding = json.loads(stripped)
        except json.JSONDecodeError:
            try:
                parsed_embedding = ast.literal_eval(stripped)
            except (SyntaxError, ValueError):
                return None

    try:
        array = np.asarray(parsed_embedding, dtype=float)
    except (TypeError, ValueError):
        return None

    if array.ndim != 1 or array.size == 0:
        return None
    return array


def _coerce_embedding_list(embedding: Any) -> list[float] | None:
    array = _coerce_embedding_array(embedding)
    if array is None:
        return None
    return array.tolist()


async def _generate_chunk_text_embeddings(
    chunk_text_items: list[tuple[str, str]],
    global_config: dict[str, Any],
) -> dict[str, list[float]]:
    if not chunk_text_items:
        return {}

    embedding_func = global_config.get("embedding_func") or openai_embed
    descriptions = [description for _, description in chunk_text_items]
    generated_embeddings = await embedding_func(descriptions)

    if generated_embeddings is None or len(generated_embeddings) != len(chunk_text_items):
        raise ValueError(
            "Generated embeddings count does not match chunk_text items count."
        )

    embeddings_by_entity: dict[str, list[float]] = {}
    for (entity_name, _), embedding in zip(chunk_text_items, generated_embeddings):
        parsed_embedding = _coerce_embedding_list(embedding)
        if parsed_embedding is None:
            raise ValueError(
                f"Generated invalid embedding for chunk_text node: {entity_name}"
            )
        embeddings_by_entity[entity_name] = parsed_embedding
    return embeddings_by_entity

def _normalize_source_text_for_match(text: str) -> str:
    if not text:
        return ""
    normalized = text.replace("\r", "\n")
    normalized = re.sub(r"<!--.*?-->", " ", normalized, flags=re.DOTALL)
    normalized = re.sub(r"```.*?```", " ", normalized, flags=re.DOTALL)
    normalized = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", normalized)
    normalized = re.sub(r"^\s*#+\s*", "", normalized, flags=re.MULTILINE)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized.strip()


def _strip_doc_name_markers(text: str) -> str:
    stripped = text or ""
    pattern = re.compile(r"^[^\n#]+#{5,7}")
    while True:
        match = pattern.match(stripped)
        if not match:
            break
        stripped = stripped[match.end() :].lstrip()
    return stripped


def _build_source_ref(
    file_path: str,
    page_numbers: list[int] | None = None,
    section_path: str | None = None,
) -> str:
    base_name = os.path.basename(file_path) if file_path else "unknown_source"
    parts = [base_name]
    if page_numbers:
        ordered_pages = sorted({int(page) for page in page_numbers if isinstance(page, int)})
        if ordered_pages:
            if len(ordered_pages) == 1:
                parts.append(f"p.{ordered_pages[0]}")
            else:
                parts.append(f"p.{ordered_pages[0]}-{ordered_pages[-1]}")
    if section_path:
        parts.append(section_path)
    return " | ".join(parts)


def _normalize_source_chunk_ids(value: Any) -> list[str]:
    if value in (None, "", [], {}, ()):
        return []

    if isinstance(value, str):
        candidates = split_string_by_multi_markers(value, [GRAPH_FIELD_SEP])
    elif isinstance(value, (list, tuple, set)):
        candidates = []
        for item in value:
            candidates.extend(_normalize_source_chunk_ids(item))
    else:
        candidates = [str(value)]

    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        chunk_id = str(candidate).strip()
        if not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)
        normalized.append(chunk_id)
    return normalized


def _serialize_source_chunk_ids(*values: Any) -> str:
    chunk_ids: list[str] = []
    seen: set[str] = set()
    for value in values:
        for chunk_id in _normalize_source_chunk_ids(value):
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            chunk_ids.append(chunk_id)
    return GRAPH_FIELD_SEP.join(chunk_ids)


def _extract_chunk_citation_fields(chunk: dict[str, Any]) -> dict[str, Any]:
    citation: dict[str, Any] = {}
    for key in (
        "file_path",
        "page_numbers",
        "page_number_start",
        "page_number_end",
        "section_path",
        "source_ref",
    ):
        value = chunk.get(key)
        if value not in (None, "", [], {}):
            citation[key] = value
    return citation


def _build_chunk_context_entry(rank: int, chunk: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "id": rank,
        "content": chunk.get("content", ""),
        "file_path": chunk.get("file_path", "unknown_source"),
    }
    entry.update(_extract_chunk_citation_fields(chunk))
    return entry


def _annotate_chunk_with_source_metadata(
    chunk: dict[str, Any],
    doc_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    if not doc_metadata:
        return chunk

    content_blocks = doc_metadata.get("content_blocks") or []
    normalized_chunk = _normalize_source_text_for_match(
        _strip_doc_name_markers(chunk.get("content", ""))
    )
    matched_blocks: list[dict[str, Any]] = []

    if normalized_chunk:
        for block in content_blocks:
            match_text = block.get("match_text") or ""
            min_length = 2 if block.get("is_heading") else 6
            if len(match_text) < min_length:
                continue
            if match_text in normalized_chunk:
                matched_blocks.append(block)

    page_numbers = sorted(
        {
            int(block["page_number"])
            for block in matched_blocks
            if isinstance(block.get("page_number"), int)
        }
    )
    if not page_numbers:
        page_numbers = [
            int(page)
            for page in doc_metadata.get("page_numbers", [])
            if isinstance(page, int)
        ]
        page_numbers = sorted(set(page_numbers))

    section_path = next(
        (
            block.get("section_path", "")
            for block in matched_blocks
            if block.get("section_path") and not block.get("is_heading")
        ),
        "",
    )
    if not section_path:
        section_path = next(
            (block.get("section_path", "") for block in matched_blocks if block.get("section_path")),
            "",
        )
    if not section_path:
        section_path = doc_metadata.get("section_path", "")

    if page_numbers:
        chunk["page_numbers"] = page_numbers
        chunk["page_number_start"] = page_numbers[0]
        chunk["page_number_end"] = page_numbers[-1]
    elif doc_metadata.get("page_number_start") is not None:
        chunk["page_number_start"] = doc_metadata.get("page_number_start")
        chunk["page_number_end"] = doc_metadata.get("page_number_end")

    if section_path:
        chunk["section_path"] = section_path

    source_ref = doc_metadata.get("source_ref")
    source_file_path = chunk.get("file_path") or doc_metadata.get("file_path", "")
    if (page_numbers or section_path) and source_file_path:
        source_ref = _build_source_ref(source_file_path, page_numbers, section_path)
    if source_ref:
        chunk["source_ref"] = source_ref

    return chunk


def chunking_by_token_size(
    doc_name: str,
    tokenizer: Tokenizer,
    content: str,
    doc_metadata: dict[str, Any] | None = None,
    split_by_character: str | None = None,
    split_by_character_only: bool = False,
    overlap_token_size: int = 128,
    max_token_size: int = 1024,
) -> list[dict[str, Any]]:
    tokens = tokenizer.encode(content)
    results: list[dict[str, Any]] = []
    if split_by_character:
        raw_chunks = content.split(split_by_character)
        new_chunks = []
        if split_by_character_only:
            for chunk in raw_chunks:
                _tokens = tokenizer.encode(chunk)
                new_chunks.append((len(_tokens), chunk))
        else:
            for chunk in raw_chunks:
                _tokens = tokenizer.encode(chunk)
                if len(_tokens) > max_token_size:
                    for start in range(
                        0, len(_tokens), max_token_size - overlap_token_size
                    ):
                        chunk_content = tokenizer.decode(
                            _tokens[start : start + max_token_size]
                        )
                        new_chunks.append(
                            (min(max_token_size, len(_tokens) - start), chunk_content)
                        )
                else:
                    new_chunks.append((len(_tokens), chunk))
        for index, (_len, chunk) in enumerate(new_chunks):
            chunk_data = {
                "tokens": _len,
                "content": doc_name + "#####" + chunk.strip(),
                "chunk_order_index": index,
            }
            results.append(_annotate_chunk_with_source_metadata(chunk_data, doc_metadata))
    else:
        for index, start in enumerate(
            range(0, len(tokens), max_token_size - overlap_token_size)
        ):
            chunk_content = tokenizer.decode(tokens[start : start + max_token_size])
            chunk_data = {
                "tokens": min(max_token_size, len(tokens) - start),
                "content": doc_name + "#####" + chunk_content.strip(),
                "chunk_order_index": index,
            }
            results.append(_annotate_chunk_with_source_metadata(chunk_data, doc_metadata))
    return results


async def apply_rerank_if_enabled(
    query: str,
    retrieved_docs: list[dict[str, Any]],
    global_config: dict[str, Any],
    enable_rerank: bool = True,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Rerank retrieved chunk dicts while preserving metadata and safe fallback."""
    if not enable_rerank or not query or not retrieved_docs:
        return retrieved_docs

    documents = [str(doc.get("content", "")) for doc in retrieved_docs]
    if not any(documents):
        return retrieved_docs

    try:
        rerank_results = await rerank_from_env(
            query=query,
            documents=documents,
            top_k=top_k,
        )
    except Exception as exc:
        logger.warning("Rerank failed, fallback to original chunk order: %s", exc)
        return retrieved_docs

    if not rerank_results:
        return retrieved_docs

    reranked_docs: list[dict[str, Any]] = []
    seen_indexes: set[int] = set()

    for item in rerank_results:
        index = item.get("index")
        if not isinstance(index, int) or not (0 <= index < len(retrieved_docs)):
            continue
        if index in seen_indexes:
            continue
        reranked_docs.append(retrieved_docs[index])
        seen_indexes.add(index)

    if not reranked_docs:
        return retrieved_docs

    for index, doc in enumerate(retrieved_docs):
        if index not in seen_indexes:
            reranked_docs.append(doc)

    return reranked_docs


async def _handle_entity_relation_summary(
    entity_or_relation_name: str,
    description: str,
    global_config: dict,
    llm_response_cache: BaseKVStorage | None = None,
) -> str:
    """Handle entity relation summary
    For each entity or relation, input is the combined description of already existing description and new description.
    If too long, use LLM to summarize.
    """
    use_llm_func: callable = global_config["llm_model_func"]
    # Apply higher priority (8) to entity/relation summary tasks
    use_llm_func = partial(use_llm_func, _priority=8)

    tokenizer: Tokenizer = global_config["tokenizer"]
    llm_max_tokens = global_config["llm_model_max_token_size"]

    language = global_config["addon_params"].get(
        "language", PROMPTS["DEFAULT_LANGUAGE"]
    )

    tokens = tokenizer.encode(description)

    ### summarize is not determined here anymore (It's determined by num_fragment now)
    # if len(tokens) < summary_max_tokens:  # No need for summary
    #     return description

    prompt_template = PROMPTS["summarize_entity_descriptions"]
    use_description = tokenizer.decode(tokens[:llm_max_tokens])
    context_base = dict(
        entity_name=entity_or_relation_name,
        description_list=use_description.split(GRAPH_FIELD_SEP),
        language=language,
    )
    use_prompt = prompt_template.format(**context_base)
    logger.debug(f"Trigger summary: {entity_or_relation_name}")

    # Use LLM function with cache (higher priority for summary generation)
    summary = await use_llm_func_with_cache(
        use_prompt,
        use_llm_func,
        llm_response_cache=llm_response_cache,
        # max_tokens=summary_max_tokens,
        cache_type="extract",
    )
    return summary


async def _handle_single_entity_extraction(
    record_attributes: list[str],
    chunk_key: str,
    file_path: str = "unknown_source",
):
    if len(record_attributes) < 4 or '"entity"' not in record_attributes[0]:
        return None

    # Clean and validate entity name
    entity_name = clean_str(record_attributes[1]).strip()
    if not entity_name:
        logger.warning(
            f"Entity extraction error: empty entity name in: {record_attributes}"
        )
        return None

    # Normalize entity name
    entity_name = normalize_extracted_info(entity_name, is_entity=True)

    # Check if entity name became empty after normalization
    if not entity_name or not entity_name.strip():
        logger.warning(
            f"Entity extraction error: entity name became empty after normalization. Original: '{record_attributes[1]}'"
        )
        return None

    # Clean and validate entity type
    entity_type = clean_str(record_attributes[2]).strip('"')
    if not entity_type.strip() or entity_type.startswith('("'):
        logger.warning(
            f"Entity extraction error: invalid entity type in: {record_attributes}"
        )
        return None

    # Clean and validate description
    entity_description = clean_str(record_attributes[3])
    entity_description = normalize_extracted_info(entity_description)

    if not entity_description.strip():
        logger.warning(
            f"Entity extraction error: empty description for entity '{entity_name}' of type '{entity_type}'"
        )
        return None

    return dict(
        entity_name=entity_name,
        entity_type=entity_type,
        description=entity_description,
        source_id=chunk_key,
        source_chunk_ids=chunk_key,
        file_path=file_path,
    )


async def _handle_single_relationship_extraction(
    record_attributes: list[str],
    chunk_key: str,
    file_path: str = "unknown_source",
):
    if len(record_attributes) < 5 or '"relationship"' not in record_attributes[0]:
        return None
    # add this record as edge
    source = clean_str(record_attributes[1])
    target = clean_str(record_attributes[2])

    # Normalize source and target entity names
    source = normalize_extracted_info(source, is_entity=True)
    target = normalize_extracted_info(target, is_entity=True)

    # Check if source or target became empty after normalization
    if not source or not source.strip():
        logger.warning(
            f"Relationship extraction error: source entity became empty after normalization. Original: '{record_attributes[1]}'"
        )
        return None

    if not target or not target.strip():
        logger.warning(
            f"Relationship extraction error: target entity became empty after normalization. Original: '{record_attributes[2]}'"
        )
        return None

    if source == target:
        logger.debug(
            f"Relationship source and target are the same in: {record_attributes}"
        )
        return None

    edge_description = clean_str(record_attributes[3])
    edge_description = normalize_extracted_info(edge_description)

    edge_keywords = normalize_extracted_info(
        clean_str(record_attributes[4]), is_entity=True
    )
    edge_keywords = edge_keywords.replace("，", ",")

    edge_source_id = chunk_key
    weight = (
        float(record_attributes[-1].strip('"').strip("'"))
        if is_float_regex(record_attributes[-1].strip('"').strip("'"))
        else 1.0
    )
    return dict(
        src_id=source,
        tgt_id=target,
        weight=weight,
        description=edge_description,
        keywords=edge_keywords,
        source_id=edge_source_id,
        source_chunk_ids=edge_source_id,
        file_path=file_path,
    )


async def _merge_nodes_then_upsert(
    entity_name: str,
    nodes_data: list[dict],
    knowledge_graph_inst: BaseGraphStorage,
    global_config: dict,
    pipeline_status: dict = None,
    pipeline_status_lock=None,
    llm_response_cache: BaseKVStorage | None = None,
):
    """Get existing nodes from knowledge graph use name,if exists, merge data, else create, then upsert."""
    already_entity_types = []
    already_source_ids = []
    already_description = []
    already_file_paths = []
    already_node = await knowledge_graph_inst.get_node(entity_name)
    if already_node:
        already_entity_types.append(already_node["entity_type"])
        already_source_ids.extend(
            _normalize_source_chunk_ids(
                already_node.get("source_chunk_ids") or already_node.get("source_id")
            )
        )
        already_file_paths.extend(
            split_string_by_multi_markers(already_node["file_path"], [GRAPH_FIELD_SEP])
        )
        already_description.append(already_node["description"])
    entity_type = sorted(
        Counter(
            [dp["entity_type"] for dp in nodes_data] + already_entity_types
        ).items(),
        key=lambda x: x[1],
        reverse=True,
    )[0][0]
    description = GRAPH_FIELD_SEP.join(
        sorted(set([dp["description"] for dp in nodes_data] + already_description))
    )
    source_id = _serialize_source_chunk_ids(
        already_source_ids,
        *[
            dp.get("source_chunk_ids") or dp.get("source_id")
            for dp in nodes_data
        ],
    )
    file_path = GRAPH_FIELD_SEP.join(
        set([dp["file_path"] for dp in nodes_data] + already_file_paths)
    )
    embeddings = next(
        (
            candidate
            for candidate in (
                _coerce_embedding_list(dp.get("embeddings")) for dp in nodes_data
            )
            if candidate is not None
        ),
        None,
    )
    if embeddings is None and already_node is not None:
        embeddings = _coerce_embedding_list(already_node.get("embeddings"))

    force_llm_summary_on_merge = global_config["force_llm_summary_on_merge"]

    num_fragment = description.count(GRAPH_FIELD_SEP) + 1
    num_new_fragment = len(set([dp["description"] for dp in nodes_data]))

    if num_fragment > 1:
        if num_fragment >= force_llm_summary_on_merge:
            status_message = f"LLM merge N: {entity_name} | {num_new_fragment}+{num_fragment-num_new_fragment}"
            logger.info(status_message)
            if pipeline_status is not None and pipeline_status_lock is not None:
                async with pipeline_status_lock:
                    pipeline_status["latest_message"] = status_message
                    pipeline_status["history_messages"].append(status_message)
            description = await _handle_entity_relation_summary(
                entity_name,
                description,
                global_config,
                llm_response_cache,
            )
        else:
            status_message = f"Merge N: {entity_name} | {num_new_fragment}+{num_fragment-num_new_fragment}"
            logger.info(status_message)
            if pipeline_status is not None and pipeline_status_lock is not None:
                async with pipeline_status_lock:
                    pipeline_status["latest_message"] = status_message
                    pipeline_status["history_messages"].append(status_message)

    if embeddings is None and entity_type == "chunk_text":
        embeddings = (
            await _generate_chunk_text_embeddings(
                [(entity_name, description)],
                global_config,
            )
        )[entity_name]
        logger.info("Backfilled missing embedding for chunk_text node: %s", entity_name)

    embeddings = embeddings or []

#    if embeddings == []:
#        embeddings_list = [entity_name + "|" + description]
#        query_embedding = await openai_embed(embeddings_list)
#        embeddings = query_embedding[0]

    node_data = dict(
        entity_id=entity_name,
        entity_type=entity_type,
        description=description,
        source_id=source_id,
        source_chunk_ids=source_id,
        file_path=file_path,
        embeddings= str(embeddings),
        created_at=int(time.time()),
    )
    await knowledge_graph_inst.upsert_node(
        entity_name,
        node_data=node_data,
    )
    node_data["entity_name"] = entity_name
    return node_data


async def _merge_edges_then_upsert(
    src_id: str,
    tgt_id: str,
    edges_data: list[dict],
    knowledge_graph_inst: BaseGraphStorage,
    global_config: dict,
    pipeline_status: dict = None,
    pipeline_status_lock=None,
    llm_response_cache: BaseKVStorage | None = None,
):
    if src_id == tgt_id:
        return None

    already_weights = []
    already_source_ids = []
    already_description = []
    already_keywords = []
    already_file_paths = []

    if await knowledge_graph_inst.has_edge(src_id, tgt_id):
        already_edge = await knowledge_graph_inst.get_edge(src_id, tgt_id)
        # Handle the case where get_edge returns None or missing fields
        if already_edge:
            # Get weight with default 0.0 if missing
            already_weights.append(already_edge.get("weight", 0.0))

            # Get source_id with empty string default if missing or None
            if already_edge.get("source_chunk_ids") is not None or already_edge.get(
                "source_id"
            ) is not None:
                already_source_ids.extend(
                    _normalize_source_chunk_ids(
                        already_edge.get("source_chunk_ids")
                        or already_edge.get("source_id")
                    )
                )

            # Get file_path with empty string default if missing or None
            if already_edge.get("file_path") is not None:
                already_file_paths.extend(
                    split_string_by_multi_markers(
                        already_edge["file_path"], [GRAPH_FIELD_SEP]
                    )
                )

            # Get description with empty string default if missing or None
            if already_edge.get("description") is not None:
                already_description.append(already_edge["description"])

            # Get keywords with empty string default if missing or None
            if already_edge.get("keywords") is not None:
                already_keywords.extend(
                    split_string_by_multi_markers(
                        already_edge["keywords"], [GRAPH_FIELD_SEP]
                    )
                )

    # Process edges_data with None checks
    weight = sum([dp["weight"] for dp in edges_data] + already_weights)
    description = GRAPH_FIELD_SEP.join(
        sorted(
            set(
                [dp["description"] for dp in edges_data if dp.get("description")]
                + already_description
            )
        )
    )

    # Split all existing and new keywords into individual terms, then combine and deduplicate
    all_keywords = set()
    # Process already_keywords (which are comma-separated)
    for keyword_str in already_keywords:
        if keyword_str:  # Skip empty strings
            all_keywords.update(k.strip() for k in keyword_str.split(",") if k.strip())
    # Process new keywords from edges_data
    for edge in edges_data:
        if edge.get("keywords"):
            all_keywords.update(
                k.strip() for k in edge["keywords"].split(",") if k.strip()
            )
    # Join all unique keywords with commas
    keywords = ",".join(sorted(all_keywords))

    source_id = _serialize_source_chunk_ids(
        already_source_ids,
        *[
            dp.get("source_chunk_ids") or dp.get("source_id")
            for dp in edges_data
        ],
    )
    file_path = GRAPH_FIELD_SEP.join(
        set(
            [dp["file_path"] for dp in edges_data if dp.get("file_path")]
            + already_file_paths
        )
    )

    for need_insert_id in [src_id, tgt_id]:
        workspace = global_config.get("workspace", "")
        namespace = f"{workspace}:GraphDB" if workspace else "GraphDB"
        async with get_storage_keyed_lock(
            [need_insert_id], namespace=namespace, enable_logging=False
        ):
            if not (await knowledge_graph_inst.has_node(need_insert_id)):
                await knowledge_graph_inst.upsert_node(
                    need_insert_id,
                    node_data={
                        "entity_id": need_insert_id,
                        "source_id": source_id,
                        "source_chunk_ids": source_id,
                        "description": description,
                        "entity_type": "UNKNOWN",
                        "file_path": file_path,
                        "created_at": int(time.time()),
                    },
                )

    force_llm_summary_on_merge = global_config["force_llm_summary_on_merge"]

    num_fragment = description.count(GRAPH_FIELD_SEP) + 1
    num_new_fragment = len(
        set([dp["description"] for dp in edges_data if dp.get("description")])
    )

    if num_fragment > 1:
        if num_fragment >= force_llm_summary_on_merge:
            status_message = f"LLM merge E: {src_id} - {tgt_id} | {num_new_fragment}+{num_fragment-num_new_fragment}"
            logger.info(status_message)
            if pipeline_status is not None and pipeline_status_lock is not None:
                async with pipeline_status_lock:
                    pipeline_status["latest_message"] = status_message
                    pipeline_status["history_messages"].append(status_message)
            description = await _handle_entity_relation_summary(
                f"({src_id}, {tgt_id})",
                description,
                global_config,
                llm_response_cache,
            )
        else:
            status_message = f"Merge E: {src_id} - {tgt_id} | {num_new_fragment}+{num_fragment-num_new_fragment}"
            logger.info(status_message)
            if pipeline_status is not None and pipeline_status_lock is not None:
                async with pipeline_status_lock:
                    pipeline_status["latest_message"] = status_message
                    pipeline_status["history_messages"].append(status_message)

    await knowledge_graph_inst.upsert_edge(
        src_id,
        tgt_id,
        edge_data=dict(
            weight=weight,
            description=description,
            keywords=keywords,
            source_id=source_id,
            source_chunk_ids=source_id,
            file_path=file_path,
            created_at=int(time.time()),
        ),
    )

    edge_data = dict(
        src_id=src_id,
        tgt_id=tgt_id,
        description=description,
        keywords=keywords,
        source_id=source_id,
        source_chunk_ids=source_id,
        file_path=file_path,
        created_at=int(time.time()),
    )

    return edge_data


async def merge_nodes_and_edges(
    chunk_results: list,
    knowledge_graph_inst: BaseGraphStorage,
    entity_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    global_config: dict[str, str],
    pipeline_status: dict = None,
    pipeline_status_lock=None,
    llm_response_cache: BaseKVStorage | None = None,
    current_file_number: int = 0,
    total_files: int = 0,
    file_path: str = "unknown_source",
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    """Merge nodes and edges from extraction results

    Args:
        chunk_results: List of tuples (maybe_nodes, maybe_edges) containing extracted entities and relationships
        knowledge_graph_inst: Knowledge graph storage
        entity_vdb: Entity vector database
        relationships_vdb: Relationship vector database
        global_config: Global configuration
        pipeline_status: Pipeline status dictionary
        pipeline_status_lock: Lock for pipeline status
        llm_response_cache: LLM response cache
    """

    # Collect all nodes and edges from all chunks
    all_nodes = defaultdict(list)
    all_edges = defaultdict(list)

    for maybe_nodes, maybe_edges in chunk_results:
        # Collect nodes
        for entity_name, entities in maybe_nodes.items():
            all_nodes[entity_name].extend(entities)

        # Collect edges with sorted keys for undirected graph
        for edge_key, edges in maybe_edges.items():
            sorted_edge_key = tuple(sorted(edge_key))
            all_edges[sorted_edge_key].extend(edges)

    # Centralized processing of all nodes and edges
    total_entities_count = len(all_nodes)
    total_relations_count = len(all_edges)

    # Merge nodes and edges
    log_message = f"Merging stage {current_file_number}/{total_files}: {file_path}"
    logger.info(log_message)
    async with pipeline_status_lock:
        pipeline_status["latest_message"] = log_message
        pipeline_status["history_messages"].append(log_message)

    # Get max async tasks limit from global_config for semaphore control
    graph_max_async = global_config.get("llm_model_max_async", 4)
    semaphore = asyncio.Semaphore(graph_max_async)

    # Process and update all entities and relationships in parallel
    log_message = f"Processing: {total_entities_count} entities and {total_relations_count} relations (async: {graph_max_async})"
    logger.info(log_message)
    async with pipeline_status_lock:
        pipeline_status["latest_message"] = log_message
        pipeline_status["history_messages"].append(log_message)

    async def _locked_process_entity_name(entity_name, entities):
        async with semaphore:
            workspace = global_config.get("workspace", "")
            namespace = f"{workspace}:GraphDB" if workspace else "GraphDB"
            async with get_storage_keyed_lock(
                [entity_name], namespace=namespace, enable_logging=False
            ):
                entity_data = await _merge_nodes_then_upsert(
                    entity_name,
                    entities,
                    knowledge_graph_inst,
                    global_config,
                    pipeline_status,
                    pipeline_status_lock,
                    llm_response_cache,
                )
                if entity_vdb is not None:
                    data_for_vdb = {
                        compute_mdhash_id(entity_data["entity_name"], prefix="ent-"): {
                            "entity_name": entity_data["entity_name"],
                            "entity_type": entity_data["entity_type"],
                            "content": f"{entity_data['entity_name']}\n{entity_data['description']}",
                            "embeddings" : entity_data["embeddings"],
                            "source_id": entity_data["source_id"],
                            "source_chunk_ids": entity_data.get(
                                "source_chunk_ids", entity_data["source_id"]
                            ),
                            "file_path": entity_data.get("file_path", "unknown_source"),
                        }
                    }
                    await entity_vdb.upsert(data_for_vdb)
                return entity_data

    async def _locked_process_edges(edge_key, edges):
        async with semaphore:
            workspace = global_config.get("workspace", "")
            namespace = f"{workspace}:GraphDB" if workspace else "GraphDB"
            async with get_storage_keyed_lock(
                f"{edge_key[0]}-{edge_key[1]}",
                namespace=namespace,
                enable_logging=False,
            ):
                edge_data = await _merge_edges_then_upsert(
                    edge_key[0],
                    edge_key[1],
                    edges,
                    knowledge_graph_inst,
                    global_config,
                    pipeline_status,
                    pipeline_status_lock,
                    llm_response_cache,
                )
                if edge_data is None:
                    return None

                if relationships_vdb is not None:
                    data_for_vdb = {
                        compute_mdhash_id(
                            edge_data["src_id"] + edge_data["tgt_id"], prefix="rel-"
                        ): {
                            "src_id": edge_data["src_id"],
                            "tgt_id": edge_data["tgt_id"],
                            "keywords": edge_data["keywords"],
                            "content": f"{edge_data['src_id']}\t{edge_data['tgt_id']}\n{edge_data['keywords']}\n{edge_data['description']}",
                            "source_id": edge_data["source_id"],
                            "source_chunk_ids": edge_data.get(
                                "source_chunk_ids", edge_data["source_id"]
                            ),
                            "file_path": edge_data.get("file_path", "unknown_source"),
                        }
                    }
                    await relationships_vdb.upsert(data_for_vdb)
                return edge_data

    # Create a single task queue for both entities and edges
    tasks = []

    async def _track_merge_task(
        task_kind: str,
        key: Any,
        coro,
    ) -> tuple[str, Any, Any]:
        result = await coro
        return task_kind, key, result

    # Add entity processing tasks
    for entity_name, entities in all_nodes.items():
        tasks.append(
            asyncio.create_task(
                _track_merge_task(
                    "entity",
                    entity_name,
                    _locked_process_entity_name(entity_name, entities),
                )
            )
        )

    # Add edge processing tasks
    for edge_key, edges in all_edges.items():
        tasks.append(
            asyncio.create_task(
                _track_merge_task(
                    "relation",
                    edge_key,
                    _locked_process_edges(edge_key, edges),
                )
            )
        )

    # Execute all tasks in parallel with semaphore control
    merged_entities = 0
    merged_relations = 0
    total_merge_items = total_entities_count + total_relations_count
    for task in asyncio.as_completed(tasks):
        task_kind, task_key, _ = await task
        if task_kind == "entity":
            merged_entities += 1
        else:
            merged_relations += 1
        if progress_callback is not None:
            progress_callback(
                {
                    "stage": "merge_graph",
                    "current": merged_entities + merged_relations,
                    "total": total_merge_items,
                    "entity_current": merged_entities,
                    "entity_total": total_entities_count,
                    "relation_current": merged_relations,
                    "relation_total": total_relations_count,
                    "entity_name": task_key if task_kind == "entity" else "",
                    "edge_key": task_key if task_kind == "relation" else None,
                    "file_path": file_path,
                }
            )


async def extract_entities(
    chunks: dict[str, TextChunkSchema],
    global_config: dict[str, str],
    pipeline_status: dict = None,
    pipeline_status_lock=None,
    llm_response_cache: BaseKVStorage | None = None,
    text_chunks_storage: BaseKVStorage | None = None,
) -> list:
    use_llm_func: callable = global_config["llm_model_func"]
    entity_extract_max_gleaning = global_config["entity_extract_max_gleaning"]

    ordered_chunks = list(chunks.items())
    # add language and example number params to prompt
    language = global_config["addon_params"].get(
        "language", PROMPTS["DEFAULT_LANGUAGE"]
    )
    entity_types = global_config["addon_params"].get(
        "entity_types", PROMPTS["DEFAULT_ENTITY_TYPES"]
    )
    example_number = global_config["addon_params"].get("example_number", None)
    if example_number and example_number < len(PROMPTS["entity_extraction_examples"]):
        examples = "\n".join(
            PROMPTS["entity_extraction_examples"][: int(example_number)]
        )
    else:
        examples = "\n".join(PROMPTS["entity_extraction_examples"])

    example_context_base = dict(
        tuple_delimiter=PROMPTS["DEFAULT_TUPLE_DELIMITER"],
        record_delimiter=PROMPTS["DEFAULT_RECORD_DELIMITER"],
        completion_delimiter=PROMPTS["DEFAULT_COMPLETION_DELIMITER"],
        entity_types=", ".join(entity_types),
        language=language,
    )
    # add example's format
    examples = examples.format(**example_context_base)

    entity_extract_prompt = PROMPTS["entity_extraction"]
    context_base = dict(
        tuple_delimiter=PROMPTS["DEFAULT_TUPLE_DELIMITER"],
        record_delimiter=PROMPTS["DEFAULT_RECORD_DELIMITER"],
        completion_delimiter=PROMPTS["DEFAULT_COMPLETION_DELIMITER"],
        entity_types=",".join(entity_types),
        examples=examples,
        language=language,
    )

    continue_prompt = PROMPTS["entity_continue_extraction"].format(**context_base)
    if_loop_prompt = PROMPTS["entity_if_loop_extraction"]

    processed_chunks = 0
    total_chunks = len(ordered_chunks)

    async def _process_extraction_result(
        result: str, chunk_key: str, file_path: str = "unknown_source"
    ):
        """Process a single extraction result (either initial or gleaning)
        Args:
            result (str): The extraction result to process
            chunk_key (str): The chunk key for source tracking
            file_path (str): The file path for citation
        Returns:
            tuple: (nodes_dict, edges_dict) containing the extracted entities and relationships
        """
        maybe_nodes = defaultdict(list)
        maybe_edges = defaultdict(list)

        records = split_string_by_multi_markers(
            result,
            [context_base["record_delimiter"], context_base["completion_delimiter"]],
        )

        for record in records:
            record = re.search(r"\((.*)\)", record)
            if record is None:
                continue
            record = record.group(1)
            record_attributes = split_string_by_multi_markers(
                record, [context_base["tuple_delimiter"]]
            )

            if_entities = await _handle_single_entity_extraction(
                record_attributes, chunk_key, file_path
            )
            if if_entities is not None:
                maybe_nodes[if_entities["entity_name"]].append(if_entities)
                continue

            if_relation = await _handle_single_relationship_extraction(
                record_attributes, chunk_key, file_path
            )
            if if_relation is not None:
                maybe_edges[(if_relation["src_id"], if_relation["tgt_id"])].append(
                    if_relation
                )

        return maybe_nodes, maybe_edges

    async def _process_single_content(chunk_key_dp: tuple[str, TextChunkSchema]):
        """Process a single chunk
        Args:
            chunk_key_dp (tuple[str, TextChunkSchema]):
                ("chunk-xxxxxx", {"tokens": int, "content": str, "full_doc_id": str, "chunk_order_index": int})
        Returns:
            tuple: (maybe_nodes, maybe_edges) containing extracted entities and relationships
        """
        nonlocal processed_chunks
        chunk_key = chunk_key_dp[0]
        chunk_dp = chunk_key_dp[1]
        content = chunk_dp["content"]
        # Get file path from chunk data or use default
        file_path = chunk_dp.get("file_path", "unknown_source")

        # Create cache keys collector for batch processing
        cache_keys_collector = []

        # Get initial extraction
        hint_prompt = entity_extract_prompt.format(
            **{**context_base, "input_text": content}
        )

        final_result = await use_llm_func_with_cache(
            hint_prompt,
            use_llm_func,
            llm_response_cache=llm_response_cache,
            cache_type="extract",
            chunk_id=chunk_key,
            cache_keys_collector=cache_keys_collector,
        )

        # Store LLM cache reference in chunk (will be handled by use_llm_func_with_cache)
        history = pack_user_ass_to_openai_messages(hint_prompt, final_result)

        # Process initial extraction with file path
        maybe_nodes, maybe_edges = await _process_extraction_result(
            final_result, chunk_key, file_path
        )

        # Process additional gleaning results
        for now_glean_index in range(entity_extract_max_gleaning):
            glean_result = await use_llm_func_with_cache(
                continue_prompt,
                use_llm_func,
                llm_response_cache=llm_response_cache,
                history_messages=history,
                cache_type="extract",
                chunk_id=chunk_key,
                cache_keys_collector=cache_keys_collector,
            )

            history += pack_user_ass_to_openai_messages(continue_prompt, glean_result)

            # Process gleaning result separately with file path
            glean_nodes, glean_edges = await _process_extraction_result(
                glean_result, chunk_key, file_path
            )

            # Merge results - only add entities and edges with new names
            for entity_name, entities in glean_nodes.items():
                if (
                    entity_name not in maybe_nodes
                ):  # Only accetp entities with new name in gleaning stage
                    maybe_nodes[entity_name].extend(entities)
            for edge_key, edges in glean_edges.items():
                if (
                    edge_key not in maybe_edges
                ):  # Only accetp edges with new name in gleaning stage
                    maybe_edges[edge_key].extend(edges)

            if now_glean_index == entity_extract_max_gleaning - 1:
                break

            if_loop_result: str = await use_llm_func_with_cache(
                if_loop_prompt,
                use_llm_func,
                llm_response_cache=llm_response_cache,
                history_messages=history,
                cache_type="extract",
                cache_keys_collector=cache_keys_collector,
            )
            if_loop_result = if_loop_result.strip().strip('"').strip("'").lower()
            if if_loop_result != "yes":
                break

        # Batch update chunk's llm_cache_list with all collected cache keys
        if cache_keys_collector and text_chunks_storage:
            await update_chunk_cache_list(
                chunk_key,
                text_chunks_storage,
                cache_keys_collector,
                "entity_extraction",
            )

        processed_chunks += 1
        entities_count = len(maybe_nodes)
        relations_count = len(maybe_edges)
        log_message = f"Chunk {processed_chunks} of {total_chunks} extracted {entities_count} Ent + {relations_count} Rel"
        logger.info(log_message)
        if pipeline_status is not None:
            async with pipeline_status_lock:
                pipeline_status["latest_message"] = log_message
                pipeline_status["history_messages"].append(log_message)
        
        content_list = [content]
        embeddings = await openai_embed(content_list)

        chunk_data = {
        'entity_name': chunk_key,
        'entity_type': "chunk_text",
        'description': content,
        'embeddings': embeddings[0],
        'source_id': chunk_key,
        'file_path': file_path
         }
        
        maybe_nodes[chunk_key].append(chunk_data)
        node_list = list(maybe_nodes.keys())[:-1]
        for cc in node_list:
            edge_data = {
            'src_id': cc, 
            'tgt_id': chunk_key, 
            'weight': 5.0, 
            'description': 'source', 
            'keywords': 'belong to',
            'source_id': chunk_key, 
            'file_path': 'unknown_source'
            }
            maybe_edges[(cc, chunk_key)].append(edge_data)
        return maybe_nodes, maybe_edges

    # Get max async tasks limit from global_config
    chunk_max_async = global_config.get("llm_model_max_async", 4)
    semaphore = asyncio.Semaphore(chunk_max_async)

    async def _process_with_semaphore(chunk):
        async with semaphore:
            return await _process_single_content(chunk)

    tasks = []
    for c in ordered_chunks:
        task = asyncio.create_task(_process_with_semaphore(c))
        tasks.append(task)

    # Wait for tasks to complete or for the first exception to occur
    # This allows us to cancel remaining tasks if any task fails
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

    # Check if any task raised an exception
    for task in done:
        if task.exception():
            # If a task failed, cancel all pending tasks
            # This prevents unnecessary processing since the parent function will abort anyway
            for pending_task in pending:
                pending_task.cancel()

            # Wait for cancellation to complete
            if pending:
                await asyncio.wait(pending)

            # Re-raise the exception to notify the caller
            raise task.exception()

    # If all tasks completed successfully, collect results
    chunk_results = [task.result() for task in tasks]

    # Return the chunk_results for later processing in merge_nodes_and_edges
    return chunk_results


async def graph_query(
    query: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    global_config: dict[str, str],
    hashing_kv: BaseKVStorage | None = None,
    system_prompt: str | None = None,
    chunks_vdb: BaseVectorStorage = None,
    return_debug: bool = False,
):
    stage_timings: list[dict[str, Any]] = []
    query_total_started_at = time.perf_counter()
    if query_param.model_func:
        use_model_func = query_param.model_func
    else:
        use_model_func = global_config["llm_model_func"]
        # Apply higher priority (5) to query relation LLM function
        use_model_func = partial(use_model_func, _priority=5)

    # Handle cache
    args_hash = compute_args_hash(query_param.mode, query)
    stage_started_at = time.perf_counter()
    cached_response, quantized, min_val, max_val = await handle_cache(
        hashing_kv, args_hash, query, query_param.mode, cache_type="query"
    )
    _record_stage_timing(
        stage_timings,
        "query_cache_lookup",
        "查询缓存检查",
        stage_started_at,
    )
    stage_started_at = time.perf_counter()
    hl_keywords, ll_keywords = await get_keywords_from_query(
        query, query_param, global_config, hashing_kv
    )
    _record_stage_timing(
        stage_timings,
        "keyword_extraction",
        "关键词提取",
        stage_started_at,
    )

    logger.debug(f"High-level keywords: {hl_keywords}")
    logger.debug(f"Low-level  keywords: {ll_keywords}")

    ll_keywords_str = ", ".join(ll_keywords) if ll_keywords else ""
    hl_keywords_str = ", ".join(hl_keywords) if hl_keywords else ""

    stage_started_at = time.perf_counter()
    ll_entities_context, ll_relations_context, _, _ = await _get_node_data(
        ll_keywords_str,
        knowledge_graph_inst,
        entities_vdb,
        query_param,
    )
    _record_stage_timing(
        stage_timings,
        "graph_entity_hits",
        "图谱命中 / 实体",
        stage_started_at,
    )
    stage_started_at = time.perf_counter()
    hl_entities_context, hl_relations_context, _, _ = await _get_edge_data(
        hl_keywords_str,
        knowledge_graph_inst,
        relationships_vdb,
        query_param,
    )
    _record_stage_timing(
        stage_timings,
        "graph_relation_hits",
        "图谱命中 / 关系",
        stage_started_at,
    )
    graph_entities = process_combine_contexts(
        ll_entities_context, hl_entities_context
    )
    graph_relations = process_combine_contexts(
        hl_relations_context, ll_relations_context
    )

    # Build context
    context = await _build_query_context(
        query,
        ll_keywords_str,
        hl_keywords_str,
        knowledge_graph_inst,
        entities_vdb,
        relationships_vdb,
        text_chunks_db,
        query_param,
        chunks_vdb,
        timing_collector=stage_timings,
    )

    debug_payload = {
        "high_level_keywords": hl_keywords,
        "low_level_keywords": ll_keywords,
        "graph_entities": graph_entities,
        "graph_relations": graph_relations,
        "final_context_text": context if context is not None else "",
        "final_prompt_text": "",
        "stage_timings": stage_timings,
    }

    if query_param.only_need_context:
        context_output = context if context is not None else PROMPTS["fail_response"]
        if return_debug:
            debug_payload["final_context_text"] = context_output
            return context_output, [], debug_payload
        return context_output
    if context is None:
        fail_response = PROMPTS["fail_response"]
        if return_debug:
            debug_payload["final_context_text"] = fail_response
            return fail_response, [], debug_payload
        return fail_response, []

    # Process conversation history
    history_context = ""
    if query_param.conversation_history:
        history_context = get_conversation_turns(
            query_param.conversation_history, query_param.history_turns
        )

    # Build system prompt
    user_prompt = (
        query_param.user_prompt
        if query_param.user_prompt
        else PROMPTS["DEFAULT_USER_PROMPT"]
    )
    sys_prompt_temp = system_prompt if system_prompt else PROMPTS["rag_response"]
    sys_prompt = sys_prompt_temp.format(
        context_data=context,
        response_type=query_param.response_type,
        history=history_context,
        user_prompt=user_prompt,
    )
    debug_payload["final_prompt_text"] = sys_prompt
    _append_stage_timing(
        stage_timings,
        "prompt_assembly",
        "回答提示词拼装",
        0.0,
    )

    if query_param.only_need_prompt:
        if return_debug:
            return sys_prompt, [], debug_payload
        return sys_prompt

    tokenizer: Tokenizer = global_config["tokenizer"]
    len_of_prompts = len(tokenizer.encode(query + sys_prompt))
    logger.debug(
        f"[kg_query] Sending to LLM: {len_of_prompts:,} tokens (Query: {len(tokenizer.encode(query))}, System: {len(tokenizer.encode(sys_prompt))})"
    )

    if cached_response is not None:
        response = cached_response
        _append_stage_timing(
            stage_timings,
            "answer_cache_hit",
            "最终答案缓存命中",
            0.0,
        )
    else:
        stage_started_at = time.perf_counter()
        response = await use_model_func(
            query,
            system_prompt=sys_prompt,
            stream=query_param.stream,
        )
        _record_stage_timing(
            stage_timings,
            "answer_generation",
            "回答生成 / 第一轮 LLM",
            stage_started_at,
        )
        if isinstance(response, str) and len(response) > len(sys_prompt):
            response = (
                response.replace(sys_prompt, "")
                .replace("user", "")
                .replace("model", "")
                .replace(query, "")
                .replace("<system>", "")
                .replace("</system>", "")
                .strip()
            )
        stage_started_at = time.perf_counter()
        response = await use_model_func(
            response,
            system_prompt=PROMPTS["rag_response_new"],
            stream=query_param.stream,
        )
        _record_stage_timing(
            stage_timings,
            "answer_polish",
            "回答润色 / 第二轮 LLM",
            stage_started_at,
        )
    image_file_path_list = []
    if cached_response is None and hashing_kv.global_config.get("enable_llm_cache"):
        # Save to cache
        await save_to_cache(
            hashing_kv,
            CacheData(
                args_hash=args_hash,
                content=response,
                prompt=query,
                quantized=quantized,
                min_val=min_val,
                max_val=max_val,
                mode=query_param.mode,
                cache_type="query",
            ),
        )
    _record_stage_timing(
        stage_timings,
        "onehop_total",
        "OneHop 查询总耗时",
        query_total_started_at,
    )

    if return_debug:
        return response, image_file_path_list, debug_payload

    return response, image_file_path_list


async def get_keywords_from_query(
    query: str,
    query_param: QueryParam,
    global_config: dict[str, str],
    hashing_kv: BaseKVStorage | None = None,
) -> tuple[list[str], list[str]]:
    """
    Retrieves high-level and low-level keywords for RAG operations.

    This function checks if keywords are already provided in query parameters,
    and if not, extracts them from the query text using LLM.

    Args:
        query: The user's query text
        query_param: Query parameters that may contain pre-defined keywords
        global_config: Global configuration dictionary
        hashing_kv: Optional key-value storage for caching results

    Returns:
        A tuple containing (high_level_keywords, low_level_keywords)
    """
    # Check if pre-defined keywords are already provided
    if query_param.hl_keywords or query_param.ll_keywords:
        return query_param.hl_keywords, query_param.ll_keywords

    # Extract keywords using extract_keywords_only function which already supports conversation history
    hl_keywords, ll_keywords = await extract_keywords_only(
        query, query_param, global_config, hashing_kv
    )
    return hl_keywords, ll_keywords


async def extract_keywords_only(
    text: str,
    param: QueryParam,
    global_config: dict[str, str],
    hashing_kv: BaseKVStorage | None = None,
) -> tuple[list[str], list[str]]:
    """
    Extract high-level and low-level keywords from the given 'text' using the LLM.
    This method does NOT build the final RAG context or provide a final answer.
    It ONLY extracts keywords (hl_keywords, ll_keywords).
    """

    # 1. Handle cache if needed - add cache type for keywords
    args_hash = compute_args_hash(param.mode, text)
    cached_response, quantized, min_val, max_val = await handle_cache(
        hashing_kv, args_hash, text, param.mode, cache_type="keywords"
    )
    if cached_response is not None:
        try:
            keywords_data = json.loads(cached_response)
            return keywords_data["high_level_keywords"], keywords_data[
                "low_level_keywords"
            ]
        except (json.JSONDecodeError, KeyError):
            logger.warning(
                "Invalid cache format for keywords, proceeding with extraction"
            )

    # 2. Build the examples
    example_number = global_config["addon_params"].get("example_number", None)
    if example_number and example_number < len(PROMPTS["keywords_extraction_examples"]):
        examples = "\n".join(
            PROMPTS["keywords_extraction_examples"][: int(example_number)]
        )
    else:
        examples = "\n".join(PROMPTS["keywords_extraction_examples"])
    language = global_config["addon_params"].get(
        "language", PROMPTS["DEFAULT_LANGUAGE"]
    )

    # 3. Process conversation history
    history_context = ""
    if param.conversation_history:
        history_context = get_conversation_turns(
            param.conversation_history, param.history_turns
        )

    # 4. Build the keyword-extraction prompt
    kw_prompt = PROMPTS["keywords_extraction"].format(
        query=text, examples=examples, language=language, history=history_context
    )

    tokenizer: Tokenizer = global_config["tokenizer"]
    len_of_prompts = len(tokenizer.encode(kw_prompt))
    logger.debug(
        f"[extract_keywords] Sending to LLM: {len_of_prompts:,} tokens (Prompt: {len_of_prompts})"
    )

    # 5. Call the LLM for keyword extraction
    if param.model_func:
        use_model_func = param.model_func
    else:
        use_model_func = global_config["llm_model_func"]
        # Apply higher priority (5) to query relation LLM function
        use_model_func = partial(use_model_func, _priority=5)

    result = await use_model_func(kw_prompt, keyword_extraction=True)

    # 6. Parse out JSON from the LLM response
    result = remove_think_tags(result)
    match = re.search(r"\{.*?\}", result, re.DOTALL)
    if not match:
        logger.error("No JSON-like structure found in the LLM respond.")
        return [], []
    try:
        keywords_data = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return [], []

    hl_keywords = keywords_data.get("high_level_keywords", [])
    ll_keywords = keywords_data.get("low_level_keywords", [])

    # 7. Cache only the processed keywords with cache type
    if hl_keywords or ll_keywords:
        cache_data = {
            "high_level_keywords": hl_keywords,
            "low_level_keywords": ll_keywords,
        }
        if hashing_kv.global_config.get("enable_llm_cache"):
            await save_to_cache(
                hashing_kv,
                CacheData(
                    args_hash=args_hash,
                    content=json.dumps(cache_data),
                    prompt=text,
                    quantized=quantized,
                    min_val=min_val,
                    max_val=max_val,
                    mode=param.mode,
                    cache_type="keywords",
                ),
            )

    return hl_keywords, ll_keywords



async def _get_vector_context_new(
    query: str,
    chunks_vdb: BaseVectorStorage,
    query_param: QueryParam,
) -> list[dict]:
    """
    Retrieve text chunks from the vector database without reranking or truncation.

    This function performs vector search to find relevant text chunks for a query.
    Reranking and truncation will be handled later in the unified processing.

    Args:
        query: The query string to search for
        chunks_vdb: Vector database containing document chunks
        query_param: Query parameters including chunk_top_k and ids

    Returns:
        List of text chunks with metadata
    """
    try:
        # Use chunk_top_k if specified, otherwise fall back to top_k
        search_top_k = query_param.chunk_top_k or query_param.top_k
        results = await chunks_vdb.query(query, top_k=search_top_k, ids=query_param.ids)
        chunk_weight = {}
        chunk_text = {}
        chunk_file_path = {}
        chunk_metadata = {}
        for rr in results:
            chunk_weight[rr.get("__id__")] = rr.get("__metrics__")
            chunk_text[rr.get("__id__")] = rr.get('content')
            chunk_file_path[rr.get("__id__")] = rr.get("file_path")
            chunk_metadata[rr.get("__id__")] = _extract_chunk_citation_fields(rr)
        return chunk_weight, chunk_text, chunk_file_path, chunk_metadata
    except Exception as e:
        logger.error(f"Error in _get_vector_context: {e}")
        return {}, {}, {}, {}


async def _build_query_context_new(
    query: str,
    ll_keywords: str,
    hl_keywords: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    query_param: QueryParam,
):
    logger.info(f"Process {os.getpid()} building query context...")
    chunk_list = []
    chunk_id_list = []
    chunk_embedding_list=[]
    chunk_file_path_list = []
    if query_param.mode == "hybrid":
        (
            _,
            _,
            node_datas,
            _,
        ) = await _get_node_data(
            ll_keywords,
            knowledge_graph_inst,
            entities_vdb,
            query_param,
        )

        (
            _,
            _,
            _,
            use_entities,
        ) = await _get_edge_data(
            hl_keywords,
            knowledge_graph_inst,
            relationships_vdb,
            query_param,
        )
        for nn in  node_datas:
            if nn.get("entity_type")=='chunk_text':
                chunk_id_list.append(nn.get('entity_id'))
                chunk_list.append(nn.get('description'))
                chunk_embedding_list.append(nn.get('embeddings'))
                chunk_file_path_list.append(nn.get('file_path'))
        for ee in use_entities:
            if ee.get("entity_type")=='chunk_text' and ee.get('entity_id') not in chunk_id_list:
                chunk_id_list.append(ee.get('entity_id'))
                chunk_list.append(ee.get('description'))
                chunk_embedding_list.append(ee.get('embeddings'))
                chunk_file_path_list.append(ee.get('file_path'))
    return chunk_id_list, chunk_list, chunk_embedding_list, chunk_file_path_list



async def _build_query_context(
    query: str,
    ll_keywords: str,
    hl_keywords: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    chunks_vdb: BaseVectorStorage = None,
    timing_collector: list[dict[str, Any]] | None = None,
):
    logger.info(f"Process {os.getpid()} building query context...")
    stage_timings = timing_collector if timing_collector is not None else []
    context_total_started_at = time.perf_counter()

    # Collect all chunks from different sources
    all_chunks = []
    entities_context = []
    relations_context = []

    # Store original data for later text chunk retrieval
    original_node_datas = []
    original_edge_datas = []

    # Handle local and global modes
    if query_param.mode == "graph":
        stage_started_at = time.perf_counter()
        ll_data = await _get_node_data(
            ll_keywords,
            knowledge_graph_inst,
            entities_vdb,
            query_param,
        )
        if timing_collector is not None:
            _record_stage_timing(
                stage_timings,
                "graph_context_entities",
                "图谱上下文补召回 / 实体",
                stage_started_at,
            )
        stage_started_at = time.perf_counter()
        hl_data = await _get_edge_data(
            hl_keywords,
            knowledge_graph_inst,
            relationships_vdb,
            query_param,
        )
        if timing_collector is not None:
            _record_stage_timing(
                stage_timings,
                "graph_context_relations",
                "图谱上下文补召回 / 关系",
                stage_started_at,
            )

        (ll_entities_context, ll_relations_context, ll_node_datas, ll_edge_datas) = (
            ll_data
        )
        (hl_entities_context, hl_relations_context, hl_edge_datas, hl_node_datas) = (
            hl_data
        )

    original_node_datas = ll_node_datas + hl_node_datas
    original_edge_datas = ll_edge_datas + hl_edge_datas

        # Combine entities and relations contexts
    entities_context = process_combine_contexts(
        ll_entities_context, hl_entities_context
    )
    relations_context = process_combine_contexts(
        hl_relations_context, ll_relations_context
    )

    logger.info(
        f"Initial context: {len(entities_context)} entities, {len(relations_context)} relations, {len(all_chunks)} chunks"
    )

    # Unified token control system - Apply precise token limits to entities and relations
    stage_started_at = time.perf_counter()
    tokenizer = text_chunks_db.global_config.get("tokenizer")
    if tokenizer:
        # Get new token limits from query_param (with fallback to global_config)
        max_entity_tokens = getattr(
            query_param,
            "max_entity_tokens",
            text_chunks_db.global_config.get(
                "max_entity_tokens", DEFAULT_MAX_ENTITY_TOKENS
            ),
        )
        max_relation_tokens = getattr(
            query_param,
            "max_relation_tokens",
            text_chunks_db.global_config.get(
                "max_relation_tokens", DEFAULT_MAX_RELATION_TOKENS
            ),
        )
        max_total_tokens = getattr(
            query_param,
            "max_total_tokens",
            text_chunks_db.global_config.get(
                "max_total_tokens", DEFAULT_MAX_TOTAL_TOKENS
            ),
        )

        # Truncate entities based on complete JSON serialization
        if entities_context:
            original_entity_count = len(entities_context)

            # Process entities context to replace GRAPH_FIELD_SEP with : in file_path fields
            for entity in entities_context:
                if "file_path" in entity and entity["file_path"]:
                    entity["file_path"] = entity["file_path"].replace(
                        GRAPH_FIELD_SEP, ";"
                    )

            entities_context = truncate_list_by_token_size(
                entities_context,
                key=lambda x: json.dumps(x, ensure_ascii=False),
                max_token_size=max_entity_tokens,
                tokenizer=tokenizer,
            )
            if len(entities_context) < original_entity_count:
                logger.debug(
                    f"Truncated entities: {original_entity_count} -> {len(entities_context)} (entity max tokens: {max_entity_tokens})"
                )

        # Truncate relations based on complete JSON serialization
        if relations_context:
            original_relation_count = len(relations_context)

            # Process relations context to replace GRAPH_FIELD_SEP with : in file_path fields
            for relation in relations_context:
                if "file_path" in relation and relation["file_path"]:
                    relation["file_path"] = relation["file_path"].replace(
                        GRAPH_FIELD_SEP, ";"
                    )

            relations_context = truncate_list_by_token_size(
                relations_context,
                key=lambda x: json.dumps(x, ensure_ascii=False),
                max_token_size=max_relation_tokens,
                tokenizer=tokenizer,
            )
            if len(relations_context) < original_relation_count:
                logger.debug(
                    f"Truncated relations: {original_relation_count} -> {len(relations_context)} (relation max tokens: {max_relation_tokens})"
                )
    if timing_collector is not None:
        _record_stage_timing(
            stage_timings,
            "graph_context_structured_pruning",
            "图谱上下文整理 / 实体关系裁剪",
            stage_started_at,
        )

    # After truncation, get text chunks based on final entities and relations
    logger.info("Getting text chunks based on truncated entities and relations...")

    # Create filtered data based on truncated context
    final_node_datas = []
    if entities_context and original_node_datas:
        final_entity_names = {e["entity"] for e in entities_context}
        seen_nodes = set()
        for node in original_node_datas:
            name = node.get("entity_name")
            if name in final_entity_names and name not in seen_nodes:
                final_node_datas.append(node)
                seen_nodes.add(name)

    final_edge_datas = []
    if relations_context and original_edge_datas:
        final_relation_pairs = {(r["entity1"], r["entity2"]) for r in relations_context}
        seen_edges = set()
        for edge in original_edge_datas:
            src, tgt = edge.get("src_id"), edge.get("tgt_id")
            if src is None or tgt is None:
                src, tgt = edge.get("src_tgt", (None, None))

            pair = (src, tgt)
            if pair in final_relation_pairs and pair not in seen_edges:
                final_edge_datas.append(edge)
                seen_edges.add(pair)

    # Get text chunks based on final filtered data
    text_chunk_tasks = []

    if final_node_datas:
        text_chunk_tasks.append(
            _find_most_related_text_unit_from_entities(
                final_node_datas,
                query_param,
                text_chunks_db,
                knowledge_graph_inst,
            )
        )

    if final_edge_datas:
        text_chunk_tasks.append(
            _find_related_text_unit_from_relationships(
                final_edge_datas,
                query_param,
                text_chunks_db,
            )
        )

    # Execute text chunk retrieval in parallel
    stage_started_at = time.perf_counter()
    if text_chunk_tasks:
        text_chunk_results = await asyncio.gather(*text_chunk_tasks)
        for chunks in text_chunk_results:
            if chunks:
                all_chunks.extend(chunks)
    if timing_collector is not None:
        _record_stage_timing(
            stage_timings,
            "graph_context_chunk_lookup",
            "图谱上下文补召回 / 文档块",
            stage_started_at,
        )

    # Apply token processing to chunks if tokenizer is available
    text_units_context = []
    stage_started_at = time.perf_counter()
    if tokenizer and all_chunks:
        # Calculate dynamic token limit for text chunks
        entities_str = json.dumps(entities_context, ensure_ascii=False)
        relations_str = json.dumps(relations_context, ensure_ascii=False)

        # Calculate base context tokens (entities + relations + template)
        kg_context_template = """-----Entities(KG)-----

```json
{entities_str}
```

-----Relationships(KG)-----

```json
{relations_str}
```

-----Document Chunks(DC)-----

```json
[]
```

"""
        kg_context = kg_context_template.format(
            entities_str=entities_str, relations_str=relations_str
        )
        kg_context_tokens = len(tokenizer.encode(kg_context))

        # Calculate actual system prompt overhead dynamically
        # 1. Calculate conversation history tokens
        history_context = ""
        if query_param.conversation_history:
            history_context = get_conversation_turns(
                query_param.conversation_history, query_param.history_turns
            )
        history_tokens = (
            len(tokenizer.encode(history_context)) if history_context else 0
        )

        # 2. Calculate system prompt template tokens (excluding context_data)
        user_prompt = query_param.user_prompt if query_param.user_prompt else ""
        response_type = (
            query_param.response_type
            if query_param.response_type
            else "Multiple Paragraphs"
        )

        # Get the system prompt template from PROMPTS
        sys_prompt_template = text_chunks_db.global_config.get(
            "system_prompt_template", PROMPTS["rag_response"]
        )

        # Create a sample system prompt with placeholders filled (excluding context_data)
        sample_sys_prompt = sys_prompt_template.format(
            history=history_context,
            context_data="",  # Empty for overhead calculation
            response_type=response_type,
            user_prompt=user_prompt,
        )
        sys_prompt_template_tokens = len(tokenizer.encode(sample_sys_prompt))

        # Total system prompt overhead = template + query tokens
        query_tokens = len(tokenizer.encode(query))
        sys_prompt_overhead = sys_prompt_template_tokens + query_tokens

        buffer_tokens = 100  # Safety buffer as requested

        # Calculate available tokens for text chunks
        used_tokens = kg_context_tokens + sys_prompt_overhead + buffer_tokens
        available_chunk_tokens = max_total_tokens - used_tokens

        logger.debug(
            f"Token allocation - Total: {max_total_tokens}, History: {history_tokens}, SysPrompt: {sys_prompt_overhead}, KG: {kg_context_tokens}, Buffer: {buffer_tokens}, Available for chunks: {available_chunk_tokens}"
        )

        # Re-process chunks with dynamic token limit
        if all_chunks:
            # Create a temporary query_param copy with adjusted chunk token limit
            temp_chunks = [chunk.copy() for chunk in all_chunks]

            # Apply token truncation to chunks using the dynamic limit
            truncated_chunks = await process_chunks_unified(
                query=query,
                chunks=temp_chunks,
                query_param=query_param,
                global_config=text_chunks_db.global_config,
                source_type="mixed",
                chunk_token_limit=available_chunk_tokens,  # Pass dynamic limit
            )

            # Rebuild text_units_context with truncated chunks
            for i, chunk in enumerate(truncated_chunks):
                text_units_context.append(_build_chunk_context_entry(i + 1, chunk))

            logger.debug(
                f"Re-truncated chunks for dynamic token limit: {len(temp_chunks)} -> {len(text_units_context)} (chunk available tokens: {available_chunk_tokens})"
            )
    if timing_collector is not None:
        _record_stage_timing(
            stage_timings,
            "graph_context_chunk_postprocess",
            "图谱上下文整理 / Chunk 重排与截断",
            stage_started_at,
        )

    logger.info(
        f"Final context: {len(entities_context)} entities, {len(relations_context)} relations, {len(text_units_context)} chunks"
    )

    # not necessary to use LLM to generate a response
    if not entities_context and not relations_context:
        if timing_collector is not None:
            _record_stage_timing(
                stage_timings,
                "graph_context_total",
                "图谱上下文构建总耗时",
                context_total_started_at,
            )
        return None

    stage_started_at = time.perf_counter()
    entities_str = json.dumps(entities_context, ensure_ascii=False)
    relations_str = json.dumps(relations_context, ensure_ascii=False)
    text_units_str = json.dumps(text_units_context, ensure_ascii=False)

    result = f"""-----Entities(KG)-----

```json
{entities_str}
```

-----Relationships(KG)-----

```json
{relations_str}
```

-----Document Chunks(DC)-----

```json
{text_units_str}
```

"""
    if timing_collector is not None:
        _record_stage_timing(
            stage_timings,
            "graph_context_serialize",
            "图谱上下文整理 / 序列化",
            stage_started_at,
        )
        _record_stage_timing(
            stage_timings,
            "graph_context_total",
            "图谱上下文构建总耗时",
            context_total_started_at,
        )
    return result


async def _get_node_data(
    query: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    query_param: QueryParam,
):
    # get similar entities
    logger.info(
        f"Query nodes: {query}, top_k: {query_param.top_k}, cosine: {entities_vdb.cosine_better_than_threshold}"
    )

    results = await entities_vdb.query(
        query, top_k=query_param.top_k, ids=query_param.ids
    )
    if not len(results):
        return "", "", [], []

    # Extract all entity IDs from your results list
    node_ids = [r["entity_name"] for r in results]

    # Call the batch node retrieval and degree functions concurrently.
    nodes_dict, degrees_dict = await asyncio.gather(
        knowledge_graph_inst.get_nodes_batch(node_ids),
        knowledge_graph_inst.node_degrees_batch(node_ids),
    )

    # Now, if you need the node data and degree in order:
    node_datas = [nodes_dict.get(nid) for nid in node_ids]
    node_degrees = [degrees_dict.get(nid, 0) for nid in node_ids]

    if not all([n is not None for n in node_datas]):
        logger.warning("Some nodes are missing, maybe the storage is damaged")

    node_datas = [
        {
            **n,
            "entity_name": k["entity_name"],
            "rank": d,
            "created_at": k.get("created_at"),
        }
        for k, n, d in zip(results, node_datas, node_degrees)
        if n is not None
    ]

    use_relations = await _find_most_related_edges_from_entities(
        node_datas,
        query_param,
        knowledge_graph_inst,
    )

    logger.info(
        f"Local query: {len(node_datas)} entites, {len(use_relations)} relations"
    )

    # build prompt
    entities_context = []
    for i, n in enumerate(node_datas):
        created_at = n.get("created_at", "UNKNOWN")
        if isinstance(created_at, (int, float)):
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))

        # Get file path from node data
        file_path = n.get("file_path", "unknown_source")

        entities_context.append(
            {
                "id": i + 1,
                "entity": n["entity_name"],
                "type": n.get("entity_type", "UNKNOWN"),
                "description": n.get("description", "UNKNOWN"),
                "created_at": created_at,
                "file_path": file_path,
                "source_chunk_ids": n.get("source_chunk_ids") or n.get("source_id", ""),
            }
        )

    relations_context = []
    for i, e in enumerate(use_relations):
        created_at = e.get("created_at", "UNKNOWN")
        # Convert timestamp to readable format
        if isinstance(created_at, (int, float)):
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))

        # Get file path from edge data
        file_path = e.get("file_path", "unknown_source")

        relations_context.append(
            {
                "id": i + 1,
                "entity1": e["src_tgt"][0],
                "entity2": e["src_tgt"][1],
                "description": e["description"],
                "created_at": created_at,
                "file_path": file_path,
                "source_chunk_ids": e.get("source_chunk_ids") or e.get("source_id", ""),
            }
        )

    return entities_context, relations_context, node_datas, use_relations


async def _find_most_related_text_unit_from_entities(
    node_datas: list[dict],
    query_param: QueryParam,
    text_chunks_db: BaseKVStorage,
    knowledge_graph_inst: BaseGraphStorage,
):
    logger.debug(f"Searching text chunks for {len(node_datas)} entities")

    text_units = [
        _normalize_source_chunk_ids(
            dp.get("source_chunk_ids") or dp.get("source_id")
        )[
            : text_chunks_db.global_config.get(
                "related_chunk_number", DEFAULT_RELATED_CHUNK_NUMBER
            )
        ]
        for dp in node_datas
        if (dp.get("source_chunk_ids") or dp.get("source_id")) is not None
    ]

    node_names = [dp["entity_name"] for dp in node_datas]
    batch_edges_dict = await knowledge_graph_inst.get_nodes_edges_batch(node_names)
    # Build the edges list in the same order as node_datas.
    edges = [batch_edges_dict.get(name, []) for name in node_names]

    all_one_hop_nodes = set()
    for this_edges in edges:
        if not this_edges:
            continue
        all_one_hop_nodes.update([e[1] for e in this_edges])

    all_one_hop_nodes = list(all_one_hop_nodes)

    # Batch retrieve one-hop node data using get_nodes_batch
    all_one_hop_nodes_data_dict = await knowledge_graph_inst.get_nodes_batch(
        all_one_hop_nodes
    )
    all_one_hop_nodes_data = [
        all_one_hop_nodes_data_dict.get(e) for e in all_one_hop_nodes
    ]

    # Add null check for node data
    all_one_hop_text_units_lookup = {
        k: set(
            _normalize_source_chunk_ids(
                v.get("source_chunk_ids") or v.get("source_id")
            )
        )
        for k, v in zip(all_one_hop_nodes, all_one_hop_nodes_data)
        if v is not None and (v.get("source_chunk_ids") or v.get("source_id"))
    }

    all_text_units_lookup = {}
    tasks = []

    for index, (this_text_units, this_edges) in enumerate(zip(text_units, edges)):
        for c_id in this_text_units:
            if c_id not in all_text_units_lookup:
                all_text_units_lookup[c_id] = index
                tasks.append((c_id, index, this_edges))

    # Process in batches tasks at a time to avoid overwhelming resources
    batch_size = 5
    results = []

    for i in range(0, len(tasks), batch_size):
        batch_tasks = tasks[i : i + batch_size]
        batch_results = await asyncio.gather(
            *[text_chunks_db.get_by_id(c_id) for c_id, _, _ in batch_tasks]
        )
        results.extend(batch_results)

    for (c_id, index, this_edges), data in zip(tasks, results):
        all_text_units_lookup[c_id] = {
            "data": data,
            "order": index,
            "relation_counts": 0,
        }

        if this_edges:
            for e in this_edges:
                if (
                    e[1] in all_one_hop_text_units_lookup
                    and c_id in all_one_hop_text_units_lookup[e[1]]
                ):
                    all_text_units_lookup[c_id]["relation_counts"] += 1

    # Filter out None values and ensure data has content
    all_text_units = [
        {"id": k, **v}
        for k, v in all_text_units_lookup.items()
        if v is not None and v.get("data") is not None and "content" in v["data"]
    ]

    if not all_text_units:
        logger.warning("No valid text units found")
        return []

    # Sort by relation counts and order, but don't truncate
    all_text_units = sorted(
        all_text_units, key=lambda x: (x["order"], -x["relation_counts"])
    )

    logger.debug(f"Found {len(all_text_units)} entity-related chunks")

    # Add source type marking and return chunk data
    result_chunks = []
    for t in all_text_units:
        chunk_data = t["data"].copy()
        chunk_data["source_type"] = "entity"
        result_chunks.append(chunk_data)

    return result_chunks


async def _find_most_related_edges_from_entities(
    node_datas: list[dict],
    query_param: QueryParam,
    knowledge_graph_inst: BaseGraphStorage,
):
    node_names = [dp["entity_name"] for dp in node_datas]
    batch_edges_dict = await knowledge_graph_inst.get_nodes_edges_batch(node_names)

    all_edges = []
    seen = set()

    for node_name in node_names:
        this_edges = batch_edges_dict.get(node_name, [])
        for e in this_edges:
            sorted_edge = tuple(sorted(e))
            if sorted_edge not in seen:
                seen.add(sorted_edge)
                all_edges.append(sorted_edge)

    # Prepare edge pairs in two forms:
    # For the batch edge properties function, use dicts.
    edge_pairs_dicts = [{"src": e[0], "tgt": e[1]} for e in all_edges]
    # For edge degrees, use tuples.
    edge_pairs_tuples = list(all_edges)  # all_edges is already a list of tuples

    # Call the batched functions concurrently.
    edge_data_dict, edge_degrees_dict = await asyncio.gather(
        knowledge_graph_inst.get_edges_batch(edge_pairs_dicts),
        knowledge_graph_inst.edge_degrees_batch(edge_pairs_tuples),
    )

    # Reconstruct edge_datas list in the same order as the deduplicated results.
    all_edges_data = []
    for pair in all_edges:
        edge_props = edge_data_dict.get(pair)
        if edge_props is not None:
            if "weight" not in edge_props:
                logger.warning(
                    f"Edge {pair} missing 'weight' attribute, using default value 0.0"
                )
                edge_props["weight"] = 0.0

            combined = {
                "src_tgt": pair,
                "rank": edge_degrees_dict.get(pair, 0),
                **edge_props,
            }
            all_edges_data.append(combined)

    all_edges_data = sorted(
        all_edges_data, key=lambda x: (x["rank"], x["weight"]), reverse=True
    )

    return all_edges_data


async def _get_edge_data(
    keywords,
    knowledge_graph_inst: BaseGraphStorage,
    relationships_vdb: BaseVectorStorage,
    query_param: QueryParam,
):
    logger.info(
        f"Query edges: {keywords}, top_k: {query_param.top_k}, cosine: {relationships_vdb.cosine_better_than_threshold}"
    )

    results = await relationships_vdb.query(
        keywords, top_k=query_param.top_k, ids=query_param.ids
    )

    if not len(results):
        return "", "", [], []

    # Prepare edge pairs in two forms:
    # For the batch edge properties function, use dicts.
    edge_pairs_dicts = [{"src": r["src_id"], "tgt": r["tgt_id"]} for r in results]
    # For edge degrees, use tuples.
    edge_pairs_tuples = [(r["src_id"], r["tgt_id"]) for r in results]

    # Call the batched functions concurrently.
    edge_data_dict, edge_degrees_dict = await asyncio.gather(
        knowledge_graph_inst.get_edges_batch(edge_pairs_dicts),
        knowledge_graph_inst.edge_degrees_batch(edge_pairs_tuples),
    )

    # Reconstruct edge_datas list in the same order as results.
    edge_datas = []
    for k in results:
        pair = (k["src_id"], k["tgt_id"])
        edge_props = edge_data_dict.get(pair)
        if edge_props is not None:
            if "weight" not in edge_props:
                logger.warning(
                    f"Edge {pair} missing 'weight' attribute, using default value 0.0"
                )
                edge_props["weight"] = 0.0

            # Use edge degree from the batch as rank.
            combined = {
                "src_id": k["src_id"],
                "tgt_id": k["tgt_id"],
                "rank": edge_degrees_dict.get(pair, k.get("rank", 0)),
                "created_at": k.get("created_at", None),
                **edge_props,
            }
            edge_datas.append(combined)

    edge_datas = sorted(
        edge_datas, key=lambda x: (x["rank"], x["weight"]), reverse=True
    )

    use_entities = await _find_most_related_entities_from_relationships(
        edge_datas,
        query_param,
        knowledge_graph_inst,
    )

    logger.info(
        f"Global query: {len(use_entities)} entites, {len(edge_datas)} relations"
    )

    relations_context = []
    for i, e in enumerate(edge_datas):
        created_at = e.get("created_at", "UNKNOWN")
        # Convert timestamp to readable format
        if isinstance(created_at, (int, float)):
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))

        # Get file path from edge data
        file_path = e.get("file_path", "unknown_source")

        relations_context.append(
            {
                "id": i + 1,
                "entity1": e["src_id"],
                "entity2": e["tgt_id"],
                "description": e["description"],
                "created_at": created_at,
                "file_path": file_path,
                "source_chunk_ids": e.get("source_chunk_ids") or e.get("source_id", ""),
            }
        )

    entities_context = []
    for i, n in enumerate(use_entities):
        created_at = n.get("created_at", "UNKNOWN")
        # Convert timestamp to readable format
        if isinstance(created_at, (int, float)):
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))

        # Get file path from node data
        file_path = n.get("file_path", "unknown_source")

        entities_context.append(
            {
                "id": i + 1,
                "entity": n["entity_name"],
                "type": n.get("entity_type", "UNKNOWN"),
                "description": n.get("description", "UNKNOWN"),
                "created_at": created_at,
                "file_path": file_path,
                "source_chunk_ids": n.get("source_chunk_ids") or n.get("source_id", ""),
            }
        )

    # Return original data for later text chunk retrieval
    return entities_context, relations_context, edge_datas, use_entities


async def _find_most_related_entities_from_relationships(
    edge_datas: list[dict],
    query_param: QueryParam,
    knowledge_graph_inst: BaseGraphStorage,
):
    entity_names = []
    seen = set()

    for e in edge_datas:
        if e["src_id"] not in seen:
            entity_names.append(e["src_id"])
            seen.add(e["src_id"])
        if e["tgt_id"] not in seen:
            entity_names.append(e["tgt_id"])
            seen.add(e["tgt_id"])

    # Batch approach: Retrieve nodes and their degrees concurrently with one query each.
    nodes_dict, degrees_dict = await asyncio.gather(
        knowledge_graph_inst.get_nodes_batch(entity_names),
        knowledge_graph_inst.node_degrees_batch(entity_names),
    )

    # Rebuild the list in the same order as entity_names
    node_datas = []
    for entity_name in entity_names:
        node = nodes_dict.get(entity_name)
        degree = degrees_dict.get(entity_name, 0)
        if node is None:
            logger.warning(f"Node '{entity_name}' not found in batch retrieval.")
            continue
        # Combine the node data with the entity name and computed degree (as rank)
        combined = {**node, "entity_name": entity_name, "rank": degree}
        node_datas.append(combined)

    return node_datas


async def _find_related_text_unit_from_relationships(
    edge_datas: list[dict],
    query_param: QueryParam,
    text_chunks_db: BaseKVStorage,
):
    logger.debug(f"Searching text chunks for {len(edge_datas)} relationships")

    text_units = [
        _normalize_source_chunk_ids(
            dp.get("source_chunk_ids") or dp.get("source_id")
        )[
            : text_chunks_db.global_config.get(
                "related_chunk_number", DEFAULT_RELATED_CHUNK_NUMBER
            )
        ]
        for dp in edge_datas
        if (dp.get("source_chunk_ids") or dp.get("source_id")) is not None
    ]
    all_text_units_lookup = {}

    async def fetch_chunk_data(c_id, index):
        if c_id not in all_text_units_lookup:
            chunk_data = await text_chunks_db.get_by_id(c_id)
            # Only store valid data
            if chunk_data is not None and "content" in chunk_data:
                all_text_units_lookup[c_id] = {
                    "data": chunk_data,
                    "order": index,
                }

    tasks = []
    for index, unit_list in enumerate(text_units):
        for c_id in unit_list:
            tasks.append(fetch_chunk_data(c_id, index))

    await asyncio.gather(*tasks)

    if not all_text_units_lookup:
        logger.warning("No valid text chunks found")
        return []

    all_text_units = [{"id": k, **v} for k, v in all_text_units_lookup.items()]
    all_text_units = sorted(all_text_units, key=lambda x: x["order"])

    # Ensure all text chunks have content
    valid_text_units = [
        t for t in all_text_units if t["data"] is not None and "content" in t["data"]
    ]

    if not valid_text_units:
        logger.warning("No valid text chunks after filtering")
        return []

    logger.debug(f"Found {len(valid_text_units)} relationship-related chunks")

    # Add source type marking and return chunk data
    result_chunks = []
    for t in valid_text_units:
        chunk_data = t["data"].copy()
        chunk_data["source_type"] = "relationship"
        result_chunks.append(chunk_data)

    return result_chunks

def weightd_merge(
    chunk1: dict[str, float], chunk2: dict[str, float], alpha: float = 0.5
):
    def min_max_normalize(chunks):
        if len(chunks) == 0:
            return {}
        scores = chunks.values()
        max_score = max(scores)
        min_score = min(scores)
        ret_docs = {}
        for doc_id, score in chunks.items():
            if math.isclose(max_score, min_score, rel_tol=1e-9):
                score = 1
            else:
                score = (score - min_score) / (max_score - min_score)
            ret_docs[doc_id] = score
        return ret_docs

    chunk1 = min_max_normalize(chunk1)
    chunk2 = min_max_normalize(chunk2)

    merged = {}
    for doc_id, score in chunk1.items():
        if doc_id in merged:
            merged_score = merged[doc_id]
            merged_score += score * alpha
            merged[doc_id] = merged_score
        else:
            merged[doc_id] = score * alpha

    for doc_id, score in chunk2.items():
        if doc_id in merged:
            merged_score = merged[doc_id]
            merged_score += score * (1 - alpha)
            merged[doc_id] = merged_score
        else:
            merged[doc_id] = score * (1 - alpha)

    return merged

def cosine_similarity(query_embedding, chunk_embedding_list) -> list:
    query_vector = _coerce_embedding_array(query_embedding)
    if query_vector is None:
        logger.warning(
            "Skipping graph chunk rescoring because the query embedding is empty or invalid."
        )
        return [0.0] * len(chunk_embedding_list)

    similarity_list = []
    for ce in chunk_embedding_list:
        np_ce = _coerce_embedding_array(ce)
        if np_ce is None or np_ce.shape != query_vector.shape:
            similarity_list.append(0.0)
            continue
        dot_product = np.dot(np_ce, query_vector)
        norm_a = np.linalg.norm(np_ce)
        norm_b = np.linalg.norm(query_vector)
        if norm_a == 0 or norm_b == 0:
            similarity_list.append(0.0)
        else:
            similarity_list.append(float(dot_product / (norm_a * norm_b)))
    return similarity_list


def _resolve_hybrid_chunk_candidate(
    chunk_id: str,
    vector_text_map: dict[str, str],
    vector_file_path_map: dict[str, str],
    vector_metadata_map: dict[str, dict[str, Any]],
    graph_text_map: dict[str, str],
    graph_file_path_map: dict[str, str],
    graph_metadata_map: dict[str, dict[str, Any]],
) -> tuple[str, str, list[str], str, dict[str, Any]]:
    sources = []
    if chunk_id in vector_text_map:
        sources.append("vector")
    if chunk_id in graph_text_map:
        sources.append("graph")

    chunk_text = vector_text_map.get(chunk_id) or graph_text_map.get(chunk_id, "")
    file_path = vector_file_path_map.get(chunk_id, "unknown_source")
    if file_path in (None, "", "unknown_source"):
        file_path = graph_file_path_map.get(chunk_id, file_path or "unknown_source")
    elif chunk_id not in vector_file_path_map:
        file_path = graph_file_path_map.get(chunk_id, file_path)

    citation_metadata = {}
    for metadata_map in (graph_metadata_map, vector_metadata_map):
        metadata = metadata_map.get(chunk_id, {})
        for key, value in metadata.items():
            if value not in (None, "", [], {}):
                citation_metadata[key] = value
    if file_path not in (None, "", "unknown_source"):
        citation_metadata["file_path"] = file_path

    source_label = "+".join(sources) if sources else "unknown"
    return chunk_text, file_path, sources, source_label, citation_metadata


async def _build_hybrid_retrieval_debug_data(
    query: str,
    chunks_vdb: BaseVectorStorage,
    knowledge_graph_inst: BaseGraphStorage,
    relationships_vdb: BaseVectorStorage,
    entities_vdb: BaseVectorStorage,
    query_param: QueryParam,
    global_config: dict[str, str],
    hashing_kv: BaseKVStorage | None = None,
) -> dict[str, Any]:
    stage_timings: list[dict[str, Any]] = []
    retrieval_total_started_at = time.perf_counter()
    stage_started_at = time.perf_counter()
    vector_weights, vector_texts, vector_file_paths, vector_metadata_map = await _get_vector_context_new(
        query, chunks_vdb, query_param
    )
    _record_stage_timing(
        stage_timings,
        "vector_retrieval",
        "混合召回 / Chunk 向量检索",
        stage_started_at,
    )

    stage_started_at = time.perf_counter()
    hl_keywords, ll_keywords = await get_keywords_from_query(
        query, query_param, global_config, hashing_kv
    )
    _record_stage_timing(
        stage_timings,
        "keyword_extraction",
        "关键词提取",
        stage_started_at,
    )

    logger.debug(f"High-level keywords: {hl_keywords}")
    logger.debug(f"Low-level  keywords: {ll_keywords}")

    ll_keywords_str = ", ".join(ll_keywords) if ll_keywords else ""
    hl_keywords_str = ", ".join(hl_keywords) if hl_keywords else ""

    stage_started_at = time.perf_counter()
    ll_entities_context, ll_relations_context, ll_node_datas, _ = await _get_node_data(
        ll_keywords_str,
        knowledge_graph_inst,
        entities_vdb,
        query_param,
    )
    _record_stage_timing(
        stage_timings,
        "graph_entity_hits",
        "图谱命中 / 实体",
        stage_started_at,
    )
    stage_started_at = time.perf_counter()
    hl_entities_context, hl_relations_context, _, hl_use_entities = await _get_edge_data(
        hl_keywords_str,
        knowledge_graph_inst,
        relationships_vdb,
        query_param,
    )
    _record_stage_timing(
        stage_timings,
        "graph_relation_hits",
        "图谱命中 / 关系",
        stage_started_at,
    )

    graph_entities = process_combine_contexts(
        ll_entities_context, hl_entities_context
    )
    graph_relations = process_combine_contexts(
        hl_relations_context, ll_relations_context
    )

    chunk_ids = []
    chunk_texts = []
    chunk_embeddings = []
    chunk_file_paths = []
    chunk_metadata_list = []
    seen_chunk_ids = set()

    for item in ll_node_datas:
        if item.get("entity_type") != "chunk_text":
            continue
        chunk_id = item.get("entity_id")
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        chunk_ids.append(chunk_id)
        chunk_texts.append(item.get("description", ""))
        chunk_embeddings.append(item.get("embeddings"))
        chunk_file_paths.append(item.get("file_path", "unknown_source"))
        chunk_metadata_list.append(_extract_chunk_citation_fields(item))

    for item in hl_use_entities:
        if item.get("entity_type") != "chunk_text":
            continue
        chunk_id = item.get("entity_id")
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        chunk_ids.append(chunk_id)
        chunk_texts.append(item.get("description", ""))
        chunk_embeddings.append(item.get("embeddings"))
        chunk_file_paths.append(item.get("file_path", "unknown_source"))
        chunk_metadata_list.append(_extract_chunk_citation_fields(item))

    graph_weights = {}
    graph_text_map = {}
    graph_file_path_map = {}
    graph_metadata_map = {}
    valid_chunk_ids = []
    valid_chunk_embeddings = []
    skipped_invalid_graph_embeddings = 0

    for chunk_id, text, embedding, file_path, chunk_metadata in zip(
        chunk_ids, chunk_texts, chunk_embeddings, chunk_file_paths, chunk_metadata_list
    ):
        graph_text_map[chunk_id] = text
        graph_file_path_map[chunk_id] = file_path
        graph_metadata_map[chunk_id] = chunk_metadata
        embedding_array = _coerce_embedding_array(embedding)
        if embedding_array is None:
            skipped_invalid_graph_embeddings += 1
            continue
        valid_chunk_ids.append(chunk_id)
        valid_chunk_embeddings.append(embedding_array)

    stage_started_at = time.perf_counter()
    if skipped_invalid_graph_embeddings:
        logger.warning(
            "Skipping %s graph chunk candidates with empty or invalid embeddings during hybrid rescoring.",
            skipped_invalid_graph_embeddings,
        )
    if valid_chunk_embeddings:
        query_embedding = await openai_embed([query])
        similarity_scores = cosine_similarity(
            query_embedding[0], valid_chunk_embeddings
        )
        for chunk_id, score in zip(valid_chunk_ids, similarity_scores):
            graph_weights[chunk_id] = score
    _record_stage_timing(
        stage_timings,
        "graph_chunk_rescoring",
        "混合召回 / 图谱候选重打分",
        stage_started_at,
    )

    stage_started_at = time.perf_counter()
    merge_weight = weightd_merge(vector_weights, graph_weights)
    sorted_items = sorted(merge_weight.items(), key=lambda x: x[1], reverse=True)
    topk_text = sorted_items[:20]

    results_text = []
    results_file_paths = []
    results_chunk_ids = []
    results_sources = []
    results_source_labels = []
    results_chunk_metadata = []
    image_file_path_list = []
    merged_candidates = []

    for index, (chunk_id, score) in enumerate(topk_text, 1):
        chunk_text, file_path, sources, source_label, chunk_metadata = _resolve_hybrid_chunk_candidate(
            chunk_id,
            vector_texts,
            vector_file_paths,
            vector_metadata_map,
            graph_text_map,
            graph_file_path_map,
            graph_metadata_map,
        )
        results_text.append(chunk_text)
        results_file_paths.append(file_path)
        results_chunk_ids.append(chunk_id)
        results_sources.append(sources)
        results_source_labels.append(source_label)
        results_chunk_metadata.append(chunk_metadata)
        image_file_path_list.append(file_path)
        merged_candidate = {
            "rank": index,
            "source": source_label,
            "sources": sources,
            "chunk_id": chunk_id,
            "score": score,
            "file_path": file_path,
            "content": chunk_text,
        }
        merged_candidate.update(chunk_metadata)
        merged_candidates.append(merged_candidate)
    _record_stage_timing(
        stage_timings,
        "candidate_merge",
        "混合召回 / 候选融合",
        stage_started_at,
    )

    rerank_results = []
    stage_started_at = time.perf_counter()
    if results_text:
        rerank_results = await rerank_from_env(
            query=query,
            documents=results_text,
            top_k=10,
        )
    _record_stage_timing(
        stage_timings,
        "rerank",
        "Rerank 重排",
        stage_started_at,
    )

    text_units_context = []
    stage_started_at = time.perf_counter()
    top_k_l = min(len(rerank_results), 10)
    for i in range(top_k_l):
        rerank_index = rerank_results[i]["index"]
        if not isinstance(rerank_index, int) or not (0 <= rerank_index < len(results_text)):
            continue
        chunk_entry = {
            "content": results_text[rerank_index],
            "file_path": results_file_paths[rerank_index],
        }
        chunk_entry.update(results_chunk_metadata[rerank_index])
        text_units_context.append(_build_chunk_context_entry(i + 1, chunk_entry))
    _record_stage_timing(
        stage_timings,
        "final_context_selection",
        "最终证据选择",
        stage_started_at,
    )

    image_file_path_list = set(image_file_path_list)
    image_file_path_list.discard("unknown_source")
    _record_stage_timing(
        stage_timings,
        "hybrid_retrieval_total",
        "混合检索总耗时",
        retrieval_total_started_at,
    )

    return {
        "high_level_keywords": hl_keywords,
        "low_level_keywords": ll_keywords,
        "ll_keywords_str": ll_keywords_str,
        "hl_keywords_str": hl_keywords_str,
        "graph_entities": graph_entities,
        "graph_relations": graph_relations,
        "vector_weights": vector_weights,
        "vector_texts": vector_texts,
        "vector_file_paths": vector_file_paths,
        "vector_metadata_map": vector_metadata_map,
        "graph_weights": graph_weights,
        "graph_texts": graph_text_map,
        "graph_file_paths": graph_file_path_map,
        "graph_metadata_map": graph_metadata_map,
        "merged_candidates": merged_candidates,
        "rerank_results": rerank_results,
        "results_text": results_text,
        "results_file_paths": results_file_paths,
        "results_chunk_ids": results_chunk_ids,
        "results_sources": results_sources,
        "results_source_labels": results_source_labels,
        "results_chunk_metadata": results_chunk_metadata,
        "text_units_context": text_units_context,
        "image_file_path_list": image_file_path_list,
        "stage_timings": stage_timings,
    }

async def hybrid_query(
    query: str,
    chunks_vdb: BaseVectorStorage,
    knowledge_graph_inst: BaseGraphStorage,
    relationships_vdb: BaseVectorStorage,
    entities_vdb: BaseVectorStorage,
    query_param: QueryParam,
    global_config: dict[str, str],
    hashing_kv: BaseKVStorage | None = None,
    system_prompt: str | None = None,
    return_debug: bool = False,
):
    stage_timings: list[dict[str, Any]] = []
    query_total_started_at = time.perf_counter()
    if query_param.model_func:
        use_model_func = query_param.model_func
    else:
        use_model_func = global_config["llm_model_func"]
        # Apply higher priority (5) to query relation LLM function
        use_model_func = partial(use_model_func, _priority=5)
    args_hash = compute_args_hash(query_param.mode, query)
    stage_started_at = time.perf_counter()
    cached_response, quantized, min_val, max_val = await handle_cache(
        hashing_kv, args_hash, query, query_param.mode, cache_type="query"
    )
    _record_stage_timing(
        stage_timings,
        "query_cache_lookup",
        "查询缓存检查",
        stage_started_at,
    )

    retrieval_debug = await _build_hybrid_retrieval_debug_data(
        query=query,
        chunks_vdb=chunks_vdb,
        knowledge_graph_inst=knowledge_graph_inst,
        relationships_vdb=relationships_vdb,
        entities_vdb=entities_vdb,
        query_param=query_param,
        global_config=global_config,
        hashing_kv=hashing_kv,
    )
    stage_timings.extend(retrieval_debug.get("stage_timings", []))

    image_file_path_list = retrieval_debug["image_file_path_list"]
    results_text = retrieval_debug["results_text"]
    results_file_paths = retrieval_debug["results_file_paths"]
    results_chunk_metadata = retrieval_debug["results_chunk_metadata"]
    result_chunk = retrieval_debug["rerank_results"]

    top_k_l = min(len(result_chunk), 10)
    text_units_context = []

    for i in range(top_k_l):
        rerank_index = result_chunk[i]["index"]
        if not isinstance(rerank_index, int) or not (0 <= rerank_index < len(results_text)):
            continue
        chunk_entry = {
            "content": results_text[rerank_index],
            "file_path": results_file_paths[rerank_index],
        }
        chunk_entry.update(results_chunk_metadata[rerank_index])
        text_units_context.append(_build_chunk_context_entry(i + 1, chunk_entry))

    text_units_str = json.dumps(text_units_context, ensure_ascii=False)
    context_text = f"""
---Document Chunks---

```json
{text_units_str}
```

"""
    tokenizer: Tokenizer = global_config["tokenizer"]
    if query_param.only_need_context:
        if return_debug:
            debug_payload = {
                **retrieval_debug,
                "final_context_document_chunks": text_units_context,
                "final_context_text": context_text,
                "final_prompt_text": "",
                "stage_timings": stage_timings,
            }
            return context_text, image_file_path_list, debug_payload
        return context_text
    # Process conversation history
    history_context = ""
    if query_param.conversation_history:
        history_context = get_conversation_turns(
            query_param.conversation_history, query_param.history_turns
        )

    # Build system prompt
    user_prompt = (
        query_param.user_prompt
        if query_param.user_prompt
        else PROMPTS["DEFAULT_USER_PROMPT"]
    )
    sys_prompt_temp = system_prompt if system_prompt else PROMPTS["naive_rag_response"]
    sys_prompt = sys_prompt_temp.format(
        content_data=text_units_str,
        response_type=query_param.response_type,
        history=history_context,
        user_prompt=user_prompt,
    )
    _append_stage_timing(
        stage_timings,
        "prompt_assembly",
        "回答提示词拼装",
        0.0,
    )
    if query_param.only_need_prompt:
        if return_debug:
            debug_payload = {
                **retrieval_debug,
                "final_context_document_chunks": text_units_context,
                "final_context_text": context_text,
                "final_prompt_text": sys_prompt,
                "stage_timings": stage_timings,
            }
            return sys_prompt, image_file_path_list, debug_payload
        return sys_prompt

    len_of_prompts = len(tokenizer.encode(query + sys_prompt))
    logger.debug(
        f"[naive_query] Sending to LLM: {len_of_prompts:,} tokens (Query: {len(tokenizer.encode(query))}, System: {len(tokenizer.encode(sys_prompt))})"
    )

    stage_started_at = time.perf_counter()
    response = await use_model_func(
        query,
        system_prompt=sys_prompt,
        stream=query_param.stream,
    )
    _record_stage_timing(
        stage_timings,
        "answer_generation",
        "回答生成 / 第一轮 LLM",
        stage_started_at,
    )

    if isinstance(response, str) and len(response) > len(sys_prompt):
        response = (
            response[len(sys_prompt) :]
            .replace(sys_prompt, "")
            .replace("user", "")
            .replace("model", "")
            .replace(query, "")
            .replace("<system>", "")
            .replace("</system>", "")
            .strip()
        )
    stage_started_at = time.perf_counter()
    response = await use_model_func(
        response,
        system_prompt=PROMPTS["naive_rag_response_new"],
        stream=query_param.stream,
    )
    _record_stage_timing(
        stage_timings,
        "answer_polish",
        "回答润色 / 第二轮 LLM",
        stage_started_at,
    )
    if hashing_kv.global_config.get("enable_llm_cache"):
        # Save to cache
        await save_to_cache(
            hashing_kv,
            CacheData(
                args_hash=args_hash,
                content=response,
                prompt=query,
                quantized=quantized,
                min_val=min_val,
                max_val=max_val,
                mode=query_param.mode,
                cache_type="query",
            ),
        )
    _record_stage_timing(
        stage_timings,
        "onehop_total",
        "OneHop 查询总耗时",
        query_total_started_at,
    )

    if return_debug:
        debug_payload = {
            **retrieval_debug,
            "final_context_document_chunks": text_units_context,
            "final_context_text": context_text,
            "final_prompt_text": sys_prompt,
            "stage_timings": stage_timings,
        }
        return response, image_file_path_list, debug_payload

    return response, image_file_path_list


async def kg_query_with_keywords(
    query: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    global_config: dict[str, str],
    hashing_kv: BaseKVStorage | None = None,
    ll_keywords: list[str] = [],
    hl_keywords: list[str] = [],
    chunks_vdb: BaseVectorStorage | None = None,
) -> str | AsyncIterator[str]:
    """
    Refactored kg_query that does NOT extract keywords by itself.
    It expects hl_keywords and ll_keywords to be set in query_param, or defaults to empty.
    Then it uses those to build context and produce a final LLM response.
    """
    if query_param.model_func:
        use_model_func = query_param.model_func
    else:
        use_model_func = global_config["llm_model_func"]
        # Apply higher priority (5) to query relation LLM function
        use_model_func = partial(use_model_func, _priority=5)

    args_hash = compute_args_hash(query_param.mode, query)
    cached_response, quantized, min_val, max_val = await handle_cache(
        hashing_kv, args_hash, query, query_param.mode, cache_type="query"
    )
    if cached_response is not None:
        return cached_response

    # If neither has any keywords, you could handle that logic here.
    if not hl_keywords and not ll_keywords:
        logger.warning(
            "No keywords found in query_param. Could default to hybrid mode or fail."
        )
        query_param.mode = "hybrid"


    ll_keywords_str = ", ".join(ll_keywords) if ll_keywords else ""
    hl_keywords_str = ", ".join(hl_keywords) if hl_keywords else ""

    context = await _build_query_context(
        query,
        ll_keywords_str,
        hl_keywords_str,
        knowledge_graph_inst,
        entities_vdb,
        relationships_vdb,
        text_chunks_db,
        query_param,
        chunks_vdb=chunks_vdb,
    )
    if not context:
        return PROMPTS["fail_response"]

    if query_param.only_need_context:
        return context

    # Process conversation history
    history_context = ""
    if query_param.conversation_history:
        history_context = get_conversation_turns(
            query_param.conversation_history, query_param.history_turns
        )

    sys_prompt_temp = PROMPTS["rag_response"]
    sys_prompt = sys_prompt_temp.format(
        context_data=context,
        response_type=query_param.response_type,
        history=history_context,
    )

    if query_param.only_need_prompt:
        return sys_prompt

    tokenizer: Tokenizer = global_config["tokenizer"]
    len_of_prompts = len(tokenizer.encode(query + sys_prompt))
    logger.debug(
        f"[kg_query_with_keywords] Sending to LLM: {len_of_prompts:,} tokens (Query: {len(tokenizer.encode(query))}, System: {len(tokenizer.encode(sys_prompt))})"
    )

    # 6. Generate response
    response = await use_model_func(
        query,
        system_prompt=sys_prompt,
        stream=query_param.stream,
    )

    # Clean up response content
    if isinstance(response, str) and len(response) > len(sys_prompt):
        response = (
            response.replace(sys_prompt, "")
            .replace("user", "")
            .replace("model", "")
            .replace(query, "")
            .replace("<system>", "")
            .replace("</system>", "")
            .strip()
        )

        if hashing_kv.global_config.get("enable_llm_cache"):
            await save_to_cache(
                hashing_kv,
                CacheData(
                    args_hash=args_hash,
                    content=response,
                    prompt=query,
                    quantized=quantized,
                    min_val=min_val,
                    max_val=max_val,
                    mode=query_param.mode,
                    cache_type="query",
                ),
            )

    return response

async def query_with_keywords(
    query: str,
    prompt: str,
    param: QueryParam,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    chunks_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    global_config: dict[str, str],
    hashing_kv: BaseKVStorage | None = None,
) -> str | AsyncIterator[str]:
    """
    Extract keywords from the query and then use them for retrieving information.

    1. Extracts high-level and low-level keywords from the query
    2. Formats the query with the extracted keywords and prompt
    3. Uses the appropriate query method based on param.mode

    Args:
        query: The user's query
        prompt: Additional prompt to prepend to the query
        param: Query parameters
        knowledge_graph_inst: Knowledge graph storage
        entities_vdb: Entities vector database
        relationships_vdb: Relationships vector database
        chunks_vdb: Document chunks vector database
        text_chunks_db: Text chunks storage
        global_config: Global configuration
        hashing_kv: Cache storage

    Returns:
        Query response or async iterator
    """
    # Extract keywords
    hl_keywords, ll_keywords = await get_keywords_from_query(
        query=query,
        query_param=param,
        global_config=global_config,
        hashing_kv=hashing_kv,
    )

    # Create a new string with the prompt and the keywords
    keywords_str = ", ".join(ll_keywords + hl_keywords)
    formatted_question = (
        f"{prompt}\n\n### Keywords\n\n{keywords_str}\n\n### Query\n\n{query}"
    )

    # Use appropriate query method based on mode
    if param.mode in ["hybrid", "graph"]:
        return await kg_query_with_keywords(
            formatted_question,
            knowledge_graph_inst,
            entities_vdb,
            relationships_vdb,
            text_chunks_db,
            param,
            global_config,
            hashing_kv=hashing_kv,
            hl_keywords=hl_keywords,
            ll_keywords=ll_keywords,
            chunks_vdb=chunks_vdb,
        )

    else:
        raise ValueError(f"Unknown mode {param.mode}")

async def process_chunks_unified(
    query: str,
    chunks: list[dict],
    query_param: QueryParam,
    global_config: dict,
    source_type: str = "mixed",
    chunk_token_limit: int = None,  # Add parameter for dynamic token limit
) -> list[dict]:
    """
    Unified processing for text chunks: deduplication, chunk_top_k limiting, reranking, and token truncation.

    Args:
        query: Search query for reranking
        chunks: List of text chunks to process
        query_param: Query parameters containing configuration
        global_config: Global configuration dictionary
        source_type: Source type for logging ("vector", "entity", "relationship", "mixed")
        chunk_token_limit: Dynamic token limit for chunks (if None, uses default)

    Returns:
        Processed and filtered list of text chunks
    """
    if not chunks:
        return []

    # 1. Deduplication based on content
    seen_content = set()
    unique_chunks = []
    for chunk in chunks:
        content = chunk.get("content", "")
        if content and content not in seen_content:
            seen_content.add(content)
            unique_chunks.append(chunk)

    logger.debug(
        f"Deduplication: {len(unique_chunks)} chunks (original: {len(chunks)})"
    )

    # 2. Apply reranking if enabled and query is provided
    if query_param.enable_rerank and query and unique_chunks:
        rerank_top_k = query_param.chunk_top_k or len(unique_chunks)
        unique_chunks = await apply_rerank_if_enabled(
            query=query,
            retrieved_docs=unique_chunks,
            global_config=global_config,
            enable_rerank=query_param.enable_rerank,
            top_k=rerank_top_k,
        )
        logger.debug(f"Rerank: {len(unique_chunks)} chunks (source: {source_type})")

    # 3. Apply chunk_top_k limiting if specified
    if query_param.chunk_top_k is not None and query_param.chunk_top_k > 0:
        if len(unique_chunks) > query_param.chunk_top_k:
            unique_chunks = unique_chunks[: query_param.chunk_top_k]
            logger.debug(
                f"Chunk top-k limiting: kept {len(unique_chunks)} chunks (chunk_top_k={query_param.chunk_top_k})"
            )

    # 4. Token-based final truncation
    tokenizer = global_config.get("tokenizer")
    if tokenizer and unique_chunks:
        # Set default chunk_token_limit if not provided
        if chunk_token_limit is None:
            # Get default from query_param or global_config
            chunk_token_limit = getattr(
                query_param,
                "max_total_tokens",
                global_config.get("MAX_TOTAL_TOKENS", 32000),
            )

        original_count = len(unique_chunks)
        unique_chunks = truncate_list_by_token_size(
            unique_chunks,
            key=lambda x: x.get("content", ""),
            max_token_size=chunk_token_limit,
            tokenizer=tokenizer,
        )
        logger.debug(
            f"Token truncation: {len(unique_chunks)} chunks from {original_count} "
            f"(chunk available tokens: {chunk_token_limit}, source: {source_type})"
        )

    return unique_chunks
