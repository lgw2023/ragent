from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class RequestKeywordInfo:
    retrieval_only: bool
    high_level_keywords: list[str]
    low_level_keywords: list[str]

    @property
    def has_explicit_keywords(self) -> bool:
        return bool(self.high_level_keywords or self.low_level_keywords)


def _parse_optional_bool(value: Any, *, field_name: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
    raise ValueError(f"{field_name} must be a boolean value when provided: {value!r}")


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _has_value(value: Any) -> bool:
    return value is not None and value != ""


def _first_with_fallback(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    tertiary: dict[str, Any],
    *keys: str,
) -> Any:
    for source in (primary, secondary, tertiary):
        for key in keys:
            if key in source and _has_value(source.get(key)):
                return source.get(key)
    return None


def _maybe_json_loads(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _merge_process_spec_item(target: dict[str, Any], item: Any) -> None:
    if isinstance(item, str):
        parsed = _maybe_json_loads(item.strip())
        if parsed is not None:
            _merge_process_spec_item(target, parsed)
        elif "=" in item:
            key, value = item.split("=", 1)
            key = key.strip()
            if key:
                target[key] = value.strip()
        return

    if isinstance(item, list):
        for nested_item in item:
            _merge_process_spec_item(target, nested_item)
        return

    if not isinstance(item, dict):
        return

    for key_name in ("key", "name", "field", "fieldName", "paramName"):
        if key_name in item and "value" in item:
            key = str(item[key_name]).strip()
            if key:
                target[key] = item.get("value")
            return
    for key_name, value_name in (
        ("key", "val"),
        ("name", "val"),
        ("fieldName", "fieldValue"),
        ("paramName", "paramValue"),
    ):
        if key_name in item and value_name in item:
            key = str(item[key_name]).strip()
            if key:
                target[key] = item.get(value_name)
            return

    for key, value in item.items():
        if key in {"processSpec", "params", "parameters"}:
            _merge_process_spec_item(target, value)
        else:
            target[key] = value


def _normalize_process_spec(process_spec: Any) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    _merge_process_spec_item(normalized, process_spec)
    return normalized


def _extract_first_file_info(data: dict[str, Any]) -> dict[str, Any]:
    file_info = data.get("fileInfo")
    if isinstance(file_info, list) and file_info and isinstance(file_info[0], dict):
        return file_info[0]
    return {}


def _resolve_source_json_path(file_info: dict[str, Any]) -> Path | None:
    source_image = file_info.get("sourceImage")
    source_path = file_info.get("sourcePath")
    if not isinstance(source_image, str) or not source_image.strip():
        return None

    image_path = Path(source_image).expanduser()
    if not image_path.is_absolute():
        if not isinstance(source_path, str) or not source_path.strip():
            return None
        image_path = Path(source_path).expanduser() / image_path
    image_path = image_path.resolve()
    if image_path.suffix.lower() != ".json" or not image_path.is_file():
        return None
    return image_path


def _load_source_json_fallback(file_info: dict[str, Any]) -> dict[str, Any]:
    source_json_path = _resolve_source_json_path(file_info)
    if source_json_path is None:
        return {}

    with source_json_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"input JSON must be an object: {source_json_path}")
    data_payload = payload.get("data")
    if isinstance(data_payload, dict):
        return data_payload
    return payload


def request_keyword_info(request: dict[str, Any]) -> RequestKeywordInfo:
    data = request.get("data") or {}
    if not isinstance(data, dict):
        return RequestKeywordInfo(
            retrieval_only=False,
            high_level_keywords=[],
            low_level_keywords=[],
        )

    file_info = _extract_first_file_info(data)
    process_spec = _normalize_process_spec(file_info.get("processSpec"))
    source_json = _load_source_json_fallback(file_info)

    retrieval_only = _parse_optional_bool(
        _first_with_fallback(
            data,
            process_spec,
            source_json,
            "retrieval_only",
            "retrievalOnly",
        ),
        field_name="retrieval_only",
    )
    only_need_context = _parse_optional_bool(
        _first_with_fallback(
            data,
            process_spec,
            source_json,
            "only_need_context",
            "onlyNeedContext",
        ),
        field_name="only_need_context",
    )

    high_level_keywords = _string_list(
        _first_with_fallback(
            data,
            process_spec,
            source_json,
            "high_level_keywords",
            "highLevelKeywords",
            "hl_keywords",
            "hlKeywords",
        )
    )
    low_level_keywords = _string_list(
        _first_with_fallback(
            data,
            process_spec,
            source_json,
            "low_level_keywords",
            "lowLevelKeywords",
            "ll_keywords",
            "llKeywords",
        )
    )

    return RequestKeywordInfo(
        retrieval_only=bool(retrieval_only) or bool(only_need_context),
        high_level_keywords=high_level_keywords,
        low_level_keywords=low_level_keywords,
    )


def _resolve_request_path(container_test_dir: Path, request_item: str) -> Path:
    request_path = Path(request_item)
    if not request_path.is_absolute():
        request_path = container_test_dir / "example" / "mep_requests" / request_item
    return request_path.resolve()


def summarize_requests(container_test_dir: Path, request_items: str) -> dict[str, Any]:
    items = [item.strip() for item in request_items.split(",") if item.strip()]
    requests: list[dict[str, Any]] = []
    requests_require_llm = False
    requests_have_retrieval_only = False
    for request_item in items:
        request_path = _resolve_request_path(container_test_dir, request_item)
        request = json.loads(request_path.read_text(encoding="utf-8"))
        info = request_keyword_info(request)
        requests_require_llm = requests_require_llm or not info.retrieval_only
        requests_have_retrieval_only = requests_have_retrieval_only or info.retrieval_only
        requests.append(
            {
                "request": str(request_path),
                "retrieval_only": info.retrieval_only,
                "has_explicit_keywords": info.has_explicit_keywords,
            }
        )
    return {
        "requests_require_llm": requests_require_llm,
        "requests_have_retrieval_only": requests_have_retrieval_only,
        "requests": requests,
    }


def _load_generated_payload(
    *,
    data: dict[str, Any],
    recommend: dict[str, Any],
    retrieval_only: bool,
) -> tuple[str, dict[str, Any] | None, Path | None]:
    retrieval_result = None
    file_info = data.get("fileInfo")
    generate_path = data.get("generatePath")
    if (
        not generate_path
        and isinstance(file_info, list)
        and file_info
        and isinstance(file_info[0], dict)
    ):
        generate_path = file_info[0].get("generatePath")

    answer = ""
    gen_json_path = None
    if isinstance(generate_path, str) and generate_path.strip():
        gen_json_path = Path(generate_path).expanduser().resolve() / "gen.json"
        if not gen_json_path.is_file():
            raise SystemExit(f"expected generated result file is missing: {gen_json_path}")
        generated = json.loads(gen_json_path.read_text(encoding="utf-8"))
        if str(generated.get("code")) != "0":
            raise SystemExit(f"generated payload code is not 0: {generated}")
        answer = str(generated.get("answer") or "").strip()
        if retrieval_only:
            retrieval_result = generated.get("retrieval_result")
    else:
        content = recommend.get("content") or []
        if content and isinstance(content[0], dict):
            answer = str(content[0].get("answer") or "").strip()
            if retrieval_only:
                retrieval_result = content[0].get("retrieval_result")
    return answer, retrieval_result, gen_json_path


def _validate_retrieval_only_keywords(
    *,
    retrieval_result: dict[str, Any],
    request_info: RequestKeywordInfo,
) -> None:
    keyword_model_error = retrieval_result.get("keyword_model_error")
    if keyword_model_error not in (None, "", []):
        raise SystemExit(f"retrieval-only keyword_model_error is not empty: {keyword_model_error!r}")

    high_level_keywords = _string_list(retrieval_result.get("high_level_keywords"))
    low_level_keywords = _string_list(retrieval_result.get("low_level_keywords"))
    if not high_level_keywords and not low_level_keywords:
        raise SystemExit(
            "retrieval-only GLiNER fallback returned no high_level_keywords or "
            "low_level_keywords"
        )

    if not request_info.has_explicit_keywords:
        if retrieval_result.get("keyword_source") != "gliner_fallback":
            raise SystemExit(
                "retrieval-only request without explicit keywords did not use "
                f"GLiNER fallback: keyword_source={retrieval_result.get('keyword_source')!r}"
            )
        if retrieval_result.get("keyword_strategy") != "token_classification_fallback":
            raise SystemExit(
                "retrieval-only request without explicit keywords used unexpected "
                f"keyword_strategy={retrieval_result.get('keyword_strategy')!r}"
            )


def validate_result(stdout_path: Path, request_work: Path) -> dict[str, Any]:
    result = json.loads(stdout_path.read_text(encoding="utf-8"))
    request = json.loads(request_work.read_text(encoding="utf-8"))
    recommend = result.get("recommendResult")
    if not isinstance(recommend, dict):
        raise SystemExit(f"missing recommendResult in {stdout_path}")
    code = str(recommend.get("code"))
    if code != "0":
        raise SystemExit(f"recommendResult.code={code}, des={recommend.get('des')!r}")

    data = request.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    request_info = request_keyword_info(request)
    retrieval_only = request_info.retrieval_only
    answer, retrieval_result, gen_json_path = _load_generated_payload(
        data=data,
        recommend=recommend,
        retrieval_only=retrieval_only,
    )

    if retrieval_only:
        if not isinstance(retrieval_result, dict):
            raise SystemExit("retrieval-only payload is missing retrieval_result")
        final_context_text = str(retrieval_result.get("final_context_text") or "").strip()
        final_context_chunks = retrieval_result.get("final_context_chunks") or []
        if not final_context_text and not final_context_chunks:
            raise SystemExit("retrieval-only payload has no final context")
        _validate_retrieval_only_keywords(
            retrieval_result=retrieval_result,
            request_info=request_info,
        )
    elif not answer:
        raise SystemExit("MEP chain returned code=0 but answer is empty")

    return {
        "recommendResult.code": code,
        "recommendResult.length": recommend.get("length"),
        "retrieval_only": retrieval_only,
        "keyword_source": (
            retrieval_result.get("keyword_source")
            if isinstance(retrieval_result, dict)
            else None
        ),
        "keyword_strategy": (
            retrieval_result.get("keyword_strategy")
            if isinstance(retrieval_result, dict)
            else None
        ),
        "keyword_model": (
            retrieval_result.get("keyword_model")
            if isinstance(retrieval_result, dict)
            else None
        ),
        "high_level_keywords": (
            retrieval_result.get("high_level_keywords")
            if isinstance(retrieval_result, dict)
            else None
        ),
        "low_level_keywords": (
            retrieval_result.get("low_level_keywords")
            if isinstance(retrieval_result, dict)
            else None
        ),
        "answer_preview": answer[:160],
        "gen_json": str(gen_json_path) if gen_json_path else None,
    }


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] in {
        "request-summary",
        "request-requires-llm",
        "request-has-retrieval-only",
    }:
        command = sys.argv[1]
        parser = argparse.ArgumentParser(
            description="Inspect MEP full-chain request flags."
        )
        parser.add_argument("command")
        parser.add_argument("container_test_dir", type=Path)
        parser.add_argument("requests")
        args = parser.parse_args()
        summary = summarize_requests(
            args.container_test_dir.expanduser().resolve(),
            args.requests,
        )
        if command == "request-requires-llm":
            print("true" if summary["requests_require_llm"] else "false")
        elif command == "request-has-retrieval-only":
            print("true" if summary["requests_have_retrieval_only"] else "false")
        else:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    parser = argparse.ArgumentParser(
        description="Validate MEP full-chain stdout and generated payload."
    )
    parser.add_argument("stdout_path", type=Path)
    parser.add_argument("request_work", type=Path)
    args = parser.parse_args()

    summary = validate_result(
        args.stdout_path.expanduser().resolve(),
        args.request_work.expanduser().resolve(),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
