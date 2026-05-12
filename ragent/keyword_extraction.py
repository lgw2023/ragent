from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
import importlib
import os
import re
import string
import threading
from typing import Any

from .utils import logger


DEFAULT_GLINER_KEYWORD_MODEL = "knowledgator/gliner-x-small"
DEFAULT_GLINER_KEYWORD_DEVICE = "cpu"
DEFAULT_GLINER_KEYWORD_THRESHOLD = 0.35
DEFAULT_GLINER_MAX_KEYWORDS = 12
DEFAULT_GLINER_WARMUP_TEXT = (
    "我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，"
    "我先 中速步行30 分钟，再爬楼多久能补回来？"
)

KEYWORD_SOURCE_REQUEST = "request"
KEYWORD_SOURCE_LLM = "llm"
KEYWORD_SOURCE_GLINER_FALLBACK = "gliner_fallback"

KEYWORD_STRATEGY_REQUEST = "request"
KEYWORD_STRATEGY_LLM = "llm_keyword_extraction"
KEYWORD_STRATEGY_TOKEN_CLASSIFICATION = "token_classification_fallback"

_HIGH_LEVEL_LABELS = {
    "topic",
    "concept",
    "domain",
    "theme",
    "problem",
    "requirement",
    "policy",
    "law",
    "standard",
    "event",
    "method",
    "process",
    "task",
    "field",
}

_DEFAULT_GLINER_LABELS = (
    "topic",
    "concept",
    "domain",
    "problem",
    "requirement",
    "policy",
    "law",
    "standard",
    "event",
    "method",
    "process",
    "technology",
    "product",
    "tool",
    "organization",
    "person",
    "location",
    "date",
    "metric",
    "document",
    "food",
    "disease",
    "medication",
)

_MODEL_CACHE: dict[tuple[str, str], Any] = {}
_MODEL_CACHE_LOCK = threading.Lock()
_PUNCT_TRANSLATION = str.maketrans({char: " " for char in string.punctuation})
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_LOCAL_WORD_TOKEN_RE = re.compile(
    r"[\u4e00-\u9fff]|[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*|[^\s]"
)
_CJK_QUERY_SPLIT_RE = re.compile(
    r"(?:是什么|有哪些|如何|怎么|怎样|为什么|多少|是否|请|帮我|一下|吗|呢|？|\?)"
)
_CJK_CONNECTOR_RE = re.compile(r"(?:以及|或者|的|和|与|及|或|在|中|为|是|对)")


class _LocalRegexWordsSplitter:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def __call__(self, text: str):
        for match in _LOCAL_WORD_TOKEN_RE.finditer(text):
            yield match.group(), match.start(), match.end()


@dataclass(frozen=True)
class KeywordResolution:
    high_level_keywords: list[str]
    low_level_keywords: list[str]
    keyword_source: str
    keyword_strategy: str
    keyword_fallback_reason: str | None = None
    keyword_model: str | None = None
    keyword_model_device: str | None = None
    keyword_model_error: str | None = None

    def metadata(self) -> dict[str, Any]:
        return {
            "keyword_source": self.keyword_source,
            "keyword_strategy": self.keyword_strategy,
            "keyword_fallback_reason": self.keyword_fallback_reason,
            "keyword_model": self.keyword_model,
            "keyword_model_device": self.keyword_model_device,
            "keyword_model_error": self.keyword_model_error,
        }


class KeywordExtractorUnavailable(RuntimeError):
    pass


def get_gliner_keyword_model_name(global_config: dict[str, Any] | None = None) -> str:
    configured = None
    if isinstance(global_config, dict):
        configured = (
            global_config.get("keyword_model")
            or global_config.get("keyword_model_name")
            or global_config.get("keyword_fallback_model")
        )
    return str(
        os.getenv("RAG_KEYWORD_FALLBACK_MODEL")
        or configured
        or DEFAULT_GLINER_KEYWORD_MODEL
    ).strip()


