import os
import asyncio
import logging
from dataclasses import asdict
from dotenv import load_dotenv
from pathlib import Path
# use the .env that is inside the current folder
# allows to use different .env file for each ragent instance
# the OS environment variables take precedence over the .env file
_ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=_ENV_PATH, override=True) #$HOME替换为本地ragent存储的绝对路径
import subprocess
from ragent import Ragent, QueryParam
from ragent.llm.openai import env_openai_complete, openai_embed
from ragent.rerank import rerank_from_env
from ragent.kg.shared_storage import initialize_pipeline_status
from ragent.utils import log_model_call, logger
from ragent.operate import (
    graph_query,
    hybrid_query,
)
import json
from ragent.prompt import dismantle_prompt
import requests
import base64
import copy
import re
import mimetypes
import time
import aiofiles
from typing import Any

from mineru.cli.common import convert_pdf_bytes_to_bytes_by_pypdfium2, prepare_env, read_fn


def _prepare_env_flat(output_dir, parse_method):
    """单文件模式：直接输出到 output_dir/parse_method，无中间层。"""
    local_md_dir = str(os.path.join(output_dir, parse_method))
    local_image_dir = os.path.join(local_md_dir, "images")
    os.makedirs(local_image_dir, exist_ok=True)
    os.makedirs(local_md_dir, exist_ok=True)
    return local_image_dir, local_md_dir
from mineru.data.data_reader_writer import FileBasedDataWriter
from mineru.utils.draw_bbox import draw_layout_bbox, draw_span_bbox
from mineru.utils.enum_class import MakeMode
from mineru.backend.vlm.vlm_analyze import doc_analyze as vlm_doc_analyze
from mineru.backend.pipeline.pipeline_analyze import doc_analyze as pipeline_doc_analyze
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make
from mineru.backend.pipeline.model_json_to_middle_json import result_to_middle_json as pipeline_result_to_middle_json
from mineru.backend.vlm.vlm_middle_json_mkcontent import union_make as vlm_union_make

_MODEL_HEALTHCHECK_DONE = False
_MODEL_HEALTHCHECK_LOCK = asyncio.Lock()
_INFO_PIPELINE_STAGE_PREFIXES = ("image_mm_", "md_injection_")
_INFO_PIPELINE_STAGE_NAMES = {"build_enhanced_md_start"}


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
    limit: int = 5,
    source: str | None = None,
):
    ranked = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:limit]
    results = []
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
        results.append(result)
    return results


def _collect_entity_hits(entities: list[dict], limit: int = 5):
    results = []
    for item in entities[:limit]:
        results.append(
            {
                "entity": item.get("entity", "UNKNOWN"),
                "type": item.get("type", "UNKNOWN"),
                "file_path": item.get("file_path", "unknown_source"),
                "preview": _preview_text(item.get("description", "")),
            }
        )
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


def _collect_relation_hits(relations: list[dict], limit: int = 5):
    results = []
    for item in relations[:limit]:
        results.append(
            {
                "entity1": item.get("entity1", "UNKNOWN"),
                "entity2": item.get("entity2", "UNKNOWN"),
                "file_path": item.get("file_path", "unknown_source"),
                "preview": _preview_text(item.get("description", "")),
            }
        )
    return results


def _collect_final_context_chunks(
    rerank_results: list[dict[str, Any]],
    results_text: list[str],
    results_file_paths: list[str],
    results_chunk_ids: list[str],
    results_source_labels: list[str],
    limit: int | None = None,
):
    final_chunks = []
    top_k = len(rerank_results) if limit is None else min(len(rerank_results), limit)
    for index in range(top_k):
        rerank_index = rerank_results[index].get("index")
        if not isinstance(rerank_index, int) or not (0 <= rerank_index < len(results_text)):
            continue
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
    return final_chunks


def _collect_rerank_results(
    rerank_results: list[dict[str, Any]],
    results_text: list[str],
    results_file_paths: list[str],
    results_chunk_ids: list[str],
    results_source_labels: list[str],
    limit: int | None = None,
):
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
    return ranked


def _build_one_hop_trace(
    query: str,
    mode: str,
    answer: str,
    image_list: list[str],
    debug_payload: dict[str, Any],
) -> dict[str, Any]:
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
        "answer": answer,
        "image_list": sorted([item for item in set(image_list) if item != "unknown_source"]),
    }

    if mode == "hybrid":
        trace["vector_candidates"] = _collect_ranked_chunks(
            debug_payload["vector_weights"],
            debug_payload["vector_texts"],
            debug_payload["vector_file_paths"],
            source="vector",
        )
        trace["graph_entity_hits"] = _collect_entity_hits(debug_payload["graph_entities"])
        trace["graph_relation_hits"] = _collect_relation_hits(debug_payload["graph_relations"])
        trace["graph_chunk_candidates"] = _collect_ranked_chunks(
            debug_payload["graph_weights"],
            debug_payload["graph_texts"],
            debug_payload["graph_file_paths"],
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
        )
        trace["rerank_input_candidates"] = list(trace["merged_candidates"])
        trace["final_context_chunks"] = _collect_final_context_chunks(
            debug_payload["rerank_results"],
            debug_payload["results_text"],
            debug_payload["results_file_paths"],
            debug_payload["results_chunk_ids"],
            debug_payload["results_source_labels"],
            limit=len(debug_payload["final_context_document_chunks"]),
        )
        trace["final_context_document_chunks"] = debug_payload["final_context_document_chunks"]
    else:
        trace["graph_entity_hits"] = _collect_entity_hits(debug_payload.get("graph_entities", []))
        trace["graph_relation_hits"] = _collect_relation_hits(debug_payload.get("graph_relations", []))
        trace["final_context_document_chunks"] = _extract_document_chunks_from_context(
            debug_payload.get("final_context_text", "") or ""
        )

    return trace


