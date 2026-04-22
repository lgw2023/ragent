from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Any, Literal

import requests

from . import QueryParam, Ragent
from .constants import GRAPH_FIELD_SEP
from .kg.shared_storage import finalize_share_data, initialize_pipeline_status
from .llm.openai import env_openai_complete, openai_embed
from .prompt import dismantle_prompt
from .rerank import rerank_from_env
from .runtime_env import bootstrap_runtime_environment
from .utils import (
    ModelUsageCollector,
    get_current_model_usage_collector,
    log_model_call,
    logger,
    model_usage_stage,
    record_model_usage,
    split_string_by_multi_markers,
    write_model_usage_report,
)
from .operate import graph_query, hybrid_query


bootstrap_runtime_environment()


QueryType = Literal["onehop", "multihop", "chat"]

_MODEL_HEALTHCHECK_DONE = False
_MODEL_HEALTHCHECK_LOCK = asyncio.Lock()


@dataclass(slots=True)
class InferenceRequest:
    query_type: QueryType
    query: str
    mode: Literal["graph", "hybrid"] = "hybrid"
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    history_turns: int | None = None
    enable_rerank: bool | None = None
    response_type: str | None = None
    include_trace: bool = False


@dataclass
class InferenceRuntimeSession:
    project_dir: str
    rag: Ragent | None = None
    query_count: int = 0
    initialized_stage_timings: list[dict[str, Any]] = field(default_factory=list)
    query_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def load(self) -> None:
        if self.rag is not None:
            return
        stage_timings: list[dict[str, Any]] = []
        self.rag = await initialize_rag(self.project_dir, stage_timings=stage_timings)
        self.initialized_stage_timings = list(stage_timings)

    async def close(self) -> None:
        if self.rag is None:
            return
        await _close_rag(self.rag)
        self.rag = None

    async def run(self, request: InferenceRequest) -> dict[str, Any]:
        await self.load()
        if self.rag is None:
            raise RuntimeError("RAG runtime is not initialized")

        async with self.query_lock:
            result = await execute_inference_request(
                self.rag,
                request,
                prefill_stage_timings=(
                    self.initialized_stage_timings
                    if request.include_trace and self.query_count == 0
                    else None
                ),
            )
            self.query_count += 1
            return result


def normalize_query_mode(mode: str | None) -> Literal["graph", "hybrid"]:
    normalized_mode = (mode or "hybrid").strip().lower()
    if normalized_mode not in {"graph", "hybrid"}:
        raise ValueError("Invalid mode. Use one of: graph | hybrid")
    return normalized_mode  # type: ignore[return-value]


def parse_history_turns(raw_value: str | int | None) -> int | None:
    if raw_value in (None, ""):
        return None
    history_turns = int(raw_value)
    if history_turns <= 0:
        raise ValueError("history_turns must be a positive integer")
    return history_turns