def get_gliner_keyword_device(global_config: dict[str, Any] | None = None) -> str:
    configured = None
    if isinstance(global_config, dict):
        configured = (
            global_config.get("keyword_model_device")
            or global_config.get("keyword_fallback_device")
        )
    return str(
        os.getenv("RAG_KEYWORD_FALLBACK_DEVICE")
        or configured
        or DEFAULT_GLINER_KEYWORD_DEVICE
    ).strip()


def keyword_fallback_enabled(global_config: dict[str, Any] | None = None) -> bool:
    configured = None
    if isinstance(global_config, dict):
        configured = global_config.get("enable_keyword_fallback")
    raw_value = os.getenv("RAG_KEYWORD_FALLBACK_ENABLED")
    if raw_value is None and configured is not None:
        raw_value = str(configured)
    return str(raw_value if raw_value is not None else "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def build_request_keyword_resolution(
    high_level_keywords: list[str],
    low_level_keywords: list[str],
) -> KeywordResolution:
    return KeywordResolution(
        high_level_keywords=list(high_level_keywords or []),
        low_level_keywords=list(low_level_keywords or []),
        keyword_source=KEYWORD_SOURCE_REQUEST,
        keyword_strategy=KEYWORD_STRATEGY_REQUEST,
    )


def build_llm_keyword_resolution(
    high_level_keywords: list[str],
    low_level_keywords: list[str],
) -> KeywordResolution:
    return KeywordResolution(
        high_level_keywords=list(high_level_keywords or []),
        low_level_keywords=list(low_level_keywords or []),
        keyword_source=KEYWORD_SOURCE_LLM,
        keyword_strategy=KEYWORD_STRATEGY_LLM,
    )


def build_gliner_unavailable_resolution(
    *,
    reason: str,
    model_name: str | None = None,
    device: str | None = None,
    error: str | None = None,
) -> KeywordResolution:
    return KeywordResolution(
        high_level_keywords=[],
        low_level_keywords=[],
        keyword_source=KEYWORD_SOURCE_GLINER_FALLBACK,
        keyword_strategy=KEYWORD_STRATEGY_TOKEN_CLASSIFICATION,
        keyword_fallback_reason=reason,
        keyword_model=model_name,
        keyword_model_device=device,
        keyword_model_error=error,
    )


def apply_keyword_resolution(query_param: Any, resolution: KeywordResolution) -> None:
    query_param.hl_keywords = list(resolution.high_level_keywords or [])
    query_param.ll_keywords = list(resolution.low_level_keywords or [])
    query_param.keyword_source = resolution.keyword_source
    query_param.keyword_strategy = resolution.keyword_strategy
    query_param.keyword_fallback_reason = resolution.keyword_fallback_reason
    query_param.keyword_model = resolution.keyword_model
    query_param.keyword_model_device = resolution.keyword_model_device
    query_param.keyword_model_error = resolution.keyword_model_error
    query_param.keyword_resolution_done = True


def keyword_metadata_from_query_param(query_param: Any) -> dict[str, Any]:
    return {
        "keyword_source": getattr(query_param, "keyword_source", None),
        "keyword_strategy": getattr(query_param, "keyword_strategy", None),
        "keyword_fallback_reason": getattr(query_param, "keyword_fallback_reason", None),
        "keyword_model": getattr(query_param, "keyword_model", None),
        "keyword_model_device": getattr(query_param, "keyword_model_device", None),
        "keyword_model_error": getattr(query_param, "keyword_model_error", None),
    }