async def _run_one_hop_with_rag(
    rag: Ragent,
    query: str,
    mode: str,
    include_trace: bool = False,
):
    query_param = QueryParam(mode=mode)
    global_config = asdict(rag)
    normalized_query = query.strip()

    if mode == "hybrid":
        if include_trace:
            answer, image_list, debug_payload = await hybrid_query(
                normalized_query,
                rag.chunks_vdb,
                rag.chunk_entity_relation_graph,
                rag.relationships_vdb,
                rag.entities_vdb,
                query_param,
                global_config,
                rag.llm_response_cache,
                return_debug=True,
            )
            await rag._query_done()
            return {
                "answer": answer,
                "image_list": sorted([item for item in set(image_list) if item != "unknown_source"]),
                "trace": _build_one_hop_trace(
                    normalized_query, mode, answer, image_list, debug_payload
                ),
            }
        answer, image_list = await hybrid_query(
            normalized_query,
            rag.chunks_vdb,
            rag.chunk_entity_relation_graph,
            rag.relationships_vdb,
            rag.entities_vdb,
            query_param,
            global_config,
            rag.llm_response_cache,
        )
    else:
        if include_trace:
            answer, image_list, debug_payload = await graph_query(
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
            await rag._query_done()
            return {
                "answer": answer,
                "image_list": sorted([item for item in set(image_list) if item != "unknown_source"]),
                "trace": _build_one_hop_trace(
                    normalized_query, mode, answer, image_list, debug_payload
                ),
            }
        answer, image_list = await graph_query(
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

    return {
        "answer": answer,
        "image_list": sorted([item for item in set(image_list) if item != "unknown_source"]),
        "trace": None,
    }


async def trace_one_hop_problem(work_dir, query, mode="hybrid"):
    rag = await initialize_rag(work_dir)
    result = await _run_one_hop_with_rag(rag, query, mode, include_trace=True)
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
):
    res_dismantle = await rag.llm_model_func(prompt=query, system_prompt=dismantle_prompt)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"问题拆解结果：{res_dismantle}")
    res_dismantle_json = _parse_dismantle_result(res_dismantle)

    memory_new = {"多跳问题分解结果": res_dismantle_json}
    steps = []
    count = 0
    final_answer = ""
    images_list = []

    for index, sub_question in enumerate(res_dismantle_json["sub_questions"]):
        if count == 2:
            prompt_summary = (
                "请对历史信息中存储的知识内容进行总结，要求字数少于1000字，并保留sub_questions列表中的问题信息，以下是历史信息\n"
                + str(memory_new)
            )
            summary_result = await _run_one_hop_with_rag(
                rag, prompt_summary, mode="hybrid", include_trace=include_trace
            )
            memory_new = {"历史信息总结": summary_result["answer"]}
            count = 0
            images_list.extend(summary_result["image_list"])
            if include_trace:
                steps.append(
                    {
                        "stage_type": "history_summary",
                        "display_question": "历史信息总结",
                        "internal_query": prompt_summary,
                        "memory_snapshot": _preview_text(
                            json.dumps(memory_new, ensure_ascii=False), limit=240
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
            internal_query = "当前回答的问题是" + sub_question + "该问题历史记录为" + str(memory_new)
            stage_type = "sub_question"

        step_result = await _run_one_hop_with_rag(
            rag, internal_query, mode="hybrid", include_trace=include_trace
        )
        memory_new[sub_question] = step_result["answer"]
        count += 1
        final_answer = step_result["answer"]
        images_list.extend(step_result["image_list"])
        if include_trace:
            steps.append(
                {
                    "stage_type": stage_type,
                    "display_question": sub_question,
                    "internal_query": internal_query,
                    "memory_snapshot": _preview_text(
                        json.dumps(memory_new, ensure_ascii=False), limit=240
                    ),
                    "trace": step_result["trace"],
                }
            )

    result = {
        "query": query,
        "decomposition": res_dismantle_json,
        "answer": final_answer,
        "image_list": sorted([item for item in set(images_list) if item != "unknown_source"]),
    }
    if include_trace:
        result["steps"] = steps
    return result


async def trace_multi_hop_problem(work_dir, query):
    rag = await initialize_rag(work_dir)
    return await _run_multi_hop_with_rag(rag, query, include_trace=True)


def _shorten_for_log(value: Any, limit: int = 600) -> str:
    text = repr(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


def _print_healthcheck(title: str, payload: Any) -> None:
    msg = f"[StartupModelCheck] {title}: {_shorten_for_log(payload)}"
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(msg)


def _print_pipeline_progress(stage: str, **payload: Any) -> None:
    details = ", ".join(f"{k}={_shorten_for_log(v, 240)}" for k, v in payload.items())
    msg = f"[PipelineProgress] stage={stage}" + (f", {details}" if details else "")
    if stage in _INFO_PIPELINE_STAGE_NAMES or stage.startswith(_INFO_PIPELINE_STAGE_PREFIXES):
        logger.info(msg)
    elif logger.isEnabledFor(logging.DEBUG):
        logger.debug(msg)


def _print_md_ready_banner(pdf_file_path: str, md_path: str, image_dir: str, pdf_outdir: str) -> None:
    """在前端输出高可见度提示：PDF 解析完成且已生成最终 md。"""
    abs_pdf = os.path.abspath(pdf_file_path)
    abs_md = os.path.abspath(md_path)
    abs_image_dir = os.path.abspath(image_dir)
    abs_outdir = os.path.abspath(pdf_outdir)
    banner_lines = [
        "============================================================",
        "[PDF->MD READY] PDF parse completed. Final markdown generated.",
        f"source_pdf_abs: {abs_pdf}",
        f"md_file_abs: {abs_md}",
        f"image_dir_abs: {abs_image_dir}",
        f"parse_output_dir_abs: {abs_outdir}",
        "============================================================",
    ]
    banner = "\n".join(banner_lines)
    logger.info(banner)


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
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 128,
    }
    log_model_call(
        "integrations._image_text_ping_sync",
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
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


async def verify_env_models_before_startup() -> None:
    timeout_sec = int(os.getenv("MODEL_STARTUP_CHECK_TIMEOUT_SECONDS", "30"))
    llm_example = {
        "model_env": "LLM_API_MODEL",
        "prompt": "这是启动前连通性检查。请只回复: LLM_OK",
        "system_prompt": "你是模型连通性检查器。",
    }
    embed_example = {
        "model_env": "EMBEDDING_MODEL",
        "texts": ["启动前 embedding 连通性检查样例文本。"],
    }
    rerank_example = {
        "model_env": "RERANK_MODEL",
        "query": "启动前 rerank 检查 query",
        "documents": ["文档A：苹果是一种水果。", "文档B：火星是太阳系行星。"],
        "top_k": 2,
    }

    _print_healthcheck("LLM 请求示例", llm_example)
    llm_result = await asyncio.wait_for(
        env_openai_complete(
            prompt=llm_example["prompt"],
            system_prompt=llm_example["system_prompt"],
            max_tokens=64,
            temperature=0,
        ),
        timeout=timeout_sec,
    )
    _print_healthcheck("LLM 真实返回", llm_result)

    _print_healthcheck("Embedding 请求示例", embed_example)
    embed_result = await asyncio.wait_for(
        openai_embed(embed_example["texts"]),
        timeout=timeout_sec,
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
        timeout=timeout_sec,
    )
    _print_healthcheck("Rerank 真实返回", rerank_result)

    image_key = os.getenv("IMAGE_MODEL_KEY")
    image_model = os.getenv("IMAGE_MODEL")
    image_url = os.getenv("IMAGE_MODEL_URL")
    if image_key and image_model and image_url:
        image_example = {
            "model_env": "IMAGE_MODEL",
            "prompt": "这是启动前图像模型文本连通性检查。请只回复: IMAGE_OK",
        }
        _print_healthcheck("Image 请求示例", image_example)
        image_result = await asyncio.wait_for(
            asyncio.to_thread(_image_text_ping_sync, image_example["prompt"]),
            timeout=timeout_sec,
        )
        _print_healthcheck("Image 真实返回", image_result)
    else:
        _print_healthcheck(
            "Image 检查跳过",
            "未配置完整 IMAGE_MODEL_KEY/IMAGE_MODEL/IMAGE_MODEL_URL，已跳过",
        )

    _print_healthcheck(
        "全部模型检查结果",
        f"通过，单项超时阈值={timeout_sec}s",
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
            _print_healthcheck("启动前模型检查失败", err_msg)
            raise RuntimeError(f"Startup model check failed: {err_msg}") from e


async def initialize_rag(WORKING_DIR):
    await ensure_startup_model_check_once()

    rag = Ragent(
        working_dir=WORKING_DIR,
        embedding_func=openai_embed,
        llm_model_func=env_openai_complete,
        rerank_model_func=rerank_from_env,
        llm_model_name=os.getenv("LLM_API_MODEL"),
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()
    return rag


async def ainsert_rag(work_dir, text, doc_name, file_paths: str | None = None):
    if not os.path.exists(work_dir):
        os.mkdir(work_dir)
    rag = await initialize_rag(work_dir)
    source_file_path = os.path.abspath(file_paths) if file_paths else None
    hard_timeout_enabled = os.getenv("RAG_INSERT_HARD_TIMEOUT", "0") == "1"
    insert_timeout = int(os.getenv("RAG_INSERT_TIMEOUT_SECONDS", "0")) if hard_timeout_enabled else 0
    max_retries = int(os.getenv("RAG_INSERT_RETRIES", "2"))
    timeout_backoff = float(os.getenv("RAG_INSERT_TIMEOUT_BACKOFF", "1.8"))
    max_timeout = int(os.getenv("RAG_INSERT_TIMEOUT_MAX_SECONDS", "600"))
    try:
        if insert_timeout <= 0:
            await rag.ainsert(text, doc_name, file_paths=source_file_path)
            return True
        for attempt in range(max_retries + 1):
            cur_timeout = min(int(insert_timeout * (timeout_backoff ** attempt)), max_timeout)
            try:
                await asyncio.wait_for(
                    rag.ainsert(text, doc_name, file_paths=source_file_path),
                    timeout=cur_timeout,
                )
                return True
            except asyncio.TimeoutError:
                if attempt >= max_retries:
                    raise
                logger.warning(
                    f"ainsert_rag timeout, retrying. doc={doc_name}, attempt={attempt + 1}/{max_retries}, timeout={cur_timeout}s"
                )
    except Exception as e:
        err_msg = str(e) if str(e) else f"{type(e).__name__}({repr(e)})"
        logger.warning(f"ainsert_rag failed, skip this chunk. doc={doc_name}, err={err_msg}")
        return False


def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def _guess_image_mime_type(image_path: str) -> str:
    guessed, _ = mimetypes.guess_type(image_path)
    # Default to jpeg to keep compatibility with existing deployments.
    return guessed or "image/jpeg"


async def multimodal_image_analysis(image_path):
    return await asyncio.to_thread(multimodal_image_analysis_sync, image_path)


def multimodal_image_analysis_sync(image_path):
    base64_image = encode_image_to_base64(image_path)
    api_key = os.getenv("IMAGE_MODEL_KEY")
    image_model = os.getenv("IMAGE_MODEL")
    image_model_url = os.getenv("IMAGE_MODEL_URL")
    if not api_key or not image_model or not image_model_url:
        logger.warning(
            "Missing IMAGE_MODEL config, skip image description. "
            "required: IMAGE_MODEL_KEY/IMAGE_MODEL/IMAGE_MODEL_URL"
        )
        return ""
    url = image_model_url.rstrip("/")
    # Support both full chat endpoint and base OpenAI-compatible endpoint.
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"
    mime_type = _guess_image_mime_type(image_path)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": image_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请详细描述这张图片的内容，描述尽量多的实体信息"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1000 
    }
    timeout_sec = int(os.getenv("IMAGE_MODEL_TIMEOUT", "90"))
    log_model_call(
        "integrations.multimodal_image_analysis_sync",
        {
            "image_path": image_path,
            "api_key": api_key,
            "image_model": image_model,
            "image_model_url": image_model_url,
            "url": url,
            "mime_type": mime_type,
            "timeout_sec": timeout_sec,
            "headers": headers,
            "payload": payload,
        },
    )
    response = None
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        detail = response.text if response is not None else str(e)
        logger.warning(
            f"Image model request failed, skip image description. url={url}, model={image_model}, detail={detail}"
        )
        return ""
    

async def process_image_file(work_dir, image_file_path, doc_name):
    rag = await initialize_rag(work_dir)
    image_description = await multimodal_image_analysis(image_file_path)
    await rag.ainsert(image_description, doc_name=doc_name, file_paths=image_file_path)


async def inference_multi_hop_problem(work_dir, query, return_all: bool = False):
    rag = await initialize_rag(work_dir)
    result = await _run_multi_hop_with_rag(rag, query, include_trace=False)
    if return_all:
        return "question:"+ query +  "answer_multi_hop:" + result["answer"] + "\nimage_list:" + str(set(result["image_list"]))
    else:
        return result["answer"]



async def inference_one_hop_problem(work_dir, query, mode, return_all: bool = False):
    rag = await initialize_rag(work_dir)
    result = await _run_one_hop_with_rag(rag, query, mode, include_trace=False)
    one_hop_query_response = result["answer"]
    image_list = result["image_list"]
    if return_all:
        return "question:"+ query +  "one_hop_query_response" + one_hop_query_response + "\nimage_list:" + str(image_list)
    else:
        return one_hop_query_response


def do_parse(
    output_dir,  # Output directory for storing parsing results
    pdf_file_names: list[str],  # List of PDF file names to be parsed
    pdf_bytes_list: list[bytes],  # List of PDF bytes to be parsed
    p_lang_list: list[str],  # List of languages for each PDF, default is 'ch' (Chinese)
    backend="pipeline",  # The backend for parsing PDF, default is 'pipeline'
    parse_method="txt",  # The method for parsing PDF, default is 'auto'
    flat_output=False,  # 单文件时直接输出到 output_dir/parse_method，无中间层
    p_formula_enable=True,  # Enable formula parsing
    p_table_enable=True,  # Enable table parsing
    server_url=None,  # Server URL for vlm-sglang-client backend
    f_draw_layout_bbox=True,  # Whether to draw layout bounding boxes
    f_draw_span_bbox=True,  # Whether to draw span bounding boxes
    f_dump_md=True,  # Whether to dump markdown files
    f_dump_middle_json=True,  # Whether to dump middle JSON files
    f_dump_model_output=True,  # Whether to dump model output files
    f_dump_orig_pdf=True,  # Whether to dump original PDF files
    f_dump_content_list=True,  # Whether to dump content list files
    f_make_md_mode=MakeMode.MM_MD,  # The mode for making markdown content, default is MM_MD
    start_page_id=0,  # Start page ID for parsing, default is 0
    end_page_id=None,  # End page ID for parsing, default is None (parse all pages until the end of the document)
):

    if backend == "pipeline":
        for idx, pdf_bytes in enumerate(pdf_bytes_list):
            new_pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)
            pdf_bytes_list[idx] = new_pdf_bytes

        infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list = pipeline_doc_analyze(pdf_bytes_list, p_lang_list, parse_method=parse_method, formula_enable=p_formula_enable,table_enable=p_table_enable)
        
        for idx, model_list in enumerate(infer_results):
            model_json = copy.deepcopy(model_list)
            pdf_file_name = pdf_file_names[idx]
            if flat_output and len(pdf_file_names) == 1:
                local_image_dir, local_md_dir = _prepare_env_flat(output_dir, parse_method)
            else:
                local_image_dir, local_md_dir = prepare_env(output_dir, pdf_file_name, parse_method)
            image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)

            images_list = all_image_lists[idx]
            pdf_doc = all_pdf_docs[idx]
            _lang = lang_list[idx]
            _ocr_enable = ocr_enabled_list[idx]
            middle_json = pipeline_result_to_middle_json(model_list, images_list, pdf_doc, image_writer, _lang, _ocr_enable, p_formula_enable)

            pdf_info = middle_json["pdf_info"]

            pdf_bytes = pdf_bytes_list[idx]
            if f_draw_layout_bbox:
                draw_layout_bbox(pdf_info, pdf_bytes, local_md_dir, f"{pdf_file_name}_layout.pdf")

            if f_draw_span_bbox:
                draw_span_bbox(pdf_info, pdf_bytes, local_md_dir, f"{pdf_file_name}_span.pdf")

            if f_dump_orig_pdf:
                md_writer.write(
                    f"{pdf_file_name}_origin.pdf",
                    pdf_bytes,
                )

            if f_dump_md:
                image_dir = str(os.path.basename(local_image_dir))
                md_content_str = pipeline_union_make(pdf_info, f_make_md_mode, image_dir)
                md_writer.write_string(
                    f"{pdf_file_name}.md",
                    md_content_str,
                )

            if f_dump_content_list:
                image_dir = str(os.path.basename(local_image_dir))
                content_list = pipeline_union_make(pdf_info, MakeMode.CONTENT_LIST, image_dir)
                md_writer.write_string(
                    f"{pdf_file_name}_content_list.json",
                    json.dumps(content_list, ensure_ascii=False, indent=4),
                )

            if f_dump_middle_json:
                md_writer.write_string(
                    f"{pdf_file_name}_middle.json",
                    json.dumps(middle_json, ensure_ascii=False, indent=4),
                )

            if f_dump_model_output:
                md_writer.write_string(
                    f"{pdf_file_name}_model.json",
                    json.dumps(model_json, ensure_ascii=False, indent=4),
                )

            logger.info(f"local output dir is {local_md_dir}")
    else:
        if backend.startswith("vlm-"):
            backend = backend[4:]

        f_draw_span_bbox = False
        parse_method = "vlm"
        for idx, pdf_bytes in enumerate(pdf_bytes_list):
            pdf_file_name = pdf_file_names[idx]
            pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)
            if flat_output and len(pdf_file_names) == 1:
                local_image_dir, local_md_dir = _prepare_env_flat(output_dir, parse_method)
            else:
                local_image_dir, local_md_dir = prepare_env(output_dir, pdf_file_name, parse_method)
            image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)
            middle_json, infer_result = vlm_doc_analyze(pdf_bytes, image_writer=image_writer, backend=backend, server_url=server_url)

            pdf_info = middle_json["pdf_info"]

            if f_draw_layout_bbox:
                draw_layout_bbox(pdf_info, pdf_bytes, local_md_dir, f"{pdf_file_name}_layout.pdf")

            if f_draw_span_bbox:
                draw_span_bbox(pdf_info, pdf_bytes, local_md_dir, f"{pdf_file_name}_span.pdf")

            if f_dump_orig_pdf:
                md_writer.write(
                    f"{pdf_file_name}_origin.pdf",
                    pdf_bytes,
                )

            if f_dump_md:
                image_dir = str(os.path.basename(local_image_dir))
                md_content_str = vlm_union_make(pdf_info, f_make_md_mode, image_dir)
                md_writer.write_string(
                    f"{pdf_file_name}.md",
                    md_content_str,
                )

            if f_dump_content_list:
                image_dir = str(os.path.basename(local_image_dir))
                content_list = vlm_union_make(pdf_info, MakeMode.CONTENT_LIST, image_dir)
                md_writer.write_string(
                    f"{pdf_file_name}_content_list.json",
                    json.dumps(content_list, ensure_ascii=False, indent=4),
                )

            if f_dump_middle_json:
                md_writer.write_string(
                    f"{pdf_file_name}_middle.json",
                    json.dumps(middle_json, ensure_ascii=False, indent=4),
                )

            if f_dump_model_output:
                model_output = ("\n" + "-" * 50 + "\n").join(infer_result)
                md_writer.write_string(
                    f"{pdf_file_name}_model_output.txt",
                    model_output,
                )

            logger.info(f"local output dir is {local_md_dir}")


def parse_doc(
        path_list: list[Path],
        output_dir,
        lang="ch",
        backend="pipeline",
        method="txt",
        flat_output=False,
        server_url=None,
        start_page_id=0,  # Start page ID for parsing, default is 0
        end_page_id=None  # End page ID for parsing, default is None (parse all pages until the end of the document)
):
    """
        Parameter description:
        path_list: List of document paths to be parsed, can be PDF or image files.
        output_dir: Output directory for storing parsing results.
        lang: Language option, default is 'ch', optional values include['ch', 'ch_server', 'ch_lite', 'en', 'korean', 'japan', 'chinese_cht', 'ta', 'te', 'ka']。
            Input the languages in the pdf (if known) to improve OCR accuracy.  Optional.
            Adapted only for the case where the backend is set to "pipeline"
        backend: the backend for parsing pdf:
            pipeline: More general.
            vlm-transformers: More general.
            vlm-sglang-engine: Faster(engine).
            vlm-sglang-client: Faster(client).
            without method specified, pipeline will be used by default.
        method: the method for parsing pdf:
            auto: Automatically determine the method based on the file type.
            txt: Use text extraction method.
            ocr: Use OCR method for image-based PDFs.
            Without method specified, 'auto' will be used by default.
            Adapted only for the case where the backend is set to "pipeline".
        server_url: When the backend is `sglang-client`, you need to specify the server_url, for example:`http://127.0.0.1:30000`
    """
    try:
        file_name_list = []
        pdf_bytes_list = []
        lang_list = []
        for path in path_list:
            file_name = str(Path(path).stem)
            pdf_bytes = read_fn(path)
            file_name_list.append(file_name)
            pdf_bytes_list.append(pdf_bytes)
            lang_list.append(lang)
        do_parse(
            output_dir=output_dir,
            pdf_file_names=file_name_list,
            pdf_bytes_list=pdf_bytes_list,
            p_lang_list=lang_list,
            backend=backend,
            parse_method=method,
            flat_output=flat_output,
            server_url=server_url,
            start_page_id=start_page_id,
            end_page_id=end_page_id
        )
    except Exception as e:
        logger.exception(e)


def mineru_process(pdf_file_path, output_dir, keep_pdf_subdir: bool = True):
    pdf_path_list = [pdf_file_path]
    os.environ['MINERU_MODEL_SOURCE'] = "local"
    pdf_name = pdf_file_path.split("/")[-1].split(".")[0]

    if keep_pdf_subdir:
        parse_doc(path_list=pdf_path_list, output_dir=output_dir, backend="pipeline")
        return os.path.join(output_dir, pdf_name, "txt")

    # 单文件模式下直接输出到 <output_dir>/txt，无中间层
    os.makedirs(output_dir, exist_ok=True)
    parse_doc(path_list=pdf_path_list, output_dir=output_dir, backend="pipeline", flat_output=True)
    return os.path.join(output_dir, "txt")


async def build_enhanced_md(pdf_file_path, mineru_output_dir, keep_pdf_subdir: bool = True):
    """第一阶段：解析文档并产出增强后的最终 md（包含图片多模态描述回写）。"""
    await ensure_startup_model_check_once()
    pdf_outdir = mineru_process(
        pdf_file_path,
        mineru_output_dir,
        keep_pdf_subdir=keep_pdf_subdir,
    )
    os.makedirs(pdf_outdir, exist_ok=True)
    image_dir = os.path.join(pdf_outdir, "images")
    os.makedirs(image_dir, exist_ok=True)
    md_name = pdf_file_path.split("/")[-1].split(".")[0] + ".md"
    md_path = os.path.join(pdf_outdir, md_name)

    async with aiofiles.open(md_path, "r", encoding="utf-8") as f:
        md_text = await f.read()
    if not md_text:
        raise ValueError("md_text is empty")

    text_list = md_text.split("images/")
    num_chars_of_behind = int(os.getenv("num_chars_of_behind") or "120")
    num_chars_of_front = int(os.getenv("num_chars_of_front") or "120")
    total_blocks = len(text_list)
    total_images = max(total_blocks - 1, 0)
    _print_pipeline_progress(
        "build_enhanced_md_start",
        source_pdf=os.path.abspath(pdf_file_path),
        md_path=os.path.abspath(md_path),
        image_dir=os.path.abspath(image_dir),
        total_blocks=total_blocks,
        total_images=total_images,
    )

    # 先并发处理所有图片信息：请求在线程池中执行，且并发上限固定为 16
    image_preprocess_concurrency = 16
    semaphore = asyncio.Semaphore(image_preprocess_concurrency)
    image_progress_state = {"completed": 0}
    image_progress_lock = asyncio.Lock()

    async def process_image(i, text):
        if i == 0:
            return None
        image_match = re.match(r"^([^)]+?\.(?:jpg|jpeg|png))\)", text, re.IGNORECASE)
        if not image_match:
            async with image_progress_lock:
                image_progress_state["completed"] += 1
                _print_pipeline_progress(
                    "image_mm_skip_invalid_chunk",
                    image_index=i,
                    completed=image_progress_state["completed"],
                    total_images=total_images,
                    chunk_preview=text[:80].replace("\n", " "),
                )
            return ""
        image_name = image_match.group(1)
        image_path = os.path.join(image_dir, image_name)
        image_illustration_front = text_list[i - 1][-num_chars_of_front:]
        image_illustration_behind = text[image_match.end():][:num_chars_of_behind]
        async with semaphore:
            _print_pipeline_progress(
                "image_mm_start",
                image_index=i,
                total_images=total_images,
                image_name=image_name,
                image_path=os.path.abspath(image_path),
            )
            try:
                image_description = await multimodal_image_analysis(image_path)
                if not image_description:
                    async with image_progress_lock:
                        image_progress_state["completed"] += 1
                        _print_pipeline_progress(
                            "image_mm_empty_desc",
                            image_index=i,
                            completed=image_progress_state["completed"],
                            total_images=total_images,
                            image_name=image_name,
                        )
                    return ""
                combined_desc = await env_openai_complete(
                    prompt="image_Illustration_front:" + image_illustration_front + "image_Illustration_behind：" + image_illustration_behind + "\n" + "image_discription:" + image_description,
                    system_prompt="请结合两端文本（分别是图片的上下文和LLM生成的描述），进行全面描述",
                )
                async with image_progress_lock:
                    image_progress_state["completed"] += 1
                    _print_pipeline_progress(
                        "image_mm_done",
                        image_index=i,
                        completed=image_progress_state["completed"],
                        total_images=total_images,
                        image_name=image_name,
                        desc_len=len(combined_desc or ""),
                    )
                return combined_desc
            except Exception as e:
                logger.warning(f"Skip image post-process for {image_name}: {e}")
                async with image_progress_lock:
                    image_progress_state["completed"] += 1
                    _print_pipeline_progress(
                        "image_mm_failed",
                        image_index=i,
                        completed=image_progress_state["completed"],
                        total_images=total_images,
                        image_name=image_name,
                        error=str(e),
                    )
                return ""

    res_dismantles = await asyncio.gather(
        *(process_image(i, text) for i, text in enumerate(text_list))
    )
    non_empty_desc_count = sum(1 for x in res_dismantles[1:] if x and str(x).strip())
    _print_pipeline_progress(
        "image_mm_all_done",
        total_images=total_images,
        generated_descriptions=non_empty_desc_count,
    )

    for i, text in enumerate(text_list):
        if i == 0:
            continue
        image_match = re.match(r"^([^)]+?\.(?:jpg|jpeg|png))\)", text, re.IGNORECASE)
        if not image_match:
            _print_pipeline_progress(
                "image_desc_write_skip_invalid_chunk",
                image_index=i,
                total_images=total_images,
            )
            continue
        image_stem = os.path.splitext(image_match.group(1))[0]
        image_dismantle = os.path.join(image_dir, image_stem + ".txt")
        async with aiofiles.open(image_dismantle, "w", encoding="utf-8") as f:
            await f.write(res_dismantles[i] or "")
        _print_pipeline_progress(
            "image_desc_written",
            image_index=i,
            total_images=total_images,
            txt_path=os.path.abspath(image_dismantle),
            text_len=len(res_dismantles[i] or ""),
        )

    # 将图片描述回写到 md 中，并加标记避免重复注入
    try:
        async with aiofiles.open(md_path, "r", encoding="utf-8") as f:
            current_md_content = await f.read()

        image_pattern = re.compile(r"!\[\]\(images/([^)]+?\.(?:jpg|jpeg|png))\)", re.IGNORECASE)
        image_matches = list(image_pattern.finditer(current_md_content))
        total_md_images = len(image_matches)
        _print_pipeline_progress(
            "md_injection_start",
            md_path=os.path.abspath(md_path),
            total_md_images=total_md_images,
        )
        has_modification = False
        new_content_parts = []
        last_pos = 0
        injected_count = 0
        skipped_existing_count = 0

        for idx, match in enumerate(image_matches, start=1):
            image_file_name = match.group(1)
            marker_start = f"<!-- image_description:{image_file_name}:start -->"
            marker_end = f"<!-- image_description:{image_file_name}:end -->"

            if marker_start in current_md_content:
                skipped_existing_count += 1
                _print_pipeline_progress(
                    "md_injection_skip_exists",
                    progress=f"{idx}/{total_md_images}",
                    image_file=image_file_name,
                )
                continue

            new_content_parts.append(current_md_content[last_pos:match.end()])

            txt_file_path = os.path.join(image_dir, os.path.splitext(image_file_name)[0] + ".txt")
            image_desc_text = ""
            if os.path.exists(txt_file_path):
                try:
                    async with aiofiles.open(txt_file_path, "r", encoding="utf-8") as tf:
                        image_desc_text = (await tf.read()).strip()
                except Exception:
                    image_desc_text = ""

            if image_desc_text:
                insertion_block = "\n" + marker_start + "\n```image_description_start\n\n" + image_desc_text + "\n\n```\n" + marker_end + "\n"
                new_content_parts.append(insertion_block)
                has_modification = True
                injected_count += 1
                _print_pipeline_progress(
                    "md_injection_done",
                    progress=f"{idx}/{total_md_images}",
                    image_file=image_file_name,
                    desc_len=len(image_desc_text),
                )
            else:
                _print_pipeline_progress(
                    "md_injection_no_desc",
                    progress=f"{idx}/{total_md_images}",
                    image_file=image_file_name,
                    txt_path=os.path.abspath(txt_file_path),
                )

            last_pos = match.end()

        new_content_parts.append(current_md_content[last_pos:])

        if has_modification:
            async with aiofiles.open(md_path, "w", encoding="utf-8") as f:
                await f.write("".join(new_content_parts))
        _print_pipeline_progress(
            "md_injection_finished",
            md_path=os.path.abspath(md_path),
            total_md_images=total_md_images,
            injected_count=injected_count,
            skipped_existing_count=skipped_existing_count,
            modified=has_modification,
        )
    except Exception as e:
        logger.exception(e)
        _print_pipeline_progress(
            "md_injection_error",
            md_path=os.path.abspath(md_path),
            error=str(e),
        )

    _print_md_ready_banner(
        pdf_file_path=pdf_file_path,
        md_path=md_path,
        image_dir=image_dir,
        pdf_outdir=pdf_outdir,
    )
    return {"md_path": md_path, "image_dir": image_dir, "pdf_outdir": pdf_outdir}


async def index_md_to_rag(pdf_file_path, project_dir, md_path, progress: dict[str, Any] | None = None):
    """第二阶段：基于最终 md 和图片描述文件，构建 RAG/KG 索引。"""
    rag = await initialize_rag(project_dir)
    image_dir = os.path.join(os.path.dirname(md_path), "images")
    source_pdf_path = os.path.abspath(pdf_file_path)
    hard_timeout_enabled = os.getenv("RAG_INSERT_HARD_TIMEOUT", "0") == "1"
    insert_timeout = int(os.getenv("RAG_INSERT_TIMEOUT_SECONDS", "0")) if hard_timeout_enabled else 0
    max_retries = int(os.getenv("RAG_INSERT_RETRIES", "2"))
    timeout_backoff = float(os.getenv("RAG_INSERT_TIMEOUT_BACKOFF", "1.8"))
    max_timeout = int(os.getenv("RAG_INSERT_TIMEOUT_MAX_SECONDS", "600"))

    async with aiofiles.open(md_path, "r", encoding="utf-8") as f:
        md_text = await f.read()
    if not md_text:
        raise ValueError("md_text is empty")

    text_list = md_text.split("images/")
    doc_name_with_ext = pdf_file_path.split("/")[-1]
    doc_name_without_ext = pdf_file_path.split("/")[-1].split(".")[0]
    total_chunks = len(text_list)
    total_image_chunks = max(total_chunks - 1, 0)
    _print_pipeline_progress(
        "rag_index_start",
        source_pdf=os.path.abspath(pdf_file_path),
        md_path=os.path.abspath(md_path),
        image_dir=os.path.abspath(image_dir),
        total_chunks=total_chunks,
        total_image_chunks=total_image_chunks,
    )
    progress_state = progress if progress is not None else {}
    progress_state["started_monotonic"] = time.monotonic()
    progress_state["last_update_monotonic"] = progress_state["started_monotonic"]
    
    def _format_err(e: Exception) -> str:
        """格式化异常信息，TimeoutError 等异常 str() 为空，需用 type+repr 补充"""
        s = str(e)
        if s:
            return s
        return f"{type(e).__name__}({repr(e)})"

    def _content_preview(text: str, max_len: int = 80) -> str:
        t = text.strip().replace("\n", " ")
        return (t[:max_len] + "…") if len(t) > max_len else t

    def _update_progress(**kwargs):
        now = time.monotonic()
        progress_state.update(kwargs)
        progress_state["last_update_monotonic"] = now
        progress_state["elapsed_sec"] = round(now - progress_state.get("started_monotonic", now), 3)

    async def safe_rag_insert(
        text: str,
        doc_name: str,
        file_paths: str | None = None,
        *,
        chunk_index: int | None = None,
        chunk_type: str = "text",
    ):
        if not text or not text.strip():
            return

        async def _ainsert_once():
            resolved_file_path = os.path.abspath(file_paths) if file_paths else source_pdf_path
            await rag.ainsert(text, doc_name=doc_name, file_paths=resolved_file_path)

        if insert_timeout <= 0:
            try:
                await _ainsert_once()
            except Exception as e:
                parts = [
                    f"doc={doc_name}",
                    f"err={_format_err(e)}",
                    f"chunk_index={chunk_index}",
                    f"chunk_type={chunk_type}",
                    f"len={len(text)}",
                    f"preview={repr(_content_preview(text))}",
                ]
                if file_paths:
                    parts.append(f"file_paths={file_paths}")
                logger.warning(f"rag insert failed, skip this chunk. " + ", ".join(parts))
            return

        for attempt in range(max_retries + 1):
            cur_timeout = min(int(insert_timeout * (timeout_backoff ** attempt)), max_timeout)
            try:
                await asyncio.wait_for(_ainsert_once(), timeout=cur_timeout)
                if attempt > 0:
                    logger.info(
                        f"rag insert retry succeeded. doc={doc_name}, chunk_index={chunk_index}, chunk_type={chunk_type}, attempt={attempt + 1}, timeout={cur_timeout}s"
                    )
                return
            except asyncio.TimeoutError as e:
                if attempt >= max_retries:
                    parts = [
                        f"doc={doc_name}",
                        f"err={_format_err(e)}",
                        f"chunk_index={chunk_index}",
                        f"chunk_type={chunk_type}",
                        f"len={len(text)}",
                        f"preview={repr(_content_preview(text))}",
                    ]
                    if file_paths:
                        parts.append(f"file_paths={file_paths}")
                    logger.warning(
                        f"rag insert timeout after retries, skip this chunk. retries={max_retries}, last_timeout={cur_timeout}s, "
                        + ", ".join(parts)
                    )
                    return
                logger.warning(
                    f"rag insert timeout, retrying. doc={doc_name}, chunk_index={chunk_index}, chunk_type={chunk_type}, "
                    f"attempt={attempt + 1}/{max_retries}, timeout={cur_timeout}s"
                )
            except Exception as e:
                parts = [
                    f"doc={doc_name}",
                    f"err={_format_err(e)}",
                    f"chunk_index={chunk_index}",
                    f"chunk_type={chunk_type}",
                    f"len={len(text)}",
                    f"preview={repr(_content_preview(text))}",
                ]
                if file_paths:
                    parts.append(f"file_paths={file_paths}")
                logger.warning(f"rag insert failed, skip this chunk. " + ", ".join(parts))
                return

    _update_progress(
        phase="split_md",
        total_chunks=total_chunks,
        doc=doc_name_with_ext,
        md_path=md_path,
    )

    image_name_pattern = re.compile(r"^([^)]+?\.(?:jpg|jpeg|png))\)", re.IGNORECASE)
    for i, text in enumerate(text_list):
        if i == 0:
            _print_pipeline_progress(
                "rag_insert_chunk_start",
                progress=f"{i + 1}/{total_chunks}",
                chunk_index=0,
                chunk_type="text_first",
                text_len=len(text),
            )
            _update_progress(
                phase="insert_text_first",
                chunk_index=0,
                chunk_type="text_first",
                file_paths=source_pdf_path,
                text_len=len(text),
                preview=_content_preview(text),
            )
            await safe_rag_insert(
                text, doc_name_with_ext, file_paths=source_pdf_path,
                chunk_index=0, chunk_type="text_first",
            )
            continue

        image_match = image_name_pattern.match(text)
        if image_match:
            image_file_name = image_match.group(1)
            image_path = os.path.abspath(os.path.join(image_dir, image_file_name))
            image_dismantle = os.path.join(image_dir, os.path.splitext(image_file_name)[0] + ".txt")
            image_desc_text = ""
            if os.path.exists(image_dismantle):
                async with aiofiles.open(image_dismantle, "r", encoding="utf-8") as f:
                    image_desc_text = (await f.read()).strip()
            if image_desc_text:
                _print_pipeline_progress(
                    "rag_insert_chunk_start",
                    progress=f"{i + 1}/{total_chunks}",
                    chunk_index=i,
                    chunk_type="image_desc",
                    image_file=image_file_name,
                    image_path=os.path.abspath(image_path),
                    text_len=len(image_desc_text),
                )
                _update_progress(
                    phase="insert_image_desc",
                    chunk_index=i,
                    chunk_type="image_desc",
                    image_file=image_file_name,
                    file_paths=image_path,
                    text_len=len(image_desc_text),
                    preview=_content_preview(image_desc_text),
                )
                await safe_rag_insert(
                    image_desc_text, doc_name_without_ext, file_paths=image_path,
                    chunk_index=i, chunk_type="image_desc",
                )

        _print_pipeline_progress(
            "rag_insert_chunk_start",
            progress=f"{i + 1}/{total_chunks}",
            chunk_index=i,
            chunk_type="text",
            text_len=len(text),
        )
        _update_progress(
            phase="insert_text",
            chunk_index=i,
            chunk_type="text",
            file_paths=source_pdf_path,
            text_len=len(text),
            preview=_content_preview(text),
        )
        await safe_rag_insert(
            text, doc_name_with_ext, file_paths=source_pdf_path,
            chunk_index=i, chunk_type="text",
        )

    _update_progress(phase="completed")
    _print_pipeline_progress(
        "rag_index_completed",
        source_pdf=os.path.abspath(pdf_file_path),
        total_chunks=total_chunks,
    )


async def pdf_insert(pdf_file_path, mineru_output_dir, project_dir, keep_pdf_subdir: bool = True):
    """兼容入口：先生成最终 md，再执行 RAG/KG 构建。"""
    artifacts = await build_enhanced_md(
        pdf_file_path,
        mineru_output_dir,
        keep_pdf_subdir=keep_pdf_subdir,
    )
    logger.info(
        "Pre-step finished: markdown artifacts are ready, start RAG/KG indexing. "
        f"md_path={os.path.abspath(artifacts['md_path'])}"
    )
    rag_timeout = int(os.getenv("RAG_INDEX_TIMEOUT_SECONDS", "30"))
    rag_progress: dict[str, Any] = {
        "phase": "not_started",
        "doc": os.path.basename(pdf_file_path),
        "md_path": artifacts["md_path"],
    }
    allowed_progress_keys = {
        "phase",
        "doc",
        "chunk_index",
        "chunk_type",
        "text_len",
        "preview",
        "image_file",
        "file_paths",
        "total_chunks",
        "md_path",
        "elapsed_sec",
    }

    def _progress_snapshot() -> dict[str, Any]:
        return {k: v for k, v in rag_progress.items() if k in allowed_progress_keys}

    rag_start = time.monotonic()
    _print_pipeline_progress(
        "rag_index_started",
        timeout_sec=rag_timeout,
        source_pdf=os.path.abspath(pdf_file_path),
        md_path=os.path.abspath(artifacts["md_path"]),
        project_dir=os.path.abspath(project_dir),
    )

    rag_task = asyncio.create_task(
        index_md_to_rag(pdf_file_path, project_dir, artifacts["md_path"], progress=rag_progress)
    )

    try:
        await asyncio.wait_for(rag_task, timeout=rag_timeout)
        total_elapsed = round(time.monotonic() - rag_start, 3)
        _print_pipeline_progress(
            "rag_index_success",
            elapsed_sec=total_elapsed,
            timeout_sec=rag_timeout,
            last_progress=_progress_snapshot(),
        )
    except asyncio.TimeoutError as e:
        total_elapsed = round(time.monotonic() - rag_start, 3)
        progress_snapshot = _progress_snapshot()
        _print_pipeline_progress(
            "rag_index_timeout",
            elapsed_sec=total_elapsed,
            timeout_sec=rag_timeout,
            last_update_ago_sec=round(
                max(time.monotonic() - rag_progress.get("last_update_monotonic", rag_start), 0.0), 3
            ),
            last_progress=progress_snapshot,
        )
        err_msg = str(e) if str(e) else f"{type(e).__name__}({repr(e)})"
        logger.warning(
            "RAG indexing timeout, skip remainder. "
            f"timeout={rag_timeout}s, elapsed={total_elapsed}s, err={err_msg}, last_progress: {progress_snapshot}"
        )
    except Exception as e:
        total_elapsed = round(time.monotonic() - rag_start, 3)
        progress_snapshot = _progress_snapshot()
        err_msg = str(e) if str(e) else f"{type(e).__name__}({repr(e)})"
        _print_pipeline_progress(
            "rag_index_failed",
            elapsed_sec=total_elapsed,
            timeout_sec=rag_timeout,
            err=err_msg,
            last_progress=progress_snapshot,
        )
        logger.warning(
            "RAG indexing failure, skip remainder. "
            f"timeout={rag_timeout}s, elapsed={total_elapsed}s, err={err_msg}, last_progress: {progress_snapshot}"
        )


async def docx2pdf(docx_path, pdf_path):
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"找不到文件: {docx_path}")
    if not docx_path.lower().endswith('.docx'):
        raise ValueError("输入文件必须是 .docx 格式")
    if pdf_path is None:
        pdf_path = os.path.splitext(docx_path)[0] + '.pdf'

    result = subprocess.run(
        [
            "soffice",               # LibreOffice 命令
            "--headless",            # 无头模式（不显示界面）
            "--norestore",           # 不恢复上次会话
            "--writer",              # 使用 Writer 组件
            "--convert-to", "pdf",   # 转换为 pdf 格式
            "--outdir", os.path.dirname(pdf_path),  # 输出目录
            docx_path                # 输入文件
        ],
        capture_output=True,
        text=True,
        check=True
    )

async def docx_insert(doc_file_path, pdf_file_path, mineru_output_dir, project_dir):
    await docx2pdf(doc_file_path, pdf_file_path)
    await pdf_insert(pdf_file_path, mineru_output_dir, project_dir)