def normalize_conversation_history(
    payload: Any,
    source_name: str = "conversation_history",
) -> list[dict[str, str]]:
    if isinstance(payload, dict):
        if "conversation_history" in payload:
            payload = payload.get("conversation_history")
        else:
            raise ValueError(
                f"Invalid {source_name}: expected a JSON list or an object "
                "with conversation_history."
            )

    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError(f"Invalid {source_name}: expected a JSON list.")

    conversation_history: list[dict[str, str]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(
                f"Invalid {source_name} entry at index {index}: expected an object."
            )
        role = item.get("role")
        content = item.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            raise ValueError(
                f"Invalid {source_name} entry at index {index}: "
                "role/content must both be strings."
            )
        conversation_history.append({"role": role, "content": content})
    return conversation_history


def _resolve_kg_usage_report_dir(project_dir: str) -> str:
    return os.path.abspath(project_dir)


def _maybe_create_usage_collector(label: str):
    if get_current_model_usage_collector() is not None:
        return nullcontext(None)
    return ModelUsageCollector(label)


def _write_usage_report_if_needed(
    collector: ModelUsageCollector | None,
    report_dir: str,
    *,
    task_name: str,
    metadata: dict[str, Any],
) -> str | None:
    if collector is None:
        return None
    report_path = write_model_usage_report(
        collector,
        report_dir,
        task_name=task_name,
        metadata=metadata,
    )
    logger.info("Model usage report written: %s", os.path.abspath(report_path))
    return report_path


def _preview_text(value: Any, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _safe_score(value: Any) -> float | None:
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _collect_ranked_chunks(
    weights: dict[str, Any],
    texts: dict[str, str],
    file_paths: dict[str, str],
    metadata_map: dict[str, dict[str, Any]] | None = None,
    limit: int = 5,
    source: str | None = None,
) -> list[dict[str, Any]]:
    ranked = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:limit]
    results: list[dict[str, Any]] = []
    for index, (chunk_id, score) in enumerate(ranked, 1):
        result = {
            "rank": index,
            "chunk_id": chunk_id,
            "score": _safe_score(score),
            "file_path": file_paths.get(chunk_id, "unknown_source"),
            "preview": _preview_text(texts.get(chunk_id, "")),
        }
        if source is not None:
            result["source"] = source
        if metadata_map:
            for key, value in metadata_map.get(chunk_id, {}).items():
                if value not in (None, "", [], {}):
                    result[key] = value
        results.append(result)
    return results


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


def _extract_source_fields(item: dict[str, Any]) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    for key in ("source_chunk_ids", "source_refs", "source_refs_display"):
        value = item.get(key)
        if value not in (None, "", [], {}):
            extracted[key] = value
    return extracted


def _collect_entity_hits(entities: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    results = []
    for item in entities[:limit]:
        result = {
            "entity": item.get("entity", "UNKNOWN"),
            "type": item.get("type", "UNKNOWN"),
            "file_path": item.get("file_path", "unknown_source"),
            "preview": _preview_text(item.get("description", "")),
        }
        result.update(_extract_source_fields(item))
        results.append(result)
    return results


def _extract_document_chunks_from_context(context_text: str) -> list[dict[str, Any]]:
    patterns = [
        r"---Document Chunks\(DC\)---\s*```json\s*(.*?)\s*```",
        r"---Document Chunks---\s*```json\s*(.*?)\s*```",
    ]
    for pattern in patterns:
        match = re.search(pattern, context_text, re.DOTALL)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return parsed
        return []
    return []


def _collect_relation_hits(relations: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    results = []
    for item in relations[:limit]:
        result = {
            "entity1": item.get("entity1", "UNKNOWN"),
            "entity2": item.get("entity2", "UNKNOWN"),
            "file_path": item.get("file_path", "unknown_source"),
            "preview": _preview_text(item.get("description", "")),
        }
        result.update(_extract_source_fields(item))
        results.append(result)
    return results


async def _enrich_graph_hits_with_chunk_sources(
    items: list[dict[str, Any]],
    chunk_storage,
    limit_per_item: int = 3,
) -> None:
    if not items or chunk_storage is None:
        return

    ordered_chunk_ids: list[str] = []
    seen_chunk_ids: set[str] = set()
    for item in items:
        for chunk_id in _normalize_source_chunk_ids(
            item.get("source_chunk_ids") or item.get("source_id")
        ):
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            ordered_chunk_ids.append(chunk_id)

    if not ordered_chunk_ids:
        return

    chunk_records = await chunk_storage.get_by_ids(ordered_chunk_ids)
    chunk_map: dict[str, dict[str, Any]] = {}
    for chunk_id, record in zip(ordered_chunk_ids, chunk_records):
        if record:
            chunk_map[chunk_id] = record

    for item in items:
        source_chunk_ids = _normalize_source_chunk_ids(
            item.get("source_chunk_ids") or item.get("source_id")
        )
        if not source_chunk_ids:
            continue
        source_refs: list[str] = []
        for chunk_id in source_chunk_ids:
            chunk = chunk_map.get(chunk_id)
            if not chunk:
                continue
            source_ref = chunk.get("source_ref") or chunk.get("file_path") or chunk_id
            if source_ref in source_refs:
                continue
            source_refs.append(source_ref)
            if len(source_refs) >= limit_per_item:
                break
        if source_refs:
            item["source_chunk_ids"] = GRAPH_FIELD_SEP.join(source_chunk_ids)
            item["source_refs"] = source_refs
            item["source_refs_display"] = " ; ".join(source_refs)


async def _enrich_debug_payload_with_chunk_sources(
    debug_payload: dict[str, Any],
    chunk_storage,
) -> None:
    await _enrich_graph_hits_with_chunk_sources(
        debug_payload.get("graph_entities", []),
        chunk_storage,
    )
    await _enrich_graph_hits_with_chunk_sources(
        debug_payload.get("graph_relations", []),
        chunk_storage,
    )


def _collect_final_context_chunks(
    rerank_results: list[dict[str, Any]],
    results_text: list[str],
    results_file_paths: list[str],
    results_chunk_ids: list[str],
    results_source_labels: list[str],
    results_chunk_metadata: list[dict[str, Any]] | None = None,
    selected_indexes: list[int] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    final_chunks = []
    if selected_indexes is not None:
        ordered_indexes = [
            index
            for index in selected_indexes
            if isinstance(index, int) and 0 <= index < len(results_text)
        ]
    else:
        top_k = len(rerank_results) if limit is None else min(len(rerank_results), limit)
        ordered_indexes = []
        for index in range(top_k):
            rerank_index = rerank_results[index].get("index")
            if not isinstance(rerank_index, int) or not (
                0 <= rerank_index < len(results_text)
            ):
                continue
            ordered_indexes.append(rerank_index)
    if limit is not None:
        ordered_indexes = ordered_indexes[:limit]
    for rerank_index in ordered_indexes:
        final_chunks.append(
            {
                "rank": len(final_chunks) + 1,
                "chunk_id": results_chunk_ids[rerank_index],
                "source": results_source_labels[rerank_index],
                "file_path": results_file_paths[rerank_index],
                "content": results_text[rerank_index],
                "preview": _preview_text(results_text[rerank_index], limit=220),
            }
        )
        if results_chunk_metadata and rerank_index < len(results_chunk_metadata):
            for key, value in results_chunk_metadata[rerank_index].items():
                if value not in (None, "", [], {}):
                    final_chunks[-1][key] = value
    return final_chunks


def _collect_rerank_results(
    rerank_results: list[dict[str, Any]],
    results_text: list[str],
    results_file_paths: list[str],
    results_chunk_ids: list[str],
    results_source_labels: list[str],
    results_chunk_metadata: list[dict[str, Any]] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    ranked = []
    top_k = len(rerank_results) if limit is None else min(len(rerank_results), limit)
    for index in range(top_k):
        item = rerank_results[index]
        rerank_index = item.get("index")
        if not isinstance(rerank_index, int) or not (0 <= rerank_index < len(results_text)):
            continue
        ranked.append(
            {
                "rank": len(ranked) + 1,
                "chunk_id": results_chunk_ids[rerank_index],
                "source": results_source_labels[rerank_index],
                "rerank_score": _safe_score(item.get("relevance_score")),
                "file_path": results_file_paths[rerank_index],
                "preview": _preview_text(results_text[rerank_index], limit=220),
            }
        )
        if results_chunk_metadata and rerank_index < len(results_chunk_metadata):
            for key, value in results_chunk_metadata[rerank_index].items():
                if value not in (None, "", [], {}):
                    ranked[-1][key] = value
    return ranked


def _normalize_referenced_file_paths(file_paths: list[str] | None) -> list[str]:
    if isinstance(file_paths, (str, bytes)):
        file_paths = [file_paths]  # type: ignore[list-item]
    return sorted(
        {
            str(item).strip()
            for item in file_paths or []
            if str(item or "").strip() and str(item).strip() != "unknown_source"
        }
    )


def _build_one_hop_trace(
    query: str,
    mode: str,
    answer: str,
    referenced_file_paths: list[str],
    debug_payload: dict[str, Any],
) -> dict[str, Any]:
    normalized_references = _normalize_referenced_file_paths(referenced_file_paths)
    trace = {
        "query": query,
        "mode": mode,
        "high_level_keywords": debug_payload.get("high_level_keywords", []),
        "low_level_keywords": debug_payload.get("low_level_keywords", []),
        "graph_entity_hits": [],
        "graph_relation_hits": [],
        "vector_candidates": [],
        "graph_chunk_candidates": [],
        "merged_candidates": [],
        "rerank_model": None,
        "rerank_input_candidates": [],
        "rerank_output_candidates": [],
        "final_context_chunks": [],
        "final_context_document_chunks": [],
        "final_context_text": (debug_payload.get("final_context_text") or "").strip(),
        "final_prompt_text": debug_payload.get("final_prompt_text", ""),
        "stage_timings": list(debug_payload.get("stage_timings", [])),
        "answer": answer,
        "referenced_file_paths": normalized_references,
        "image_list": normalized_references,
    }

    if mode == "hybrid":
        trace["vector_candidates"] = _collect_ranked_chunks(
            debug_payload["vector_weights"],
            debug_payload["vector_texts"],
            debug_payload["vector_file_paths"],
            debug_payload.get("vector_metadata_map"),
            source="vector",
        )
        trace["graph_entity_hits"] = _collect_entity_hits(debug_payload["graph_entities"])
        trace["graph_relation_hits"] = _collect_relation_hits(debug_payload["graph_relations"])
        trace["graph_chunk_candidates"] = _collect_ranked_chunks(
            debug_payload["graph_weights"],
            debug_payload["graph_texts"],
            debug_payload["graph_file_paths"],
            debug_payload.get("graph_metadata_map"),
            source="graph",
        )
        trace["merged_candidates"] = [
            {
                "rank": item["rank"],
                "source": item["source"],
                "sources": item.get("sources", []),
                "chunk_id": item["chunk_id"],
                "score": _safe_score(item.get("score")),
                "file_path": item["file_path"],
                "preview": _preview_text(item.get("content", "")),
            }
            for item in debug_payload["merged_candidates"]
        ]
        trace["rerank_model"] = os.getenv("RERANK_MODEL")
        trace["rerank_output_candidates"] = _collect_rerank_results(
            debug_payload["rerank_results"],
            debug_payload["results_text"],
            debug_payload["results_file_paths"],
            debug_payload["results_chunk_ids"],
            debug_payload["results_source_labels"],
            debug_payload.get("results_chunk_metadata"),
        )
        trace["rerank_input_candidates"] = list(trace["merged_candidates"])
        trace["final_context_chunks"] = _collect_final_context_chunks(
            debug_payload["rerank_results"],
            debug_payload["results_text"],
            debug_payload["results_file_paths"],
            debug_payload["results_chunk_ids"],
            debug_payload["results_source_labels"],
            debug_payload.get("results_chunk_metadata"),
            selected_indexes=debug_payload.get("selected_candidate_indexes"),
            limit=len(debug_payload["final_context_document_chunks"]),
        )
        trace["final_context_document_chunks"] = debug_payload["final_context_document_chunks"]
    else:
        trace["graph_entity_hits"] = _collect_entity_hits(debug_payload.get("graph_entities", []))
        trace["graph_relation_hits"] = _collect_relation_hits(
            debug_payload.get("graph_relations", [])
        )
        trace["final_context_document_chunks"] = debug_payload.get(
            "final_context_document_chunks"
        ) or _extract_document_chunks_from_context(
            debug_payload.get("final_context_text", "") or ""
        )

    return trace


async def _run_one_hop_with_rag(
    rag: Ragent,
    query: str,
    mode: str,
    conversation_history: list[dict[str, Any]] | None = None,
    history_turns: int | None = None,
    include_trace: bool = False,
    prefill_stage_timings: list[dict[str, Any]] | None = None,
    enable_rerank: bool | None = None,
    response_type: str | None = None,
) -> dict[str, Any]:
    query_param = QueryParam(mode=mode)
    if enable_rerank is not None:
        query_param.enable_rerank = enable_rerank
    if response_type:
        query_param.response_type = response_type
    if conversation_history:
        query_param.conversation_history = [
            {"role": str(item["role"]), "content": str(item["content"])}
            for item in conversation_history
        ]
    if history_turns is not None:
        query_param.history_turns = history_turns
    global_config = await rag._build_runtime_global_config()
    normalized_query = query.strip()

    if mode == "hybrid":
        if include_trace:
            answer, referenced_file_paths, debug_payload = await hybrid_query(
                normalized_query,
                rag.chunks_vdb,
                rag.chunk_entity_relation_graph,
                rag.relationships_vdb,
                rag.entities_vdb,
                rag.text_chunks,
                query_param,
                global_config,
                rag.llm_response_cache,
                return_debug=True,
            )
            if prefill_stage_timings:
                debug_payload["stage_timings"] = [
                    *prefill_stage_timings,
                    *debug_payload.get("stage_timings", []),
                ]
            await _enrich_debug_payload_with_chunk_sources(debug_payload, rag.text_chunks)
            await rag._query_done()
            normalized_references = _normalize_referenced_file_paths(referenced_file_paths)
            return {
                "answer": answer,
                "referenced_file_paths": normalized_references,
                "image_list": normalized_references,
                "trace": _build_one_hop_trace(
                    normalized_query,
                    mode,
                    answer,
                    referenced_file_paths,
                    debug_payload,
                ),
            }
        answer, referenced_file_paths = await hybrid_query(
            normalized_query,
            rag.chunks_vdb,
            rag.chunk_entity_relation_graph,
            rag.relationships_vdb,
            rag.entities_vdb,
            rag.text_chunks,
            query_param,
            global_config,
            rag.llm_response_cache,
        )
    else:
        if include_trace:
            answer, referenced_file_paths, debug_payload = await graph_query(
                normalized_query,
                rag.chunk_entity_relation_graph,
                rag.entities_vdb,
                rag.relationships_vdb,
                rag.text_chunks,
                query_param,
                global_config,
                rag.llm_response_cache,
                chunks_vdb=rag.chunks_vdb,
                return_debug=True,
            )
            if prefill_stage_timings:
                debug_payload["stage_timings"] = [
                    *prefill_stage_timings,
                    *debug_payload.get("stage_timings", []),
                ]
            await _enrich_debug_payload_with_chunk_sources(debug_payload, rag.text_chunks)
            await rag._query_done()
            normalized_references = _normalize_referenced_file_paths(referenced_file_paths)
            return {
                "answer": answer,
                "referenced_file_paths": normalized_references,
                "image_list": normalized_references,
                "trace": _build_one_hop_trace(
                    normalized_query,
                    mode,
                    answer,
                    referenced_file_paths,
                    debug_payload,
                ),
            }
        answer, referenced_file_paths = await graph_query(
            normalized_query,
            rag.chunk_entity_relation_graph,
            rag.entities_vdb,
            rag.relationships_vdb,
            rag.text_chunks,
            query_param,
            global_config,
            rag.llm_response_cache,
            chunks_vdb=rag.chunks_vdb,
        )

    await rag._query_done()

    normalized_references = _normalize_referenced_file_paths(referenced_file_paths)
    return {
        "answer": answer,
        "referenced_file_paths": normalized_references,
        "image_list": normalized_references,
        "trace": None,
    }


async def trace_one_hop_problem(
    work_dir: str,
    query: str,
    mode: str = "hybrid",
    conversation_history: list[dict[str, Any]] | None = None,
    history_turns: int | None = None,
    enable_rerank: bool | None = None,
    response_type: str | None = None,
) -> dict[str, Any]:
    stage_timings: list[dict[str, Any]] = []
    with _maybe_create_usage_collector("onehop_trace") as collector:
        rag = await initialize_rag(work_dir, stage_timings=stage_timings)
        try:
            result = await _run_one_hop_with_rag(
                rag,
                query,
                mode,
                conversation_history=conversation_history,
                history_turns=history_turns,
                include_trace=True,
                prefill_stage_timings=stage_timings,
                enable_rerank=enable_rerank,
                response_type=response_type,
            )
        finally:
            await _close_rag(rag)
        if collector is not None and result.get("trace") is not None:
            result["trace"]["model_usage"] = collector.snapshot()
    _write_usage_report_if_needed(
        collector,
        _resolve_kg_usage_report_dir(work_dir),
        task_name="onehop",
        metadata={
            "query": query,
            "mode": mode,
            "trace": True,
            "history_messages": len(conversation_history or []),
            "history_turns": history_turns,
            "enable_rerank": enable_rerank,
            "response_type": response_type,
        },
    )
    return result["trace"]


def _parse_dismantle_result(raw_text: str) -> dict[str, Any]:
    try:
        return json.loads(raw_text)
    except Exception:
        return json.loads(raw_text.split("```json")[1].split("```")[0])


async def _run_multi_hop_with_rag(
    rag: Ragent,
    query: str,
    include_trace: bool = False,
) -> dict[str, Any]:
    res_dismantle = await rag.llm_model_func(prompt=query, system_prompt=dismantle_prompt)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("问题拆解结果：%s", res_dismantle)
    res_dismantle_json = _parse_dismantle_result(res_dismantle)

    memory_new: dict[str, Any] = {"多跳问题分解结果": res_dismantle_json}
    steps = []
    count = 0
    final_answer = ""
    referenced_file_paths: list[str] = []

    for index, sub_question in enumerate(res_dismantle_json["sub_questions"]):
        if count == 2:
            prompt_summary = (
                "请对历史信息中存储的知识内容进行总结，要求字数少于1000字，并保留sub_questions列表中的问题信息，以下是历史信息\n"
                + str(memory_new)
            )
            summary_result = await _run_one_hop_with_rag(
                rag,
                prompt_summary,
                mode="hybrid",
                include_trace=include_trace,
            )
            memory_new = {"历史信息总结": summary_result["answer"]}
            count = 0
            referenced_file_paths.extend(
                summary_result.get("referenced_file_paths")
                or summary_result.get("image_list")
                or []
            )
            if include_trace:
                steps.append(
                    {
                        "stage_type": "history_summary",
                        "display_question": "历史信息总结",
                        "internal_query": prompt_summary,
                        "memory_snapshot": _preview_text(
                            json.dumps(memory_new, ensure_ascii=False),
                            limit=240,
                        ),
                        "trace": summary_result["trace"],
                    }
                )

        if index == len(res_dismantle_json["sub_questions"]) - 1 and index > 0:
            internal_query = (
                "当前回答的问题是"
                + sub_question
                + "该问题历史记录为"
                + str(memory_new)
                + "当前是最后一个子问题在回答子问题的基础上请对以上内容进行总结回答"
            )
            stage_type = "final_synthesis"
        else:
            internal_query = "当前回答的问题是" + sub_question + "该问题历史记录为" + str(
                memory_new
            )
            stage_type = "sub_question"

        step_result = await _run_one_hop_with_rag(
            rag,
            internal_query,
            mode="hybrid",
            include_trace=include_trace,
        )
        memory_new[sub_question] = step_result["answer"]
        count += 1
        final_answer = step_result["answer"]
        referenced_file_paths.extend(
            step_result.get("referenced_file_paths")
            or step_result.get("image_list")
            or []
        )
        if include_trace:
            steps.append(
                {
                    "stage_type": stage_type,
                    "display_question": sub_question,
                    "internal_query": internal_query,
                    "memory_snapshot": _preview_text(
                        json.dumps(memory_new, ensure_ascii=False),
                        limit=240,
                    ),
                    "trace": step_result["trace"],
                }
            )

    normalized_references = _normalize_referenced_file_paths(referenced_file_paths)
    result: dict[str, Any] = {
        "query": query,
        "decomposition": res_dismantle_json,
        "answer": final_answer,
        "referenced_file_paths": normalized_references,
        "image_list": normalized_references,
    }
    if include_trace:
        result["steps"] = steps
    return result


async def trace_multi_hop_problem(work_dir: str, query: str) -> dict[str, Any]:
    rag = await initialize_rag(work_dir)
    try:
        with _maybe_create_usage_collector("multihop_trace") as collector:
            result = await _run_multi_hop_with_rag(rag, query, include_trace=True)
    finally:
        await _close_rag(rag)
    _write_usage_report_if_needed(
        collector,
        _resolve_kg_usage_report_dir(work_dir),
        task_name="multihop",
        metadata={"query": query, "trace": True},
    )
    return result


def _shorten_for_log(value: Any, limit: int = 600) -> str:
    text = repr(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


def _print_healthcheck(title: str, payload: Any) -> None:
    msg = f"[StartupModelCheck] {title}: {_shorten_for_log(payload)}"
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(msg)


def _parse_positive_int_env(name: str) -> int | None:
    raw_value = os.getenv(name)
    if not raw_value:
        return None
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning("Invalid %s value: %s. Ignore timeout override.", name, raw_value)
        return None
    if value <= 0:
        logger.warning("Non-positive %s value: %s. Ignore timeout override.", name, raw_value)
        return None
    return value


def _resolve_startup_check_timeout_seconds(
    *fallback_env_vars: str,
    default: int = 30,
) -> int:
    explicit_timeout = _parse_positive_int_env("MODEL_STARTUP_CHECK_TIMEOUT_SECONDS")
    if explicit_timeout is not None:
        return explicit_timeout

    candidates = [default]
    for env_var in fallback_env_vars:
        value = _parse_positive_int_env(env_var)
        if value is not None:
            candidates.append(value)
    return max(candidates)


def _image_text_ping_sync(prompt: str) -> str:
    api_key = os.getenv("IMAGE_MODEL_KEY")
    image_model = os.getenv("IMAGE_MODEL")
    image_model_url = os.getenv("IMAGE_MODEL_URL")
    if not api_key or not image_model or not image_model_url:
        raise ValueError(
            "Missing IMAGE_MODEL config, required: IMAGE_MODEL_KEY/IMAGE_MODEL/IMAGE_MODEL_URL"
        )

    url = image_model_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"

    timeout_sec = int(os.getenv("IMAGE_MODEL_TIMEOUT", "90"))
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": image_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 128,
    }
    log_model_call(
        "ragent.inference_runtime._image_text_ping_sync",
        {
            "prompt": prompt,
            "api_key": api_key,
            "image_model": image_model,
            "image_model_url": image_model_url,
            "url": url,
            "timeout_sec": timeout_sec,
            "headers": headers,
            "payload": payload,
        },
    )
    image_req_start = time.perf_counter()
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
    resp.raise_for_status()
    data = resp.json()
    image_elapsed = time.perf_counter() - image_req_start
    record_model_usage(
        "image",
        image_model,
        data,
        source="ragent.inference_runtime._image_text_ping_sync",
        extra={"elapsed_seconds": round(image_elapsed, 3)},
    )
    return data["choices"][0]["message"]["content"]


async def verify_env_models_before_startup() -> None:
    llm_timeout_sec = _resolve_startup_check_timeout_seconds("LLM_API_TIMEOUT_SECONDS")
    embedding_timeout_sec = _resolve_startup_check_timeout_seconds(
        "EMBEDDING_TIMEOUT_SECONDS",
        "LLM_API_TIMEOUT_SECONDS",
    )
    rerank_timeout_sec = _resolve_startup_check_timeout_seconds(
        "RERANK_TIMEOUT_SECONDS",
        "LLM_API_TIMEOUT_SECONDS",
    )
    image_timeout_sec = _resolve_startup_check_timeout_seconds(
        "IMAGE_MODEL_TIMEOUT",
        "LLM_API_TIMEOUT_SECONDS",
    )
    llm_example = {
        "model_env": "LLM_MODEL",
        "prompt": "这是启动前连通性检查。请只回复: LLM_OK",
        "system_prompt": "你是模型连通性检查器。",
        "timeout_seconds": llm_timeout_sec,
    }
    embed_example = {
        "model_env": "EMBEDDING_MODEL",
        "texts": ["启动前 embedding 连通性检查样例文本。"],
        "timeout_seconds": embedding_timeout_sec,
    }
    rerank_example = {
        "model_env": "RERANK_MODEL",
        "query": "启动前 rerank 检查 query",
        "documents": ["文档A：苹果是一种水果。", "文档B：火星是太阳系行星。"],
        "top_k": 2,
        "timeout_seconds": rerank_timeout_sec,
    }

    _print_healthcheck("LLM 请求示例", llm_example)
    llm_result = await asyncio.wait_for(
        env_openai_complete(
            prompt=llm_example["prompt"],
            system_prompt=llm_example["system_prompt"],
            max_tokens=64,
            temperature=0,
        ),
        timeout=llm_timeout_sec,
    )
    _print_healthcheck("LLM 真实返回", llm_result)

    _print_healthcheck("Embedding 请求示例", embed_example)
    embed_result = await asyncio.wait_for(
        openai_embed(embed_example["texts"]),
        timeout=embedding_timeout_sec,
    )
    embed_shape = getattr(embed_result, "shape", None)
    first_vec_preview = None
    if len(embed_result) > 0:
        first_vec_preview = embed_result[0][:8].tolist()
    _print_healthcheck(
        "Embedding 真实返回",
        {"shape": embed_shape, "first_vector_head8": first_vec_preview},
    )

    _print_healthcheck("Rerank 请求示例", rerank_example)
    rerank_result = await asyncio.wait_for(
        rerank_from_env(
            query=rerank_example["query"],
            documents=rerank_example["documents"],
            top_k=rerank_example["top_k"],
        ),
        timeout=rerank_timeout_sec,
    )
    _print_healthcheck("Rerank 真实返回", rerank_result)

    image_key = os.getenv("IMAGE_MODEL_KEY")
    image_model = os.getenv("IMAGE_MODEL")
    image_url = os.getenv("IMAGE_MODEL_URL")
    if image_key and image_model and image_url:
        image_example = {
            "model_env": "IMAGE_MODEL",
            "prompt": "这是启动前图像模型文本连通性检查。请只回复: IMAGE_OK",
            "timeout_seconds": image_timeout_sec,
        }
        _print_healthcheck("Image 请求示例", image_example)
        image_result = await asyncio.wait_for(
            asyncio.to_thread(_image_text_ping_sync, image_example["prompt"]),
            timeout=image_timeout_sec,
        )
        _print_healthcheck("Image 真实返回", image_result)
    else:
        _print_healthcheck(
            "Image 检查跳过",
            "未配置完整 IMAGE_MODEL_KEY/IMAGE_MODEL/IMAGE_MODEL_URL，已跳过",
        )

    _print_healthcheck(
        "全部模型检查结果",
        {
            "llm_timeout_seconds": llm_timeout_sec,
            "embedding_timeout_seconds": embedding_timeout_sec,
            "rerank_timeout_seconds": rerank_timeout_sec,
            "image_timeout_seconds": (
                image_timeout_sec if image_key and image_model and image_url else None
            ),
        },
    )


async def ensure_startup_model_check_once() -> None:
    global _MODEL_HEALTHCHECK_DONE
    startup_check_enabled = os.getenv("MODEL_STARTUP_CHECK_ENABLED", "1") == "1"
    if not startup_check_enabled or _MODEL_HEALTHCHECK_DONE:
        return
    async with _MODEL_HEALTHCHECK_LOCK:
        if _MODEL_HEALTHCHECK_DONE:
            return
        try:
            await verify_env_models_before_startup()
            _MODEL_HEALTHCHECK_DONE = True
        except Exception as e:
            err_msg = str(e) if str(e) else f"{type(e).__name__}({repr(e)})"
            if isinstance(e, asyncio.TimeoutError):
                hint = (
                    "healthcheck timeout; set MODEL_STARTUP_CHECK_TIMEOUT_SECONDS "
                    "or increase LLM_API_TIMEOUT_SECONDS / IMAGE_MODEL_TIMEOUT"
                )
                err_msg = f"{err_msg}. {hint}"
            _print_healthcheck("启动前模型检查失败", err_msg)
            raise RuntimeError(f"Startup model check failed: {err_msg}") from e


async def initialize_rag(
    working_dir: str,
    stage_timings: list[dict[str, Any]] | None = None,
) -> Ragent:
    total_started_at = time.perf_counter()
    startup_started_at = time.perf_counter()
    with model_usage_stage("startup_model_check", "启动前模型检查"):
        await ensure_startup_model_check_once()
    if stage_timings is not None:
        stage_timings.append(
            {
                "stage": "startup_model_check",
                "label": "启动前模型检查",
                "seconds": round(time.perf_counter() - startup_started_at, 3),
            }
        )

    rag_create_started_at = time.perf_counter()
    rag = Ragent(
        working_dir=working_dir,
        embedding_func=openai_embed,
        llm_model_func=env_openai_complete,
        rerank_model_func=rerank_from_env,
        llm_model_name=os.getenv("LLM_MODEL"),
    )
    if stage_timings is not None:
        stage_timings.append(
            {
                "stage": "rag_object_setup",
                "label": "RAG 对象构建",
                "seconds": round(time.perf_counter() - rag_create_started_at, 3),
            }
        )

    storage_init_started_at = time.perf_counter()
    await rag.initialize_storages()
    if stage_timings is not None:
        stage_timings.append(
            {
                "stage": "storage_initialization",
                "label": "本地存储初始化",
                "seconds": round(time.perf_counter() - storage_init_started_at, 3),
            }
        )

    pipeline_status_started_at = time.perf_counter()
    await initialize_pipeline_status()
    if stage_timings is not None:
        stage_timings.append(
            {
                "stage": "pipeline_status_initialization",
                "label": "Pipeline 状态初始化",
                "seconds": round(time.perf_counter() - pipeline_status_started_at, 3),
            }
        )
        stage_timings.append(
            {
                "stage": "rag_initialization_total",
                "label": "查询前初始化总耗时",
                "seconds": round(time.perf_counter() - total_started_at, 3),
            }
        )
    return rag


async def _close_rag(rag: Ragent | None) -> None:
    if rag is None:
        return

    cleanup_errors: list[str] = []

    for attr_name in ("embedding_func", "llm_model_func"):
        target = getattr(rag, attr_name, None)
        shutdown = getattr(target, "shutdown", None)
        if callable(shutdown):
            try:
                await shutdown()
            except Exception as e:
                cleanup_errors.append(f"{attr_name}.shutdown: {e}")

    try:
        await rag.finalize_storages()
    except Exception as e:
        cleanup_errors.append(f"finalize_storages: {e}")

    try:
        finalize_share_data()
    except Exception as e:
        cleanup_errors.append(f"finalize_share_data: {e}")

    if cleanup_errors:
        logger.warning("RAG cleanup completed with errors: %s", "; ".join(cleanup_errors))


async def inference_multi_hop_problem(
    work_dir: str,
    query: str,
    return_all: bool = False,
):
    rag = await initialize_rag(work_dir)
    try:
        with _maybe_create_usage_collector("multihop_query") as collector:
            result = await _run_multi_hop_with_rag(rag, query, include_trace=False)
    finally:
        await _close_rag(rag)
    _write_usage_report_if_needed(
        collector,
        _resolve_kg_usage_report_dir(work_dir),
        task_name="multihop",
        metadata={"query": query, "trace": False},
    )
    if return_all:
        return (
            "question:"
            + query
            + "answer_multi_hop:"
            + result["answer"]
            + "\nreferenced_file_paths:"
            + str(set(result["referenced_file_paths"]))
            + "\nimage_list:"
            + str(set(result["image_list"]))
        )
    return result["answer"]


async def inference_one_hop_problem(
    work_dir: str,
    query: str,
    mode: str,
    return_all: bool = False,
    conversation_history: list[dict[str, Any]] | None = None,
    history_turns: int | None = None,
    enable_rerank: bool | None = None,
    response_type: str | None = None,
):
    rag = await initialize_rag(work_dir)
    try:
        with _maybe_create_usage_collector("onehop_query") as collector:
            result = await _run_one_hop_with_rag(
                rag,
                query,
                mode,
                conversation_history=conversation_history,
                history_turns=history_turns,
                include_trace=False,
                enable_rerank=enable_rerank,
                response_type=response_type,
            )
    finally:
        await _close_rag(rag)
    _write_usage_report_if_needed(
        collector,
        _resolve_kg_usage_report_dir(work_dir),
        task_name="onehop",
        metadata={
            "query": query,
            "mode": mode,
            "trace": False,
            "history_messages": len(conversation_history or []),
            "history_turns": history_turns,
            "enable_rerank": enable_rerank,
            "response_type": response_type,
        },
    )
    if return_all:
        return (
            "question:"
            + query
            + "one_hop_query_response"
            + result["answer"]
            + "\nreferenced_file_paths:"
            + str(result["referenced_file_paths"])
            + "\nimage_list:"
            + str(result["image_list"])
        )
    return result["answer"]


async def execute_inference_request(
    rag: Ragent,
    request: InferenceRequest,
    *,
    prefill_stage_timings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if request.query_type in {"onehop", "chat"}:
        result = await _run_one_hop_with_rag(
            rag,
            request.query,
            normalize_query_mode(request.mode),
            conversation_history=request.conversation_history or None,
            history_turns=request.history_turns,
            include_trace=request.include_trace,
            prefill_stage_timings=prefill_stage_timings,
            enable_rerank=request.enable_rerank,
            response_type=request.response_type,
        )
        return {
            **result,
            "query": request.query,
            "query_type": request.query_type,
            "mode": normalize_query_mode(request.mode),
            "conversation_history_used_count": len(request.conversation_history or []),
            "history_turns": request.history_turns,
            "enable_rerank": request.enable_rerank,
            "response_type": request.response_type,
        }

    result = await _run_multi_hop_with_rag(
        rag,
        request.query,
        include_trace=request.include_trace,
    )
    return {
        **result,
        "query_type": request.query_type,
        "mode": "hybrid",
        "conversation_history_used_count": 0,
        "history_turns": None,
        "enable_rerank": None,
        "response_type": None,
        "trace": None,
    }


__all__ = [
    "InferenceRequest",
    "InferenceRuntimeSession",
    "_close_rag",
    "_run_multi_hop_with_rag",
    "_run_one_hop_with_rag",
    "ensure_startup_model_check_once",
    "execute_inference_request",
    "inference_multi_hop_problem",
    "inference_one_hop_problem",
    "initialize_rag",
    "normalize_conversation_history",
    "normalize_query_mode",
    "parse_history_turns",
    "trace_multi_hop_problem",
    "trace_one_hop_problem",
]
