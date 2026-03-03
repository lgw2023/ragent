from __future__ import annotations

import os
import aiohttp
from typing import Any, Dict, List, Optional

from .utils import logger, log_model_call


def _normalize_rerank_url(base_url: str | None) -> str | None:
    """Normalize rerank endpoint for different provider styles."""
    if not base_url:
        return None
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/reranks"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/reranks"
    return normalized


def _extract_rerank_results(result: dict) -> list[dict[str, Any]]:
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
        raise ValueError("Missing required env/config: RERANK_API_KEY")

    if not documents:
        return []
    if not model:
        raise ValueError("Missing required env/config: RERANK_MODEL")

    base_url = _normalize_rerank_url(base_url)
    if not base_url:
        raise ValueError("Missing required env/config: RERANK_URL")

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    data = {"model": model, "query": query, "documents": documents, **kwargs}

    if top_k is not None:
        top_n = min(top_k, len(documents))
        # DashScope expects top_n. Keep top_k for compatibility with other endpoints.
        data["top_n"] = top_n
        data["top_k"] = top_n

    async with aiohttp.ClientSession() as session:
        async with session.post(base_url, headers=headers, json=data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(
                    f"Rerank API error {response.status}. url={base_url}, model={model}, detail={error_text}"
                )

            result = await response.json()
            results = _extract_rerank_results(result)
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
                f"Rerank response format unsupported or empty. url={base_url}, model={model}, response={result}"
            )


async def rerank_from_env(
    query: str,
    documents: List[str],
    top_k: Optional[int] = None,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Rerank documents via HTTP API, using RERANK_* env vars for config."""
    if api_key is None:
        api_key = os.getenv("RERANK_API_KEY")
    rerank_url = os.getenv("RERANK_URL")
    rerank_model = os.getenv("RERANK_MODEL")
    log_model_call(
        "ragent.rerank.rerank_from_env",
        {
            "query": query,
            "documents": documents,
            "top_k": top_k,
            "api_key": api_key,
            "rerank_url": rerank_url,
            "rerank_model": rerank_model,
        },
    )

    return await rerank_api(
        query=query,
        documents=documents,
        model=rerank_model,
        base_url=rerank_url,
        api_key=api_key,
        top_k=top_k,
    )
