from __future__ import annotations

import os
import time
import aiohttp
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .utils import logger, log_model_call, record_model_usage


def _normalize_RERANK_MODEL_URL(base_url: str | None) -> str | None:
    """Normalize rerank base URL while preserving provider-specific endpoint styles."""
    if not base_url:
        return None
    return base_url.strip().rstrip("/")


def _is_deepinfra_inference_endpoint(base_url: str | None) -> bool:
    if not base_url:
        return False
    return "api.deepinfra.com/v1/inference" in base_url.strip().lower()


def _build_deepinfra_inference_url(base_url: str, model: str) -> str:
    """DeepInfra rerank uses /v1/inference/<model> instead of a model field in JSON."""
    normalized = _normalize_RERANK_MODEL_URL(base_url)
    if not normalized:
        raise ValueError("Missing required env/config: RERANK_MODEL_URL")

    if not model:
        raise ValueError("Missing required env/config: RERANK_MODEL")

    # If the caller already supplied a full model-specific inference endpoint, keep it.
    marker = "/v1/inference"
    lower = normalized.lower()
    marker_index = lower.find(marker)
    if marker_index == -1:
        return normalized

    suffix = normalized[marker_index + len(marker) :].lstrip("/")
    if suffix:
        return normalized

    encoded_model = quote(model.strip("/"), safe="/")
    return f"{normalized}/{encoded_model}"


def _build_rerank_request(
    *,
    query: str,
    documents: list[str],
    model: str,
    base_url: str,
    top_k: int | None,
    **kwargs: Any,
) -> tuple[str, dict[str, Any]]:
    normalized_base_url = _normalize_RERANK_MODEL_URL(base_url)
    if not normalized_base_url:
        raise ValueError("Missing required env/config: RERANK_MODEL_URL")

    if _is_deepinfra_inference_endpoint(normalized_base_url):
        request_url = _build_deepinfra_inference_url(normalized_base_url, model)
        # DeepInfra inference expects the model in the path and queries as a list.
        payload = {"queries": [query], "documents": documents, **kwargs}
        return request_url, payload

    if normalized_base_url.endswith("/reranks"):
        request_url = normalized_base_url
    elif normalized_base_url.endswith("/v1"):
        request_url = f"{normalized_base_url}/reranks"
    else:
        request_url = normalized_base_url

    payload = {"model": model, "query": query, "documents": documents, **kwargs}
    if top_k is not None:
        top_n = min(top_k, len(documents))
        # DashScope expects top_n. Keep top_k for compatibility with other endpoints.
        payload["top_n"] = top_n
        payload["top_k"] = top_n
    return request_url, payload


def _extract_rerank_results(
    result: dict,
    *,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Support multiple rerank response formats and normalize to list."""
    if not isinstance(result, dict):
        return []
    if isinstance(result.get("results"), list):
        return result["results"]
    if isinstance(result.get("data"), list):
        return result["data"]
    output = result.get("output")
    if isinstance(output, dict) and isinstance(output.get("results"), list):
        return output["results"]
    scores = result.get("scores")
    if isinstance(scores, list):
        normalized_scores: list[dict[str, Any]] = []
        for idx, score in enumerate(scores):
            try:
                normalized_score = float(score)
            except (TypeError, ValueError):
                normalized_score = 0.0
            normalized_scores.append(
                {"index": idx, "relevance_score": normalized_score}
            )
        normalized_scores.sort(
            key=lambda item: item.get("relevance_score", 0.0),
            reverse=True,
        )
        if top_k is not None:
            normalized_scores = normalized_scores[:top_k]
        return normalized_scores
    return []


def _normalize_result_item(item: dict[str, Any], fallback_index: int) -> dict[str, Any]:
    """Normalize provider-specific fields to stable keys used by retrieval flow."""
    if not isinstance(item, dict):
        return {"index": fallback_index, "relevance_score": 0.0}
    index = item.get("index", fallback_index)
    score = item.get("relevance_score", item.get("score", 0.0))
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0
    normalized = dict(item)
    normalized["index"] = index
    normalized["relevance_score"] = score
    return normalized


async def rerank_api(
    query: str,
    documents: List[str],
    model: str,
    base_url: str,
    api_key: str,
    top_k: Optional[int] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    log_model_call(
        "ragent.rerank.rerank_api",
        {
            "query": query,
            "documents": documents,
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
            "top_k": top_k,
            "kwargs": kwargs,
        },
    )
    if not api_key:
        raise ValueError("Missing required env/config: RERANK_MODEL_KEY")

    if not documents:
        return []
    if not model:
        raise ValueError("Missing required env/config: RERANK_MODEL")

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    request_url, data = _build_rerank_request(
        query=query,
        documents=documents,
        model=model,
        base_url=base_url,
        top_k=top_k,
        **kwargs,
    )

    rerank_req_start = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        async with session.post(request_url, headers=headers, json=data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(
                    f"Rerank API error {response.status}. url={request_url}, model={model}, detail={error_text}"
                )

            result = await response.json()
            rerank_elapsed = time.perf_counter() - rerank_req_start
            record_model_usage(
                "rerank",
                model,
                result,
                source="ragent.rerank.rerank_api",
                extra={
                    "document_count": len(documents),
                    "top_k": top_k,
                    "elapsed_seconds": round(rerank_elapsed, 3),
                },
            )
            results = _extract_rerank_results(result, top_k=top_k)
            if results:
                normalized = [
                    _normalize_result_item(item, idx) for idx, item in enumerate(results)
                ]
                normalized = [
                    item
                    for item in normalized
                    if isinstance(item.get("index"), int)
                    and 0 <= item["index"] < len(documents)
                ]
                if normalized:
                    return normalized
            raise RuntimeError(
                f"Rerank response format unsupported or empty. url={request_url}, model={model}, response={result}"
            )


async def rerank_from_env(
    query: str,
    documents: List[str],
    top_k: Optional[int] = None,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Rerank documents via HTTP API, using RERANK_* env vars for config."""
    if api_key is None:
        api_key = os.getenv("RERANK_MODEL_KEY")
    RERANK_MODEL_URL = os.getenv("RERANK_MODEL_URL")
    rerank_model = os.getenv("RERANK_MODEL")
    log_model_call(
        "ragent.rerank.rerank_from_env",
        {
            "query": query,
            "documents": documents,
            "top_k": top_k,
            "api_key": api_key,
            "RERANK_MODEL_URL": RERANK_MODEL_URL,
            "rerank_model": rerank_model,
        },
    )

    return await rerank_api(
        query=query,
        documents=documents,
        model=rerank_model,
        base_url=RERANK_MODEL_URL,
        api_key=api_key,
        top_k=top_k,
    )
