from __future__ import annotations
from functools import partial

import asyncio
import ast
from contextlib import asynccontextmanager
import json
import math
import os
import re
import numpy as np
from typing import Any, AsyncIterator, Callable
from collections import Counter, defaultdict
from . import keyword_extraction
from .utils import (
    logger,
    clean_str,
    compute_mdhash_id,
    compute_structured_hash,
    Tokenizer,
    is_float_regex,
    normalize_extracted_info,
    pack_user_ass_to_openai_messages,
    split_string_by_multi_markers,
    truncate_list_by_token_size,
    process_combine_contexts,
    handle_cache,
    save_to_cache,
    CacheData,
    get_conversation_turns,
    resolve_callable_cache_id,
    use_llm_func_with_cache,
    update_chunk_cache_list,
    remove_think_tags,
    model_usage_stage,
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


async def openai_embed(*args, **kwargs):
    from .llm.openai import openai_embed as openai_embed_impl

    return await openai_embed_impl(*args, **kwargs)


async def rerank_from_env(*args, **kwargs):
    from ragent.rerank import rerank_from_env as rerank_from_env_impl

    return await rerank_from_env_impl(*args, **kwargs)


_LOCAL_QUERY_CACHE_SINGLEFLIGHT_LOCKS: dict[str, asyncio.Lock] = {}


@asynccontextmanager
async def _query_cache_singleflight_lock(key: str):
    try:
        async with get_storage_keyed_lock(
            key,
            namespace="QueryCacheSingleflight",
        ):
            yield
            return
    except RuntimeError:
        lock = _LOCAL_QUERY_CACHE_SINGLEFLIGHT_LOCKS.setdefault(key, asyncio.Lock())
        await lock.acquire()
        try:
            yield
        finally:
            lock.release()


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


def _resolve_answer_prompt_mode(
    query_param: QueryParam,
    global_config: dict[str, Any],
) -> str:
    raw_value = (
        getattr(query_param, "answer_prompt_mode", None)
        or global_config.get("answer_prompt_mode")
        or "single_prompt"
    )
    normalized = str(raw_value).strip().lower()
    aliases = {
        "single": "single_prompt",
        "single_prompt": "single_prompt",
        "one_stage": "single_prompt",
        "one_pass": "single_prompt",
        "two_stage": "two_stage",
        "two_pass": "two_stage",
    }
    resolved = aliases.get(normalized)
    if resolved is None:
        logger.warning(
            "Unknown answer prompt mode %r, fallback to 'single_prompt'.",
            raw_value,
        )
        return "single_prompt"
    return resolved


_QUERY_CACHE_SCHEMA_VERSION = 2
_QUERY_CACHE_TYPE_KEYWORDS = "keywords"
_QUERY_CACHE_TYPE_RETRIEVAL = "retrieval"
_QUERY_CACHE_TYPE_RENDER = "render"
_QUERY_CACHE_TYPE_ANSWER = "answer"
_QUERY_RESULT_KIND_RETRIEVAL = "retrieval"
_QUERY_RESULT_KIND_CONTEXT = "context"
_QUERY_RESULT_KIND_PROMPT = "prompt"
_QUERY_RESULT_KIND_ANSWER = "answer"


def _validate_query_request_flags(query_param: QueryParam):
    if query_param.only_need_context and query_param.only_need_prompt:
        raise ValueError(
            "only_need_context and only_need_prompt cannot both be True"
        )


def _normalize_conversation_history(
    conversation_history: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    normalized_history = []
    for item in conversation_history or []:
        normalized_history.append(
            {
                "role": str(item.get("role", "")),
                "content": str(item.get("content", "")),
            }
        )
    return normalized_history


def _normalize_referenced_file_paths(file_paths: Any) -> list[str]:
    if not file_paths:
        return []
    if isinstance(file_paths, (str, bytes)):
        file_paths = [file_paths]
    normalized_paths: set[str] = set()
    for item in file_paths:
        file_path = str(item or "").strip()
        if file_path and file_path != "unknown_source":
            normalized_paths.add(file_path)
    return sorted(normalized_paths)


def _collect_referenced_file_paths(*collections: list[dict[str, Any]]) -> list[str]:
    file_paths: list[str] = []
    for collection in collections:
        for item in collection or []:
            if not isinstance(item, dict):
                continue
            file_path = str(item.get("file_path") or "").strip()
            if file_path and file_path != "unknown_source":
                file_paths.append(file_path)
    return _normalize_referenced_file_paths(file_paths)


def _coerce_non_negative_int(value: Any, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _normalize_dependency_chunk_ids(value: Any) -> list[str]:
    normalized_ids: list[str] = []
    seen: set[str] = set()
    for chunk_id in _normalize_source_chunk_ids(value):
        normalized = str(chunk_id).strip()
        if (
            not normalized
            or not normalized.startswith("chunk-")
            or normalized in seen
        ):
            continue
        seen.add(normalized)
        normalized_ids.append(normalized)
    return normalized_ids


def _collect_dependency_chunk_ids(
    *,
    final_context_document_chunks: list[dict[str, Any]] | None = None,
    debug_payload_cacheable: dict[str, Any] | None = None,
    dependency_chunk_ids: list[str] | None = None,
) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()

    def _add(values: Any) -> None:
        for chunk_id in _normalize_dependency_chunk_ids(values):
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            collected.append(chunk_id)

    _add(dependency_chunk_ids or [])

    for chunk in final_context_document_chunks or []:
        if not isinstance(chunk, dict):
            continue
        _add(chunk.get("chunk_id"))
        if isinstance(chunk.get("id"), str):
            _add(chunk.get("id"))
        _add(chunk.get("source_chunk_ids"))

    debug_payload = debug_payload_cacheable or {}
    if isinstance(debug_payload, dict):
        _add(debug_payload.get("results_chunk_ids"))
        for collection_name in (
            "merged_candidates",
            "text_units_context",
            "entities_context",
            "relations_context",
            "graph_entities",
            "graph_relations",
        ):
            for item in debug_payload.get(collection_name) or []:
                if not isinstance(item, dict):
                    continue
                _add(item.get("chunk_id"))
                if isinstance(item.get("id"), str):
                    _add(item.get("id"))
                _add(item.get("source_chunk_ids"))
                _add(item.get("source_id"))

    return collected


def _query_cache_enabled(hashing_kv: BaseKVStorage | None) -> bool:
    return bool(
        hashing_kv is not None and hashing_kv.global_config.get("enable_llm_cache")
    )


def _resolve_query_model_identifier(
    query_param: QueryParam,
    global_config: dict[str, Any],
) -> Any | None:
    if query_param.model_func is not None:
        callable_id = resolve_callable_cache_id(query_param.model_func)
        if callable_id is None:
            return None
        return {"source": "query_override", "callable": callable_id}

    llm_model_name = global_config.get("llm_model_name")
    if llm_model_name:
        return {"source": "global", "model_name": llm_model_name}

    callable_id = resolve_callable_cache_id(global_config.get("llm_model_func"))
    if callable_id is None:
        return None
    return {"source": "global", "callable": callable_id}


def _resolve_rerank_identifier(global_config: dict[str, Any]) -> Any:
    rerank_identifier: dict[str, Any] = {}
    rerank_model_name = os.getenv("RERANK_MODEL")
    if rerank_model_name:
        rerank_identifier["model_name"] = rerank_model_name
    rerank_callable = resolve_callable_cache_id(global_config.get("rerank_model_func"))
    if rerank_callable is not None:
        rerank_identifier["callable"] = rerank_callable
    return rerank_identifier or None


def _llm_keyword_extraction_allowed(query_param: QueryParam) -> bool:
    return bool(
        getattr(query_param, "allow_llm_keyword_extraction", True)
        and not getattr(query_param, "only_need_context", False)
    )


def _resolve_keyword_fingerprint_metadata(
    query_param: QueryParam,
    global_config: dict[str, Any],
) -> dict[str, Any]:
    keyword_source = getattr(query_param, "keyword_source", None)
    keyword_strategy = getattr(query_param, "keyword_strategy", None)
    keyword_model = getattr(query_param, "keyword_model", None)
    keyword_model_device = getattr(query_param, "keyword_model_device", None)

    if not keyword_source or not keyword_strategy:
        if query_param.hl_keywords or query_param.ll_keywords:
            keyword_source = keyword_extraction.KEYWORD_SOURCE_REQUEST
            keyword_strategy = keyword_extraction.KEYWORD_STRATEGY_REQUEST
        elif _llm_keyword_extraction_allowed(query_param):
            keyword_source = keyword_extraction.KEYWORD_SOURCE_LLM
            keyword_strategy = keyword_extraction.KEYWORD_STRATEGY_LLM
        else:
            keyword_source = keyword_extraction.KEYWORD_SOURCE_GLINER_FALLBACK
            keyword_strategy = keyword_extraction.KEYWORD_STRATEGY_TOKEN_CLASSIFICATION
            keyword_model = keyword_extraction.get_gliner_keyword_model_name(
                global_config
            )
            keyword_model_device = keyword_extraction.get_gliner_keyword_device(
                global_config
            )

    metadata = {
        "keyword_source": keyword_source,
        "keyword_strategy": keyword_strategy,
        "keyword_fallback_reason": getattr(
            query_param, "keyword_fallback_reason", None
        ),
        "keyword_model": keyword_model,
        "keyword_model_device": keyword_model_device,
        "keyword_model_error": getattr(query_param, "keyword_model_error", None),
    }
    return {key: value for key, value in metadata.items() if value is not None}


async def _resolve_no_llm_keywords_for_retrieval_cache(
    query: str,
    query_param: QueryParam,
    global_config: dict[str, Any],
    hashing_kv: BaseKVStorage | None,
) -> None:
    keyword_extraction.prepare_keyword_metadata_for_cache(
        query_param,
        global_config,
        allow_llm_keyword_extraction=_llm_keyword_extraction_allowed(query_param),
    )
    if (
        not _llm_keyword_extraction_allowed(query_param)
        and not getattr(query_param, "keyword_resolution_done", False)
    ):
        await get_keywords_from_query(query, query_param, global_config, hashing_kv)


def _resolve_query_llm_func(
    query_param: QueryParam,
    global_config: dict[str, Any],
) -> Callable[..., Any]:
    if query_param.model_func:
        return query_param.model_func
    use_model_func = global_config["llm_model_func"]
    return partial(use_model_func, _priority=5)


def _has_complete_rerank_env_config() -> bool:
    return all(
        (os.getenv(name) or "").strip()
        for name in (
            "RERANK_MODEL_KEY",
            "RERANK_MODEL_URL",
            "RERANK_MODEL",
        )
    )


def _missing_rerank_env_names() -> list[str]:
    return [
        name
        for name in (
            "RERANK_MODEL_KEY",
            "RERANK_MODEL_URL",
            "RERANK_MODEL",
        )
        if not (os.getenv(name) or "").strip()
    ]


def _has_unstable_rerank_callable(global_config: dict[str, Any]) -> bool:
    rerank_model_func = global_config.get("rerank_model_func")
    return callable(rerank_model_func) and resolve_callable_cache_id(rerank_model_func) is None


def _resolve_tokenizer_identifier(global_config: dict[str, Any]) -> dict[str, Any]:
    tokenizer = global_config.get("tokenizer")
    if tokenizer is None:
        return {}
    tokenizer_identifier = {
        "type": f"{type(tokenizer).__module__}.{type(tokenizer).__qualname__}"
    }
    tokenizer_model_name = (
        global_config.get("tiktoken_model_name")
        or getattr(tokenizer, "model_name", None)
    )
    if tokenizer_model_name:
        tokenizer_identifier["model_name"] = tokenizer_model_name
    return tokenizer_identifier


def _build_query_request_fingerprint_payload(
    *,
    scope: str,
    query: str,
    query_param: QueryParam,
    global_config: dict[str, Any],
    answer_prompt_mode: str,
    system_prompt: str | None = None,
    render_kind: str | None = None,
) -> dict[str, Any] | None:
    query_model_identifier = _resolve_query_model_identifier(query_param, global_config)
    if scope in (_QUERY_CACHE_TYPE_KEYWORDS, _QUERY_CACHE_TYPE_RETRIEVAL, _QUERY_CACHE_TYPE_ANSWER) and query_model_identifier is None:
        logger.debug("Skip query cache: unable to resolve a stable model identifier.")
        return None

    normalized_history = _normalize_conversation_history(
        query_param.conversation_history
    )
    addon_params = global_config.get("addon_params") or {}
    if not isinstance(addon_params, dict):
        addon_params = {}

    payload: dict[str, Any] = {
        "schema_version": _QUERY_CACHE_SCHEMA_VERSION,
        "scope": scope,
        "mode": query_param.mode,
        "query": query,
        "corpus_revision": _coerce_non_negative_int(
            global_config.get("corpus_revision"),
            0,
        ),
        "index_digest": global_config.get("index_digest"),
    }

    if scope == _QUERY_CACHE_TYPE_KEYWORDS:
        payload.update(
            {
                "conversation_history": normalized_history,
                "history_turns": query_param.history_turns,
                "language": addon_params.get("language"),
                "example_number": addon_params.get("example_number"),
                "model": query_model_identifier,
                "keyword_metadata": _resolve_keyword_fingerprint_metadata(
                    query_param, global_config
                ),
            }
        )
        return payload

    if scope == _QUERY_CACHE_TYPE_RETRIEVAL:
        if query_param.enable_rerank and _has_unstable_rerank_callable(global_config):
            logger.debug("Skip query cache: unable to resolve a stable rerank identifier.")
            return None
        payload.update(
            {
                "response_type": query_param.response_type,
                "user_prompt": query_param.user_prompt,
                "hl_keywords": list(query_param.hl_keywords or []),
                "ll_keywords": list(query_param.ll_keywords or []),
                "keyword_metadata": _resolve_keyword_fingerprint_metadata(
                    query_param, global_config
                ),
                "ids": list(query_param.ids or []),
                "top_k": query_param.top_k,
                "chunk_top_k": query_param.chunk_top_k,
                "max_entity_tokens": query_param.max_entity_tokens,
                "max_relation_tokens": query_param.max_relation_tokens,
                "max_total_tokens": query_param.max_total_tokens,
                "related_chunk_number": global_config.get("related_chunk_number"),
                "system_prompt_template": global_config.get("system_prompt_template"),
                "cosine_better_than_threshold": global_config.get(
                    "cosine_better_than_threshold"
                ),
                "vector_db_storage_cls_kwargs": global_config.get(
                    "vector_db_storage_cls_kwargs"
                ),
                "enable_rerank": query_param.enable_rerank,
                "conversation_history": normalized_history,
                "history_turns": query_param.history_turns,
                "keyword_language": addon_params.get("language"),
                "keyword_example_number": addon_params.get("example_number"),
                "tokenizer": _resolve_tokenizer_identifier(global_config),
                "query_model": query_model_identifier,
                "rerank_model": _resolve_rerank_identifier(global_config),
                "addon_params": addon_params,
            }
        )
        return payload

    if scope == _QUERY_CACHE_TYPE_RENDER:
        if render_kind not in (_QUERY_RESULT_KIND_CONTEXT, _QUERY_RESULT_KIND_PROMPT):
            raise ValueError(f"Unsupported render kind: {render_kind}")
        retrieval_fingerprint_payload = _build_query_request_fingerprint_payload(
            scope=_QUERY_CACHE_TYPE_RETRIEVAL,
            query=query,
            query_param=query_param,
            global_config=global_config,
            answer_prompt_mode=answer_prompt_mode,
        )
        if retrieval_fingerprint_payload is None:
            return None
        payload.update(
            {
                "render_kind": render_kind,
                "answer_prompt_mode": answer_prompt_mode,
                "retrieval_fingerprint": retrieval_fingerprint_payload,
            }
        )
        if render_kind == _QUERY_RESULT_KIND_PROMPT:
            payload.update(
                {
                    "response_type": query_param.response_type,
                    "user_prompt": query_param.user_prompt,
                    "conversation_history": normalized_history,
                    "history_turns": query_param.history_turns,
                    "system_prompt": system_prompt,
                }
            )
        return payload

    if scope == _QUERY_CACHE_TYPE_ANSWER:
        if query_param.stream:
            return None
        render_prompt_payload = _build_query_request_fingerprint_payload(
            scope=_QUERY_CACHE_TYPE_RENDER,
            query=query,
            query_param=query_param,
            global_config=global_config,
            answer_prompt_mode=answer_prompt_mode,
            system_prompt=system_prompt,
            render_kind=_QUERY_RESULT_KIND_PROMPT,
        )
        if render_prompt_payload is None:
            return None
        payload.update(
            {
                "result_kind": _QUERY_RESULT_KIND_ANSWER,
                "render_prompt_fingerprint": render_prompt_payload,
                "answer_model": query_model_identifier,
            }
        )
        return payload

    raise ValueError(f"Unsupported query cache scope: {scope}")


def _build_query_request_fingerprint(
    *,
    scope: str,
    query: str,
    query_param: QueryParam,
    global_config: dict[str, Any],
    answer_prompt_mode: str,
    system_prompt: str | None = None,
    render_kind: str | None = None,
) -> str | None:
    payload = _build_query_request_fingerprint_payload(
        scope=scope,
        query=query,
        query_param=query_param,
        global_config=global_config,
        answer_prompt_mode=answer_prompt_mode,
        system_prompt=system_prompt,
        render_kind=render_kind,
    )
    if payload is None:
        return None
    return compute_structured_hash(payload, strict=True)


def _build_query_cache_payload(
    *,
    result_kind: str,
    answer: str = "",
    context_text: str = "",
    prompt_text: str = "",
    referenced_file_paths: list[str] | None = None,
    final_context_document_chunks: list[dict[str, Any]] | None = None,
    debug_payload_cacheable: dict[str, Any] | None = None,
    context_available: bool = True,
    corpus_revision: int = 0,
    dependency_chunk_ids: list[str] | None = None,
    created_at: int | None = None,
    last_accessed_at: int | None = None,
    access_count: int | None = None,
) -> dict[str, Any]:
    created_timestamp = (
        _coerce_non_negative_int(created_at, 0)
        if created_at is not None
        else int(time.time())
    )
    last_accessed_timestamp = (
        _coerce_non_negative_int(last_accessed_at, created_timestamp)
        if last_accessed_at is not None
        else created_timestamp
    )
    normalized_access_count = (
        _coerce_non_negative_int(access_count, 1)
        if access_count is not None
        else 1
    )
    return {
        "schema_version": _QUERY_CACHE_SCHEMA_VERSION,
        "result_kind": result_kind,
        "answer": answer,
        "context_text": context_text,
        "prompt_text": prompt_text,
        "referenced_file_paths": _normalize_referenced_file_paths(
            referenced_file_paths or []
        ),
        "final_context_document_chunks": list(final_context_document_chunks or []),
        "debug_payload_cacheable": dict(debug_payload_cacheable or {}),
        "context_available": context_available,
        "corpus_revision": _coerce_non_negative_int(corpus_revision, 0),
        "dependency_chunk_ids": _collect_dependency_chunk_ids(
            final_context_document_chunks=final_context_document_chunks,
            debug_payload_cacheable=debug_payload_cacheable,
            dependency_chunk_ids=dependency_chunk_ids,
        ),
        "created_at": created_timestamp,
        "last_accessed_at": last_accessed_timestamp,
        "access_count": normalized_access_count,
    }


def _coerce_query_cache_payload(
    cached_content: Any,
    *,
    expected_result_kind: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(cached_content, dict):
        return None
    payload = dict(cached_content)
    result_kind = str(payload.get("result_kind") or "").strip()
    if expected_result_kind is not None and result_kind != expected_result_kind:
        return None
    final_context_document_chunks = payload.get("final_context_document_chunks") or []
    if not isinstance(final_context_document_chunks, list):
        final_context_document_chunks = []
    debug_payload_cacheable = payload.get("debug_payload_cacheable") or {}
    if not isinstance(debug_payload_cacheable, dict):
        debug_payload_cacheable = {}
    created_at = _coerce_non_negative_int(payload.get("created_at"), 0)
    last_accessed_at = _coerce_non_negative_int(
        payload.get("last_accessed_at"),
        created_at,
    )
    return {
        "schema_version": payload.get("schema_version", _QUERY_CACHE_SCHEMA_VERSION),
        "result_kind": result_kind,
        "answer": str(payload.get("answer") or ""),
        "context_text": str(payload.get("context_text") or ""),
        "prompt_text": str(payload.get("prompt_text") or ""),
        "referenced_file_paths": _normalize_referenced_file_paths(
            payload.get("referenced_file_paths") or []
        ),
        "final_context_document_chunks": list(final_context_document_chunks),
        "debug_payload_cacheable": dict(debug_payload_cacheable),
        "context_available": bool(payload.get("context_available", True)),
        "corpus_revision": _coerce_non_negative_int(
            payload.get("corpus_revision"),
            0,
        ),
        "dependency_chunk_ids": _normalize_dependency_chunk_ids(
            payload.get("dependency_chunk_ids") or []
        ),
        "created_at": created_at,
        "last_accessed_at": last_accessed_at,
        "access_count": _coerce_non_negative_int(payload.get("access_count"), 0),
    }


def _strip_stage_timings(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in payload.items() if key != "stage_timings"
    }


def _hydrate_debug_payload(
    *,
    cacheable_debug_payload: dict[str, Any],
    context_text: str,
    prompt_text: str,
    final_context_document_chunks: list[dict[str, Any]],
    stage_timings: list[dict[str, Any]],
) -> dict[str, Any]:
    debug_payload = dict(cacheable_debug_payload or {})
    debug_payload["final_context_document_chunks"] = list(
        final_context_document_chunks or []
    )
    debug_payload["final_context_text"] = context_text
    debug_payload["final_prompt_text"] = prompt_text
    debug_payload["stage_timings"] = stage_timings
    return debug_payload


async def _load_query_cache_payload(
    hashing_kv: BaseKVStorage | None,
    *,
    args_hash: str | None,
    mode: str,
    cache_type: str,
    expected_result_kind: str,
    stage_timings: list[dict[str, Any]] | None = None,
    lookup_stage: str | None = None,
    lookup_label: str | None = None,
    hit_stage: str | None = None,
    hit_label: str | None = None,
) -> dict[str, Any] | None:
    if not _query_cache_enabled(hashing_kv) or not args_hash:
        return None

    stage_started_at = time.perf_counter()
    cached_content, _, _, _ = await handle_cache(
        hashing_kv,
        args_hash,
        "",
        mode,
        cache_type=cache_type,
    )
    if (
        stage_timings is not None
        and lookup_stage is not None
        and lookup_label is not None
    ):
        _record_stage_timing(stage_timings, lookup_stage, lookup_label, stage_started_at)

    payload = _coerce_query_cache_payload(
        cached_content,
        expected_result_kind=expected_result_kind,
    )
    if (
        payload is not None
        and stage_timings is not None
        and hit_stage is not None
        and hit_label is not None
    ):
        _append_stage_timing(stage_timings, hit_stage, hit_label, 0.0)
    return payload


async def _save_query_cache_payload(
    hashing_kv: BaseKVStorage | None,
    *,
    args_hash: str | None,
    mode: str,
    cache_type: str,
    prompt: str,
    payload: dict[str, Any],
):
    if not _query_cache_enabled(hashing_kv) or not args_hash:
        return
    await save_to_cache(
        hashing_kv,
        CacheData(
            args_hash=args_hash,
            content=payload,
            prompt=prompt,
            mode=mode,
            cache_type=cache_type,
        ),
    )


async def _get_or_compute_query_cache_payload(
    hashing_kv: BaseKVStorage | None,
    *,
    args_hash: str | None,
    mode: str,
    cache_type: str,
    expected_result_kind: str,
    prompt: str,
    compute_payload: Callable[[], Any],
    stage_timings: list[dict[str, Any]] | None = None,
    lookup_stage: str | None = None,
    lookup_label: str | None = None,
    hit_stage: str | None = None,
    hit_label: str | None = None,
    skip_initial_lookup: bool = False,
) -> dict[str, Any]:
    if not skip_initial_lookup:
        payload = await _load_query_cache_payload(
            hashing_kv,
            args_hash=args_hash,
            mode=mode,
            cache_type=cache_type,
            expected_result_kind=expected_result_kind,
            stage_timings=stage_timings,
            lookup_stage=lookup_stage,
            lookup_label=lookup_label,
            hit_stage=hit_stage,
            hit_label=hit_label,
        )
        if payload is not None:
            return payload

    if not _query_cache_enabled(hashing_kv) or not args_hash:
        return await compute_payload()

    cache_lock_key = f"{mode}:{cache_type}:{args_hash}"
    async with _query_cache_singleflight_lock(cache_lock_key):
        payload = await _load_query_cache_payload(
            hashing_kv,
            args_hash=args_hash,
            mode=mode,
            cache_type=cache_type,
            expected_result_kind=expected_result_kind,
        )
        if payload is not None:
            if (
                stage_timings is not None
                and hit_stage is not None
                and hit_label is not None
            ):
                _append_stage_timing(stage_timings, hit_stage, hit_label, 0.0)
            return payload

        payload = await compute_payload()
        await _save_query_cache_payload(
            hashing_kv,
            args_hash=args_hash,
            mode=mode,
            cache_type=cache_type,
            prompt=prompt,
            payload=payload,
        )
        return payload


def _sanitize_llm_context_payload(
    payload: Any,
    *,
    answer_prompt_mode: str,
) -> Any:
    if answer_prompt_mode != "single_prompt":
        return payload
    if isinstance(payload, dict):
        has_chunk_like_fields = any(
            key in payload
            for key in (
                "content",
                "page_numbers",
                "page_number_start",
                "page_number_end",
                "section_path",
                "source_ref",
            )
        )
        source_ref = str(payload.get("source_ref") or "").strip()
        base_name = ""
        if source_ref:
            base_name = source_ref.split(" | ", 1)[0].strip()
        file_path = str(payload.get("file_path") or "").strip()
        if not base_name and file_path and file_path != "unknown_source":
            base_name = os.path.basename(file_path)

        page_label = ""
        page_start = payload.get("page_number_start")
        page_end = payload.get("page_number_end")
        if isinstance(page_start, int) and isinstance(page_end, int):
            page_label = f"p.{page_start}" if page_start == page_end else f"p.{page_start}-{page_end}"
        else:
            page_numbers = payload.get("page_numbers")
            if isinstance(page_numbers, list):
                ordered_pages = sorted({int(page) for page in page_numbers if isinstance(page, int)})
                if ordered_pages:
                    page_label = (
                        f"p.{ordered_pages[0]}"
                        if len(ordered_pages) == 1
                        else f"p.{ordered_pages[0]}-{ordered_pages[-1]}"
                    )
        compact_source_ref = ""
        if has_chunk_like_fields and base_name:
            compact_source_ref = f"{base_name} | {page_label}" if page_label else base_name

        sanitized: dict[str, Any] = {}
        if "id" in payload:
            sanitized["id"] = _sanitize_llm_context_payload(
                payload.get("id"),
                answer_prompt_mode=answer_prompt_mode,
            )
        if compact_source_ref:
            sanitized["source_ref"] = compact_source_ref
        for key, value in payload.items():
            if key in {
                "id",
                "file_path",
                "page_numbers",
                "page_number_start",
                "page_number_end",
                "section_path",
                "source_ref",
            }:
                continue
            sanitized[key] = _sanitize_llm_context_payload(
                value,
                answer_prompt_mode=answer_prompt_mode,
            )
        return sanitized
    if isinstance(payload, list):
        return [
            _sanitize_llm_context_payload(
                item,
                answer_prompt_mode=answer_prompt_mode,
            )
            for item in payload
        ]
    return payload

_MEASUREMENT_UNITS_PATTERN = (
    r"(?:kg|千克|g|克|斤|千卡|kcal|卡|大卡|cm|厘米|mm|毫米|m|米|ml|毫升|l|升|"
    r"mg|毫克|ug|微克|μg|mmhg|毫米汞柱|分钟|min|小时|h|天|周|月|个月|年|岁|次|%|％)"
)
_RETRIEVAL_QUERY_SPLIT_RE = re.compile(r"[,，;；、\n]+")
_RETRIEVAL_VARIANT_TRANSLATION = str.maketrans(
    {
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "：": ":",
        "～": "~",
        "－": "-",
        "—": "-",
        "–": "-",
        "　": " ",
    }
)
_DIVERSIFIED_RETRIEVAL_RRF_K = 60
_DIVERSIFIED_RETRIEVAL_MAX_TERMS = 8
_DIVERSIFIED_RETRIEVAL_FULL_QUERY_WEIGHT = 0.75
_STANDALONE_NUMERIC_KEYWORD_RE = re.compile(
    rf"^[<>~≈约≤≥]?\s*\d+(?:\.\d+)?\s*(?:{_MEASUREMENT_UNITS_PATTERN})?(?:\s*(?:/|~|～|-|—|–|到|至)\s*\d+(?:\.\d+)?\s*(?:{_MEASUREMENT_UNITS_PATTERN})?)*$",
    re.IGNORECASE,
)
_LOW_SIGNAL_LOW_LEVEL_KEYWORDS = {"补回", "超量", "达标"}
_NO_LLM_GENERIC_QUERY_KEYWORDS = {
    "什么",
    "文档",
    "文件",
    "资料",
    "内容",
    "主题",
    "主要主题",
    "核心主题",
    "文档主题",
    "文档主要主题",
    "文档的主要主题",
    "主要内容",
    "文档内容",
    "这篇文档",
    "这份文档",
    "是什么",
}
_CJK_PHRASE_RE = re.compile(r"[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9_（）()《》\-]{1,24}")
_HASH_LIKE_RE = re.compile(r"^[0-9a-fA-F]{16,}$")


def _clean_keyword_text(keyword: Any) -> str:
    cleaned = clean_str(str(keyword or ""))
    cleaned = cleaned.replace("，", ",")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" ,;；、。.()（）[]【】")


def _keyword_generic_key(keyword: Any) -> str:
    return re.sub(r"[\s,，;；、。.?!！？:：()（）\[\]【】《》\"'“”‘’]+", "", str(keyword or ""))


def _is_no_llm_generic_keyword(keyword: Any) -> bool:
    normalized = _keyword_generic_key(keyword)
    if not normalized:
        return True
    if normalized in _NO_LLM_GENERIC_QUERY_KEYWORDS:
        return True
    return normalized.endswith("是什么") and len(normalized) <= 12


def _filter_no_llm_informative_keywords(keywords: list[str]) -> list[str]:
    return [
        keyword
        for keyword in _dedupe_keywords([_clean_keyword_text(item) for item in keywords])
        if keyword and not _is_no_llm_generic_keyword(keyword)
    ]


def _normalize_retrieval_query_text(value: Any) -> str:
    normalized = clean_str(str(value or ""))
    normalized = normalized.translate(_RETRIEVAL_VARIANT_TRANSLATION)
    normalized = normalized.replace("，", ",")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip(" ,;；、。")


def _build_diversified_retrieval_queries(query: Any) -> list[str]:
    primary_query = _normalize_retrieval_query_text(query)
    if not primary_query:
        return []

    diversified_queries = [primary_query]
    split_queries = [
        _normalize_retrieval_query_text(part)
        for part in _RETRIEVAL_QUERY_SPLIT_RE.split(primary_query)
    ]
    diversified_queries.extend(part for part in split_queries if part)

    deduped_queries: list[str] = []
    seen: set[str] = set()
    for item in diversified_queries:
        normalized = item.casefold()
        if not item or normalized in seen:
            continue
        seen.add(normalized)
        deduped_queries.append(item)
        if len(deduped_queries) >= _DIVERSIFIED_RETRIEVAL_MAX_TERMS:
            break
    return deduped_queries


def _is_atomic_retrieval_variant(variant: Any) -> bool:
    normalized = _normalize_retrieval_query_text(variant)
    if not normalized:
        return False
    return not bool(_RETRIEVAL_QUERY_SPLIT_RE.search(normalized))


def _get_vector_result_identity(result: dict[str, Any]) -> tuple[str, ...]:
    entity_name = str(result.get("entity_name") or "").strip()
    if entity_name:
        return ("entity", entity_name)

    src_id = str(result.get("src_id") or "").strip()
    tgt_id = str(result.get("tgt_id") or "").strip()
    if src_id and tgt_id:
        return ("relationship", src_id, tgt_id)

    record_id = str(result.get("id") or result.get("__id__") or "").strip()
    if record_id:
        return ("record", record_id)

    return ("fallback", json.dumps(result, sort_keys=True, ensure_ascii=False))


def _merge_diversified_vector_query_results(
    query_variants: list[str],
    result_sets: list[list[dict[str, Any]]],
 ) -> list[dict[str, Any]]:
    merged: dict[tuple[str, ...], dict[str, Any]] = {}

    for variant_index, (variant, results) in enumerate(zip(query_variants, result_sets)):
        weight = (
            1.0
            if len(query_variants) == 1 or variant_index > 0
            else _DIVERSIFIED_RETRIEVAL_FULL_QUERY_WEIGHT
        )
        for rank, result in enumerate(results):
            identity = _get_vector_result_identity(result)
            distance = _coerce_score(result.get("distance") or result.get("__metrics__"))
            entry = merged.setdefault(
                identity,
                {
                    "identity": identity,
                    "best_result": result,
                    "best_distance": distance,
                    "rrf_score": 0.0,
                    "matched_variants": set(),
                },
            )
            entry["rrf_score"] += weight / (_DIVERSIFIED_RETRIEVAL_RRF_K + rank + 1)
            entry["matched_variants"].add(variant.casefold())
            if distance > entry["best_distance"]:
                entry["best_distance"] = distance
                entry["best_result"] = result

    merged_results: list[dict[str, Any]] = []
    for entry in merged.values():
        merged_result = dict(entry["best_result"])
        merged_result["distance"] = entry["best_distance"]
        merged_result["query_rrf_score"] = entry["rrf_score"]
        merged_result["query_variant_hit_count"] = len(entry["matched_variants"])
        merged_result["matched_query_variants"] = sorted(entry["matched_variants"])
        merged_result["_vector_result_identity"] = entry["identity"]
        merged_results.append(merged_result)

    merged_results.sort(
        key=lambda item: (
            -_coerce_score(item.get("query_rrf_score")),
            -_coerce_score(item.get("distance")),
            -_coerce_score(item.get("query_variant_hit_count")),
        )
    )
    return merged_results


def _select_diversified_vector_results(
    merged_results: list[dict[str, Any]],
    query_variants: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    if len(query_variants) <= 1:
        selected_results = merged_results[:top_k]
    else:
        selected_results: list[dict[str, Any]] = []
        selected_identities: set[tuple[str, ...]] = set()

        for variant in [item.casefold() for item in query_variants[1:]]:
            for result in merged_results:
                matched_variants = {
                    str(item).casefold()
                    for item in result.get("matched_query_variants", [])
                }
                identity = result.get("_vector_result_identity")
                if variant not in matched_variants or identity in selected_identities:
                    continue
                selected_results.append(result)
                if identity is not None:
                    selected_identities.add(identity)
                break

        for result in merged_results:
            if len(selected_results) >= top_k:
                break
            identity = result.get("_vector_result_identity")
            if identity in selected_identities:
                continue
            selected_results.append(result)
            if identity is not None:
                selected_identities.add(identity)

    for result in selected_results:
        result.pop("_vector_result_identity", None)
    return selected_results[:top_k]


async def _query_vector_storage_diversified(
    query: Any,
    vector_storage: BaseVectorStorage,
    top_k: int,
    ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    query_variants = _build_diversified_retrieval_queries(query)
    if not query_variants:
        return []
    if len(query_variants) == 1:
        return await vector_storage.query(query_variants[0], top_k=top_k, ids=ids)

    per_query_top_k = min(
        max(top_k * 3, len(query_variants) * 4, 6),
        24,
    )
    result_sets = await asyncio.gather(
        *[
            vector_storage.query(variant, top_k=per_query_top_k, ids=ids)
            for variant in query_variants
        ]
    )
    merged_results = _merge_diversified_vector_query_results(query_variants, result_sets)
    return _select_diversified_vector_results(merged_results, query_variants, top_k)


def _dedupe_keywords(keywords: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        normalized = keyword.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(keyword)
    return deduped


def _strip_generated_suffix(value: str) -> str:
    cleaned = re.sub(r"\.[A-Za-z0-9]{1,8}$", "", value)
    cleaned = re.sub(r"[_-]?\d{4}(?:版)?$", "", cleaned)
    cleaned = re.sub(r"[_-]?[0-9a-fA-F]{8,}$", "", cleaned)
    return cleaned.strip(" _-")


def _split_derived_keyword_phrases(value: Any) -> list[str]:
    raw_text = clean_str(str(value or ""))
    if not raw_text:
        return []
    raw_text = raw_text.replace(GRAPH_FIELD_SEP, " ")
    raw_text = raw_text.replace("\\n", " ")
    phrases: list[str] = []
    for match in _CJK_PHRASE_RE.finditer(raw_text):
        phrase = match.group()
        phrase = re.sub(r"^#+", "", phrase)
        phrase = re.sub(r"^准则[一二三四五六七八九十\d]+", "", phrase)
        phrase = re.sub(r"^[一二三四五六七八九十\d]+[、.．]", "", phrase)
        phrase = _strip_generated_suffix(_clean_keyword_text(phrase))
        if (
            2 <= len(phrase) <= 18
            and not _is_no_llm_generic_keyword(phrase)
            and not _HASH_LIKE_RE.match(phrase)
        ):
            phrases.append(phrase)
    return _dedupe_keywords(phrases)


def _file_title_keywords(file_path: Any) -> list[str]:
    raw_path = str(file_path or "").split(GRAPH_FIELD_SEP)[0]
    if not raw_path:
        return []
    stem = _strip_generated_suffix(os.path.basename(raw_path))
    if _HASH_LIKE_RE.match(stem):
        parent = os.path.basename(os.path.dirname(raw_path))
        stem = _strip_generated_suffix(parent)
    return _split_derived_keyword_phrases(stem)


def _derive_vector_context_keywords(
    vector_weights: dict[str, float],
    vector_texts: dict[str, str],
    vector_file_paths: dict[str, str],
    vector_metadata_map: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    high_level: list[str] = []
    low_level: list[str] = []
    sorted_chunk_ids = [
        chunk_id
        for chunk_id, _score in sorted(
            vector_weights.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ][:8]
    for chunk_id in sorted_chunk_ids:
        metadata = vector_metadata_map.get(chunk_id, {})
        low_level.extend(_file_title_keywords(vector_file_paths.get(chunk_id)))
        low_level.extend(_file_title_keywords(metadata.get("file_path")))
        source_ref = metadata.get("source_ref")
        if source_ref:
            parts = [part.strip() for part in str(source_ref).split("|") if part.strip()]
            if parts:
                low_level.extend(_split_derived_keyword_phrases(parts[0]))
            high_level.extend(
                phrase
                for part in parts[1:]
                for phrase in _split_derived_keyword_phrases(part)
            )
        high_level.extend(_split_derived_keyword_phrases(metadata.get("section_path")))

        text = str(vector_texts.get(chunk_id) or "")
        for heading in re.findall(r"#{1,6}\s*([^#\n]{2,80})", text[:1200]):
            high_level.extend(_split_derived_keyword_phrases(heading))
        first_line = text.splitlines()[0] if text else ""
        low_level.extend(_split_derived_keyword_phrases(first_line.split("#####", 1)[0]))

    high_level = _filter_no_llm_informative_keywords(high_level)
    low_level = _filter_no_llm_informative_keywords(low_level)
    high_set = {item.casefold() for item in high_level}
    low_level = [item for item in low_level if item.casefold() not in high_set]
    return high_level[:8], low_level[:8]


def _build_vector_keyword_context(
    vector_weights: dict[str, float],
    vector_texts: dict[str, str],
    vector_file_paths: dict[str, str],
    vector_metadata_map: dict[str, dict[str, Any]],
) -> str:
    snippets: list[str] = []
    sorted_chunk_ids = [
        chunk_id
        for chunk_id, _score in sorted(
            vector_weights.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ][:5]
    for chunk_id in sorted_chunk_ids:
        metadata = vector_metadata_map.get(chunk_id, {})
        fields = [
            vector_file_paths.get(chunk_id),
            metadata.get("source_ref"),
            metadata.get("section_path"),
            str(vector_texts.get(chunk_id) or "")[:500],
        ]
        snippets.append(" ".join(str(item) for item in fields if item))
    return "\n".join(snippets)


async def _derive_no_llm_keywords_from_vector_context(
    *,
    vector_weights: dict[str, float],
    vector_texts: dict[str, str],
    vector_file_paths: dict[str, str],
    vector_metadata_map: dict[str, dict[str, Any]],
    global_config: dict[str, Any],
) -> keyword_extraction.KeywordResolution | None:
    reason = (
        "query-only GLiNER keywords were non-informative; derived no-LLM "
        "keywords from first-pass vector evidence"
    )
    context_text = _build_vector_keyword_context(
        vector_weights,
        vector_texts,
        vector_file_paths,
        vector_metadata_map,
    )

    gliner_resolution: keyword_extraction.KeywordResolution | None = None
    if context_text.strip():
        gliner_resolution = await keyword_extraction.extract_keywords_with_gliner(
            context_text,
            global_config,
            fallback_reason=reason,
        )
        high_level = _filter_no_llm_informative_keywords(
            gliner_resolution.high_level_keywords
        )
        low_level = _filter_no_llm_informative_keywords(
            gliner_resolution.low_level_keywords
        )
    else:
        high_level = []
        low_level = []

    heuristic_high, heuristic_low = _derive_vector_context_keywords(
        vector_weights,
        vector_texts,
        vector_file_paths,
        vector_metadata_map,
    )
    high_level = _dedupe_keywords([*high_level, *heuristic_high])[:8]
    high_set = {item.casefold() for item in high_level}
    low_level = [
        item
        for item in _dedupe_keywords([*low_level, *heuristic_low])
        if item.casefold() not in high_set
    ][:8]
    if not high_level and not low_level:
        return None

    return keyword_extraction.KeywordResolution(
        high_level_keywords=high_level,
        low_level_keywords=low_level,
        keyword_source=keyword_extraction.KEYWORD_SOURCE_GLINER_FALLBACK,
        keyword_strategy=keyword_extraction.KEYWORD_STRATEGY_TOKEN_CLASSIFICATION,
        keyword_fallback_reason=reason,
        keyword_model=(
            gliner_resolution.keyword_model
            if gliner_resolution is not None
            else keyword_extraction.get_gliner_keyword_model_name(global_config)
        ),
        keyword_model_device=(
            gliner_resolution.keyword_model_device
            if gliner_resolution is not None
            else keyword_extraction.get_gliner_keyword_device(global_config)
        ),
        keyword_model_error=(
            gliner_resolution.keyword_model_error
            if gliner_resolution is not None
            else None
        ),
    )


async def _refresh_no_llm_keywords_from_vector_context(
    query_param: QueryParam,
    *,
    vector_weights: dict[str, float],
    vector_texts: dict[str, str],
    vector_file_paths: dict[str, str],
    vector_metadata_map: dict[str, dict[str, Any]],
    global_config: dict[str, Any],
) -> tuple[list[str], list[str]]:
    if (
        getattr(query_param, "keyword_source", None)
        != keyword_extraction.KEYWORD_SOURCE_GLINER_FALLBACK
    ):
        return query_param.hl_keywords, query_param.ll_keywords

    informative_hl = _filter_no_llm_informative_keywords(query_param.hl_keywords)
    informative_ll = _filter_no_llm_informative_keywords(query_param.ll_keywords)
    if informative_hl or informative_ll:
        if (
            informative_hl != query_param.hl_keywords
            or informative_ll != query_param.ll_keywords
        ):
            keyword_extraction.apply_keyword_resolution(
                query_param,
                keyword_extraction.KeywordResolution(
                    high_level_keywords=informative_hl,
                    low_level_keywords=informative_ll,
                    keyword_source=query_param.keyword_source,
                    keyword_strategy=query_param.keyword_strategy,
                    keyword_fallback_reason=query_param.keyword_fallback_reason,
                    keyword_model=query_param.keyword_model,
                    keyword_model_device=query_param.keyword_model_device,
                    keyword_model_error=query_param.keyword_model_error,
                ),
            )
        return query_param.hl_keywords, query_param.ll_keywords

    derived_resolution = await _derive_no_llm_keywords_from_vector_context(
        vector_weights=vector_weights,
        vector_texts=vector_texts,
        vector_file_paths=vector_file_paths,
        vector_metadata_map=vector_metadata_map,
        global_config=global_config,
    )
    if derived_resolution is not None:
        keyword_extraction.apply_keyword_resolution(query_param, derived_resolution)
    return query_param.hl_keywords, query_param.ll_keywords


def _normalize_high_level_keyword(keyword: Any) -> str | None:
    cleaned = _clean_keyword_text(keyword)
    if not cleaned or _STANDALONE_NUMERIC_KEYWORD_RE.match(cleaned):
        return None
    return cleaned


def _normalize_low_level_keyword(keyword: Any) -> str | None:
    cleaned = _clean_keyword_text(keyword)
    if not cleaned or cleaned in _LOW_SIGNAL_LOW_LEVEL_KEYWORDS:
        return None

    if _STANDALONE_NUMERIC_KEYWORD_RE.match(cleaned):
        return cleaned

    if cleaned in _LOW_SIGNAL_LOW_LEVEL_KEYWORDS:
        return None
    return cleaned


def _postprocess_extracted_keywords(
    hl_keywords: list[str],
    ll_keywords: list[str],
) -> tuple[list[str], list[str]]:
    normalized_hl = _dedupe_keywords(
        [
            keyword
            for keyword in (
                _normalize_high_level_keyword(item) for item in (hl_keywords or [])
            )
            if keyword
        ]
    )
    normalized_ll = _dedupe_keywords(
        [
            keyword
            for keyword in (
                _normalize_low_level_keyword(item) for item in (ll_keywords or [])
            )
            if keyword
        ]
    )

    hl_set = {keyword.casefold() for keyword in normalized_hl}
    normalized_ll = [
        keyword for keyword in normalized_ll if keyword.casefold() not in hl_set
    ]
    return normalized_hl, normalized_ll


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


_IMAGE_FILE_SUFFIXES = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg")
_LOW_SIGNAL_SECTION_HINTS = ("食谱示例", "地区", "图片", "附录")
_NORMATIVE_SECTION_HINTS = ("原则", "建议", "要点", "说明", "规范", "标准", "推荐", "控制", "限制", "范围")
_NORMATIVE_CONTENT_HINTS = (
    "建议",
    "推荐",
    "应",
    "宜",
    "控制",
    "限制",
    "减少",
    "摄入",
    "能量",
    "热量",
    "kcal",
    "千卡",
    "每日",
    "男性",
    "女性",
)
_QUANTITATIVE_REFERENCE_HINTS = (
    "kcal",
    "千卡",
    "热量",
    "能量",
    "MET",
    "分钟",
    "min",
    "km/h",
    "mmhg",
    "%",
    "％",
)
_QUERY_VARIANT_MATCH_STRIP_RE = re.compile(
    r"[\s,;；、。:：()（）\[\]【】<>《》\"'“”‘’/\\|_~～+=*\-]+"
)
_QUERY_VARIANT_METADATA_SUPPORT_FLOOR = 0.3
_QUERY_VARIANT_WEAK_SUPPORT_THRESHOLD = 0.2
_QUERY_VARIANT_STRONG_SUPPORT_THRESHOLD = 0.45


def _coerce_score(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        if isinstance(value, str):
            if not value.strip():
                return 0.0
            return float(value)
        if isinstance(value, np.ndarray):
            if value.size != 1:
                return 0.0
            return float(value.reshape(-1)[0])
        if isinstance(value, (list, tuple, set, dict)):
            if not value:
                return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _chunk_file_group_key(file_path: str, metadata: dict[str, Any] | None = None) -> str:
    source_ref = str((metadata or {}).get("source_ref") or "").strip()
    if source_ref:
        return source_ref

    normalized = str(file_path or "").strip()
    if not normalized:
        return "unknown_source"
    return os.path.basename(normalized) or normalized


def _dedupe_graph_node_seeds(node_datas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_nodes: dict[str, dict[str, Any]] = {}
    for node in node_datas or []:
        if not isinstance(node, dict):
            continue
        entity_name = str(node.get("entity_name") or node.get("entity_id") or "").strip()
        if not entity_name:
            continue
        normalized_source_ids = _serialize_source_chunk_ids(
            node.get("source_chunk_ids"),
            node.get("source_id"),
        )
        if entity_name not in merged_nodes:
            merged_nodes[entity_name] = {
                **node,
                "query_score": _coerce_score(node.get("query_score")),
            }
            if normalized_source_ids:
                merged_nodes[entity_name]["source_chunk_ids"] = normalized_source_ids
            continue

        existing = merged_nodes[entity_name]
        existing["query_score"] = max(
            _coerce_score(existing.get("query_score")),
            _coerce_score(node.get("query_score")),
        )
        existing["rank"] = max(
            _coerce_score(existing.get("rank")),
            _coerce_score(node.get("rank")),
        )
        merged_source_ids = _serialize_source_chunk_ids(
            existing.get("source_chunk_ids"),
            existing.get("source_id"),
            normalized_source_ids,
        )
        if merged_source_ids:
            existing["source_chunk_ids"] = merged_source_ids
        for key in ("description", "file_path", "entity_type", "entity_id", "created_at"):
            if existing.get(key) in (None, "", [], {}):
                existing[key] = node.get(key)

    return list(merged_nodes.values())


def _get_edge_seed_key(edge_data: dict[str, Any]) -> tuple[str, str] | None:
    if not isinstance(edge_data, dict):
        return None
    src_tgt = edge_data.get("src_tgt")
    if isinstance(src_tgt, (list, tuple)) and len(src_tgt) >= 2:
        return (str(src_tgt[0]), str(src_tgt[1]))
    src = edge_data.get("src_id") or edge_data.get("src")
    tgt = edge_data.get("tgt_id") or edge_data.get("tgt")
    if src in (None, "") or tgt in (None, ""):
        return None
    return (str(src), str(tgt))


def _dedupe_graph_edge_seeds(edge_datas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_edges: dict[tuple[str, str], dict[str, Any]] = {}
    for edge in edge_datas or []:
        edge_key = _get_edge_seed_key(edge)
        if edge_key is None:
            continue
        normalized_source_ids = _serialize_source_chunk_ids(
            edge.get("source_chunk_ids"),
            edge.get("source_id"),
        )
        if edge_key not in merged_edges:
            merged_edges[edge_key] = {
                **edge,
                "src_tgt": edge_key,
                "src_id": edge_key[0],
                "tgt_id": edge_key[1],
                "query_score": _coerce_score(edge.get("query_score")),
            }
            if normalized_source_ids:
                merged_edges[edge_key]["source_chunk_ids"] = normalized_source_ids
            continue

        existing = merged_edges[edge_key]
        existing["query_score"] = max(
            _coerce_score(existing.get("query_score")),
            _coerce_score(edge.get("query_score")),
        )
        existing["rank"] = max(
            _coerce_score(existing.get("rank")),
            _coerce_score(edge.get("rank")),
        )
        existing["weight"] = max(
            _coerce_score(existing.get("weight")),
            _coerce_score(edge.get("weight")),
        )
        merged_source_ids = _serialize_source_chunk_ids(
            existing.get("source_chunk_ids"),
            existing.get("source_id"),
            normalized_source_ids,
        )
        if merged_source_ids:
            existing["source_chunk_ids"] = merged_source_ids
        for key in ("description", "file_path", "created_at"):
            if existing.get(key) in (None, "", [], {}):
                existing[key] = edge.get(key)

    return list(merged_edges.values())


def _compute_graph_chunk_support_score(chunk: dict[str, Any]) -> float:
    return (
        0.6 * _coerce_score(chunk.get("graph_query_score"))
        + 0.25 * math.log1p(max(int(_coerce_score(chunk.get("graph_matched_seed_count"))), 0))
        + 0.15 * math.log1p(max(int(_coerce_score(chunk.get("graph_relation_support"))), 0))
    )


def _is_quantitative_reference_chunk(
    metadata: dict[str, Any],
    content: str,
) -> bool:
    haystack = " ".join(
        [
            str(metadata.get("section_path", "")),
            str(metadata.get("source_ref", "")),
            str(content or "")[:800],
        ]
    )
    numeric_count = len(re.findall(r"\d+(?:\.\d+)?", haystack))
    if numeric_count < 4:
        return False
    return any(hint in haystack for hint in _QUANTITATIVE_REFERENCE_HINTS)


def _normalize_query_variant_match_text(value: Any) -> str:
    normalized = _normalize_retrieval_query_text(value)
    normalized = _QUERY_VARIANT_MATCH_STRIP_RE.sub("", normalized)
    return normalized.casefold()


def _build_character_ngrams(text: str, n: int) -> set[str]:
    if not text or n <= 0:
        return set()
    if len(text) <= n:
        return {text}
    return {text[index : index + n] for index in range(len(text) - n + 1)}


def _compute_ngram_overlap_score(query_text: str, haystack_text: str, n: int) -> float:
    query_ngrams = _build_character_ngrams(query_text, n)
    if not query_ngrams:
        return 0.0
    haystack_ngrams = _build_character_ngrams(haystack_text, n)
    if not haystack_ngrams:
        return 0.0
    return len(query_ngrams & haystack_ngrams) / len(query_ngrams)


def _compute_query_variant_content_evidence(
    variant: str,
    metadata: dict[str, Any],
    content: str,
) -> float:
    normalized_variant = _normalize_query_variant_match_text(variant)
    if not normalized_variant:
        return 0.0

    haystack = " ".join(
        [
            str(metadata.get("section_path", "")),
            str(metadata.get("source_ref", "")),
            str(content or "")[:1200],
        ]
    )
    normalized_haystack = _normalize_query_variant_match_text(haystack)
    if not normalized_haystack:
        return 0.0
    if normalized_variant in normalized_haystack:
        return 1.0

    unigram_overlap = _compute_ngram_overlap_score(
        normalized_variant,
        normalized_haystack,
        1,
    )
    bigram_overlap = _compute_ngram_overlap_score(
        normalized_variant,
        normalized_haystack,
        2,
    )
    trigram_overlap = _compute_ngram_overlap_score(
        normalized_variant,
        normalized_haystack,
        3,
    )
    if len(normalized_variant) < 3:
        return min(1.0, unigram_overlap * 0.55 + bigram_overlap * 0.45)
    return min(
        1.0,
        unigram_overlap * 0.35 + bigram_overlap * 0.4 + trigram_overlap * 0.25,
    )


def _compute_query_variant_support_score(
    variant: str,
    metadata: dict[str, Any],
    content: str,
) -> float:
    content_evidence = _compute_query_variant_content_evidence(
        variant,
        metadata,
        content,
    )
    metadata_variants = {
        str(item).casefold()
        for item in metadata.get("matched_query_variants", [])
        if _is_atomic_retrieval_variant(item)
    }
    if variant.casefold() not in metadata_variants:
        return content_evidence
    if content_evidence <= 0.0:
        return _QUERY_VARIANT_METADATA_SUPPORT_FLOOR
    return max(content_evidence, min(1.0, content_evidence * 0.7 + 0.3))


def _is_low_signal_chunk_candidate(
    file_path: str,
    metadata: dict[str, Any],
    content: str,
) -> bool:
    normalized_file_path = str(file_path or "").lower()
    if normalized_file_path.endswith(_IMAGE_FILE_SUFFIXES):
        return True

    section_haystack = " ".join(
        [
            str(metadata.get("section_path", "")),
            str(metadata.get("source_ref", "")),
        ]
    )
    if any(hint in section_haystack for hint in _LOW_SIGNAL_SECTION_HINTS):
        if _is_quantitative_reference_chunk(metadata, content):
            return False
        return True

    content_preview = str(content or "")[:240]
    return "食谱示例" in content_preview


def _is_normative_chunk_candidate(
    metadata: dict[str, Any],
    content: str,
) -> bool:
    if _is_quantitative_reference_chunk(metadata, content):
        return True

    section_haystack = " ".join(
        [
            str(metadata.get("section_path", "")),
            str(metadata.get("source_ref", "")),
        ]
    )
    if any(hint in section_haystack for hint in _NORMATIVE_SECTION_HINTS):
        return True

    content_preview = str(content or "")[:320]
    return any(hint in content_preview for hint in _NORMATIVE_CONTENT_HINTS)


def _build_candidate_order(rerank_results: list[dict[str, Any]], total_count: int) -> list[int]:
    ordered_indexes: list[int] = []
    seen_indexes: set[int] = set()

    for item in rerank_results or []:
        index = item.get("index")
        if not isinstance(index, int) or not (0 <= index < total_count):
            continue
        if index in seen_indexes:
            continue
        seen_indexes.add(index)
        ordered_indexes.append(index)

    for index in range(total_count):
        if index not in seen_indexes:
            ordered_indexes.append(index)

    return ordered_indexes


def _select_hybrid_context_entries(
    rerank_results: list[dict[str, Any]],
    results_text: list[str],
    results_file_paths: list[str],
    results_chunk_metadata: list[dict[str, Any]],
    query_param: QueryParam,
    query_variants: list[str] | None = None,
) -> tuple[list[int], list[dict[str, Any]]]:
    if not results_text:
        return [], []

    chunk_limit = query_param.chunk_top_k or 10
    final_limit = min(len(results_text), max(1, min(chunk_limit, 10)))
    retrieval_indexes = list(range(len(results_text)))
    rerank_indexes = _build_candidate_order(rerank_results, len(results_text))

    candidate_meta: dict[int, dict[str, Any]] = {}
    for index in retrieval_indexes:
        file_path = results_file_paths[index]
        metadata = results_chunk_metadata[index]
        content = results_text[index]
        candidate_meta[index] = {
            "file_key": _chunk_file_group_key(file_path, metadata),
            "low_signal": _is_low_signal_chunk_candidate(file_path, metadata, content),
            "normative": _is_normative_chunk_candidate(metadata, content),
            "quantitative": _is_quantitative_reference_chunk(metadata, content),
            "matched_query_variants": {
                variant
                for variant in metadata.get("matched_query_variants", [])
                if _is_atomic_retrieval_variant(variant)
            },
            "retrieval_rank": index,
        }

    atomic_query_variants: list[str] = []
    seen_variants: set[str] = set()

    if query_variants:
        for variant in query_variants:
            normalized_variant = _normalize_retrieval_query_text(variant)
            if not normalized_variant:
                continue
            if not _is_atomic_retrieval_variant(normalized_variant):
                continue
            normalized_key = normalized_variant.casefold()
            if normalized_key in seen_variants:
                continue
            seen_variants.add(normalized_key)
            atomic_query_variants.append(normalized_variant)
    else:
        for index in retrieval_indexes:
            for variant in candidate_meta[index]["matched_query_variants"]:
                normalized_variant = variant.casefold()
                if normalized_variant in seen_variants:
                    continue
                seen_variants.add(normalized_variant)
                atomic_query_variants.append(variant)

    for index in retrieval_indexes:
        metadata = results_chunk_metadata[index]
        content = results_text[index]
        support_scores: dict[str, float] = {}
        for variant in atomic_query_variants:
            support_score = _compute_query_variant_support_score(
                variant,
                metadata,
                content,
            )
            if support_score <= 0.0:
                continue
            support_scores[variant.casefold()] = support_score
        candidate_meta[index]["query_support_scores"] = support_scores
        candidate_meta[index]["query_support_total"] = sum(
            score
            for score in support_scores.values()
            if score >= _QUERY_VARIANT_WEAK_SUPPORT_THRESHOLD
        )
        candidate_meta[index]["query_support_hit_count"] = sum(
            1
            for score in support_scores.values()
            if score >= _QUERY_VARIANT_STRONG_SUPPORT_THRESHOLD
        )

    selected_indexes: list[int] = []
    selected_set: set[int] = set()
    file_counts: Counter[str] = Counter()

    def _try_select(index: int) -> bool:
        if index in selected_set:
            return False
        file_key = candidate_meta[index]["file_key"]
        if file_counts[file_key] >= 2:
            return False
        selected_indexes.append(index)
        selected_set.add(index)
        file_counts[file_key] += 1
        return True

    def _run_selection_pass(
        ordered_indexes: list[int],
        predicate,
        target_limit: int,
    ) -> None:
        for index in ordered_indexes:
            if len(selected_indexes) >= target_limit:
                break
            if predicate(candidate_meta[index]):
                _try_select(index)

    retrieval_seed_limit = min(final_limit, max(2, min(5, (final_limit + 1) // 2)))
    covered_query_variants: set[str] = set()

    variant_support_counts: dict[str, int] = {}
    for variant in atomic_query_variants:
        variant_key = variant.casefold()
        variant_support_counts[variant_key] = sum(
            1
            for index in retrieval_indexes
            if candidate_meta[index]["query_support_scores"].get(variant_key, 0.0)
            >= _QUERY_VARIANT_STRONG_SUPPORT_THRESHOLD
        )

    def _variant_priority_key(variant: str) -> tuple[float, int, int]:
        variant_key = variant.casefold()
        support_count = variant_support_counts.get(variant_key, 0)
        return (
            math.inf if support_count == 0 else support_count,
            -len(_normalize_query_variant_match_text(variant)),
            atomic_query_variants.index(variant),
        )

    prioritized_query_variants = sorted(
        atomic_query_variants,
        key=_variant_priority_key,
    )

    retrieval_priority_indexes = sorted(
        retrieval_indexes,
        key=lambda index: (
            -candidate_meta[index]["query_support_hit_count"],
            -candidate_meta[index]["query_support_total"],
            index,
        ),
    )

    for variant in prioritized_query_variants:
        if len(selected_indexes) >= retrieval_seed_limit:
            break
        variant_key = variant.casefold()
        best_index = None
        best_key = None
        for index in retrieval_priority_indexes:
            meta = candidate_meta[index]
            if meta["low_signal"]:
                continue
            support_score = meta["query_support_scores"].get(variant_key, 0.0)
            if support_score < _QUERY_VARIANT_WEAK_SUPPORT_THRESHOLD:
                continue
            candidate_key = (
                support_score,
                meta["query_support_hit_count"],
                meta["query_support_total"],
                -meta["retrieval_rank"],
            )
            if best_key is None or candidate_key > best_key:
                best_key = candidate_key
                best_index = index
        if best_index is None:
            continue
        if not _try_select(best_index):
            continue
        covered_query_variants.update(
            variant.casefold()
            for variant in candidate_meta[best_index]["matched_query_variants"]
        )

    retrieval_first_passes = (
        lambda meta: meta["normative"] and not meta["low_signal"],
        lambda meta: not meta["low_signal"],
    )
    rerank_passes = (
        lambda meta: meta["normative"] and not meta["low_signal"],
        lambda meta: not meta["low_signal"],
        lambda meta: meta["normative"] and not meta["low_signal"] and file_counts[meta["file_key"]] == 0,
        lambda meta: not meta["low_signal"] and file_counts[meta["file_key"]] == 0,
        lambda meta: True,
    )

    for predicate in retrieval_first_passes:
        _run_selection_pass(retrieval_priority_indexes, predicate, retrieval_seed_limit)
        if len(selected_indexes) >= retrieval_seed_limit:
            break

    for index in selected_indexes:
        covered_query_variants.update(
            variant.casefold()
            for variant in candidate_meta[index]["matched_query_variants"]
        )

    for predicate in rerank_passes:
        _run_selection_pass(rerank_indexes, predicate, final_limit)
        if len(selected_indexes) >= final_limit:
            break

    grouped_selected_indexes: dict[str, list[int]] = defaultdict(list)
    for selected_index in selected_indexes:
        grouped_selected_indexes[candidate_meta[selected_index]["file_key"]].append(
            selected_index
        )

    for file_key, group_selected in grouped_selected_indexes.items():
        if not group_selected:
            continue
        if not any(candidate_meta[index]["quantitative"] for index in group_selected):
            continue

        group_candidates = sorted(
            [
                index
                for index in retrieval_indexes
                if candidate_meta[index]["file_key"] == file_key
                and candidate_meta[index]["quantitative"]
                and not candidate_meta[index]["low_signal"]
            ],
            key=lambda index: (
                -candidate_meta[index]["query_support_hit_count"],
                -candidate_meta[index]["query_support_total"],
                -int(candidate_meta[index]["normative"]),
                candidate_meta[index]["retrieval_rank"],
            ),
        )
        if not group_candidates:
            continue

        preferred_group_candidates = group_candidates[: len(group_selected)]
        missing_candidates = [
            index for index in preferred_group_candidates if index not in selected_set
        ]
        if not missing_candidates:
            continue

        replaceable_positions = sorted(
            [
                position
                for position, index in enumerate(selected_indexes)
                if candidate_meta[index]["file_key"] == file_key
                and index not in preferred_group_candidates
            ],
            key=lambda position: (
                candidate_meta[selected_indexes[position]]["query_support_hit_count"],
                candidate_meta[selected_indexes[position]]["query_support_total"],
                int(candidate_meta[selected_indexes[position]]["normative"]),
                -candidate_meta[selected_indexes[position]]["retrieval_rank"],
            ),
        )
        for new_index, replace_position in zip(missing_candidates, replaceable_positions):
            old_index = selected_indexes[replace_position]
            selected_indexes[replace_position] = new_index
            selected_set.remove(old_index)
            selected_set.add(new_index)

    text_units_context: list[dict[str, Any]] = []
    for rank, index in enumerate(selected_indexes, 1):
        chunk_entry = {
            "content": results_text[index],
            "file_path": results_file_paths[index],
        }
        chunk_entry.update(results_chunk_metadata[index])
        text_units_context.append(_build_chunk_context_entry(rank, chunk_entry))

    return selected_indexes, text_units_context


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
    if doc_metadata and doc_metadata.get("preserve_chunking"):
        chunk_content = _strip_doc_name_markers(content).strip()
        chunk_data = {
            "tokens": len(tokenizer.encode(chunk_content)),
            "content": doc_name + "#####" + chunk_content,
            "chunk_order_index": 0,
        }
        return [_annotate_chunk_with_source_metadata(chunk_data, doc_metadata)]

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
    if not _has_complete_rerank_env_config():
        logger.warning(
            "Rerank skipped because RERANK_* config is incomplete: missing %s",
            ", ".join(_missing_rerank_env_names()),
        )
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
    entity_vdb_payload: dict[str, dict[str, Any]] = {}
    relationship_vdb_payload: dict[str, dict[str, Any]] = {}
    for task in asyncio.as_completed(tasks):
        task_kind, task_key, task_result = await task
        if task_kind == "entity":
            merged_entities += 1
            if task_result is not None and entity_vdb is not None:
                entity_vdb_payload[
                    compute_mdhash_id(task_result["entity_name"], prefix="ent-")
                ] = {
                    "entity_name": task_result["entity_name"],
                    "entity_type": task_result["entity_type"],
                    "content": (
                        f"{task_result['entity_name']}\n"
                        f"{task_result['description']}"
                    ),
                    "embeddings": task_result["embeddings"],
                    "source_id": task_result["source_id"],
                    "source_chunk_ids": task_result.get(
                        "source_chunk_ids", task_result["source_id"]
                    ),
                    "file_path": task_result.get("file_path", "unknown_source"),
                }
        else:
            merged_relations += 1
            if task_result is not None and relationships_vdb is not None:
                relationship_vdb_payload[
                    compute_mdhash_id(
                        task_result["src_id"] + task_result["tgt_id"],
                        prefix="rel-",
                    )
                ] = {
                    "src_id": task_result["src_id"],
                    "tgt_id": task_result["tgt_id"],
                    "keywords": task_result["keywords"],
                    "content": (
                        f"{task_result['src_id']}\t{task_result['tgt_id']}\n"
                        f"{task_result['keywords']}\n{task_result['description']}"
                    ),
                    "source_id": task_result["source_id"],
                    "source_chunk_ids": task_result.get(
                        "source_chunk_ids", task_result["source_id"]
                    ),
                    "file_path": task_result.get("file_path", "unknown_source"),
                }
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

    upsert_tasks = []
    if entity_vdb is not None and entity_vdb_payload:
        upsert_tasks.append(entity_vdb.upsert(entity_vdb_payload))
    if relationships_vdb is not None and relationship_vdb_payload:
        upsert_tasks.append(relationships_vdb.upsert(relationship_vdb_payload))
    if upsert_tasks:
        await asyncio.gather(*upsert_tasks)


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
    entity_extract_gleaning_level = global_config.get(
        "entity_extract_gleaning_level", 1
    )
    if not isinstance(entity_extract_gleaning_level, int):
        entity_extract_gleaning_level = 1
    entity_extract_gleaning_level = max(1, min(2, entity_extract_gleaning_level))

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

        async def _should_continue_gleaning(history_messages: list[dict[str, str]]) -> bool:
            if_loop_result: str = await use_llm_func_with_cache(
                if_loop_prompt,
                use_llm_func,
                llm_response_cache=llm_response_cache,
                history_messages=history_messages,
                cache_type="extract",
                cache_keys_collector=cache_keys_collector,
            )
            if_loop_result = if_loop_result.strip().strip('"').strip("'").lower()
            return if_loop_result == "yes"

        # Process additional gleaning results
        for now_glean_index in range(entity_extract_max_gleaning):
            if now_glean_index == 0:
                if entity_extract_gleaning_level >= 2 and not (
                    await _should_continue_gleaning(history)
                ):
                    break
            else:
                if not await _should_continue_gleaning(history):
                    break

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
        
        chunk_embedding = chunk_dp.get("embeddings")
        if chunk_embedding is None:
            chunk_embedding = (
                await _generate_chunk_text_embeddings(
                    [(chunk_key, content)],
                    global_config,
                )
            )[chunk_key]

        chunk_data = {
        'entity_name': chunk_key,
        'entity_type': "chunk_text",
        'description': content,
        'embeddings': chunk_embedding,
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


async def _build_graph_context_debug_data_from_hits(
    query: str,
    *,
    ll_entities_context: list[dict[str, Any]],
    hl_entities_context: list[dict[str, Any]],
    ll_relations_context: list[dict[str, Any]],
    hl_relations_context: list[dict[str, Any]],
    ll_node_datas: list[dict[str, Any]],
    hl_node_datas: list[dict[str, Any]],
    ll_edge_datas: list[dict[str, Any]],
    hl_edge_datas: list[dict[str, Any]],
    knowledge_graph_inst: BaseGraphStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    timing_collector: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    logger.info(f"Process {os.getpid()} building graph retrieval context...")
    stage_timings = timing_collector if timing_collector is not None else []
    context_total_started_at = time.perf_counter()

    all_chunks: list[dict[str, Any]] = []
    entities_context = process_combine_contexts(
        ll_entities_context,
        hl_entities_context,
    )
    relations_context = process_combine_contexts(
        hl_relations_context,
        ll_relations_context,
    )
    original_node_datas = list(ll_node_datas or []) + list(hl_node_datas or [])
    original_edge_datas = list(ll_edge_datas or []) + list(hl_edge_datas or [])

    logger.info(
        "Initial graph context: %s entities, %s relations, %s chunks",
        len(entities_context),
        len(relations_context),
        len(all_chunks),
    )

    tokenizer = text_chunks_db.global_config.get("tokenizer")
    stage_started_at = time.perf_counter()
    if tokenizer:
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

        if entities_context:
            original_entity_count = len(entities_context)
            for entity in entities_context:
                if "file_path" in entity and entity["file_path"]:
                    entity["file_path"] = entity["file_path"].replace(
                        GRAPH_FIELD_SEP, ";"
                    )
            entities_context = truncate_list_by_token_size(
                entities_context,
                key=lambda item: json.dumps(item, ensure_ascii=False),
                max_token_size=max_entity_tokens,
                tokenizer=tokenizer,
            )
            if len(entities_context) < original_entity_count:
                logger.debug(
                    "Truncated entities: %s -> %s (entity max tokens: %s)",
                    original_entity_count,
                    len(entities_context),
                    max_entity_tokens,
                )

        if relations_context:
            original_relation_count = len(relations_context)
            for relation in relations_context:
                if "file_path" in relation and relation["file_path"]:
                    relation["file_path"] = relation["file_path"].replace(
                        GRAPH_FIELD_SEP, ";"
                    )
            relations_context = truncate_list_by_token_size(
                relations_context,
                key=lambda item: json.dumps(item, ensure_ascii=False),
                max_token_size=max_relation_tokens,
                tokenizer=tokenizer,
            )
            if len(relations_context) < original_relation_count:
                logger.debug(
                    "Truncated relations: %s -> %s (relation max tokens: %s)",
                    original_relation_count,
                    len(relations_context),
                    max_relation_tokens,
                )
    if timing_collector is not None:
        _record_stage_timing(
            stage_timings,
            "graph_context_structured_pruning",
            "图谱上下文整理 / 实体关系裁剪",
            stage_started_at,
        )

    logger.info("Getting text chunks based on truncated entities and relations...")
    final_node_datas: list[dict[str, Any]] = []
    if entities_context and original_node_datas:
        final_entity_names = {item["entity"] for item in entities_context}
        seen_nodes = set()
        for node in original_node_datas:
            name = node.get("entity_name")
            if name in final_entity_names and name not in seen_nodes:
                final_node_datas.append(node)
                seen_nodes.add(name)

    final_edge_datas: list[dict[str, Any]] = []
    if relations_context and original_edge_datas:
        final_relation_pairs = {
            (item["entity1"], item["entity2"]) for item in relations_context
        }
        seen_edges = set()
        for edge in original_edge_datas:
            src, tgt = edge.get("src_id"), edge.get("tgt_id")
            if src is None or tgt is None:
                src, tgt = edge.get("src_tgt", (None, None))
            pair = (src, tgt)
            if pair in final_relation_pairs and pair not in seen_edges:
                final_edge_datas.append(edge)
                seen_edges.add(pair)

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

    text_units_context: list[dict[str, Any]] = []
    stage_started_at = time.perf_counter()
    if tokenizer and all_chunks:
        entities_str = json.dumps(entities_context, ensure_ascii=False)
        relations_str = json.dumps(relations_context, ensure_ascii=False)
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
            entities_str=entities_str,
            relations_str=relations_str,
        )
        kg_context_tokens = len(tokenizer.encode(kg_context))

        history_context = ""
        if query_param.conversation_history:
            history_context = get_conversation_turns(
                query_param.conversation_history,
                query_param.history_turns,
            )

        user_prompt = query_param.user_prompt if query_param.user_prompt else ""
        response_type = query_param.response_type or "Multiple Paragraphs"
        sys_prompt_template = text_chunks_db.global_config.get(
            "system_prompt_template", PROMPTS["rag_response"]
        )
        sample_sys_prompt = sys_prompt_template.format(
            history=history_context,
            context_data="",
            response_type=response_type,
            user_prompt=user_prompt,
        )
        query_tokens = len(tokenizer.encode(query))
        sys_prompt_template_tokens = len(tokenizer.encode(sample_sys_prompt))
        sys_prompt_overhead = sys_prompt_template_tokens + query_tokens
        buffer_tokens = 100
        used_tokens = kg_context_tokens + sys_prompt_overhead + buffer_tokens
        available_chunk_tokens = max_total_tokens - used_tokens

        logger.debug(
            "Token allocation - Total: %s, SysPrompt: %s, KG: %s, Buffer: %s, Available for chunks: %s",
            max_total_tokens,
            sys_prompt_overhead,
            kg_context_tokens,
            buffer_tokens,
            available_chunk_tokens,
        )

        temp_chunks = [chunk.copy() for chunk in all_chunks]
        truncated_chunks = await process_chunks_unified(
            query=query,
            chunks=temp_chunks,
            query_param=query_param,
            global_config=text_chunks_db.global_config,
            source_type="mixed",
            chunk_token_limit=available_chunk_tokens,
        )
        for index, chunk in enumerate(truncated_chunks):
            text_units_context.append(_build_chunk_context_entry(index + 1, chunk))

        logger.debug(
            "Re-truncated chunks for dynamic token limit: %s -> %s (chunk available tokens: %s)",
            len(temp_chunks),
            len(text_units_context),
            available_chunk_tokens,
        )
    if timing_collector is not None:
        _record_stage_timing(
            stage_timings,
            "graph_context_chunk_postprocess",
            "图谱上下文整理 / Chunk 重排与截断",
            stage_started_at,
        )
        _record_stage_timing(
            stage_timings,
            "graph_context_total",
            "图谱上下文构建总耗时",
            context_total_started_at,
        )

    referenced_file_paths = _collect_referenced_file_paths(
        entities_context,
        relations_context,
        text_units_context,
    )

    logger.info(
        "Final graph retrieval context: %s entities, %s relations, %s chunks",
        len(entities_context),
        len(relations_context),
        len(text_units_context),
    )

    return {
        "entities_context": entities_context,
        "relations_context": relations_context,
        "text_units_context": text_units_context,
        "referenced_file_paths": referenced_file_paths,
        "context_available": bool(entities_context or relations_context),
        "stage_timings": stage_timings,
    }


async def _build_graph_retrieval_debug_data(
    query: str,
    knowledge_graph_inst: BaseGraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    global_config: dict[str, Any],
    hashing_kv: BaseKVStorage | None = None,
) -> dict[str, Any]:
    stage_timings: list[dict[str, Any]] = []
    stage_started_at = time.perf_counter()
    hl_keywords, ll_keywords = await get_keywords_from_query(
        query,
        query_param,
        global_config,
        hashing_kv,
    )
    _record_stage_timing(
        stage_timings,
        "keyword_extraction",
        "关键词提取",
        stage_started_at,
    )

    ll_keywords_str = ", ".join(ll_keywords) if ll_keywords else ""
    hl_keywords_str = ", ".join(hl_keywords) if hl_keywords else ""

    stage_started_at = time.perf_counter()
    ll_entities_context, ll_relations_context, ll_node_datas, ll_use_relations = (
        await _get_node_data(
            ll_keywords_str,
            knowledge_graph_inst,
            entities_vdb,
            query_param,
        )
    )
    _record_stage_timing(
        stage_timings,
        "graph_entity_hits",
        "图谱命中 / 实体",
        stage_started_at,
    )

    stage_started_at = time.perf_counter()
    hl_entities_context, hl_relations_context, hl_edge_datas, hl_use_entities = (
        await _get_edge_data(
            hl_keywords_str,
            knowledge_graph_inst,
            relationships_vdb,
            query_param,
        )
    )
    _record_stage_timing(
        stage_timings,
        "graph_relation_hits",
        "图谱命中 / 关系",
        stage_started_at,
    )

    graph_entities = process_combine_contexts(
        ll_entities_context,
        hl_entities_context,
    )
    graph_relations = process_combine_contexts(
        hl_relations_context,
        ll_relations_context,
    )

    context_debug = await _build_graph_context_debug_data_from_hits(
        query,
        ll_entities_context=ll_entities_context,
        hl_entities_context=hl_entities_context,
        ll_relations_context=ll_relations_context,
        hl_relations_context=hl_relations_context,
        ll_node_datas=ll_node_datas,
        hl_node_datas=hl_use_entities,
        ll_edge_datas=ll_use_relations,
        hl_edge_datas=hl_edge_datas,
        knowledge_graph_inst=knowledge_graph_inst,
        text_chunks_db=text_chunks_db,
        query_param=query_param,
        timing_collector=stage_timings,
    )

    return {
        "high_level_keywords": hl_keywords,
        "low_level_keywords": ll_keywords,
        **keyword_extraction.keyword_metadata_from_query_param(query_param),
        "graph_entities": graph_entities,
        "graph_relations": graph_relations,
        **context_debug,
        "stage_timings": stage_timings,
    }


def _build_graph_context_cache_payload(
    retrieval_debug: dict[str, Any],
    *,
    answer_prompt_mode: str,
    corpus_revision: int,
) -> dict[str, Any]:
    context_available = bool(retrieval_debug.get("context_available"))
    referenced_file_paths = retrieval_debug.get("referenced_file_paths") or []
    debug_payload_cacheable = _strip_stage_timings(retrieval_debug)
    if not context_available:
        return _build_query_cache_payload(
            result_kind=_QUERY_RESULT_KIND_CONTEXT,
            context_text=PROMPTS["fail_response"],
            referenced_file_paths=referenced_file_paths,
            final_context_document_chunks=[],
            debug_payload_cacheable=debug_payload_cacheable,
            context_available=False,
            corpus_revision=corpus_revision,
        )

    llm_entities_context = _sanitize_llm_context_payload(
        retrieval_debug.get("entities_context", []),
        answer_prompt_mode=answer_prompt_mode,
    )
    llm_relations_context = _sanitize_llm_context_payload(
        retrieval_debug.get("relations_context", []),
        answer_prompt_mode=answer_prompt_mode,
    )
    llm_text_units_context = _sanitize_llm_context_payload(
        retrieval_debug.get("text_units_context", []),
        answer_prompt_mode=answer_prompt_mode,
    )
    entities_str = json.dumps(llm_entities_context, ensure_ascii=False)
    relations_str = json.dumps(llm_relations_context, ensure_ascii=False)
    text_units_str = json.dumps(llm_text_units_context, ensure_ascii=False)
    context_text = f"""-----Entities(KG)-----

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
    return _build_query_cache_payload(
        result_kind=_QUERY_RESULT_KIND_CONTEXT,
        context_text=context_text,
        referenced_file_paths=referenced_file_paths,
        final_context_document_chunks=llm_text_units_context,
        debug_payload_cacheable=debug_payload_cacheable,
        context_available=True,
        corpus_revision=corpus_revision,
    )


def _build_graph_prompt_cache_payload(
    context_payload: dict[str, Any],
    *,
    query_param: QueryParam,
    system_prompt: str | None,
    answer_prompt_mode: str,
    corpus_revision: int,
) -> dict[str, Any]:
    if not context_payload.get("context_available", True):
        return _build_query_cache_payload(
            result_kind=_QUERY_RESULT_KIND_PROMPT,
            context_text=context_payload.get("context_text", PROMPTS["fail_response"]),
            referenced_file_paths=context_payload.get("referenced_file_paths") or [],
            final_context_document_chunks=context_payload.get(
                "final_context_document_chunks"
            )
            or [],
            debug_payload_cacheable=context_payload.get("debug_payload_cacheable")
            or {},
            context_available=False,
            corpus_revision=corpus_revision,
        )

    history_context = ""
    if query_param.conversation_history:
        history_context = get_conversation_turns(
            query_param.conversation_history, query_param.history_turns
        )

    user_prompt = (
        query_param.user_prompt
        if query_param.user_prompt
        else PROMPTS["DEFAULT_USER_PROMPT"]
    )
    default_prompt_key = (
        "rag_response_single_prompt"
        if answer_prompt_mode == "single_prompt"
        else "rag_response"
    )
    sys_prompt_template = system_prompt if system_prompt else PROMPTS[default_prompt_key]
    prompt_text = sys_prompt_template.format(
        context_data=context_payload["context_text"],
        response_type=query_param.response_type,
        history=history_context,
        user_prompt=user_prompt,
    )
    return _build_query_cache_payload(
        result_kind=_QUERY_RESULT_KIND_PROMPT,
        context_text=context_payload["context_text"],
        prompt_text=prompt_text,
        referenced_file_paths=context_payload.get("referenced_file_paths") or [],
        final_context_document_chunks=context_payload.get(
            "final_context_document_chunks"
        )
        or [],
        debug_payload_cacheable=context_payload.get("debug_payload_cacheable") or {},
        context_available=True,
        corpus_revision=corpus_revision,
    )


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
    _validate_query_request_flags(query_param)
    stage_timings: list[dict[str, Any]] = []
    query_total_started_at = time.perf_counter()
    await _resolve_no_llm_keywords_for_retrieval_cache(
        query,
        query_param,
        global_config,
        hashing_kv,
    )
    answer_prompt_mode = _resolve_answer_prompt_mode(query_param, global_config)
    corpus_revision = _coerce_non_negative_int(
        global_config.get("corpus_revision"),
        0,
    )
    answer_cache_key = _build_query_request_fingerprint(
        scope=_QUERY_CACHE_TYPE_ANSWER,
        query=query,
        query_param=query_param,
        global_config=global_config,
        answer_prompt_mode=answer_prompt_mode,
        system_prompt=system_prompt,
    )

    if not query_param.only_need_context and not query_param.only_need_prompt:
        answer_cache_payload = await _load_query_cache_payload(
            hashing_kv,
            args_hash=answer_cache_key,
            mode=query_param.mode,
            cache_type=_QUERY_CACHE_TYPE_ANSWER,
            expected_result_kind=_QUERY_RESULT_KIND_ANSWER,
            stage_timings=stage_timings,
            lookup_stage="query_cache_lookup",
            lookup_label="最终答案缓存检查",
            hit_stage="answer_cache_hit",
            hit_label="最终答案缓存命中",
        )
        if answer_cache_payload is not None:
            referenced_file_paths = answer_cache_payload["referenced_file_paths"]
            response = answer_cache_payload["answer"]
            _record_stage_timing(
                stage_timings,
                "onehop_total",
                "OneHop 查询总耗时",
                query_total_started_at,
            )
            if return_debug:
                debug_payload = _hydrate_debug_payload(
                    cacheable_debug_payload=answer_cache_payload[
                        "debug_payload_cacheable"
                    ],
                    context_text=answer_cache_payload["context_text"],
                    prompt_text=answer_cache_payload["prompt_text"],
                    final_context_document_chunks=answer_cache_payload[
                        "final_context_document_chunks"
                    ],
                    stage_timings=stage_timings,
                )
                return response, referenced_file_paths, debug_payload
            return response, referenced_file_paths

    retrieval_cache_key = _build_query_request_fingerprint(
        scope=_QUERY_CACHE_TYPE_RETRIEVAL,
        query=query,
        query_param=query_param,
        global_config=global_config,
        answer_prompt_mode=answer_prompt_mode,
    )
    async def _compute_graph_retrieval_payload() -> dict[str, Any]:
        retrieval_debug = await _build_graph_retrieval_debug_data(
            query,
            knowledge_graph_inst,
            entities_vdb,
            relationships_vdb,
            text_chunks_db,
            query_param,
            global_config,
            hashing_kv,
        )
        stage_timings.extend(retrieval_debug.get("stage_timings", []))
        return _build_query_cache_payload(
            result_kind=_QUERY_RESULT_KIND_RETRIEVAL,
            referenced_file_paths=retrieval_debug.get("referenced_file_paths")
            or [],
            debug_payload_cacheable=_strip_stage_timings(retrieval_debug),
            context_available=bool(retrieval_debug.get("context_available", True)),
            corpus_revision=corpus_revision,
        )

    retrieval_cache_payload = await _get_or_compute_query_cache_payload(
        hashing_kv,
        args_hash=retrieval_cache_key,
        mode=query_param.mode,
        cache_type=_QUERY_CACHE_TYPE_RETRIEVAL,
        expected_result_kind=_QUERY_RESULT_KIND_RETRIEVAL,
        prompt=query,
        compute_payload=_compute_graph_retrieval_payload,
        stage_timings=stage_timings,
        lookup_stage="retrieval_cache_lookup",
        lookup_label="检索缓存检查",
        hit_stage="retrieval_cache_hit",
        hit_label="检索缓存命中",
    )
    retrieval_debug = dict(retrieval_cache_payload["debug_payload_cacheable"])

    context_cache_key = _build_query_request_fingerprint(
        scope=_QUERY_CACHE_TYPE_RENDER,
        query=query,
        query_param=query_param,
        global_config=global_config,
        answer_prompt_mode=answer_prompt_mode,
        render_kind=_QUERY_RESULT_KIND_CONTEXT,
    )
    context_payload = await _load_query_cache_payload(
        hashing_kv,
        args_hash=context_cache_key,
        mode=query_param.mode,
        cache_type=_QUERY_CACHE_TYPE_RENDER,
        expected_result_kind=_QUERY_RESULT_KIND_CONTEXT,
        stage_timings=stage_timings,
        lookup_stage="render_cache_lookup",
        lookup_label="上下文渲染缓存检查",
        hit_stage="render_cache_hit",
        hit_label="上下文渲染缓存命中",
    )
    if context_payload is None:
        stage_started_at = time.perf_counter()
        context_payload = _build_graph_context_cache_payload(
            retrieval_debug,
            answer_prompt_mode=answer_prompt_mode,
            corpus_revision=corpus_revision,
        )
        _record_stage_timing(
            stage_timings,
            "graph_context_serialize",
            "图谱上下文整理 / 序列化",
            stage_started_at,
        )
        await _save_query_cache_payload(
            hashing_kv,
            args_hash=context_cache_key,
            mode=query_param.mode,
            cache_type=_QUERY_CACHE_TYPE_RENDER,
            prompt=query,
            payload=context_payload,
        )

    referenced_file_paths = context_payload["referenced_file_paths"]

    if query_param.only_need_context:
        context_output = context_payload["context_text"]
        if return_debug:
            debug_payload = _hydrate_debug_payload(
                cacheable_debug_payload=context_payload["debug_payload_cacheable"],
                context_text=context_output,
                prompt_text="",
                final_context_document_chunks=context_payload[
                    "final_context_document_chunks"
                ],
                stage_timings=stage_timings,
            )
            _record_stage_timing(
                stage_timings,
                "onehop_total",
                "OneHop 查询总耗时",
                query_total_started_at,
            )
            debug_payload["stage_timings"] = stage_timings
            return context_output, referenced_file_paths, debug_payload
        return context_output

    if not context_payload.get("context_available", True):
        fail_response = context_payload["context_text"]
        _record_stage_timing(
            stage_timings,
            "onehop_total",
            "OneHop 查询总耗时",
            query_total_started_at,
        )
        if return_debug:
            debug_payload = _hydrate_debug_payload(
                cacheable_debug_payload=context_payload["debug_payload_cacheable"],
                context_text=fail_response,
                prompt_text="",
                final_context_document_chunks=context_payload[
                    "final_context_document_chunks"
                ],
                stage_timings=stage_timings,
            )
            return fail_response, referenced_file_paths, debug_payload
        return fail_response, referenced_file_paths

    prompt_cache_key = _build_query_request_fingerprint(
        scope=_QUERY_CACHE_TYPE_RENDER,
        query=query,
        query_param=query_param,
        global_config=global_config,
        answer_prompt_mode=answer_prompt_mode,
        system_prompt=system_prompt,
        render_kind=_QUERY_RESULT_KIND_PROMPT,
    )
    prompt_payload = await _load_query_cache_payload(
        hashing_kv,
        args_hash=prompt_cache_key,
        mode=query_param.mode,
        cache_type=_QUERY_CACHE_TYPE_RENDER,
        expected_result_kind=_QUERY_RESULT_KIND_PROMPT,
        stage_timings=stage_timings,
        lookup_stage="prompt_cache_lookup",
        lookup_label="Prompt 渲染缓存检查",
        hit_stage="prompt_cache_hit",
        hit_label="Prompt 渲染缓存命中",
    )
    if prompt_payload is None:
        prompt_payload = _build_graph_prompt_cache_payload(
            context_payload,
            query_param=query_param,
            system_prompt=system_prompt,
            answer_prompt_mode=answer_prompt_mode,
            corpus_revision=corpus_revision,
        )
        _append_stage_timing(
            stage_timings,
            "prompt_assembly",
            "回答提示词拼装",
            0.0,
        )
        await _save_query_cache_payload(
            hashing_kv,
            args_hash=prompt_cache_key,
            mode=query_param.mode,
            cache_type=_QUERY_CACHE_TYPE_RENDER,
            prompt=query,
            payload=prompt_payload,
        )

    if query_param.only_need_prompt:
        prompt_text = prompt_payload["prompt_text"]
        if return_debug:
            _record_stage_timing(
                stage_timings,
                "onehop_total",
                "OneHop 查询总耗时",
                query_total_started_at,
            )
            debug_payload = _hydrate_debug_payload(
                cacheable_debug_payload=prompt_payload["debug_payload_cacheable"],
                context_text=context_payload["context_text"],
                prompt_text=prompt_text,
                final_context_document_chunks=context_payload[
                    "final_context_document_chunks"
                ],
                stage_timings=stage_timings,
            )
            return prompt_text, referenced_file_paths, debug_payload
        return prompt_text

    use_model_func = _resolve_query_llm_func(query_param, global_config)
    tokenizer: Tokenizer = global_config["tokenizer"]
    prompt_text = prompt_payload["prompt_text"]
    len_of_prompts = len(tokenizer.encode(query + prompt_text))
    logger.debug(
        f"[kg_query] Sending to LLM: {len_of_prompts:,} tokens (Query: {len(tokenizer.encode(query))}, System: {len(tokenizer.encode(prompt_text))})"
    )

    answer_cache_payload = None
    if return_debug:
        answer_cache_payload = await _load_query_cache_payload(
            hashing_kv,
            args_hash=answer_cache_key,
            mode=query_param.mode,
            cache_type=_QUERY_CACHE_TYPE_ANSWER,
            expected_result_kind=_QUERY_RESULT_KIND_ANSWER,
            stage_timings=stage_timings,
            lookup_stage="answer_cache_lookup",
            lookup_label="最终答案缓存检查",
            hit_stage="answer_cache_hit",
            hit_label="最终答案缓存命中",
        )

    if answer_cache_payload is None:
        async def _compute_graph_answer_payload() -> dict[str, Any]:
            stage_started_at = time.perf_counter()
            response = await use_model_func(
                query,
                system_prompt=prompt_text,
                stream=query_param.stream,
            )
            _record_stage_timing(
                stage_timings,
                "answer_generation",
                "回答生成 / 单轮 LLM"
                if answer_prompt_mode == "single_prompt"
                else "回答生成 / 第一轮 LLM",
                stage_started_at,
            )
            if isinstance(response, str) and len(response) > len(prompt_text):
                response = (
                    response.replace(prompt_text, "")
                    .replace("user", "")
                    .replace("model", "")
                    .replace(query, "")
                    .replace("<system>", "")
                    .replace("</system>", "")
                    .strip()
                )
            if answer_prompt_mode == "two_stage":
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
            return _build_query_cache_payload(
                result_kind=_QUERY_RESULT_KIND_ANSWER,
                answer=response if isinstance(response, str) else "",
                context_text=context_payload["context_text"],
                prompt_text=prompt_text,
                referenced_file_paths=referenced_file_paths,
                final_context_document_chunks=context_payload[
                    "final_context_document_chunks"
                ],
                debug_payload_cacheable=prompt_payload["debug_payload_cacheable"],
                context_available=True,
                corpus_revision=corpus_revision,
            )

        answer_cache_payload = await _get_or_compute_query_cache_payload(
            hashing_kv,
            args_hash=answer_cache_key,
            mode=query_param.mode,
            cache_type=_QUERY_CACHE_TYPE_ANSWER,
            expected_result_kind=_QUERY_RESULT_KIND_ANSWER,
            prompt=query,
            compute_payload=_compute_graph_answer_payload,
            stage_timings=stage_timings,
            lookup_stage="answer_cache_lookup",
            lookup_label="最终答案缓存检查",
            hit_stage="answer_cache_hit",
            hit_label="最终答案缓存命中",
            skip_initial_lookup=answer_cache_payload is None,
        )
    response = answer_cache_payload["answer"]

    _record_stage_timing(
        stage_timings,
        "onehop_total",
        "OneHop 查询总耗时",
        query_total_started_at,
    )

    if return_debug:
        debug_payload = _hydrate_debug_payload(
            cacheable_debug_payload=prompt_payload["debug_payload_cacheable"],
            context_text=context_payload["context_text"],
            prompt_text=prompt_text,
            final_context_document_chunks=context_payload[
                "final_context_document_chunks"
            ],
            stage_timings=stage_timings,
        )
        return response, referenced_file_paths, debug_payload

    return response, referenced_file_paths


async def get_keywords_from_query(
    query: str,
    query_param: QueryParam,
    global_config: dict[str, Any],
    hashing_kv: BaseKVStorage | None = None,
) -> tuple[list[str], list[str]]:
    """
    Retrieves high-level and low-level keywords for RAG operations.

    This function checks if keywords are already provided in query parameters,
    and if not, resolves them with either no-LLM token classification fallback
    or LLM extraction depending on QueryParam.

    Args:
        query: The user's query text
        query_param: Query parameters that may contain pre-defined keywords
        global_config: Global configuration dictionary
        hashing_kv: Optional key-value storage for caching results

    Returns:
        A tuple containing (high_level_keywords, low_level_keywords)
    """
    if getattr(query_param, "keyword_resolution_done", False):
        return query_param.hl_keywords, query_param.ll_keywords

    # Check if pre-defined keywords are already provided
    if query_param.hl_keywords or query_param.ll_keywords:
        keyword_extraction.apply_keyword_resolution(
            query_param,
            keyword_extraction.build_request_keyword_resolution(
                query_param.hl_keywords,
                query_param.ll_keywords,
            ),
        )
        return query_param.hl_keywords, query_param.ll_keywords

    llm_keyword_allowed = _llm_keyword_extraction_allowed(query_param)
    keyword_extraction.prepare_keyword_metadata_for_cache(
        query_param,
        global_config,
        allow_llm_keyword_extraction=llm_keyword_allowed,
    )

    if not llm_keyword_allowed:
        fallback_reason = (
            "explicit keywords missing and LLM keyword extraction disabled; "
            "using no-LLM token classification fallback"
        )
        resolution = await keyword_extraction.extract_keywords_with_gliner(
            query,
            global_config,
            fallback_reason=fallback_reason,
        )
        keyword_extraction.apply_keyword_resolution(query_param, resolution)
        return query_param.hl_keywords, query_param.ll_keywords

    # Extract keywords using extract_keywords_only function which already supports conversation history
    hl_keywords, ll_keywords = await extract_keywords_only(
        query, query_param, global_config, hashing_kv
    )
    keyword_extraction.apply_keyword_resolution(
        query_param,
        keyword_extraction.build_llm_keyword_resolution(hl_keywords, ll_keywords),
    )
    return hl_keywords, ll_keywords


async def extract_keywords_only(
    text: str,
    param: QueryParam,
    global_config: dict[str, Any],
    hashing_kv: BaseKVStorage | None = None,
) -> tuple[list[str], list[str]]:
    """
    Extract high-level and low-level keywords from the given 'text' using the LLM.
    This method does NOT build the final RAG context or provide a final answer.
    It ONLY extracts keywords (hl_keywords, ll_keywords).
    """

    # 1. Handle cache if needed - add cache type for keywords
    args_hash = _build_query_request_fingerprint(
        scope=_QUERY_CACHE_TYPE_KEYWORDS,
        query=text,
        query_param=param,
        global_config=global_config,
        answer_prompt_mode=_resolve_answer_prompt_mode(param, global_config),
    )
    cached_response = None
    if args_hash:
        cached_response, _, _, _ = await handle_cache(
            hashing_kv,
            args_hash,
            text,
            param.mode,
            cache_type=_QUERY_CACHE_TYPE_KEYWORDS,
        )
    if cached_response is not None:
        try:
            if isinstance(cached_response, dict):
                keywords_data = cached_response
            else:
                keywords_data = json.loads(cached_response)
            return _postprocess_extracted_keywords(
                keywords_data["high_level_keywords"],
                keywords_data["low_level_keywords"],
            )
        except (json.JSONDecodeError, KeyError, TypeError):
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

    raw_hl_keywords = keywords_data.get("high_level_keywords", [])
    raw_ll_keywords = keywords_data.get("low_level_keywords", [])
    hl_keywords, ll_keywords = _postprocess_extracted_keywords(
        raw_hl_keywords, raw_ll_keywords
    )
    if raw_hl_keywords != hl_keywords or raw_ll_keywords != ll_keywords:
        logger.debug(
            "Keyword postprocess adjusted extracted keywords. High-level: %s -> %s; Low-level: %s -> %s",
            raw_hl_keywords,
            hl_keywords,
            raw_ll_keywords,
            ll_keywords,
        )

    # 7. Cache only the processed keywords with cache type
    if hl_keywords or ll_keywords:
        cache_data = {
            "high_level_keywords": hl_keywords,
            "low_level_keywords": ll_keywords,
        }
        if _query_cache_enabled(hashing_kv) and args_hash:
            await save_to_cache(
                hashing_kv,
                CacheData(
                    args_hash=args_hash,
                    content=cache_data,
                    prompt=text,
                    mode=param.mode,
                    cache_type=_QUERY_CACHE_TYPE_KEYWORDS,
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
            chunk_id = rr.get("__id__") or rr.get("id")
            if not chunk_id:
                continue
            chunk_weight[chunk_id] = rr.get("__metrics__") or rr.get("distance") or 0.0
            chunk_text[chunk_id] = rr.get("content", "")
            chunk_file_path[chunk_id] = rr.get("file_path", "unknown_source")
            chunk_metadata[chunk_id] = _extract_chunk_citation_fields(rr)
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
    answer_prompt_mode: str = "single_prompt",
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
    llm_entities_context = _sanitize_llm_context_payload(
        entities_context,
        answer_prompt_mode=answer_prompt_mode,
    )
    llm_relations_context = _sanitize_llm_context_payload(
        relations_context,
        answer_prompt_mode=answer_prompt_mode,
    )
    llm_text_units_context = _sanitize_llm_context_payload(
        text_units_context,
        answer_prompt_mode=answer_prompt_mode,
    )
    entities_str = json.dumps(llm_entities_context, ensure_ascii=False)
    relations_str = json.dumps(llm_relations_context, ensure_ascii=False)
    text_units_str = json.dumps(llm_text_units_context, ensure_ascii=False)

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
    query_variants = _build_diversified_retrieval_queries(query)
    # get similar entities
    logger.info(
        "Query nodes: %s, variants: %s, top_k: %s, cosine: %s",
        query,
        query_variants,
        query_param.top_k,
        entities_vdb.cosine_better_than_threshold,
    )

    results = await _query_vector_storage_diversified(
        query,
        entities_vdb,
        top_k=query_param.top_k,
        ids=query_param.ids,
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
            "query_score": _coerce_score(k.get("distance") or k.get("__metrics__")),
            "matched_query_variants": k.get("matched_query_variants", []),
            "query_variant_hit_count": int(
                _coerce_score(k.get("query_variant_hit_count"))
            ),
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

    related_chunk_number = text_chunks_db.global_config.get(
        "related_chunk_number", DEFAULT_RELATED_CHUNK_NUMBER
    )

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

    all_text_units_lookup: dict[str, dict[str, Any]] = {}
    tasks: list[str] = []

    for index, (node_data, this_edges) in enumerate(zip(node_datas, edges)):
        this_text_units = _normalize_source_chunk_ids(
            node_data.get("source_chunk_ids") or node_data.get("source_id")
        )[:related_chunk_number]
        if not this_text_units:
            continue
        seed_query_score = _coerce_score(node_data.get("query_score"))
        for c_id in this_text_units:
            if c_id not in all_text_units_lookup:
                all_text_units_lookup[c_id] = {
                    "order": index,
                    "matched_seed_count": 0,
                    "relation_counts": 0,
                    "max_query_score": 0.0,
                    "matched_query_variants": set(),
                }
                tasks.append(c_id)

            candidate = all_text_units_lookup[c_id]
            candidate["order"] = min(candidate["order"], index)
            candidate["matched_seed_count"] += 1
            candidate["max_query_score"] = max(
                candidate["max_query_score"],
                seed_query_score,
            )
            candidate["matched_query_variants"].update(
                {
                    variant
                    for variant in node_data.get("matched_query_variants", [])
                    if _is_atomic_retrieval_variant(variant)
                }
            )
            if this_edges:
                candidate["relation_counts"] += sum(
                    1
                    for e in this_edges
                    if e[1] in all_one_hop_text_units_lookup
                    and c_id in all_one_hop_text_units_lookup[e[1]]
                )

    # Process in batches tasks at a time to avoid overwhelming resources
    batch_size = 5
    results = []

    for i in range(0, len(tasks), batch_size):
        batch_tasks = tasks[i : i + batch_size]
        batch_results = await asyncio.gather(
            *[text_chunks_db.get_by_id(c_id) for c_id in batch_tasks]
        )
        results.extend(batch_results)

    for c_id, data in zip(tasks, results):
        all_text_units_lookup[c_id]["data"] = data

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
        all_text_units,
        key=lambda x: (
            -x["max_query_score"],
            -x["matched_seed_count"],
            -x["relation_counts"],
            x["order"],
        ),
    )

    logger.debug(f"Found {len(all_text_units)} entity-related chunks")

    # Add source type marking and return chunk data
    result_chunks = []
    for t in all_text_units:
        chunk_data = t["data"].copy()
        chunk_data["chunk_id"] = t["id"]
        chunk_data["source_type"] = "entity"
        chunk_data["graph_query_score"] = t["max_query_score"]
        chunk_data["graph_matched_seed_count"] = t["matched_seed_count"]
        chunk_data["graph_relation_support"] = t["relation_counts"]
        if t.get("matched_query_variants"):
            chunk_data["matched_query_variants"] = sorted(t["matched_query_variants"])
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
    node_query_scores = {
        dp["entity_name"]: _coerce_score(dp.get("query_score")) for dp in node_datas
    }

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
                "query_score": max(
                    node_query_scores.get(pair[0], 0.0),
                    node_query_scores.get(pair[1], 0.0),
                ),
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
    query_variants = _build_diversified_retrieval_queries(keywords)
    logger.info(
        "Query edges: %s, variants: %s, top_k: %s, cosine: %s",
        keywords,
        query_variants,
        query_param.top_k,
        relationships_vdb.cosine_better_than_threshold,
    )

    results = await _query_vector_storage_diversified(
        keywords,
        relationships_vdb,
        top_k=query_param.top_k,
        ids=query_param.ids,
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
                "query_score": _coerce_score(k.get("distance") or k.get("__metrics__")),
                "matched_query_variants": k.get("matched_query_variants", []),
                "query_variant_hit_count": int(
                    _coerce_score(k.get("query_variant_hit_count"))
                ),
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
    entity_query_scores: dict[str, float] = defaultdict(float)
    entity_relation_support: Counter[str] = Counter()

    for e in edge_datas:
        if e["src_id"] not in seen:
            entity_names.append(e["src_id"])
            seen.add(e["src_id"])
        if e["tgt_id"] not in seen:
            entity_names.append(e["tgt_id"])
            seen.add(e["tgt_id"])
        edge_query_score = _coerce_score(e.get("query_score"))
        entity_query_scores[e["src_id"]] = max(
            entity_query_scores[e["src_id"]],
            edge_query_score,
        )
        entity_query_scores[e["tgt_id"]] = max(
            entity_query_scores[e["tgt_id"]],
            edge_query_score,
        )
        entity_relation_support[e["src_id"]] += 1
        entity_relation_support[e["tgt_id"]] += 1

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
        combined = {
            **node,
            "entity_name": entity_name,
            "rank": degree,
            "query_score": entity_query_scores.get(entity_name, 0.0),
            "relation_support": entity_relation_support.get(entity_name, 0),
        }
        node_datas.append(combined)

    return node_datas


async def _find_related_text_unit_from_relationships(
    edge_datas: list[dict],
    query_param: QueryParam,
    text_chunks_db: BaseKVStorage,
):
    logger.debug(f"Searching text chunks for {len(edge_datas)} relationships")

    related_chunk_number = text_chunks_db.global_config.get(
        "related_chunk_number", DEFAULT_RELATED_CHUNK_NUMBER
    )
    all_text_units_lookup: dict[str, dict[str, Any]] = {}
    tasks: list[str] = []
    for index, edge_data in enumerate(edge_datas):
        unit_list = _normalize_source_chunk_ids(
            edge_data.get("source_chunk_ids") or edge_data.get("source_id")
        )[:related_chunk_number]
        if not unit_list:
            continue
        seed_query_score = _coerce_score(edge_data.get("query_score"))
        for c_id in unit_list:
            if c_id not in all_text_units_lookup:
                all_text_units_lookup[c_id] = {
                    "order": index,
                    "matched_seed_count": 0,
                    "relation_counts": 0,
                    "max_query_score": 0.0,
                    "matched_query_variants": set(),
                }
                tasks.append(c_id)
            candidate = all_text_units_lookup[c_id]
            candidate["order"] = min(candidate["order"], index)
            candidate["matched_seed_count"] += 1
            candidate["relation_counts"] += 1
            candidate["max_query_score"] = max(
                candidate["max_query_score"],
                seed_query_score,
            )
            candidate["matched_query_variants"].update(
                {
                    variant
                    for variant in edge_data.get("matched_query_variants", [])
                    if _is_atomic_retrieval_variant(variant)
                }
            )

    if tasks:
        fetched_chunks = await asyncio.gather(
            *[text_chunks_db.get_by_id(c_id) for c_id in tasks]
        )
        for c_id, chunk_data in zip(tasks, fetched_chunks):
            all_text_units_lookup[c_id]["data"] = chunk_data

    if not all_text_units_lookup:
        logger.warning("No valid text chunks found")
        return []

    all_text_units = [{"id": k, **v} for k, v in all_text_units_lookup.items()]
    all_text_units = sorted(
        all_text_units,
        key=lambda x: (
            -x["max_query_score"],
            -x["matched_seed_count"],
            -x["relation_counts"],
            x["order"],
        ),
    )

    # Ensure all text chunks have content
    valid_text_units = [
        t for t in all_text_units if t.get("data") is not None and "content" in t["data"]
    ]

    if not valid_text_units:
        logger.warning("No valid text chunks after filtering")
        return []

    logger.debug(f"Found {len(valid_text_units)} relationship-related chunks")

    # Add source type marking and return chunk data
    result_chunks = []
    for t in valid_text_units:
        chunk_data = t["data"].copy()
        chunk_data["chunk_id"] = t["id"]
        chunk_data["source_type"] = "relationship"
        chunk_data["graph_query_score"] = t["max_query_score"]
        chunk_data["graph_matched_seed_count"] = t["matched_seed_count"]
        chunk_data["graph_relation_support"] = t["relation_counts"]
        if t.get("matched_query_variants"):
            chunk_data["matched_query_variants"] = sorted(t["matched_query_variants"])
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
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    global_config: dict[str, str],
    hashing_kv: BaseKVStorage | None = None,
) -> dict[str, Any]:
    stage_timings: list[dict[str, Any]] = []
    retrieval_total_started_at = time.perf_counter()
    stage_started_at = time.perf_counter()
    with model_usage_stage("vector_retrieval", "混合召回 / Chunk 向量检索"):
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
    with model_usage_stage("keyword_extraction", "关键词提取"):
        hl_keywords, ll_keywords = await get_keywords_from_query(
            query, query_param, global_config, hashing_kv
        )
        if not _llm_keyword_extraction_allowed(query_param):
            hl_keywords, ll_keywords = await _refresh_no_llm_keywords_from_vector_context(
                query_param,
                vector_weights=vector_weights,
                vector_texts=vector_texts,
                vector_file_paths=vector_file_paths,
                vector_metadata_map=vector_metadata_map,
                global_config=global_config,
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
    with model_usage_stage("graph_entity_hits", "图谱命中 / 实体"):
        (
            ll_entities_context,
            ll_relations_context,
            ll_node_datas,
            ll_use_relations,
        ) = await _get_node_data(
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
    with model_usage_stage("graph_relation_hits", "图谱命中 / 关系"):
        (
            hl_entities_context,
            hl_relations_context,
            hl_edge_datas,
            hl_use_entities,
        ) = await _get_edge_data(
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

    graph_weights = {}
    graph_text_map = {}
    graph_file_path_map = {}
    graph_metadata_map = {}

    stage_started_at = time.perf_counter()
    graph_node_seeds = _dedupe_graph_node_seeds([*ll_node_datas, *hl_use_entities])
    graph_edge_seeds = _dedupe_graph_edge_seeds([*ll_use_relations, *hl_edge_datas])

    graph_chunk_candidates: list[dict[str, Any]] = []
    text_chunk_tasks = []
    if graph_node_seeds:
        text_chunk_tasks.append(
            _find_most_related_text_unit_from_entities(
                graph_node_seeds,
                query_param,
                text_chunks_db,
                knowledge_graph_inst,
            )
        )
    if graph_edge_seeds:
        text_chunk_tasks.append(
            _find_related_text_unit_from_relationships(
                graph_edge_seeds,
                query_param,
                text_chunks_db,
            )
        )
    if text_chunk_tasks:
        text_chunk_results = await asyncio.gather(*text_chunk_tasks)
        for chunks in text_chunk_results:
            if chunks:
                graph_chunk_candidates.extend(chunks)

    for chunk in graph_chunk_candidates:
        chunk_id = str(chunk.get("chunk_id") or "").strip()
        if not chunk_id:
            continue
        graph_text_map[chunk_id] = chunk.get("content", "")
        graph_file_path_map[chunk_id] = chunk.get("file_path", "unknown_source")
        graph_weights[chunk_id] = graph_weights.get(chunk_id, 0.0) + _compute_graph_chunk_support_score(
            chunk
        )

        metadata = graph_metadata_map.setdefault(chunk_id, {})
        for key, value in _extract_chunk_citation_fields(chunk).items():
            if value not in (None, "", [], {}):
                metadata[key] = value
        metadata.setdefault("matched_query_variants", [])
        merged_variants = {
            variant
            for variant in metadata.get("matched_query_variants", [])
            if _is_atomic_retrieval_variant(variant)
        }
        merged_variants.update(
            {
                variant
                for variant in chunk.get("matched_query_variants", [])
                if _is_atomic_retrieval_variant(variant)
            }
        )
        if merged_variants:
            metadata["matched_query_variants"] = sorted(merged_variants)
        metadata["graph_query_score"] = max(
            _coerce_score(metadata.get("graph_query_score")),
            _coerce_score(chunk.get("graph_query_score")),
        )
        metadata["graph_matched_seed_count"] = (
            int(_coerce_score(metadata.get("graph_matched_seed_count")))
            + int(_coerce_score(chunk.get("graph_matched_seed_count")))
        )
        metadata["graph_relation_support"] = (
            int(_coerce_score(metadata.get("graph_relation_support")))
            + int(_coerce_score(chunk.get("graph_relation_support")))
        )
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
    referenced_file_paths = []
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
        referenced_file_paths.append(file_path)
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
    rerank_used = False
    rerank_skip_reason = None
    rerank_model = os.getenv("RERANK_MODEL")
    stage_started_at = time.perf_counter()
    with model_usage_stage("rerank", "Rerank 重排"):
        if results_text and query_param.enable_rerank:
            if _has_complete_rerank_env_config():
                try:
                    rerank_results = await rerank_from_env(
                        query=query,
                        documents=results_text,
                        top_k=len(results_text),
                    )
                    rerank_used = bool(rerank_results)
                    if not rerank_results:
                        rerank_skip_reason = "rerank returned no candidates"
                        rerank_results = [
                            {"index": index} for index in range(len(results_text))
                        ]
                except Exception as exc:
                    rerank_skip_reason = f"rerank failed: {exc}"
                    logger.warning(
                        "Rerank failed, fallback to merged candidate order: %s",
                        exc,
                    )
                    rerank_results = [
                        {"index": index} for index in range(len(results_text))
                    ]
            else:
                rerank_skip_reason = (
                    "missing required RERANK_* config: "
                    + ", ".join(_missing_rerank_env_names())
                )
                logger.warning(
                    "Rerank skipped, fallback to merged candidate order: %s",
                    rerank_skip_reason,
                )
                rerank_results = [{"index": index} for index in range(len(results_text))]
        elif results_text:
            rerank_skip_reason = "enable_rerank=false"
            rerank_results = [{"index": index} for index in range(len(results_text))]
    _record_stage_timing(
        stage_timings,
        "rerank",
        "Rerank 重排",
        stage_started_at,
    )

    selected_candidate_indexes: list[int] = []
    text_units_context = []
    stage_started_at = time.perf_counter()
    selected_candidate_indexes, text_units_context = _select_hybrid_context_entries(
        rerank_results=rerank_results,
        results_text=results_text,
        results_file_paths=results_file_paths,
        results_chunk_metadata=results_chunk_metadata,
        query_param=query_param,
        query_variants=_dedupe_keywords([*ll_keywords, *hl_keywords]),
    )
    _record_stage_timing(
        stage_timings,
        "final_context_selection",
        "最终证据选择",
        stage_started_at,
    )

    referenced_file_paths = _normalize_referenced_file_paths(referenced_file_paths)
    _record_stage_timing(
        stage_timings,
        "hybrid_retrieval_total",
        "混合检索总耗时",
        retrieval_total_started_at,
    )

    return {
        "high_level_keywords": hl_keywords,
        "low_level_keywords": ll_keywords,
        **keyword_extraction.keyword_metadata_from_query_param(query_param),
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
        "rerank_used": rerank_used,
        "rerank_model": rerank_model,
        "rerank_skip_reason": rerank_skip_reason,
        "rerank_results": rerank_results,
        "selected_candidate_indexes": selected_candidate_indexes,
        "results_text": results_text,
        "results_file_paths": results_file_paths,
        "results_chunk_ids": results_chunk_ids,
        "results_sources": results_sources,
        "results_source_labels": results_source_labels,
        "results_chunk_metadata": results_chunk_metadata,
        "text_units_context": text_units_context,
        "referenced_file_paths": referenced_file_paths,
        "stage_timings": stage_timings,
    }


def _build_hybrid_context_cache_payload(
    retrieval_debug: dict[str, Any],
    *,
    answer_prompt_mode: str,
    corpus_revision: int,
) -> dict[str, Any]:
    llm_text_units_context = _sanitize_llm_context_payload(
        retrieval_debug.get("text_units_context", []),
        answer_prompt_mode=answer_prompt_mode,
    )
    text_units_str = json.dumps(llm_text_units_context, ensure_ascii=False)
    context_text = f"""
---Document Chunks---

```json
{text_units_str}
```

"""
    return _build_query_cache_payload(
        result_kind=_QUERY_RESULT_KIND_CONTEXT,
        context_text=context_text,
        referenced_file_paths=retrieval_debug.get("referenced_file_paths") or [],
        final_context_document_chunks=llm_text_units_context,
        debug_payload_cacheable=_strip_stage_timings(retrieval_debug),
        context_available=True,
        corpus_revision=corpus_revision,
    )


def _build_hybrid_prompt_cache_payload(
    context_payload: dict[str, Any],
    *,
    query_param: QueryParam,
    system_prompt: str | None,
    answer_prompt_mode: str,
    corpus_revision: int,
) -> dict[str, Any]:
    history_context = ""
    if query_param.conversation_history:
        history_context = get_conversation_turns(
            query_param.conversation_history, query_param.history_turns
        )

    user_prompt = (
        query_param.user_prompt
        if query_param.user_prompt
        else PROMPTS["DEFAULT_USER_PROMPT"]
    )
    default_prompt_key = (
        "naive_rag_response_single_prompt"
        if answer_prompt_mode == "single_prompt"
        else "naive_rag_response"
    )
    prompt_template = system_prompt if system_prompt else PROMPTS[default_prompt_key]
    content_data = json.dumps(
        context_payload.get("final_context_document_chunks") or [],
        ensure_ascii=False,
    )
    prompt_text = prompt_template.format(
        content_data=content_data,
        response_type=query_param.response_type,
        history=history_context,
        user_prompt=user_prompt,
    )
    return _build_query_cache_payload(
        result_kind=_QUERY_RESULT_KIND_PROMPT,
        context_text=context_payload.get("context_text", ""),
        prompt_text=prompt_text,
        referenced_file_paths=context_payload.get("referenced_file_paths") or [],
        final_context_document_chunks=context_payload.get(
            "final_context_document_chunks"
        )
        or [],
        debug_payload_cacheable=context_payload.get("debug_payload_cacheable") or {},
        context_available=True,
        corpus_revision=corpus_revision,
    )

async def hybrid_query(
    query: str,
    chunks_vdb: BaseVectorStorage,
    knowledge_graph_inst: BaseGraphStorage,
    relationships_vdb: BaseVectorStorage,
    entities_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage,
    query_param: QueryParam,
    global_config: dict[str, str],
    hashing_kv: BaseKVStorage | None = None,
    system_prompt: str | None = None,
    return_debug: bool = False,
):
    _validate_query_request_flags(query_param)
    stage_timings: list[dict[str, Any]] = []
    query_total_started_at = time.perf_counter()
    await _resolve_no_llm_keywords_for_retrieval_cache(
        query,
        query_param,
        global_config,
        hashing_kv,
    )
    answer_prompt_mode = _resolve_answer_prompt_mode(query_param, global_config)
    corpus_revision = _coerce_non_negative_int(
        global_config.get("corpus_revision"),
        0,
    )
    tokenizer: Tokenizer = global_config["tokenizer"]
    answer_cache_key = _build_query_request_fingerprint(
        scope=_QUERY_CACHE_TYPE_ANSWER,
        query=query,
        query_param=query_param,
        global_config=global_config,
        answer_prompt_mode=answer_prompt_mode,
        system_prompt=system_prompt,
    )

    if not query_param.only_need_context and not query_param.only_need_prompt:
        answer_cache_payload = await _load_query_cache_payload(
            hashing_kv,
            args_hash=answer_cache_key,
            mode=query_param.mode,
            cache_type=_QUERY_CACHE_TYPE_ANSWER,
            expected_result_kind=_QUERY_RESULT_KIND_ANSWER,
            stage_timings=stage_timings,
            lookup_stage="query_cache_lookup",
            lookup_label="最终答案缓存检查",
            hit_stage="answer_cache_hit",
            hit_label="最终答案缓存命中",
        )
        if answer_cache_payload is not None:
            referenced_file_paths = answer_cache_payload["referenced_file_paths"]
            response = answer_cache_payload["answer"]
            _record_stage_timing(
                stage_timings,
                "onehop_total",
                "OneHop 查询总耗时",
                query_total_started_at,
            )
            if return_debug:
                debug_payload = _hydrate_debug_payload(
                    cacheable_debug_payload=answer_cache_payload[
                        "debug_payload_cacheable"
                    ],
                    context_text=answer_cache_payload["context_text"],
                    prompt_text=answer_cache_payload["prompt_text"],
                    final_context_document_chunks=answer_cache_payload[
                        "final_context_document_chunks"
                    ],
                    stage_timings=stage_timings,
                )
                return response, referenced_file_paths, debug_payload
            return response, referenced_file_paths

    retrieval_cache_key = _build_query_request_fingerprint(
        scope=_QUERY_CACHE_TYPE_RETRIEVAL,
        query=query,
        query_param=query_param,
        global_config=global_config,
        answer_prompt_mode=answer_prompt_mode,
    )
    async def _compute_hybrid_retrieval_payload() -> dict[str, Any]:
        retrieval_debug = await _build_hybrid_retrieval_debug_data(
            query=query,
            chunks_vdb=chunks_vdb,
            knowledge_graph_inst=knowledge_graph_inst,
            relationships_vdb=relationships_vdb,
            entities_vdb=entities_vdb,
            text_chunks_db=text_chunks_db,
            query_param=query_param,
            global_config=global_config,
            hashing_kv=hashing_kv,
        )
        stage_timings.extend(retrieval_debug.get("stage_timings", []))
        return _build_query_cache_payload(
            result_kind=_QUERY_RESULT_KIND_RETRIEVAL,
            referenced_file_paths=retrieval_debug.get("referenced_file_paths")
            or [],
            debug_payload_cacheable=_strip_stage_timings(retrieval_debug),
            corpus_revision=corpus_revision,
        )

    retrieval_cache_payload = await _get_or_compute_query_cache_payload(
        hashing_kv,
        args_hash=retrieval_cache_key,
        mode=query_param.mode,
        cache_type=_QUERY_CACHE_TYPE_RETRIEVAL,
        expected_result_kind=_QUERY_RESULT_KIND_RETRIEVAL,
        prompt=query,
        compute_payload=_compute_hybrid_retrieval_payload,
        stage_timings=stage_timings,
        lookup_stage="retrieval_cache_lookup",
        lookup_label="检索缓存检查",
        hit_stage="retrieval_cache_hit",
        hit_label="检索缓存命中",
    )
    retrieval_debug = dict(retrieval_cache_payload["debug_payload_cacheable"])

    context_cache_key = _build_query_request_fingerprint(
        scope=_QUERY_CACHE_TYPE_RENDER,
        query=query,
        query_param=query_param,
        global_config=global_config,
        answer_prompt_mode=answer_prompt_mode,
        render_kind=_QUERY_RESULT_KIND_CONTEXT,
    )
    context_payload = await _load_query_cache_payload(
        hashing_kv,
        args_hash=context_cache_key,
        mode=query_param.mode,
        cache_type=_QUERY_CACHE_TYPE_RENDER,
        expected_result_kind=_QUERY_RESULT_KIND_CONTEXT,
        stage_timings=stage_timings,
        lookup_stage="render_cache_lookup",
        lookup_label="上下文渲染缓存检查",
        hit_stage="render_cache_hit",
        hit_label="上下文渲染缓存命中",
    )
    if context_payload is None:
        context_payload = _build_hybrid_context_cache_payload(
            retrieval_debug,
            answer_prompt_mode=answer_prompt_mode,
            corpus_revision=corpus_revision,
        )
        await _save_query_cache_payload(
            hashing_kv,
            args_hash=context_cache_key,
            mode=query_param.mode,
            cache_type=_QUERY_CACHE_TYPE_RENDER,
            prompt=query,
            payload=context_payload,
        )

    referenced_file_paths = context_payload["referenced_file_paths"]
    if query_param.only_need_context:
        context_text = context_payload["context_text"]
        if return_debug:
            _record_stage_timing(
                stage_timings,
                "onehop_total",
                "OneHop 查询总耗时",
                query_total_started_at,
            )
            debug_payload = _hydrate_debug_payload(
                cacheable_debug_payload=context_payload["debug_payload_cacheable"],
                context_text=context_text,
                prompt_text="",
                final_context_document_chunks=context_payload[
                    "final_context_document_chunks"
                ],
                stage_timings=stage_timings,
            )
            return context_text, referenced_file_paths, debug_payload
        return context_text

    prompt_cache_key = _build_query_request_fingerprint(
        scope=_QUERY_CACHE_TYPE_RENDER,
        query=query,
        query_param=query_param,
        global_config=global_config,
        answer_prompt_mode=answer_prompt_mode,
        system_prompt=system_prompt,
        render_kind=_QUERY_RESULT_KIND_PROMPT,
    )
    prompt_payload = await _load_query_cache_payload(
        hashing_kv,
        args_hash=prompt_cache_key,
        mode=query_param.mode,
        cache_type=_QUERY_CACHE_TYPE_RENDER,
        expected_result_kind=_QUERY_RESULT_KIND_PROMPT,
        stage_timings=stage_timings,
        lookup_stage="prompt_cache_lookup",
        lookup_label="Prompt 渲染缓存检查",
        hit_stage="prompt_cache_hit",
        hit_label="Prompt 渲染缓存命中",
    )
    if prompt_payload is None:
        prompt_payload = _build_hybrid_prompt_cache_payload(
            context_payload,
            query_param=query_param,
            system_prompt=system_prompt,
            answer_prompt_mode=answer_prompt_mode,
            corpus_revision=corpus_revision,
        )
        _append_stage_timing(
            stage_timings,
            "prompt_assembly",
            "回答提示词拼装",
            0.0,
        )
        await _save_query_cache_payload(
            hashing_kv,
            args_hash=prompt_cache_key,
            mode=query_param.mode,
            cache_type=_QUERY_CACHE_TYPE_RENDER,
            prompt=query,
            payload=prompt_payload,
        )

    if query_param.only_need_prompt:
        prompt_text = prompt_payload["prompt_text"]
        if return_debug:
            _record_stage_timing(
                stage_timings,
                "onehop_total",
                "OneHop 查询总耗时",
                query_total_started_at,
            )
            debug_payload = _hydrate_debug_payload(
                cacheable_debug_payload=prompt_payload["debug_payload_cacheable"],
                context_text=context_payload["context_text"],
                prompt_text=prompt_text,
                final_context_document_chunks=context_payload[
                    "final_context_document_chunks"
                ],
                stage_timings=stage_timings,
            )
            return prompt_text, referenced_file_paths, debug_payload
        return prompt_text

    use_model_func = _resolve_query_llm_func(query_param, global_config)
    prompt_text = prompt_payload["prompt_text"]
    len_of_prompts = len(tokenizer.encode(query + prompt_text))
    logger.debug(
        f"[naive_query] Sending to LLM: {len_of_prompts:,} tokens (Query: {len(tokenizer.encode(query))}, System: {len(tokenizer.encode(prompt_text))})"
    )

    answer_cache_payload = None
    if return_debug:
        answer_cache_payload = await _load_query_cache_payload(
            hashing_kv,
            args_hash=answer_cache_key,
            mode=query_param.mode,
            cache_type=_QUERY_CACHE_TYPE_ANSWER,
            expected_result_kind=_QUERY_RESULT_KIND_ANSWER,
            stage_timings=stage_timings,
            lookup_stage="answer_cache_lookup",
            lookup_label="最终答案缓存检查",
            hit_stage="answer_cache_hit",
            hit_label="最终答案缓存命中",
        )

    if answer_cache_payload is None:
        async def _compute_hybrid_answer_payload() -> dict[str, Any]:
            stage_started_at = time.perf_counter()
            with model_usage_stage(
                "answer_generation",
                "回答生成 / 单轮 LLM"
                if answer_prompt_mode == "single_prompt"
                else "回答生成 / 第一轮 LLM",
            ):
                response = await use_model_func(
                    query,
                    system_prompt=prompt_text,
                    stream=query_param.stream,
                )
            _record_stage_timing(
                stage_timings,
                "answer_generation",
                "回答生成 / 单轮 LLM"
                if answer_prompt_mode == "single_prompt"
                else "回答生成 / 第一轮 LLM",
                stage_started_at,
            )

            if isinstance(response, str) and len(response) > len(prompt_text):
                response = (
                    response[len(prompt_text) :]
                    .replace(prompt_text, "")
                    .replace("user", "")
                    .replace("model", "")
                    .replace(query, "")
                    .replace("<system>", "")
                    .replace("</system>", "")
                    .strip()
                )
            if answer_prompt_mode == "two_stage":
                stage_started_at = time.perf_counter()
                with model_usage_stage("answer_polish", "回答润色 / 第二轮 LLM"):
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
            return _build_query_cache_payload(
                result_kind=_QUERY_RESULT_KIND_ANSWER,
                answer=response if isinstance(response, str) else "",
                context_text=context_payload["context_text"],
                prompt_text=prompt_text,
                referenced_file_paths=referenced_file_paths,
                final_context_document_chunks=context_payload[
                    "final_context_document_chunks"
                ],
                debug_payload_cacheable=prompt_payload["debug_payload_cacheable"],
                corpus_revision=corpus_revision,
            )

        answer_cache_payload = await _get_or_compute_query_cache_payload(
            hashing_kv,
            args_hash=answer_cache_key,
            mode=query_param.mode,
            cache_type=_QUERY_CACHE_TYPE_ANSWER,
            expected_result_kind=_QUERY_RESULT_KIND_ANSWER,
            prompt=query,
            compute_payload=_compute_hybrid_answer_payload,
            stage_timings=stage_timings,
            lookup_stage="answer_cache_lookup",
            lookup_label="最终答案缓存检查",
            hit_stage="answer_cache_hit",
            hit_label="最终答案缓存命中",
            skip_initial_lookup=answer_cache_payload is None,
        )
    response = answer_cache_payload["answer"]

    _record_stage_timing(
        stage_timings,
        "onehop_total",
        "OneHop 查询总耗时",
        query_total_started_at,
    )

    if return_debug:
        debug_payload = _hydrate_debug_payload(
            cacheable_debug_payload=prompt_payload["debug_payload_cacheable"],
            context_text=context_payload["context_text"],
            prompt_text=prompt_text,
            final_context_document_chunks=context_payload[
                "final_context_document_chunks"
            ],
            stage_timings=stage_timings,
        )
        return response, referenced_file_paths, debug_payload

    return response, referenced_file_paths


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
    _validate_query_request_flags(query_param)
    if query_param.model_func:
        use_model_func = query_param.model_func
    else:
        use_model_func = global_config["llm_model_func"]
        # Apply higher priority (5) to query relation LLM function
        use_model_func = partial(use_model_func, _priority=5)
    answer_prompt_mode = _resolve_answer_prompt_mode(query_param, global_config)
    corpus_revision = _coerce_non_negative_int(
        global_config.get("corpus_revision"),
        0,
    )

    answer_fingerprint_payload = _build_query_request_fingerprint_payload(
        scope=_QUERY_CACHE_TYPE_ANSWER,
        query=query,
        query_param=query_param,
        global_config=global_config,
        answer_prompt_mode=answer_prompt_mode,
    )
    args_hash = (
        compute_structured_hash(
            {
                "schema_version": _QUERY_CACHE_SCHEMA_VERSION,
                "scope": "answer_with_keywords",
                "base": answer_fingerprint_payload,
                "hl_keywords": list(hl_keywords or []),
                "ll_keywords": list(ll_keywords or []),
            },
            strict=True,
        )
        if answer_fingerprint_payload is not None
        and not query_param.only_need_context
        and not query_param.only_need_prompt
        else None
    )
    cached_answer = await _load_query_cache_payload(
        hashing_kv,
        args_hash=args_hash,
        mode=query_param.mode,
        cache_type=_QUERY_CACHE_TYPE_ANSWER,
        expected_result_kind=_QUERY_RESULT_KIND_ANSWER,
    )
    if cached_answer is not None:
        return cached_answer["answer"]

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
        answer_prompt_mode=answer_prompt_mode,
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

    user_prompt = (
        query_param.user_prompt
        if query_param.user_prompt
        else PROMPTS["DEFAULT_USER_PROMPT"]
    )
    default_prompt_key = (
        "rag_response_single_prompt"
        if answer_prompt_mode == "single_prompt"
        else "rag_response"
    )
    sys_prompt_temp = PROMPTS[default_prompt_key]
    sys_prompt = sys_prompt_temp.format(
        context_data=context,
        response_type=query_param.response_type,
        history=history_context,
        user_prompt=user_prompt,
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

    if answer_prompt_mode == "two_stage":
        response = await use_model_func(
            response,
            system_prompt=PROMPTS["rag_response_new"],
            stream=query_param.stream,
        )

    if isinstance(response, str):
        await _save_query_cache_payload(
            hashing_kv,
            args_hash=args_hash,
            mode=query_param.mode,
            cache_type=_QUERY_CACHE_TYPE_ANSWER,
            prompt=query,
            payload=_build_query_cache_payload(
                result_kind=_QUERY_RESULT_KIND_ANSWER,
                answer=response,
                context_text=context,
                prompt_text=sys_prompt,
                corpus_revision=corpus_revision,
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