def prepare_keyword_metadata_for_cache(
    query_param: Any,
    global_config: dict[str, Any] | None = None,
    *,
    allow_llm_keyword_extraction: bool,
) -> None:
    if getattr(query_param, "hl_keywords", None) or getattr(
        query_param, "ll_keywords", None
    ):
        if not getattr(query_param, "keyword_source", None):
            query_param.keyword_source = KEYWORD_SOURCE_REQUEST
        if not getattr(query_param, "keyword_strategy", None):
            query_param.keyword_strategy = KEYWORD_STRATEGY_REQUEST
        query_param.keyword_resolution_done = True
        return

    if getattr(query_param, "keyword_source", None) and getattr(
        query_param, "keyword_strategy", None
    ):
        return

    if allow_llm_keyword_extraction:
        query_param.keyword_source = KEYWORD_SOURCE_LLM
        query_param.keyword_strategy = KEYWORD_STRATEGY_LLM
        return

    query_param.keyword_source = KEYWORD_SOURCE_GLINER_FALLBACK
    query_param.keyword_strategy = KEYWORD_STRATEGY_TOKEN_CLASSIFICATION
    query_param.keyword_model = get_gliner_keyword_model_name(global_config)
    query_param.keyword_model_device = get_gliner_keyword_device(global_config)
    query_param.keyword_fallback_reason = (
        "explicit keywords missing and LLM keyword extraction disabled; "
        "using no-LLM token classification fallback"
    )


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _gliner_threshold(global_config: dict[str, Any] | None = None) -> float:
    configured = None
    if isinstance(global_config, dict):
        configured = global_config.get("keyword_fallback_threshold")
    return _coerce_float(
        os.getenv("RAG_KEYWORD_FALLBACK_THRESHOLD") or configured,
        DEFAULT_GLINER_KEYWORD_THRESHOLD,
    )


def _gliner_max_keywords(global_config: dict[str, Any] | None = None) -> int:
    configured = None
    if isinstance(global_config, dict):
        configured = global_config.get("keyword_fallback_max_keywords")
    return max(
        1,
        _coerce_int(
            os.getenv("RAG_KEYWORD_FALLBACK_MAX_KEYWORDS") or configured,
            DEFAULT_GLINER_MAX_KEYWORDS,
        ),
    )


def _gliner_labels(global_config: dict[str, Any] | None = None) -> list[str]:
    configured = None
    if isinstance(global_config, dict):
        configured = global_config.get("keyword_fallback_labels")
    raw_value = os.getenv("RAG_KEYWORD_FALLBACK_LABELS") or configured
    if isinstance(raw_value, str):
        labels = [item.strip() for item in raw_value.split(",") if item.strip()]
        return labels or list(_DEFAULT_GLINER_LABELS)
    if isinstance(raw_value, (list, tuple)):
        labels = [str(item).strip() for item in raw_value if str(item).strip()]
        return labels or list(_DEFAULT_GLINER_LABELS)
    return list(_DEFAULT_GLINER_LABELS)


@contextmanager
def _patched_gliner_words_splitter():
    patched_modules: list[tuple[Any, Any]] = []
    for module_name in ("gliner.data_processing.processor", "gliner.model"):
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue
        if not hasattr(module, "WordsSplitter"):
            continue
        patched_modules.append((module, getattr(module, "WordsSplitter")))
        setattr(module, "WordsSplitter", _LocalRegexWordsSplitter)

    try:
        yield
    finally:
        for module, original_words_splitter in reversed(patched_modules):
            setattr(module, "WordsSplitter", original_words_splitter)


def _install_local_words_splitter(model: Any) -> None:
    data_processor = getattr(model, "data_processor", None)
    if data_processor is not None:
        try:
            data_processor.words_splitter = _LocalRegexWordsSplitter()
        except Exception:
            logger.debug("Unable to install local GLiNER words splitter", exc_info=True)


def _load_gliner_model(model_name: str, device: str) -> Any:
    cache_key = (model_name, device)
    with _MODEL_CACHE_LOCK:
        cached_model = _MODEL_CACHE.get(cache_key)
        if cached_model is not None:
            return cached_model
        try:
            from gliner import GLiNER  # type: ignore
        except Exception as exc:  # pragma: no cover - exercised via fallback tests
            raise KeywordExtractorUnavailable(
                "python package 'gliner' is not installed or cannot be imported"
            ) from exc

        try:
            with _patched_gliner_words_splitter():
                model = GLiNER.from_pretrained(model_name)
            _install_local_words_splitter(model)
            to_device = getattr(model, "to", None)
            if callable(to_device):
                model = to_device(device)
                _install_local_words_splitter(model)
            eval_model = getattr(model, "eval", None)
            if callable(eval_model):
                eval_model()
        except Exception as exc:  # pragma: no cover - depends on local model runtime
            raise KeywordExtractorUnavailable(
                f"failed to load GLiNER keyword model '{model_name}': {exc}"
            ) from exc
        _MODEL_CACHE[cache_key] = model
        return model


