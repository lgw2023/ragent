from ..utils import verbose_debug, VERBOSE_DEBUG
import sys
import os
import json
import logging
import time
from urllib.parse import unquote, urlsplit

if sys.version_info < (3, 9):
    from typing import AsyncIterator, Iterator
else:
    from collections.abc import AsyncIterator, Iterator
try:
    from litellm import (
    acompletion,
    aembedding,
    APIConnectionError,
    InternalServerError,
    RateLimitError,
    Timeout as APITimeoutError,
    get_llm_provider,
    get_supported_openai_params,
    supports_response_schema,
    )
except ModuleNotFoundError as exc:
    if exc.name != "litellm":
        raise
    raise ModuleNotFoundError(
        "缺少依赖 `litellm`。请先运行 `uv sync`（或重新执行 `uv run ...` 让 uv 按 `pyproject.toml` 安装基础依赖）。"
    ) from exc
# LiteLLM attaches handlers at import time; re-apply after import in case load order differed.
for _litellm_log_name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy"):
    logging.getLogger(_litellm_log_name).propagate = False
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    retry_if_exception_type,
)
from pydantic import BaseModel
from ragent.utils import (
    wrap_embedding_func_with_attrs,
    locate_json_string_body_from_string,
    safe_unicode_decode,
    get_configured_embedding_dim,
    get_configured_embedding_dimensions,
    logger,
    log_exception,
    log_model_call,
    record_model_usage,
    is_verbose_error_logging_enabled,
)
from ragent.types import GPTKeywordExtractionFormat

import numpy as np
from typing import Any, Union
import httpx


class InvalidResponseError(Exception):
    """Custom exception class for triggering retry mechanism"""

    pass


_TRANSIENT_HTTPX_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadError,
    httpx.RemoteProtocolError,
    httpx.TimeoutException,
    httpx.WriteError,
)

_TRANSIENT_ERROR_MARKERS = (
    "connection error",
    "server disconnected",
    "read error",
    "readerror",
    "connect error",
    "connecterror",
    "timed out",
    "timeout",
)

_PROVIDER_API_BASE_HINTS: dict[str, tuple[str, ...]] = {
    "dashscope": (
        "dashscope.aliyuncs.com/compatible-mode",
        "dashscope-intl.aliyuncs.com/compatible-mode",
        "dashscope.aliyuncs.com/compatible-api",
        "dashscope-intl.aliyuncs.com/compatible-api",
    ),
    "deepinfra": (
        "api.deepinfra.com/v1/openai",
    ),
}

_PROVIDER_DEFAULT_API_BASES: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deepinfra": "https://api.deepinfra.com/v1/openai",
}

_PROVIDER_API_KEY_ENV_VARS: dict[str, tuple[str, ...]] = {
    "dashscope": ("DASHSCOPE_API_KEY",),
    "deepinfra": ("DEEPINFRA_API_KEY",),
}

_PLACEHOLDER_REQUEST_URLS = {
    "https://cloud.google.com/vertex-ai/",
    "https://openai.com/",
    "https://api.openai.com/v1",
    "https://api.openai.com/v1/",
}

_BOOLEAN_TRUE_VALUES = {"1", "true", "yes", "on"}
_BOOLEAN_FALSE_VALUES = {"0", "false", "no", "off"}


def _iter_exception_chain(exc: BaseException | None):
    seen: set[int] = set()
    current = exc
    while current is not None and id(current) not in seen:
        yield current
        seen.add(id(current))
        current = current.__cause__ or current.__context__


def _has_transient_error_marker(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_ERROR_MARKERS)


def _is_retryable_transport_error(exc: BaseException) -> bool:
    for chained_exc in _iter_exception_chain(exc):
        if isinstance(
            chained_exc,
            (
                APIConnectionError,
                APITimeoutError,
                *_TRANSIENT_HTTPX_EXCEPTIONS,
            ),
        ):
            return True
        if isinstance(chained_exc, InternalServerError) and _has_transient_error_marker(
            chained_exc
        ):
            return True
    return False


def _extract_http_status_error(
    exc: BaseException,
) -> httpx.HTTPStatusError | None:
    for chained_exc in _iter_exception_chain(exc):
        if isinstance(chained_exc, httpx.HTTPStatusError):
            return chained_exc
    return None


def _extract_http_error_response_details(response: httpx.Response) -> dict[str, Any]:
    error_type = None
    error_code = None
    error_message = None
    request_id = response.headers.get("x-request-id") or response.headers.get(
        "request-id"
    )

    body_text: str | None = None
    try:
        body_text = response.text
    except Exception:
        body_text = None

    body_json: Any | None = None
    try:
        body_json = response.json()
    except Exception:
        body_json = None

    if isinstance(body_json, dict):
        error_payload = body_json.get("error")
        if isinstance(error_payload, dict):
            error_type = error_payload.get("type")
            error_code = error_payload.get("code")
            error_message = error_payload.get("message")

    body_preview_source = body_text
    if not body_preview_source and body_json is not None:
        body_preview_source = _safe_serialize_for_log(body_json, max_len=1200)

    return {
        "status_code": response.status_code,
        "request_id": request_id,
        "error_type": error_type,
        "error_code": error_code,
        "error_message": error_message,
        "body_preview": _truncate_for_log(body_preview_source or "", max_len=1200),
    }


