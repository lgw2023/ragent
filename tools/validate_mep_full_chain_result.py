from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _request_has_explicit_keywords(data: dict[str, Any]) -> bool:
    for key in (
        "high_level_keywords",
        "low_level_keywords",
        "hl_keywords",
        "ll_keywords",
    ):
        if _string_list(data.get(key)):
            return True
    return False


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
    data: dict[str, Any],
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

    if not _request_has_explicit_keywords(data):
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
    retrieval_only = _is_true(data.get("retrieval_only")) or _is_true(
        data.get("only_need_context")
    )
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
            data=data,
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