def _normalize_keyword(value: Any, query: str) -> str | None:
    keyword = re.sub(r"\s+", " ", str(value or "").strip())
    keyword = keyword.strip(" \t\r\n,，.。;；:：!?！？\"'“”‘’()（）[]【】{}")
    if not keyword:
        return None
    if len(keyword) == 1 and keyword.isascii() and not keyword.isalnum():
        return None
    normalized_query = re.sub(r"\s+", " ", query.strip())
    if keyword == normalized_query and len(keyword) > 24:
        return None
    return keyword


def _dedupe_limited_keywords(values: list[str], limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def _predict_gliner_entities(
    text: str,
    *,
    model_name: str,
    device: str,
    labels: list[str],
    threshold: float,
) -> list[dict[str, Any]]:
    model = _load_gliner_model(model_name, device)
    predict_entities = getattr(model, "predict_entities", None)
    if not callable(predict_entities):
        raise KeywordExtractorUnavailable(
            f"GLiNER model '{model_name}' does not expose predict_entities"
        )
    entities = predict_entities(text, labels, threshold=threshold)
    if not isinstance(entities, list):
        return []
    return [item for item in entities if isinstance(item, dict)]


def _warmup_gliner_model(
    *,
    model_name: str,
    device: str,
    labels: list[str],
    threshold: float,
    warmup_text: str | None,
) -> int:
    model = _load_gliner_model(model_name, device)
    if not warmup_text:
        return 0
    predict_entities = getattr(model, "predict_entities", None)
    if not callable(predict_entities):
        return 0
    entities = predict_entities(warmup_text, labels, threshold=threshold)
    return len(entities) if isinstance(entities, list) else 0


async def ensure_gliner_keyword_model_ready(
    global_config: dict[str, Any] | None = None,
    *,
    warmup_text: str | None = None,
) -> dict[str, Any]:
    model_name = get_gliner_keyword_model_name(global_config)
    device = get_gliner_keyword_device(global_config)
    if not keyword_fallback_enabled(global_config):
        raise KeywordExtractorUnavailable("GLiNER keyword fallback is disabled")

    resolved_warmup_text = (
        os.getenv("RAG_KEYWORD_FALLBACK_WARMUP_TEXT")
        if warmup_text is None
        else warmup_text
    )
    if resolved_warmup_text is None:
        resolved_warmup_text = DEFAULT_GLINER_WARMUP_TEXT
    resolved_warmup_text = str(resolved_warmup_text).strip()

    entity_count = await asyncio.to_thread(
        _warmup_gliner_model,
        model_name=model_name,
        device=device,
        labels=_gliner_labels(global_config),
        threshold=_gliner_threshold(global_config),
        warmup_text=resolved_warmup_text,
    )
    return {
        "keyword_model": model_name,
        "keyword_model_device": device,
        "warmup_text": resolved_warmup_text,
        "warmup_entity_count": entity_count,
    }


def _fallback_keyword_candidates(text: str) -> list[str]:
    if not re.search(r"\s", text) and _CJK_RE.search(text):
        normalized = text.translate(_PUNCT_TRANSLATION)
        normalized = re.sub(r"[，。！？；：、（）【】《》“”‘’]", " ", normalized)
        normalized = re.sub(r"\s+", "", normalized)
        candidates: list[str] = []
        for phrase in _CJK_QUERY_SPLIT_RE.split(normalized):
            phrase = phrase.strip()
            if not phrase:
                continue
            parts = [part for part in _CJK_CONNECTOR_RE.split(phrase) if part]
            if len(phrase) <= 16:
                candidates.append(phrase)
            candidates.extend(part for part in parts if 1 < len(part) <= 16)
        return candidates
    candidate_text = text.translate(_PUNCT_TRANSLATION)
    candidate_text = re.sub(r"[，。！？；：、（）【】《》“”‘’]", " ", candidate_text)
    return [item for item in re.split(r"\s+", candidate_text) if item.strip()]


def _keywords_from_gliner_entities(
    text: str,
    entities: list[dict[str, Any]],
    *,
    max_keywords: int,
) -> tuple[list[str], list[str]]:
    high_level_keywords: list[str] = []
    low_level_keywords: list[str] = []
    for entity in sorted(
        entities,
        key=lambda item: (
            int(item.get("start", 1_000_000) or 1_000_000),
            -float(item.get("score", 0.0) or 0.0),
        ),
    ):
        keyword = _normalize_keyword(entity.get("text"), text)
        if not keyword:
            continue
        label = str(entity.get("label") or "").strip().lower()
        if label in _HIGH_LEVEL_LABELS:
            high_level_keywords.append(keyword)
        else:
            low_level_keywords.append(keyword)

    if not high_level_keywords and not low_level_keywords:
        return [], []

    combined = _dedupe_limited_keywords(
        [*high_level_keywords, *low_level_keywords],
        max_keywords,
    )
    high_set = {item.casefold() for item in high_level_keywords}
    high_level_keywords = [item for item in combined if item.casefold() in high_set]
    low_level_keywords = [item for item in combined if item.casefold() not in high_set]
    return high_level_keywords, low_level_keywords


async def extract_keywords_with_gliner(
    text: str,
    global_config: dict[str, Any] | None = None,
    *,
    fallback_reason: str | None = None,
) -> KeywordResolution:
    model_name = get_gliner_keyword_model_name(global_config)
    device = get_gliner_keyword_device(global_config)
    reason = fallback_reason or (
        "explicit keywords missing and LLM keyword extraction disabled; "
        "using no-LLM token classification fallback"
    )
    if not keyword_fallback_enabled(global_config):
        return build_gliner_unavailable_resolution(
            reason=f"{reason}; GLiNER fallback disabled",
            model_name=model_name,
            device=device,
            error="RAG_KEYWORD_FALLBACK_ENABLED=false",
        )

    labels = _gliner_labels(global_config)
    threshold = _gliner_threshold(global_config)
    max_keywords = _gliner_max_keywords(global_config)

    try:
        entities = await asyncio.to_thread(
            _predict_gliner_entities,
            text,
            model_name=model_name,
            device=device,
            labels=labels,
            threshold=threshold,
        )
        high_level_keywords, low_level_keywords = _keywords_from_gliner_entities(
            text,
            entities,
            max_keywords=max_keywords,
        )
        if not high_level_keywords and not low_level_keywords:
            candidates = [
                keyword
                for keyword in (
                    _normalize_keyword(item, text)
                    for item in _fallback_keyword_candidates(text)
                )
                if keyword
            ]
            low_level_keywords = _dedupe_limited_keywords(candidates, max_keywords)
            if low_level_keywords:
                reason = f"{reason}; GLiNER returned no entities, used token candidates"
            else:
                reason = f"{reason}; GLiNER returned no keywords"
        return KeywordResolution(
            high_level_keywords=high_level_keywords,
            low_level_keywords=low_level_keywords,
            keyword_source=KEYWORD_SOURCE_GLINER_FALLBACK,
            keyword_strategy=KEYWORD_STRATEGY_TOKEN_CLASSIFICATION,
            keyword_fallback_reason=reason,
            keyword_model=model_name,
            keyword_model_device=device,
        )
    except KeywordExtractorUnavailable as exc:
        logger.warning("GLiNER keyword fallback unavailable: %s", exc)
        return build_gliner_unavailable_resolution(
            reason=f"{reason}; GLiNER fallback unavailable: {exc}",
            model_name=model_name,
            device=device,
            error=str(exc),
        )
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        logger.warning("GLiNER keyword fallback failed: %s", exc)
        return build_gliner_unavailable_resolution(
            reason=f"{reason}; GLiNER fallback failed: {exc}",
            model_name=model_name,
            device=device,
            error=str(exc),
        )