def _is_non_retryable_quota_http_status_error(response: httpx.Response) -> bool:
    if response.status_code != 429:
        return False

    details = _extract_http_error_response_details(response)
    markers = " ".join(
        str(value).lower()
        for value in (
            details["error_type"],
            details["error_code"],
            details["error_message"],
            details["body_preview"],
        )
        if value
    )
    return any(
        marker in markers
        for marker in (
            "insufficient_quota",
            "quota exceeded",
            "quota_exceeded",
            "current quota",
            "billing details",
            "token-limit",
            "token limit",
        )
    )


def _is_retryable_http_status_error(exc: BaseException) -> bool:
    """429/502/503/504 from httpx (e.g. DashScope OpenAI-compatible /embeddings)."""
    http_status_error = _extract_http_status_error(exc)
    if http_status_error is None:
        return False

    response = http_status_error.response
    code = response.status_code
    if code == 429 and _is_non_retryable_quota_http_status_error(response):
        return False
    return code in (429, 502, 503, 504)


def _parse_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _normalize_provider_name(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized or normalized.lower() in {"auto", "detect"}:
        return None
    return normalized


def _trace_model(msg: str) -> None:
    env_value = os.getenv("RAG_TRACE_MODEL_CALLS")
    if env_value is not None:
        enabled = env_value.lower() in ("1", "true", "yes", "on")
    else:
        enabled = VERBOSE_DEBUG or logger.isEnabledFor(logging.DEBUG)
    if enabled:
        logger.debug(f"[MODEL-TRACE] {msg}")


def _truncate_for_log(text: str, max_len: int = 300) -> str:
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}... (truncated, len={len(text)})"


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def _safe_serialize_for_log(value: Any, max_len: int = 4000) -> str:
    try:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        serialized = repr(value)
    return _truncate_for_log(serialized, max_len=max_len)


def _summarize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summarized_messages: list[dict[str, Any]] = []
    for index, message in enumerate(messages[:8]):
        summary: dict[str, Any] = {
            "index": index,
            "role": message.get("role"),
        }
        content = message.get("content")
        if isinstance(content, str):
            summary["content_len"] = len(content)
            summary["content_preview"] = _truncate_for_log(content, max_len=160)
        elif isinstance(content, list):
            summary["content_items"] = len(content)
            summary["content_types"] = [
                item.get("type", type(item).__name__)
                if isinstance(item, dict)
                else type(item).__name__
                for item in content[:8]
            ]
        elif content is not None:
            summary["content_type"] = type(content).__name__
            summary["content_preview"] = _truncate_for_log(
                repr(content), max_len=160
            )
        summarized_messages.append(summary)

    if len(messages) > 8:
        summarized_messages.append({"omitted_messages": len(messages) - 8})
    return summarized_messages


def _normalize_url_for_logging(url: httpx.URL | str | None) -> str | None:
    if url is None:
        return None
    normalized = str(url).strip()
    return normalized or None


def _is_placeholder_request_url(url: httpx.URL | str | None) -> bool:
    normalized = _normalize_url_for_logging(url)
    if not normalized:
        return False
    decoded = unquote(normalized).strip().lower()
    return decoded in _PLACEHOLDER_REQUEST_URLS


def _iter_request_candidates_from_exception(
    exc: BaseException,
) -> Iterator[httpx.Request]:
    for chained_exc in _iter_exception_chain(exc):
        request = getattr(chained_exc, "request", None)
        if isinstance(request, httpx.Request):
            yield request

        response = getattr(chained_exc, "response", None)
        response_request = getattr(response, "request", None)
        if isinstance(response_request, httpx.Request):
            yield response_request

        for arg in getattr(chained_exc, "args", ()):
            if isinstance(arg, httpx.Request):
                yield arg


def _extract_request_from_exception(exc: BaseException) -> httpx.Request | None:
    fallback_request: httpx.Request | None = None
    for request in _iter_request_candidates_from_exception(exc):
        if fallback_request is None:
            fallback_request = request
        if not _is_placeholder_request_url(request.url):
            return request
    return fallback_request


def _extract_url_parts(url: httpx.URL | str | None) -> dict[str, Any]:
    normalized_url = _normalize_url_for_logging(url)
    if normalized_url is None:
        return {
            "scheme": None,
            "host": None,
            "port": None,
            "path": None,
            "query": None,
        }

    if isinstance(url, httpx.URL):
        scheme = url.scheme
        host = url.host
        port = url.port
        path = url.path
        query = str(url.query.decode()) if url.query else None
    else:
        parsed = urlsplit(normalized_url)
        scheme = parsed.scheme or None
        host = parsed.hostname
        port = parsed.port
        path = parsed.path or None
        query = parsed.query or None

    if port is None:
        if scheme == "https":
            port = 443
        elif scheme == "http":
            port = 80

    return {
        "scheme": scheme,
        "host": host,
        "port": port,
        "path": path,
        "query": query,
    }


def _resolve_timeout(
    client_configs: dict[str, Any],
    env_var: str = "LLM_API_TIMEOUT_SECONDS",
) -> float | None:
    timeout = client_configs.get("timeout")
    if timeout is not None:
        return timeout

    timeout_env = os.getenv(env_var)
    if timeout_env:
        try:
            return float(timeout_env)
        except ValueError:
            logger.warning(
                "Invalid %s value: %s. Ignore timeout override.",
                env_var,
                timeout_env,
            )
    return None


def _resolve_num_retries(client_configs: dict[str, Any]) -> int:
    if "num_retries" in client_configs:
        try:
            return int(client_configs["num_retries"])
        except (TypeError, ValueError):
            logger.warning(
                "Invalid client_configs['num_retries'] value: %r. Use 0.",
                client_configs["num_retries"],
            )
            return 0

    if "max_retries" in client_configs:
        try:
            return int(client_configs["max_retries"])
        except (TypeError, ValueError):
            logger.warning(
                "Invalid client_configs['max_retries'] value: %r. Use 0.",
                client_configs["max_retries"],
            )
            return 0

    max_retries_env = os.getenv("LLM_API_CLIENT_MAX_RETRIES")
    if max_retries_env:
        try:
            return int(max_retries_env)
        except ValueError:
            logger.warning(
                "Invalid LLM_API_CLIENT_MAX_RETRIES value: %s. Use 0.",
                max_retries_env,
            )
    return 0


def _is_openai_default_base(api_base: str | None) -> bool:
    if not api_base:
        return True
    normalized = api_base.rstrip("/").lower()
    return normalized in {
        "https://api.openai.com",
        "https://api.openai.com/v1",
    }


def _infer_provider_from_api_base(api_base: str | None) -> str | None:
    normalized_api_base = (api_base or "").strip().lower()
    if not normalized_api_base:
        return None
    for provider, hints in _PROVIDER_API_BASE_HINTS.items():
        if any(hint in normalized_api_base for hint in hints):
            return provider
    return None


def _infer_provider_with_litellm(
    model: str,
    *,
    api_base: str | None,
    api_key: str | None,
) -> str | None:
    try:
        _, detected_provider, _, _ = get_llm_provider(
            model=model,
            api_base=api_base,
            api_key=api_key,
        )
    except Exception:
        return None
    return _normalize_provider_name(detected_provider)


def _resolve_api_key_for_provider(
    api_key: str | None,
    *,
    provider: str | None,
) -> str | None:
    if api_key:
        return api_key
    if not provider:
        return None
    for env_var in _PROVIDER_API_KEY_ENV_VARS.get(provider, ()):
        env_value = os.getenv(env_var)
        if env_value:
            return env_value
    return None


def _resolve_api_base_for_provider(
    *,
    model: str,
    provider: str | None,
    api_base: str | None,
    api_key: str | None,
) -> str | None:
    resolved_api_base = api_base
    if provider:
        try:
            _, detected_provider, _, detected_api_base = get_llm_provider(
                model=model,
                custom_llm_provider=provider,
                api_base=api_base,
                api_key=api_key,
            )
            normalized_detected_provider = _normalize_provider_name(detected_provider)
            if normalized_detected_provider:
                provider = normalized_detected_provider
            if detected_api_base:
                resolved_api_base = detected_api_base
        except Exception:
            pass
    if resolved_api_base:
        return resolved_api_base
    if provider:
        return _PROVIDER_DEFAULT_API_BASES.get(provider)
    return None


def _resolve_provider(
    model: str,
    *,
    api_base: str | None,
    api_key: str | None,
    provider_env_var: str,
    default_provider: str = "openai",
) -> str | None:
    explicit_provider = _normalize_provider_name(os.getenv(provider_env_var))
    if explicit_provider:
        return explicit_provider
    inferred_provider = _infer_provider_from_api_base(api_base)
    if inferred_provider:
        return inferred_provider
    inferred_provider = _infer_provider_with_litellm(
        model,
        api_base=api_base,
        api_key=api_key,
    )
    if inferred_provider:
        return inferred_provider
    if "/" in model:
        return None
    if api_base and not _is_openai_default_base(api_base):
        return "custom_openai"
    return default_provider


def _supports_openai_param(
    *,
    model: str,
    provider: str | None,
    request_type: str = "chat_completion",
    param_name: str,
) -> bool:
    try:
        supported = get_supported_openai_params(
            model=model,
            custom_llm_provider=provider,
            request_type=request_type,
        )
    except Exception:
        return False
    return bool(supported and param_name in supported)


def _parse_optional_env_bool(*names: str) -> bool | None:
    for name in names:
        value = os.getenv(name)
        if value is None:
            continue
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized in _BOOLEAN_TRUE_VALUES:
            return True
        if normalized in _BOOLEAN_FALSE_VALUES:
            return False
        logger.warning("Invalid boolean env value for %s=%s. Ignore override.", name, value)
        return None
    return None


def _is_bge_m3_embedding_model(model: str | None) -> bool:
    normalized = (model or "").strip().lower().replace("_", "-").replace("/", "-")
    return normalized in {"bge-m3", "baai-bge-m3"} or normalized.endswith("-bge-m3")


def _resolve_openai_http_embedding_dimensions(
    *,
    dimensions: str | None,
    provider: str | None,
    model: str,
) -> int | None:
    if not dimensions:
        return None
    try:
        resolved_dimensions = int(dimensions)
    except ValueError:
        logger.warning(
            "Invalid EMBEDDING_DIMENSIONS value: %s. Ignore dimensions override.",
            dimensions,
        )
        return None

    send_dimensions = _parse_optional_env_bool(
        "EMBEDDING_SEND_DIMENSIONS",
        "EMBEDDING_REQUEST_DIMENSIONS",
    )
    if send_dimensions is False:
        logger.info(
            "Skip EMBEDDING_DIMENSIONS for provider=%s model=%s because EMBEDDING_SEND_DIMENSIONS=0.",
            provider or "openai-compatible",
            model,
        )
        return None
    if send_dimensions is True:
        return resolved_dimensions

    if provider in {None, "custom_openai"} and _is_bge_m3_embedding_model(model):
        logger.info(
            "Skip EMBEDDING_DIMENSIONS for provider=%s model=%s because BGE-M3 does not support OpenAI dimensions/matryoshka requests. Set EMBEDDING_SEND_DIMENSIONS=1 to force.",
            provider or "openai-compatible",
            model,
        )
        return None
    return resolved_dimensions


def _normalize_response_format(
    *,
    model: str,
    provider: str | None,
    response_format: Any,
) -> Any:
    if response_format is None:
        return None

    if response_format == "json":
        return {"type": "json_object"}

    if isinstance(response_format, dict):
        return response_format

    if isinstance(response_format, type) and issubclass(response_format, BaseModel):
        if supports_response_schema(model=model, custom_llm_provider=provider):
            return response_format
        if _supports_openai_param(
            model=model,
            provider=provider,
            param_name="response_format",
        ):
            return {"type": "json_object"}
        return None

    return response_format


def _apply_dashscope_qwen3_compat(
    model_name: str | None,
    base_url: str | None,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Normalize request params for DashScope Qwen3 chat-completions compatibility."""
    resolved_model = (model_name or "").lower()
    resolved_base_url = (
        base_url or os.getenv("LLM_MODEL_URL") or os.getenv("LLM_API_BASE") or ""
    ).lower()
    if "dashscope.aliyuncs.com" not in resolved_base_url:
        return kwargs
    if not resolved_model.startswith("qwen3"):
        return kwargs

    normalized_kwargs = dict(kwargs)
    stream = bool(normalized_kwargs.get("stream", False))
    extra_body = normalized_kwargs.get("extra_body")
    if extra_body is None:
        extra_body = {}
    elif isinstance(extra_body, dict):
        extra_body = dict(extra_body)
    else:
        logger.warning(
            "Ignore non-dict extra_body while applying DashScope Qwen3 compatibility: %r",
            extra_body,
        )
        extra_body = {}

    env_thinking = _parse_optional_bool(os.getenv("LLM_API_ENABLE_THINKING"))
    if env_thinking is not None and "enable_thinking" not in extra_body:
        extra_body["enable_thinking"] = env_thinking

    if not stream and extra_body.get("enable_thinking") is not False:
        extra_body["enable_thinking"] = False

    if extra_body:
        normalized_kwargs["extra_body"] = extra_body
    return normalized_kwargs


def _build_error_context(
    *,
    model: str,
    provider: str | None,
    prompt: str,
    system_prompt: str | None,
    api_base: str | None,
    api_key: str | None,
    client_configs: dict[str, Any],
    kwargs: dict[str, Any],
    messages: list[dict[str, Any]],
    exc: BaseException,
) -> dict[str, Any]:
    request = _extract_request_from_exception(exc)
    raw_request_url = _normalize_url_for_logging(request.url) if request else None
    ignored_request_url = (
        raw_request_url if _is_placeholder_request_url(raw_request_url) else None
    )
    request_url = None if ignored_request_url else raw_request_url
    request_url_parts = _extract_url_parts(request_url)
    base_url_parts = _extract_url_parts(api_base)

    return {
        "model": model,
        "provider": provider,
        "request_method": request.method if request else "POST",
        "request_url": request_url,
        "request_host": request_url_parts["host"] or base_url_parts["host"],
        "request_port": request_url_parts["port"] or base_url_parts["port"],
        "request_path": request_url_parts["path"] or base_url_parts["path"],
        "request_query": request_url_parts["query"] or base_url_parts["query"],
        "ignored_exception_request_url": ignored_request_url,
        "request_url_source": "exception_request" if request_url else "api_base_fallback",
        "api_base": api_base,
        "api_key_hint": _mask_secret(api_key),
        "prompt_len": len(prompt) if prompt else 0,
        "system_prompt_len": len(system_prompt) if system_prompt else 0,
        "message_count": len(messages),
        "message_roles": [message.get("role") for message in messages],
        "messages_preview": _summarize_messages(messages),
        "request_kwargs": kwargs,
        "client_configs": client_configs,
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "cause_type": type(exc.__cause__).__name__ if exc.__cause__ else None,
        "cause_message": str(exc.__cause__) if exc.__cause__ else None,
    }


def _extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                elif (
                    item.get("type") == "text"
                    and isinstance(item.get("content"), str)
                ):
                    parts.append(item["content"])
        return "".join(parts)

    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"]
        return json.dumps(content, ensure_ascii=False)

    if content is None:
        return ""

    return str(content)


def _extract_completion_content(response: Any) -> str:
    if not response or not getattr(response, "choices", None):
        raise InvalidResponseError("Invalid response from LiteLLM")

    message = getattr(response.choices[0], "message", None)
    if message is None:
        raise InvalidResponseError("Missing message in LiteLLM response")

    content = _extract_text_from_content(getattr(message, "content", None))
    if not content:
        parsed = getattr(message, "parsed", None)
        if parsed is not None:
            if isinstance(parsed, BaseModel):
                content = parsed.model_dump_json()
            elif isinstance(parsed, (dict, list)):
                content = json.dumps(parsed, ensure_ascii=False)
            else:
                content = str(parsed)

    if not content or content.strip() == "":
        raise InvalidResponseError("Received empty content from LiteLLM")

    if r"\u" in content:
        content = safe_unicode_decode(content.encode("utf-8"))
    return content


def _usage_to_token_counts(usage: Any) -> dict[str, int]:
    if usage is None:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def _read(obj: Any, *keys: str) -> int:
        for key in keys:
            if isinstance(obj, dict) and key in obj:
                try:
                    return int(obj[key] or 0)
                except (TypeError, ValueError):
                    return 0
            if hasattr(obj, key):
                try:
                    return int(getattr(obj, key) or 0)
                except (TypeError, ValueError):
                    return 0
        return 0

    prompt_tokens = _read(usage, "prompt_tokens", "input_tokens")
    completion_tokens = _read(usage, "completion_tokens", "output_tokens")
    total_tokens = _read(usage, "total_tokens")
    if total_tokens == 0:
        total_tokens = prompt_tokens + completion_tokens
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def _build_litellm_request(
    *,
    model: str,
    api_key: str | None,
    api_base: str | None,
    client_configs: dict[str, Any],
    provider_env_var: str,
    default_provider: str = "openai",
) -> tuple[str, str | None, dict[str, Any]]:
    provider = _resolve_provider(
        model,
        api_base=api_base,
        api_key=api_key,
        provider_env_var=provider_env_var,
        default_provider=default_provider,
    )
    resolved_api_key = _resolve_api_key_for_provider(api_key, provider=provider)
    resolved_api_base = _resolve_api_base_for_provider(
        model=model,
        provider=provider,
        api_base=api_base,
        api_key=resolved_api_key,
    )
    timeout = _resolve_timeout(client_configs)
    num_retries = _resolve_num_retries(client_configs)
    request_kwargs: dict[str, Any] = {
        "api_key": resolved_api_key,
        "api_base": resolved_api_base,
        "custom_llm_provider": provider,
        "drop_params": True,
        "num_retries": num_retries,
    }

    if timeout is not None:
        request_kwargs["timeout"] = timeout
    extra_headers = client_configs.get("extra_headers")
    if extra_headers is not None:
        request_kwargs["extra_headers"] = extra_headers

    for key, value in client_configs.items():
        if key in {"timeout", "max_retries", "num_retries"}:
            continue
        request_kwargs.setdefault(key, value)

    return model, provider, request_kwargs


def _normalize_openai_embeddings_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/embeddings"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/embeddings"
    return f"{normalized}/embeddings"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=(
        retry_if_exception_type(RateLimitError)
        | retry_if_exception_type(InvalidResponseError)
        | retry_if_exception(_is_retryable_transport_error)
    ),
)
async def openai_complete_if_cache(
    model: str,
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict[str, Any]] | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    token_tracker: Any | None = None,
    **kwargs: Any,
) -> Union[str, AsyncIterator[str]]:
    if history_messages is None:
        history_messages = []

    client_configs = kwargs.pop("openai_client_configs", {}) or {}
    kwargs.pop("hashing_kv", None)
    kwargs.pop("keyword_extraction", None)

    resolved_model = os.environ.get("LLM_MODEL") or model
    resolved_api_base = (
        base_url
        or os.getenv("LLM_MODEL_URL")
        or os.getenv("LLM_API_BASE")
    )
    resolved_api_key = api_key or os.getenv("LLM_MODEL_KEY")

    request_model, request_provider, litellm_request_kwargs = _build_litellm_request(
        model=resolved_model,
        api_key=resolved_api_key,
        api_base=resolved_api_base,
        client_configs=client_configs,
        provider_env_var="LLM_API_PROVIDER",
        default_provider="openai",
    )
    resolved_api_base = litellm_request_kwargs.get("api_base") or resolved_api_base
    resolved_api_key = litellm_request_kwargs.get("api_key") or resolved_api_key

    kwargs = _apply_dashscope_qwen3_compat(
        model_name=request_model,
        base_url=resolved_api_base,
        kwargs=kwargs,
    )

    response_format = _normalize_response_format(
        model=request_model,
        provider=request_provider,
        response_format=kwargs.get("response_format"),
    )
    if response_format is None:
        kwargs.pop("response_format", None)
    else:
        kwargs["response_format"] = response_format

    if kwargs.get("stream") and "stream_options" not in kwargs:
        kwargs["stream_options"] = {"include_usage": True}

    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})
    messages = kwargs.pop("messages", messages)

    logger.debug("===== Entering func of LLM =====")
    logger.debug(
        "Model: %s   Provider: %s   API Base: %s",
        request_model,
        request_provider,
        resolved_api_base,
    )
    logger.debug("Additional kwargs: %s", kwargs)
    logger.debug("Num of history messages: %s", len(history_messages))
    verbose_debug(f"System prompt: {system_prompt}")
    verbose_debug(f"Query: {prompt}")
    logger.debug("===== Sending Query to LLM =====")

    log_model_call(
        "ragent.llm.openai.openai_complete_if_cache",
        {
            "model_arg": model,
            "resolved_model": request_model,
            "provider": request_provider,
            "base_url_arg": base_url,
            "resolved_base_url": resolved_api_base,
            "prompt": prompt,
            "system_prompt": system_prompt,
            "history_messages": history_messages,
            "messages": messages,
            "api_key": resolved_api_key,
            "client_configs": client_configs,
            "kwargs": kwargs,
            "litellm_request_kwargs": {
                k: v for k, v in litellm_request_kwargs.items() if k != "api_key"
            },
        },
    )

    llm_req_start = time.perf_counter()
    _trace_model(
        f"llm.request.start model={request_model} provider={request_provider} message_count={len(messages)} prompt_len={len(prompt) if prompt else 0}"
    )

    request_kwargs = {
        **litellm_request_kwargs,
        "model": request_model,
        "messages": messages,
        **kwargs,
    }

    try:
        response = await acompletion(**request_kwargs)
        llm_elapsed = time.perf_counter() - llm_req_start
        _trace_model(
            f"llm.request.done model={request_model} provider={request_provider} elapsed={llm_elapsed:.2f}s"
        )
    except APIConnectionError as e:
        _trace_model(
            f"llm.request.failed model={request_model} provider={request_provider} elapsed={time.perf_counter() - llm_req_start:.2f}s err={type(e).__name__}({repr(e)})"
        )
        error_context = None
        if is_verbose_error_logging_enabled():
            error_context = _safe_serialize_for_log(
                _build_error_context(
                    model=request_model,
                    provider=request_provider,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    api_base=resolved_api_base,
                    api_key=resolved_api_key,
                    client_configs=client_configs,
                    kwargs=kwargs,
                    messages=messages,
                    exc=e,
                )
            )
        log_exception(None, e, context=error_context)
        raise
    except RateLimitError as e:
        _trace_model(
            f"llm.request.failed model={request_model} provider={request_provider} elapsed={time.perf_counter() - llm_req_start:.2f}s err={type(e).__name__}({repr(e)})"
        )
        error_context = None
        if is_verbose_error_logging_enabled():
            error_context = _safe_serialize_for_log(
                _build_error_context(
                    model=request_model,
                    provider=request_provider,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    api_base=resolved_api_base,
                    api_key=resolved_api_key,
                    client_configs=client_configs,
                    kwargs=kwargs,
                    messages=messages,
                    exc=e,
                )
            )
        log_exception(None, e, context=error_context)
        raise
    except APITimeoutError as e:
        _trace_model(
            f"llm.request.failed model={request_model} provider={request_provider} elapsed={time.perf_counter() - llm_req_start:.2f}s err={type(e).__name__}({repr(e)})"
        )
        error_context = None
        if is_verbose_error_logging_enabled():
            error_context = _safe_serialize_for_log(
                _build_error_context(
                    model=request_model,
                    provider=request_provider,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    api_base=resolved_api_base,
                    api_key=resolved_api_key,
                    client_configs=client_configs,
                    kwargs=kwargs,
                    messages=messages,
                    exc=e,
                )
            )
        log_exception(None, e, context=error_context)
        raise
    except Exception as e:
        _trace_model(
            f"llm.request.failed model={request_model} provider={request_provider} elapsed={time.perf_counter() - llm_req_start:.2f}s err={type(e).__name__}({repr(e)})"
        )
        error_context = None
        if is_verbose_error_logging_enabled():
            error_context = _safe_serialize_for_log(
                _build_error_context(
                    model=request_model,
                    provider=request_provider,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    api_base=resolved_api_base,
                    api_key=resolved_api_key,
                    client_configs=client_configs,
                    kwargs=kwargs,
                    messages=messages,
                    exc=e,
                )
            )
        log_exception(None, e, context=error_context)
        raise

    if hasattr(response, "__aiter__"):

        async def inner():
            final_chunk_usage = None

            try:
                async for chunk in response:
                    usage = getattr(chunk, "usage", None)
                    if usage:
                        final_chunk_usage = usage
                        logger.debug(
                            "Received usage info in streaming chunk: %s", usage
                        )

                    choices = getattr(chunk, "choices", None)
                    if not choices:
                        logger.warning("Received chunk without choices: %s", chunk)
                        continue

                    delta = getattr(choices[0], "delta", None)
                    if delta is None:
                        continue

                    content = _extract_text_from_content(getattr(delta, "content", None))
                    if not content:
                        continue
                    if r"\u" in content:
                        content = safe_unicode_decode(content.encode("utf-8"))
                    yield content

                stream_elapsed = time.perf_counter() - llm_req_start
                if final_chunk_usage:
                    if token_tracker:
                        token_counts = _usage_to_token_counts(final_chunk_usage)
                        token_tracker.add_usage(token_counts)
                        logger.debug("Streaming token usage (from API): %s", token_counts)
                else:
                    logger.debug("No usage information available in streaming response")
                record_model_usage(
                    "chat",
                    os.environ.get("LLM_MODEL") or model,
                    final_chunk_usage,
                    source="ragent.llm.openai.openai_complete_if_cache.stream",
                    extra={
                        "elapsed_seconds": round(stream_elapsed, 3),
                        "message_count": len(messages),
                        "prompt_length_chars": len(prompt) if prompt else 0,
                        "stream": True,
                    },
                )
            except Exception as e:
                logger.error("Error in stream response: %s", str(e))
                if hasattr(response, "aclose") and callable(getattr(response, "aclose")):
                    try:
                        await response.aclose()
                    except Exception as close_error:
                        logger.warning(
                            "Failed to close stream response after error: %s",
                            close_error,
                        )
                raise
            finally:
                if hasattr(response, "aclose") and callable(getattr(response, "aclose")):
                    try:
                        await response.aclose()
                    except Exception as close_error:
                        logger.warning(
                            "Failed to close stream response in finally block: %s",
                            close_error,
                        )

        return inner()

    content = _extract_completion_content(response)
    usage = getattr(response, "usage", None)
    if token_tracker and usage:
        token_tracker.add_usage(_usage_to_token_counts(usage))
    record_model_usage(
        "chat",
        os.environ.get("LLM_MODEL") or model,
        usage,
        source="ragent.llm.openai.openai_complete_if_cache",
        extra={
            "elapsed_seconds": round(llm_elapsed, 3),
            "message_count": len(messages),
            "prompt_length_chars": len(prompt) if prompt else 0,
            "stream": False,
        },
    )

    logger.debug("Response content len: %s", len(content))
    verbose_debug(f"Response: {response}")
    return content


async def openai_complete(
    prompt,
    system_prompt=None,
    history_messages=None,
    keyword_extraction=False,
    **kwargs,
) -> Union[str, AsyncIterator[str]]:
    if history_messages is None:
        history_messages = []
    keyword_extraction = kwargs.pop("keyword_extraction", keyword_extraction)
    if keyword_extraction:
        kwargs["response_format"] = "json"
    model_name = kwargs["hashing_kv"].global_config["llm_model_name"]
    return await openai_complete_if_cache(
        model_name,
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        **kwargs,
    )


async def gpt_4o_complete(
    prompt,
    system_prompt=None,
    history_messages=None,
    keyword_extraction=False,
    **kwargs,
) -> str:
    if history_messages is None:
        history_messages = []
    keyword_extraction = kwargs.pop("keyword_extraction", keyword_extraction)
    if keyword_extraction:
        kwargs["response_format"] = GPTKeywordExtractionFormat
    return await openai_complete_if_cache(
        "gpt-4o",
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        **kwargs,
    )


async def env_openai_complete(
    prompt,
    system_prompt=None,
    history_messages=None,
    keyword_extraction=False,
    **kwargs,
) -> str:
    if history_messages is None:
        history_messages = []
    keyword_extraction = kwargs.pop("keyword_extraction", keyword_extraction)
    if keyword_extraction:
        kwargs["response_format"] = GPTKeywordExtractionFormat
    return await openai_complete_if_cache(
        os.environ["LLM_MODEL"],
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        **kwargs,
    )


async def gpt_4o_mini_complete(
    prompt,
    system_prompt=None,
    history_messages=None,
    keyword_extraction=False,
    **kwargs,
) -> str:
    return await env_openai_complete(
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        keyword_extraction=keyword_extraction,
        **kwargs,
    )


async def nvidia_openai_complete(
    prompt,
    system_prompt=None,
    history_messages=None,
    keyword_extraction=False,
    **kwargs,
) -> str:
    if history_messages is None:
        history_messages = []
    keyword_extraction = kwargs.pop("keyword_extraction", keyword_extraction)
    result = await openai_complete_if_cache(
        "nvidia_nim/llama-3.1-nemotron-70b-instruct",
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        base_url="https://integrate.api.nvidia.com/v1",
        **kwargs,
    )
    if keyword_extraction:
        return locate_json_string_body_from_string(result)
    return result


@wrap_embedding_func_with_attrs(
    embedding_dim=get_configured_embedding_dim(),
    max_token_size=8192,
)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=(
        retry_if_exception_type(RateLimitError)
        | retry_if_exception(_is_retryable_transport_error)
        | retry_if_exception(_is_retryable_http_status_error)
    ),
)
async def openai_embed(
    texts: list[str],
    model: str = "text-embedding-v3",
    base_url: str = None,
    api_key: str = None,
    client_configs: dict[str, Any] = None,
) -> np.ndarray:
    embedding_api_key = (
        api_key if api_key is not None else os.getenv("EMBEDDING_MODEL_KEY")
    )
    embedding_base_url = (
        base_url if base_url is not None else os.getenv("EMBEDDING_MODEL_URL")
    )
    embedding_model = os.getenv("EMBEDDING_MODEL") or model

    if not embedding_model:
        raise ValueError("Missing required env/config: EMBEDDING_MODEL")

    client_configs = client_configs or {}
    dimensions = get_configured_embedding_dimensions()
    resolved_provider = _resolve_provider(
        embedding_model,
        api_base=embedding_base_url,
        api_key=embedding_api_key,
        provider_env_var="EMBEDDING_PROVIDER",
        default_provider="openai",
    )
    embedding_api_key = _resolve_api_key_for_provider(
        embedding_api_key,
        provider=resolved_provider,
    )
    embedding_base_url = _resolve_api_base_for_provider(
        model=embedding_model,
        provider=resolved_provider,
        api_base=embedding_base_url,
        api_key=embedding_api_key,
    )

    if not embedding_api_key:
        raise ValueError("Missing required env/config: EMBEDDING_MODEL_KEY")
    if not embedding_base_url:
        raise ValueError("Missing required env/config: EMBEDDING_MODEL_URL")

    use_openai_compatible_http = resolved_provider in {
        None,
        "openai",
        "custom_openai",
        "dashscope",
        "deepinfra",
    }

    if use_openai_compatible_http:
        resolved_dimensions = _resolve_openai_http_embedding_dimensions(
            dimensions=dimensions,
            provider=resolved_provider,
            model=embedding_model,
        )

        timeout = _resolve_timeout(client_configs)
        extra_headers = client_configs.get("extra_headers")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {embedding_api_key}",
        }
        if isinstance(extra_headers, dict):
            headers.update(extra_headers)

        request_url = _normalize_openai_embeddings_url(embedding_base_url)
        payload: dict[str, Any] = {
            "model": embedding_model,
            "input": texts,
            "encoding_format": "float",
        }
        if resolved_dimensions is not None:
            payload["dimensions"] = resolved_dimensions

        log_model_call(
            "ragent.llm.openai.openai_embed",
            {
                "transport": "openai-compatible-http",
                "texts": texts,
                "model_arg": model,
                "resolved_model": embedding_model,
                "provider": resolved_provider or "openai-compatible",
                "base_url_arg": base_url,
                "resolved_base_url": embedding_base_url,
                "request_url": request_url,
                "api_key": embedding_api_key,
                "client_configs": client_configs,
                "payload": payload,
                "headers": {k: v for k, v in headers.items() if k.lower() != "authorization"},
            },
        )

        emb_req_start = time.perf_counter()
        _trace_model(
            f"embed.request.start model={embedding_model} provider={resolved_provider or 'openai-compatible'} batch_size={len(texts)}"
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(request_url, headers=headers, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                details = _extract_http_error_response_details(response)
                logger.error(
                    "Embedding HTTP request failed. model=%s provider=%s batch_size=%s total_chars=%s request_url=%s status=%s request_id=%s error_code=%s error_type=%s message=%s body=%s",
                    embedding_model,
                    resolved_provider or "openai-compatible",
                    len(texts),
                    sum(len(text) for text in texts),
                    request_url,
                    details["status_code"],
                    details["request_id"],
                    details["error_code"],
                    details["error_type"],
                    details["error_message"],
                    details["body_preview"],
                )
                raise
            response_payload = response.json()
        emb_elapsed = time.perf_counter() - emb_req_start
        record_model_usage(
            "embedding",
            embedding_model,
            response_payload.get("usage"),
            source="ragent.llm.openai.openai_embed",
            extra={
                "batch_size": len(texts),
                "elapsed_seconds": round(emb_elapsed, 3),
            },
        )
        _trace_model(
            f"embed.request.done model={embedding_model} provider={resolved_provider or 'openai-compatible'} batch_size={len(texts)} elapsed={emb_elapsed:.2f}s"
        )

        data = response_payload.get("data") or []
        embeddings: list[list[float]] = []
        for item in data:
            if isinstance(item, dict):
                embeddings.append(item["embedding"])
            else:
                embeddings.append(getattr(item, "embedding"))
        return np.array(embeddings)

    request_model, request_provider, litellm_request_kwargs = _build_litellm_request(
        model=embedding_model,
        api_key=embedding_api_key,
        api_base=embedding_base_url,
        client_configs=client_configs,
        provider_env_var="EMBEDDING_PROVIDER",
        default_provider="openai",
    )
    embedding_base_url = litellm_request_kwargs.get("api_base") or embedding_base_url
    embedding_api_key = litellm_request_kwargs.get("api_key") or embedding_api_key

    request_kwargs: dict[str, Any] = {
        **litellm_request_kwargs,
        "model": request_model,
        "input": texts,
        "encoding_format": "float",
    }
    if dimensions:
        supports_dimensions = _supports_openai_param(
            model=request_model,
            provider=request_provider,
            request_type="embeddings",
            param_name="dimensions",
        )
        if supports_dimensions:
            try:
                request_kwargs["dimensions"] = int(dimensions)
            except ValueError:
                logger.warning(
                    "Invalid EMBEDDING_DIMENSIONS value: %s. Ignore dimensions override.",
                    dimensions,
                )
        else:
            logger.info(
                "Skip EMBEDDING_DIMENSIONS for provider=%s model=%s because the embeddings endpoint does not advertise dimensions support.",
                request_provider,
                request_model,
            )

    log_model_call(
        "ragent.llm.openai.openai_embed",
        {
            "transport": "litellm",
            "texts": texts,
            "model_arg": model,
            "resolved_model": request_model,
            "provider": request_provider,
            "base_url_arg": base_url,
            "resolved_base_url": embedding_base_url,
            "api_key": embedding_api_key,
            "client_configs": client_configs,
            "request_kwargs": {
                k: v for k, v in request_kwargs.items() if k != "api_key"
            },
        },
    )

    emb_req_start = time.perf_counter()
    _trace_model(
        f"embed.request.start model={request_model} provider={request_provider} batch_size={len(texts)}"
    )
    try:
        response = await aembedding(**request_kwargs)
        emb_elapsed = time.perf_counter() - emb_req_start
        record_model_usage(
            "embedding",
            request_model,
            getattr(response, "usage", None),
            source="ragent.llm.openai.openai_embed",
            extra={
                "batch_size": len(texts),
                "elapsed_seconds": round(emb_elapsed, 3),
            },
        )
        _trace_model(
            f"embed.request.done model={request_model} provider={request_provider} batch_size={len(texts)} elapsed={emb_elapsed:.2f}s"
        )
    except Exception as e:
        _trace_model(
            f"embed.request.failed model={request_model} provider={request_provider} batch_size={len(texts)} elapsed={time.perf_counter() - emb_req_start:.2f}s err={type(e).__name__}({repr(e)})"
        )
        raise

    data = getattr(response, "data", None) or []
    embeddings: list[list[float]] = []
    for item in data:
        if isinstance(item, dict):
            embeddings.append(item["embedding"])
        else:
            embeddings.append(getattr(item, "embedding"))
    return np.array(embeddings)
