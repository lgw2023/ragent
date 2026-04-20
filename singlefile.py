import sys
import asyncio
import os
import logging
import json
import re
from collections import Counter
from contextlib import contextmanager
from typing import Any
if __package__:
    # Package execution (e.g., python -m ragent.singlefile)
    from .integrations import (
        wide_table_insert,
        pdf_insert,
        build_enhanced_md,
        index_md_to_rag,
        get_mineru_output_subdirs_for_lookup,
        inference_one_hop_problem,
        inference_multi_hop_problem,
        trace_multi_hop_problem,
        trace_one_hop_problem,
    )
    from .ragent.utils import is_exception_logged, log_exception, logger
else:
    # Script execution (e.g., python singlefile.py ...)
    from integrations import (
        wide_table_insert,
        pdf_insert,
        build_enhanced_md,
        index_md_to_rag,
        get_mineru_output_subdirs_for_lookup,
        inference_one_hop_problem,
        inference_multi_hop_problem,
        trace_multi_hop_problem,
        trace_one_hop_problem,
    )
    from ragent.utils import is_exception_logged, log_exception, logger

_IS_TTY = sys.stdout.isatty()
_USE_COLOR = _IS_TTY and os.getenv("NO_COLOR") is None
_USE_MARKDOWN = not _IS_TTY
_RESET = "\033[0m" if _USE_COLOR else ""
_BOLD = "\033[1m" if _USE_COLOR else ""
_DIM = "\033[2m" if _USE_COLOR else ""
_CYAN = "\033[36m" if _USE_COLOR else ""
_BLUE = "\033[34m" if _USE_COLOR else ""
_GREEN = "\033[32m" if _USE_COLOR else ""
_YELLOW = "\033[33m" if _USE_COLOR else ""
_MAGENTA = "\033[35m" if _USE_COLOR else ""
_WHITE = "\033[37m" if _USE_COLOR else ""


def _style(text: str, *codes: str) -> str:
    if not _USE_COLOR:
        return text
    return "".join(codes) + text + _RESET


def _label(text: str) -> str:
    return _style(text, _BOLD, _CYAN)


def _muted(text: str) -> str:
    return _style(text, _DIM)


def _accent(text: str) -> str:
    return _style(text, _BOLD, _BLUE)


def _success(text: str) -> str:
    return _style(text, _BOLD, _GREEN)


def _warn(text: str) -> str:
    return _style(text, _BOLD, _YELLOW)


def _section_rule(char: str = "=") -> str:
    return _style(char * 78, _DIM, _WHITE)


def _markdown_heading(level: int, title: str) -> str:
    normalized_level = min(max(level, 1), 6)
    return f"{'#' * normalized_level} {title}"


def _print_key_value(label: str, value: Any):
    if _USE_MARKDOWN:
        normalized_label = label.strip().strip("[]")
        if normalized_label.endswith(":"):
            normalized_label = normalized_label[:-1]
        print(f"- {normalized_label}: {value}")
        return
    print(f"{_label(label)} {value}")


def _print_markdown_entry(title: str, meta_lines: list[str] | None = None, body: str | None = None, level: int = 4):
    print(_markdown_heading(level, title))
    if meta_lines:
        for line in meta_lines:
            print(f"- {line}")
    if body is not None:
        body_text = str(body).strip("\n")
        if body_text:
            print()
            print(body_text)
    print()

_WIDE_TABLE_EXTENSIONS = {".csv", ".tsv", ".txt", ".xlsx", ".xlsm"}


def _is_wide_table_path(file_path: str) -> bool:
    return os.path.splitext(file_path)[1].lower() in _WIDE_TABLE_EXTENSIONS


def _cli_excepthook(exc_type, exc, tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    if not is_exception_logged(exc):
        log_exception(None, exc)


@contextmanager
def _temporary_log_level(logger_names: list[str], level: int):
    """Temporarily raise selected logger levels during onehop query."""
    saved = []
    try:
        for name in logger_names:
            target_logger = logging.getLogger(name)
            saved.append((target_logger, target_logger.level))
            target_logger.setLevel(level)
        yield
    finally:
        for target_logger, original_level in saved:
            target_logger.setLevel(original_level)


def _print_stage_header(title: str, level: int = 2):
    if _USE_MARKDOWN:
        print(f"\n{_markdown_heading(level, title)}\n")
        return
    print(f"\n{_section_rule('=')}")
    print(_accent(title))
    print(_section_rule('='))


def _print_subsection_header(title: str, level: int = 3):
    if _USE_MARKDOWN:
        print(f"\n{_markdown_heading(level, title)}\n")
        return
    print(f"\n{_section_rule('-')}")
    print(_style(title, _BOLD, _MAGENTA))
    print(_section_rule('-'))


def _print_block_header(title: str, level: int = 3):
    if _USE_MARKDOWN:
        print(f"\n{_markdown_heading(level, title)}\n")
        return
    print(_style(f"[{title}]", _BOLD, _YELLOW))


def _print_item_box(lines: list[str], color: str = _DIM):
    if not lines:
        return
    if _USE_MARKDOWN:
        for line in lines:
            print(f"- {line}")
        print()
        return
    prefix = _style("  | ", color)
    for line in lines:
        print(f"{prefix}{line}")


def _print_multiline_value(label: str, value: str, color: str = _WHITE):
    lines = value.splitlines() or [""]
    _print_item_box([f"{label}: {lines[0]}", *lines[1:]], color)


def _print_trace_list(title: str, items: list[dict], kind: str, heading_level: int = 3):
    _print_block_header(title, level=heading_level)
    if not items:
        print("- 无" if _USE_MARKDOWN else _muted("  - 无  "))
        return
    if isinstance(items, (str, dict)):
        items = [items]
    for item in items:
        if kind == "keyword":
            if _USE_MARKDOWN:
                print(f"- {str(item)}")
            else:
                print(f"  - {_style(str(item), _GREEN)}  ")
            continue
        if not isinstance(item, dict):
            _print_item_box([str(item)], _WHITE)
            continue
        source_label = item.get("source_ref") or item.get("source_refs_display") or item.get("file_path", "unknown_source")
        if _USE_MARKDOWN:
            if kind == "entity":
                _print_markdown_entry(
                    str(item["entity"]),
                    [
                        f"type: {item['type']}",
                        f"source: {source_label}",
                    ],
                    item.get("preview"),
                    level=min(heading_level + 1, 6),
                )
                continue
            if kind == "relation":
                _print_markdown_entry(
                    f"{item['entity1']} -> {item['entity2']}",
                    [f"source: {source_label}"],
                    item.get("preview"),
                    level=min(heading_level + 1, 6),
                )
                continue
            if kind == "chunk":
                meta_lines = [f"source: {source_label}"]
                if "source" in item:
                    meta_lines.append(f"recall_type: {item['source']}")
                if item.get("score") is not None:
                    meta_lines.append(f"score: {item['score']}")
                meta_lines.append(f"chunk_id: {item.get('chunk_id', 'n/a')}")
                _print_markdown_entry(
                    f"候选 #{item['rank']}",
                    meta_lines,
                    item.get("preview"),
                    level=min(heading_level + 1, 6),
                )
                continue
            if kind == "final_chunk":
                meta_lines = [f"source: {source_label}"]
                if "source" in item:
                    meta_lines.append(f"recall_type: {item['source']}")
                meta_lines.append(f"chunk_id: {item.get('chunk_id', 'n/a')}")
                _print_markdown_entry(
                    f"证据 #{item['rank']}",
                    meta_lines,
                    item.get("preview"),
                    level=min(heading_level + 1, 6),
                )
                continue
            if kind == "rerank_chunk":
                meta_lines = [f"source: {source_label}"]
                if "source" in item:
                    meta_lines.append(f"recall_type: {item['source']}")
                if item.get("rerank_score") is not None:
                    meta_lines.append(f"rerank_score: {item['rerank_score']}")
                meta_lines.append(f"chunk_id: {item.get('chunk_id', 'n/a')}")
                _print_markdown_entry(
                    f"候选 #{item['rank']}",
                    meta_lines,
                    item.get("preview"),
                    level=min(heading_level + 1, 6),
                )
                continue
            if kind == "context_chunk":
                _print_markdown_entry(
                    f"Chunk {item.get('id', 'n/a')}",
                    [f"source: {source_label}"],
                    _truncate_console(item.get("content", ""), limit=320),
                    level=min(heading_level + 1, 6),
                )
                continue
        if kind == "entity":
            _print_item_box(
                [
                    f"{_style(item['entity'], _BOLD, _GREEN)} | type={item['type']} | source={source_label}",
                    item["preview"],
                ],
                _GREEN,
            )
            continue
        if kind == "relation":
            _print_item_box(
                [
                    f"{_style(item['entity1'], _BOLD, _BLUE)} -> {_style(item['entity2'], _BOLD, _BLUE)} | source={source_label}",
                    item["preview"],
                ],
                _BLUE,
            )
            continue
        if kind == "chunk":
            score = item.get("score")
            score_text = f" | score={score}" if score is not None else ""
            source_text = f" | source={item['source']}" if "source" in item else ""
            _print_item_box(
                [
                    f"#{item['rank']}{source_text}{score_text} | {source_label}",
                    f"chunk_id={item.get('chunk_id', 'n/a')}",
                    item["preview"],
                ],
                _CYAN,
            )
            continue
        if kind == "final_chunk":
            source_text = f" | source={item['source']}" if "source" in item else ""
            _print_item_box(
                [
                    f"#{item['rank']}{source_text} | {source_label}",
                    f"chunk_id={item.get('chunk_id', 'n/a')}",
                    item["preview"],
                ],
                _MAGENTA,
            )
            continue
        if kind == "rerank_chunk":
            score = item.get("rerank_score")
            score_text = f" | rerank_score={score}" if score is not None else ""
            source_text = f" | source={item['source']}" if "source" in item else ""
            _print_item_box(
                [
                    f"#{item['rank']}{source_text}{score_text} | {source_label}",
                    f"chunk_id={item.get('chunk_id', 'n/a')}",
                    item["preview"],
                ],
                _YELLOW,
            )
            continue
        if kind == "context_chunk":
            _print_item_box(
                [
                    f"#{item.get('id', 'n/a')} | {source_label}",
                    _truncate_console(item.get("content", ""), limit=320),
                ],
                _WHITE,
            )


def _parse_titled_sections(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"(?m)^---([^\n]+?)---\s*$")
    matches = list(pattern.finditer(text))
    if not matches:
        stripped = text.strip()
        return [("Content", stripped)] if stripped else []

    sections = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append((title, body))
    return sections


def _extract_fenced_json(body: str):
    match = re.search(r"```json\s*(.*?)\s*```", body, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _extract_plain_json(body: str):
    stripped = body.strip()
    if not stripped:
        return None
    if not ((stripped.startswith("[") and stripped.endswith("]")) or (stripped.startswith("{") and stripped.endswith("}"))):
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _extract_section_json(body: str):
    return _extract_fenced_json(body) or _extract_plain_json(body)


def _print_structured_json_item(item: dict, color: str = _WHITE):
    if _USE_MARKDOWN:
        multiline_fields = []
        for key, value in item.items():
            if isinstance(value, str) and "\n" in value:
                multiline_fields.append((key, value))
            else:
                print(f"- {key}: {value}")
        for key, value in multiline_fields:
            print()
            print(f"**{key}**")
            print()
            print(str(value).strip("\n") or _muted("(空)"))
        print()
        return
    lines = []
    for key, value in item.items():
        if isinstance(value, str) and "\n" in value:
            lines.append(f"{key}:")
            lines.extend(value.splitlines())
        else:
            lines.append(f"{key}: {value}")
    _print_item_box(lines, color)


def _print_document_chunks_json(parsed_json: Any):
    if not isinstance(parsed_json, list):
        _print_item_box([str(parsed_json)], _WHITE)
        return
    if not parsed_json:
        print(_muted("(空列表)"))
        return
    for item in parsed_json:
        if isinstance(item, dict):
            if _USE_MARKDOWN:
                meta_lines = [f"id: {item.get('id', 'n/a')}"]
                body_sections = []
                for key, value in item.items():
                    if key == "id":
                        continue
                    if key == "content":
                        body_sections.append(("content", str(value)))
                        continue
                    if isinstance(value, str) and "\n" in value:
                        body_sections.append((key, value))
                    else:
                        meta_lines.append(f"{key}: {value}")
                _print_markdown_entry(
                    f"Document Chunk {item.get('id', 'n/a')}",
                    meta_lines,
                    None,
                    level=4,
                )
                for key, value in body_sections:
                    print(f"**{key}**")
                    print()
                    print(str(value).strip("\n") or _muted("(空)"))
                    print()
                continue
            lines = [f"id: {item.get('id', 'n/a')}"]
            for key, value in item.items():
                if key == "id":
                    continue
                if key == "content":
                    lines.append("content:")
                    lines.extend(str(value).splitlines() or [""])
                    continue
                lines.append(f"{key}: {value}")
            _print_item_box(lines, _WHITE)
        else:
            _print_item_box([str(item)], _WHITE)


def _print_structured_section(title: str, body: str, heading_level: int = 3):
    _print_subsection_header(title, level=heading_level)
    parsed_json = _extract_section_json(body)
    if "Document Chunks" in title and parsed_json is not None:
        _print_document_chunks_json(parsed_json)
        return
    if parsed_json is None:
        if body:
            print(body)
        else:
            print(_muted("(空)"))
        return

    if isinstance(parsed_json, list):
        if not parsed_json:
            print(_muted("(空列表)"))
            return
        for item in parsed_json:
            if isinstance(item, dict):
                _print_structured_json_item(item)
            else:
                _print_item_box([str(item)], _WHITE)
        return

    if isinstance(parsed_json, dict):
        _print_structured_json_item(parsed_json)
        return

    print(parsed_json)


def _print_structured_text_sections(text: str, heading_level: int = 3):
    sections = _parse_titled_sections(text)
    if not sections:
        print(_muted("(空)"))
        return
    for title, body in sections:
        _print_structured_section(title, body, heading_level=heading_level)


_MISSING = object()


def _stage_timing_seconds(item: dict | None):
    if not isinstance(item, dict):
        return None
    seconds = item.get("seconds")
    if isinstance(seconds, (int, float)):
        return seconds
    return None


def _sum_stage_timing_seconds(items: list[dict | None]):
    seconds_values = [_stage_timing_seconds(item) for item in items]
    seconds_values = [seconds for seconds in seconds_values if seconds is not None]
    if not seconds_values:
        return None
    return sum(seconds_values)


def _print_timing_row(label: str, seconds=_MISSING, depth: int = 0):
    indent = "  " * depth if _USE_MARKDOWN else "  " * (depth + 1)
    if seconds is _MISSING:
        print(f"{indent}- {label}")
        return
    if isinstance(seconds, (int, float)):
        seconds_text = _style(f"{seconds:.3f}s", _BOLD, _CYAN)
    else:
        seconds_text = _muted("n/a")
    print(f"{indent}- {label}: {seconds_text}")


def _print_timing_leaf(
    timings_by_stage: dict[str, dict],
    printed_stages: set[str],
    stage: str,
    depth: int,
    label: str | None = None,
) -> dict | None:
    item = timings_by_stage.get(stage)
    if not item:
        return None
    printed_stages.add(stage)
    _print_timing_row(
        label or item.get("label") or item.get("stage") or "unknown",
        _stage_timing_seconds(item),
        depth,
    )
    return item


def _print_timing_computed_group(
    label: str,
    child_items: list[dict | None],
    depth: int,
) -> bool:
    present_items = [item for item in child_items if item]
    if not present_items:
        return False
    _print_timing_row(label, _sum_stage_timing_seconds(present_items), depth)
    return True


def _print_onehop_timing_tree(stage_timings: list[dict]) -> bool:
    timings_by_stage = {
        str(item.get("stage")): item
        for item in stage_timings
        if isinstance(item, dict) and item.get("stage")
    }
    printed_stages: set[str] = set()
    printed_any = False

    initialization_children = [
        timings_by_stage.get(stage)
        for stage in (
            "startup_model_check",
            "rag_object_setup",
            "storage_initialization",
            "pipeline_status_initialization",
        )
    ]
    initialization_total = timings_by_stage.get("rag_initialization_total")
    if initialization_total:
        printed_any = True
        printed_stages.add("rag_initialization_total")
        _print_timing_row(
            initialization_total.get("label") or "查询前初始化总耗时",
            _stage_timing_seconds(initialization_total),
            0,
        )
        for stage in (
            "startup_model_check",
            "rag_object_setup",
            "storage_initialization",
            "pipeline_status_initialization",
        ):
            _print_timing_leaf(timings_by_stage, printed_stages, stage, 1)
    elif any(initialization_children):
        printed_any = True
        _print_timing_computed_group("查询前初始化小计", initialization_children, 0)
        for stage in (
            "startup_model_check",
            "rag_object_setup",
            "storage_initialization",
            "pipeline_status_initialization",
        ):
            _print_timing_leaf(timings_by_stage, printed_stages, stage, 1)

    onehop_total = timings_by_stage.get("onehop_total")
    if onehop_total:
        printed_any = True
        printed_stages.add("onehop_total")
        _print_timing_row(
            onehop_total.get("label") or "OneHop 查询总耗时",
            _stage_timing_seconds(onehop_total),
            0,
        )
        query_depth = 1
    else:
        query_depth = 0

    _print_timing_leaf(timings_by_stage, printed_stages, "query_cache_lookup", query_depth)

    hybrid_total = timings_by_stage.get("hybrid_retrieval_total")
    if hybrid_total:
        printed_any = True
        printed_stages.add("hybrid_retrieval_total")
        _print_timing_row(
            hybrid_total.get("label") or "混合检索总耗时",
            _stage_timing_seconds(hybrid_total),
            query_depth,
        )

        recall_fusion_stages = (
            "vector_retrieval",
            "keyword_extraction",
            "graph_entity_hits",
            "graph_relation_hits",
            "graph_chunk_rescoring",
            "candidate_merge",
        )
        recall_fusion_items = [
            timings_by_stage.get(stage)
            for stage in recall_fusion_stages
        ]
        if _print_timing_computed_group("召回与融合小计", recall_fusion_items, query_depth + 1):
            _print_timing_leaf(
                timings_by_stage,
                printed_stages,
                "vector_retrieval",
                query_depth + 2,
                "Chunk 向量检索",
            )
            _print_timing_leaf(
                timings_by_stage,
                printed_stages,
                "keyword_extraction",
                query_depth + 2,
            )

            graph_hit_items = [
                timings_by_stage.get("graph_entity_hits"),
                timings_by_stage.get("graph_relation_hits"),
            ]
            if _print_timing_computed_group("图谱命中小计", graph_hit_items, query_depth + 2):
                _print_timing_leaf(
                    timings_by_stage,
                    printed_stages,
                    "graph_entity_hits",
                    query_depth + 3,
                    "实体",
                )
                _print_timing_leaf(
                    timings_by_stage,
                    printed_stages,
                    "graph_relation_hits",
                    query_depth + 3,
                    "关系",
                )

            _print_timing_leaf(
                timings_by_stage,
                printed_stages,
                "graph_chunk_rescoring",
                query_depth + 2,
                "图谱候选重打分",
            )
            _print_timing_leaf(
                timings_by_stage,
                printed_stages,
                "candidate_merge",
                query_depth + 2,
                "候选融合",
            )

        _print_timing_leaf(timings_by_stage, printed_stages, "rerank", query_depth + 1)
        _print_timing_leaf(
            timings_by_stage,
            printed_stages,
            "final_context_selection",
            query_depth + 1,
        )
    else:
        _print_timing_leaf(timings_by_stage, printed_stages, "keyword_extraction", query_depth)
        graph_hit_items = [
            timings_by_stage.get("graph_entity_hits"),
            timings_by_stage.get("graph_relation_hits"),
        ]
        if _print_timing_computed_group("图谱命中小计", graph_hit_items, query_depth):
            printed_any = True
            _print_timing_leaf(
                timings_by_stage,
                printed_stages,
                "graph_entity_hits",
                query_depth + 1,
                "实体",
            )
            _print_timing_leaf(
                timings_by_stage,
                printed_stages,
                "graph_relation_hits",
                query_depth + 1,
                "关系",
            )

        graph_context_total = timings_by_stage.get("graph_context_total")
        if graph_context_total:
            printed_any = True
            printed_stages.add("graph_context_total")
            _print_timing_row(
                graph_context_total.get("label") or "图谱上下文构建总耗时",
                _stage_timing_seconds(graph_context_total),
                query_depth,
            )
            graph_recall_items = [
                timings_by_stage.get("graph_context_entities"),
                timings_by_stage.get("graph_context_relations"),
                timings_by_stage.get("graph_context_chunk_lookup"),
            ]
            if _print_timing_computed_group("图谱上下文补召回小计", graph_recall_items, query_depth + 1):
                _print_timing_leaf(
                    timings_by_stage,
                    printed_stages,
                    "graph_context_entities",
                    query_depth + 2,
                    "实体",
                )
                _print_timing_leaf(
                    timings_by_stage,
                    printed_stages,
                    "graph_context_relations",
                    query_depth + 2,
                    "关系",
                )
                _print_timing_leaf(
                    timings_by_stage,
                    printed_stages,
                    "graph_context_chunk_lookup",
                    query_depth + 2,
                    "文档块",
                )

            graph_context_post_items = [
                timings_by_stage.get("graph_context_structured_pruning"),
                timings_by_stage.get("graph_context_chunk_postprocess"),
                timings_by_stage.get("graph_context_serialize"),
            ]
            if _print_timing_computed_group("图谱上下文整理小计", graph_context_post_items, query_depth + 1):
                _print_timing_leaf(
                    timings_by_stage,
                    printed_stages,
                    "graph_context_structured_pruning",
                    query_depth + 2,
                    "实体关系裁剪",
                )
                _print_timing_leaf(
                    timings_by_stage,
                    printed_stages,
                    "graph_context_chunk_postprocess",
                    query_depth + 2,
                    "Chunk 重排与截断",
                )
                _print_timing_leaf(
                    timings_by_stage,
                    printed_stages,
                    "graph_context_serialize",
                    query_depth + 2,
                    "序列化",
                )

    for stage in (
        "prompt_assembly",
        "answer_cache_hit",
        "answer_generation",
        "answer_polish",
    ):
        if _print_timing_leaf(timings_by_stage, printed_stages, stage, query_depth):
            printed_any = True

    remaining_items = [
        item
        for item in stage_timings
        if isinstance(item, dict)
        and item.get("stage")
        and str(item.get("stage")) not in printed_stages
    ]
    if remaining_items:
        printed_any = True
        _print_timing_row("其他计时", depth=0)
        for item in remaining_items:
            printed_stages.add(str(item.get("stage")))
            _print_timing_row(
                item.get("label") or item.get("stage") or "unknown",
                _stage_timing_seconds(item),
                1,
            )

    return printed_any


def _print_stage_timing_summary(trace: dict):
    stage_timings = trace.get("stage_timings", [])
    if not stage_timings:
        print(_muted("(未记录阶段耗时)"))
        return
    if _print_onehop_timing_tree(stage_timings):
        return
    for item in stage_timings:
        label = item.get("label") or item.get("stage") or "unknown"
        seconds = item.get("seconds")
        if isinstance(seconds, (int, float)):
            prefix = "- " if _USE_MARKDOWN else "  - "
            print(f"{prefix}{label}: {_style(f'{seconds:.3f}s', _BOLD, _CYAN)}")
        else:
            prefix = "- " if _USE_MARKDOWN else "  - "
            print(f"{prefix}{label}: {_muted('n/a')}")


def _format_timing_seconds(seconds: Any) -> str:
    if isinstance(seconds, (int, float)):
        return f"{seconds:.3f}s"
    return "n/a"


def _usage_counts(event: dict) -> tuple[int, int, int]:
    usage = event.get("usage") or {}
    return (
        int(usage.get("input_tokens", 0) or 0),
        int(usage.get("output_tokens", 0) or 0),
        int(usage.get("total_tokens", 0) or 0),
    )


def _event_elapsed_seconds(event: dict):
    extra = event.get("extra") or {}
    elapsed = extra.get("elapsed_seconds")
    if isinstance(elapsed, (int, float)):
        return float(elapsed)
    return None


def _model_stage_label(event: dict) -> tuple[str, str]:
    extra = event.get("extra") or {}
    stage = str(extra.get("stage") or "unknown_model_stage")
    label = str(extra.get("stage_label") or "未标注阶段")
    return stage, label


def _print_model_call_summary(trace: dict, heading_level: int = 3) -> bool:
    model_usage = trace.get("model_usage") or {}
    events = [
        event
        for event in model_usage.get("events", [])
        if isinstance(event, dict)
    ]
    if not events:
        return False

    stage_timings = {
        str(item.get("stage")): item
        for item in trace.get("stage_timings", [])
        if isinstance(item, dict) and item.get("stage")
    }
    stage_order = [
        str(item.get("stage"))
        for item in trace.get("stage_timings", [])
        if isinstance(item, dict) and item.get("stage")
    ]

    _print_block_header("模型调用概览", level=heading_level)
    aggregate = model_usage.get("aggregate", {})
    if aggregate:
        total_calls = sum(
            int((aggregate.get(model_type) or {}).get("call_count", 0) or 0)
            for model_type in ("chat", "embedding", "rerank", "image")
        )
        print(f"- 记录到模型调用: {_style(str(total_calls), _BOLD, _CYAN)} 次")
        print("- 说明: 阶段耗时是墙钟时间；模型调用耗时合计是单次调用耗时求和，并发调用时可能大于阶段耗时。")
        for model_type in ("chat", "embedding", "rerank", "image"):
            bucket = aggregate.get(model_type) or {}
            call_count = int(bucket.get("call_count", 0) or 0)
            if not call_count:
                continue
            models = ", ".join(sorted((bucket.get("models") or {}).keys())) or "unknown_model"
            print(
                f"  - {model_type}: {call_count} 次 | models: {models} | "
                f"tokens in/out/total: {bucket.get('input_tokens', 0)}/"
                f"{bucket.get('output_tokens', 0)}/{bucket.get('total_tokens', 0)}"
            )

    grouped: dict[str, dict[str, Any]] = {}
    for event in events:
        stage, label = _model_stage_label(event)
        stage_group = grouped.setdefault(
            stage,
            {
                "label": label,
                "models": {},
            },
        )
        model_key = (
            str(event.get("model_type") or "unknown_type"),
            str(event.get("model_name") or "unknown_model"),
        )
        model_group = stage_group["models"].setdefault(
            model_key,
            {
                "call_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "elapsed_seconds": 0.0,
                "missing_elapsed_count": 0,
                "extra_counts": Counter(),
            },
        )
        input_tokens, output_tokens, total_tokens = _usage_counts(event)
        model_group["call_count"] += 1
        model_group["input_tokens"] += input_tokens
        model_group["output_tokens"] += output_tokens
        model_group["total_tokens"] += total_tokens
        elapsed = _event_elapsed_seconds(event)
        if elapsed is None:
            model_group["missing_elapsed_count"] += 1
        else:
            model_group["elapsed_seconds"] += elapsed
        extra = event.get("extra") or {}
        if extra.get("batch_size") is not None:
            model_group["extra_counts"]["batch_size"] += int(extra.get("batch_size") or 0)
        if extra.get("document_count") is not None:
            model_group["extra_counts"]["document_count"] += int(extra.get("document_count") or 0)

    def stage_sort_key(stage: str) -> tuple[int, str]:
        try:
            return (stage_order.index(stage), stage)
        except ValueError:
            return (len(stage_order), stage)

    _print_block_header("模型调用按阶段", level=heading_level)
    for stage in sorted(grouped, key=stage_sort_key):
        stage_group = grouped[stage]
        timing = stage_timings.get(stage)
        stage_seconds = _stage_timing_seconds(timing)
        stage_header = stage_group["label"]
        if stage_seconds is not None:
            stage_header = f"{stage_header}（阶段耗时 {_format_timing_seconds(stage_seconds)}）"
        print(f"- {stage_header}")
        for (model_type, model_name), model_group in sorted(stage_group["models"].items()):
            elapsed_text = _format_timing_seconds(model_group["elapsed_seconds"])
            if model_group["missing_elapsed_count"]:
                elapsed_text = f"{elapsed_text}，另有 {model_group['missing_elapsed_count']} 次未返回耗时"
            extra_text_parts = []
            if model_group["extra_counts"].get("batch_size"):
                extra_text_parts.append(f"batch={model_group['extra_counts']['batch_size']}")
            if model_group["extra_counts"].get("document_count"):
                extra_text_parts.append(f"docs={model_group['extra_counts']['document_count']}")
            extra_text = f" | {'; '.join(extra_text_parts)}" if extra_text_parts else ""
            print(
                f"  - {model_type} / {model_name}: {model_group['call_count']} 次 | "
                f"模型调用耗时合计 {elapsed_text} | "
                f"tokens in/out/total: {model_group['input_tokens']}/"
                f"{model_group['output_tokens']}/{model_group['total_tokens']}"
                f"{extra_text}"
            )

    _print_block_header("模型调用明细", level=heading_level)
    for index, event in enumerate(events, start=1):
        _, stage_label = _model_stage_label(event)
        input_tokens, output_tokens, total_tokens = _usage_counts(event)
        extra = event.get("extra") or {}
        detail_parts = [
            f"耗时 {_format_timing_seconds(_event_elapsed_seconds(event))}",
            f"tokens {input_tokens}/{output_tokens}/{total_tokens}",
        ]
        if extra.get("batch_size") is not None:
            detail_parts.append(f"batch={extra.get('batch_size')}")
        if extra.get("document_count") is not None:
            detail_parts.append(f"docs={extra.get('document_count')}")
        prefix = f"{index}. " if _USE_MARKDOWN else f"  {index}. "
        print(
            f"{prefix}[{stage_label}] {event.get('model_type')} / "
            f"{event.get('model_name')}: " + " | ".join(detail_parts)
        )

    return True


def _print_onehop_trace(trace: dict, header: str = "OneHop 图谱检索推理过程", header_level: int = 1):
    stage_level = min(header_level + 1, 6)
    block_level = min(stage_level + 1, 6)

    _print_stage_header(header, level=header_level)
    _print_key_value("[输入问题]", trace["query"])
    _print_key_value("[检索模式]", _style(trace["mode"], _BOLD, _GREEN))

    _print_stage_header("阶段 0 / 耗时概览", level=stage_level)
    _print_stage_timing_summary(trace)
    _print_model_call_summary(trace, heading_level=block_level)

    _print_stage_header("阶段 1 / 关键词提取", level=stage_level)
    _print_trace_list("高层关键词", trace.get("high_level_keywords", []), "keyword", heading_level=block_level)
    _print_trace_list("低层关键词", trace.get("low_level_keywords", []), "keyword", heading_level=block_level)

    _print_stage_header("阶段 2 / 图谱命中", level=stage_level)
    _print_trace_list("实体命中 Top", trace.get("graph_entity_hits", []), "entity", heading_level=block_level)
    _print_trace_list("关系命中 Top", trace.get("graph_relation_hits", []), "relation", heading_level=block_level)

    if trace.get("mode") == "hybrid":
        _print_stage_header("阶段 3 / 混合召回", level=stage_level)
        _print_trace_list("向量召回候选 Top", trace.get("vector_candidates", []), "chunk", heading_level=block_level)
        _print_trace_list("图谱关联候选 Top", trace.get("graph_chunk_candidates", []), "chunk", heading_level=block_level)
        _print_trace_list("融合候选池（完整）", trace.get("merged_candidates", []), "chunk", heading_level=block_level)
        _print_stage_header("阶段 4 / Rerank 重排", level=stage_level)
        _print_key_value("Rerank 模型:", trace.get("rerank_model") or "未配置")
        _print_trace_list(
            "送入 Rerank 的候选池",
            trace.get("rerank_input_candidates", []),
            "chunk",
            heading_level=block_level,
        )
        _print_trace_list(
            "Rerank 后排序结果",
            trace.get("rerank_output_candidates", []),
            "rerank_chunk",
            heading_level=block_level,
        )
        _print_trace_list(
            "最终送入回答模型的证据",
            trace.get("final_context_chunks", []),
            "final_chunk",
            heading_level=block_level,
        )

    referenced_file_paths = trace.get("referenced_file_paths") or trace.get("image_list")
    if referenced_file_paths:
        _print_stage_header("阶段 5 / 引用到的文件", level=stage_level)
        for item in referenced_file_paths:
            prefix = "- " if _USE_MARKDOWN else "  - "
            print(f"{prefix}{_style(item, _MAGENTA)}")

    _print_stage_header("阶段 6 / 最终拼接上下文", level=stage_level)
    _print_structured_text_sections(trace.get("final_context_text", ""), heading_level=block_level)

    _print_stage_header("阶段 7 / 最终发送给回答模型的 Prompt", level=stage_level)
    _print_structured_text_sections(trace.get("final_prompt_text", ""), heading_level=block_level)

    _print_stage_header("最终答案", level=stage_level)
    print(_success(trace["answer"]))


def _print_multihop_trace(trace: dict, header_level: int = 1):
    stage_level = min(header_level + 1, 6)
    block_level = min(stage_level + 1, 6)

    _print_stage_header("MultiHop 图谱检索推理过程", level=header_level)
    _print_key_value("[原始问题]", trace["query"])

    _print_stage_header("阶段 1 / 问题拆解", level=stage_level)
    reasoning = trace["decomposition"].get("reasoning", "")
    if reasoning:
        _print_key_value("[拆解理由]", reasoning)
    sub_questions = trace["decomposition"].get("sub_questions", [])
    _print_block_header("子问题列表", level=block_level)
    if not sub_questions:
        print("- 无" if _USE_MARKDOWN else _muted("  - 无"))
    else:
        for index, sub_question in enumerate(sub_questions, 1):
            prefix = f"{index}. " if _USE_MARKDOWN else f"  {index}. "
            print(f"{prefix}{_style(sub_question, _BOLD)}")

    for index, step in enumerate(trace.get("steps", []), 1):
        stage_type = step.get("stage_type", "sub_question")
        if stage_type == "history_summary":
            title = f"阶段 2.{index} / 历史信息压缩"
        elif stage_type == "final_synthesis":
            title = f"阶段 2.{index} / 最终综合回答"
        else:
            title = f"阶段 2.{index} / 子问题求解"
        _print_onehop_trace(
            {
                **step["trace"],
                "query": step["display_question"],
            },
            header=title,
            header_level=stage_level,
        )
        _print_key_value("[内部检索提示]", _truncate_console(step.get("internal_query", "")))
        _print_key_value("[当前记忆快照]", step.get("memory_snapshot", ""))

    _print_stage_header("最终答案", level=stage_level)
    print(_success(trace["answer"]))


def _truncate_console(text: str, limit: int = 240) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _normalize_query_mode(mode: str | None) -> str:
    normalized_mode = (mode or "hybrid").strip().lower()
    if normalized_mode not in {"graph", "hybrid"}:
        raise ValueError("Invalid mode. Use one of: graph | hybrid")
    return normalized_mode


def _parse_history_turns(raw_value: str | None) -> int | None:
    if raw_value is None:
        return None
    history_turns = int(raw_value)
    if history_turns <= 0:
        raise ValueError("history_turns must be a positive integer")
    return history_turns


def _normalize_conversation_history(
    payload: Any,
    history_path: str,
) -> list[dict[str, str]]:
    if isinstance(payload, dict):
        if "conversation_history" not in payload:
            raise ValueError(
                f"Invalid conversation history file: {history_path}. "
                "Expected a JSON list or an object with conversation_history."
            )
        payload = payload.get("conversation_history")

    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError(
            f"Invalid conversation history file: {history_path}. Expected a JSON list."
        )

    conversation_history = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(
                f"Invalid conversation history entry at index {index}: expected an object."
            )
        role = item.get("role")
        content = item.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            raise ValueError(
                f"Invalid conversation history entry at index {index}: "
                "role/content must both be strings."
            )
        conversation_history.append({"role": role, "content": content})
    return conversation_history


def _load_conversation_history(history_path: str) -> list[dict[str, str]]:
    if not history_path:
        raise ValueError("Missing required argument: history_path")
    if not os.path.exists(history_path):
        return []
    with open(history_path, encoding="utf-8") as history_file:
        raw_text = history_file.read()
    if not raw_text.strip():
        return []
    payload = json.loads(raw_text)
    return _normalize_conversation_history(payload, history_path)


def _write_conversation_history(
    history_path: str,
    conversation_history: list[dict[str, str]],
) -> None:
    history_dir = os.path.dirname(os.path.abspath(history_path))
    if history_dir:
        os.makedirs(history_dir, exist_ok=True)
    with open(history_path, "w", encoding="utf-8") as history_file:
        json.dump(conversation_history, history_file, ensure_ascii=False, indent=2)
        history_file.write("\n")


def _append_conversation_turn(
    history_path: str,
    conversation_history: list[dict[str, str]],
    query: str,
    answer: str,
) -> list[dict[str, str]]:
    updated_history = [
        *conversation_history,
        {"role": "user", "content": query},
        {"role": "assistant", "content": answer},
    ]
    _write_conversation_history(history_path, updated_history)
    return updated_history


class RagentApp:
    def __init__(self, project_dir: str | None = None, mineru_output_dir: str | None = None):
        self.project_dir = project_dir
        self.mineru_output_dir = mineru_output_dir

    async def parse(
        self,
        pdf_file_path: str,
        mineru_output_dir: str | None = None,
        project_dir: str | None = None,
        stage: str = "auto",
        keep_pdf_subdir: bool = True,
    ):
        target_output_dir = mineru_output_dir or self.mineru_output_dir
        target_project_dir = project_dir or self.project_dir
        valid_stages = {"auto", "all", "md", "rag"}
        if stage not in valid_stages:
            raise ValueError("Invalid stage. Use one of: auto | all | md | rag")

        if not pdf_file_path:
            raise ValueError("Missing required argument: pdf_file_path")

        resolved_input_path = os.path.abspath(pdf_file_path)
        if _is_wide_table_path(pdf_file_path):
            table_project_dir = target_project_dir or target_output_dir
            if stage == "md":
                raise ValueError("宽表输入不支持 md 阶段，请使用 auto | all | rag")
            if not table_project_dir:
                raise ValueError("宽表输入需要 project_dir")
            if target_project_dir is None and target_output_dir is not None:
                logger.warning(
                    "宽表输入未提供独立 project_dir，复用第二个参数作为 project_dir: %s",
                    os.path.abspath(table_project_dir),
                )

            resolved_stage = "rag" if stage in {"auto", "all", "rag"} else stage
            logger.info(
                "parse 执行阶段: %s (wide_table=%s, project_dir=%s)",
                resolved_stage,
                resolved_input_path,
                os.path.abspath(table_project_dir),
            )
            logger.info("开始解析宽表并构建知识库...")
            await wide_table_insert(pdf_file_path, table_project_dir)
            logger.info("宽表知识库构建完成。")
            return

        if stage in {"auto", "all", "md"} and not target_output_dir:
            raise ValueError("Missing required argument for md stage: mineru_output_dir")

        if stage in {"all", "rag"} and not target_project_dir:
            raise ValueError("Missing required argument for rag stage: project_dir")

        resolved_stage = stage
        if stage == "auto":
            # 自动规则：
            # 1) 未提供 project_dir -> 仅做 md
            # 2) 提供 project_dir 且已有对应 md -> 仅做 rag
            # 3) 提供 project_dir 且无 md -> 做 all
            if not target_project_dir:
                resolved_stage = "md"
            else:
                md_path = self._resolve_existing_md_path(
                    pdf_file_path,
                    target_output_dir,
                    keep_pdf_subdir=keep_pdf_subdir,
                )
                resolved_stage = "rag" if md_path else "all"
            logger.info(f"自动推断阶段: {resolved_stage}")

        logger.info(
            "parse 执行阶段: %s (input=%s, mineru_output_dir=%s, project_dir=%s)",
            resolved_stage,
            resolved_input_path,
            os.path.abspath(target_output_dir) if target_output_dir else None,
            os.path.abspath(target_project_dir) if target_project_dir else None,
        )

        if resolved_stage == "all":
            logger.info("开始提取PDF并构建知识库...")
            await pdf_insert(
                pdf_file_path,
                target_output_dir,
                target_project_dir,
                keep_pdf_subdir=keep_pdf_subdir,
            )
            logger.info("PDF提取与知识库构建完成。")
            return

        if resolved_stage == "md":
            logger.info("开始提取PDF并生成增强 md...")
            artifacts = await build_enhanced_md(
                pdf_file_path,
                target_output_dir,
                keep_pdf_subdir=keep_pdf_subdir,
            )
            logger.info(f"增强 md 生成完成: {artifacts['md_path']}")
            return

        # resolved_stage == "rag"
        # 仅构建 RAG/KG：依赖已经存在的最终 md 文件
        md_path = self._resolve_existing_md_path(
            pdf_file_path,
            target_output_dir,
            keep_pdf_subdir=keep_pdf_subdir,
        )
        if not md_path:
            candidate_paths = self._build_md_candidate_paths(
                pdf_file_path,
                target_output_dir,
                keep_pdf_subdir=keep_pdf_subdir,
            )
            raise FileNotFoundError(
                "未找到最终 md 文件，请先执行 md 阶段。已检查路径: "
                + " | ".join(candidate_paths)
            )
        logger.info(f"开始基于最终 md 构建知识库: {md_path}")
        await index_md_to_rag(pdf_file_path, target_project_dir, md_path)
        logger.info("知识库构建完成。")

    @staticmethod
    def _build_md_candidate_paths(
        pdf_file_path: str,
        mineru_output_dir: str | None,
        keep_pdf_subdir: bool = True,
    ) -> list[str]:
        if not mineru_output_dir:
            return []

        pdf_name = os.path.basename(pdf_file_path).rsplit(".", 1)[0]
        candidate_paths = []
        output_subdirs = get_mineru_output_subdirs_for_lookup()
        if keep_pdf_subdir:
            for output_subdir in output_subdirs:
                candidate_paths.append(
                    os.path.join(mineru_output_dir, pdf_name, output_subdir, f"{pdf_name}.md")
                )
            for output_subdir in output_subdirs:
                candidate_paths.append(
                    os.path.join(mineru_output_dir, output_subdir, f"{pdf_name}.md")
                )
        else:
            for output_subdir in output_subdirs:
                candidate_paths.append(
                    os.path.join(mineru_output_dir, output_subdir, f"{pdf_name}.md")
                )
            for output_subdir in output_subdirs:
                candidate_paths.append(
                    os.path.join(mineru_output_dir, pdf_name, output_subdir, f"{pdf_name}.md")
                )

        deduped_paths: list[str] = []
        for candidate in candidate_paths:
            if candidate not in deduped_paths:
                deduped_paths.append(candidate)
        return deduped_paths

    @staticmethod
    def _resolve_existing_md_path(
        pdf_file_path: str,
        mineru_output_dir: str | None,
        keep_pdf_subdir: bool = True,
    ) -> str | None:
        for md_path in RagentApp._build_md_candidate_paths(
            pdf_file_path,
            mineru_output_dir,
            keep_pdf_subdir=keep_pdf_subdir,
        ):
            if os.path.exists(md_path):
                return md_path
        return None

    async def onehop(
        self,
        simple_query: str | None = None,
        project_dir: str | None = None,
        mode: str = "hybrid",
        conversation_history: list[dict[str, str]] | None = None,
        history_turns: int | None = None,
        quiet: bool = True,
        show_trace: bool = True,
    ):
        target_project_dir = project_dir or self.project_dir
        if not target_project_dir:
            raise ValueError("Missing required argument: project_dir")
        resolved_mode = _normalize_query_mode(mode)
        query = "文档的主要主题是什么？" if not simple_query else simple_query
        if show_trace:
            if quiet:
                with _temporary_log_level(["ragent", "nano-vectordb"], logging.WARNING):
                    trace = await trace_one_hop_problem(
                        target_project_dir,
                        query,
                        mode=resolved_mode,
                        conversation_history=conversation_history,
                        history_turns=history_turns,
                    )
            else:
                trace = await trace_one_hop_problem(
                    target_project_dir,
                    query,
                    mode=resolved_mode,
                    conversation_history=conversation_history,
                    history_turns=history_turns,
                )
            _print_onehop_trace(trace)
            return trace["answer"]

        if quiet:
            with _temporary_log_level(["ragent", "nano-vectordb"], logging.WARNING):
                answer = await inference_one_hop_problem(
                    target_project_dir,
                    query,
                    mode=resolved_mode,
                    conversation_history=conversation_history,
                    history_turns=history_turns,
                )
        else:
            answer = await inference_one_hop_problem(
                target_project_dir,
                query,
                mode=resolved_mode,
                conversation_history=conversation_history,
                history_turns=history_turns,
            )
        print(answer)
        return answer

    async def chat(
        self,
        query: str,
        history_path: str,
        project_dir: str | None = None,
        mode: str = "hybrid",
        history_turns: int | None = None,
        quiet: bool = True,
        show_trace: bool = True,
    ):
        target_project_dir = project_dir or self.project_dir
        if not target_project_dir:
            raise ValueError("Missing required argument: project_dir")
        if not query:
            raise ValueError("Missing required argument: query")

        resolved_mode = _normalize_query_mode(mode)
        conversation_history = _load_conversation_history(history_path)
        answer = await self.onehop(
            query,
            project_dir=target_project_dir,
            mode=resolved_mode,
            conversation_history=conversation_history,
            history_turns=history_turns,
            quiet=quiet,
            show_trace=show_trace,
        )
        _append_conversation_turn(history_path, conversation_history, query, answer)
        logger.info(
            "会话历史已更新: %s (messages=%d)",
            os.path.abspath(history_path),
            len(conversation_history) + 2,
        )
        return answer

    async def multihop(
        self,
        complex_query: str | None = None,
        project_dir: str | None = None,
        quiet: bool = True,
        show_trace: bool = True,
    ):
        target_project_dir = project_dir or self.project_dir
        if not target_project_dir:
            raise ValueError("Missing required argument: project_dir")
        query = "比较第2节和第3节中描述的方法，它们的主要区别是什么？" if not complex_query else complex_query
        if show_trace:
            if quiet:
                with _temporary_log_level(["ragent", "nano-vectordb"], logging.WARNING):
                    trace = await trace_multi_hop_problem(target_project_dir, query)
            else:
                trace = await trace_multi_hop_problem(target_project_dir, query)
            _print_multihop_trace(trace)
            return trace["answer"]

        if quiet:
            with _temporary_log_level(["ragent", "nano-vectordb"], logging.WARNING):
                answer = await inference_multi_hop_problem(target_project_dir, query)
        else:
            answer = await inference_multi_hop_problem(target_project_dir, query)
        print(answer)
        return answer


async def main(
    MODULE,
    PDF_FILE_PATH: str | None = None,
    MINERU_OUTPUT_DIR: str | None = None,
    PROJECT_DIR: str | None = None,
    simple_query: str | None = None,
    complex_query: str | None = None,
    history_path: str | None = None,
    stage: str = "auto",
    mode: str = "hybrid",
    history_turns: int | None = None,
    keep_pdf_subdir: bool = True,
):
    app = RagentApp(PROJECT_DIR, MINERU_OUTPUT_DIR)
    if MODULE == "parse":
        await app.parse(PDF_FILE_PATH, stage=stage, keep_pdf_subdir=keep_pdf_subdir)
        return
    elif MODULE == "onehop":
        return await app.onehop(simple_query, mode=mode)
    elif MODULE == "chat":
        return await app.chat(
            simple_query or "",
            history_path or "",
            mode=mode,
            history_turns=history_turns,
        )
    elif MODULE == "multihop":
        return await app.multihop(complex_query)
    else:
        raise ValueError(f"Invalid module: {MODULE}")

if __name__ == "__main__":
    sys.excepthook = _cli_excepthook
    MODULE, PDF_FILE_PATH, MINERU_OUTPUT_DIR, PROJECT_DIR, simple_query, complex_query, history_path, stage = None, None, None, None, None, None, None, "auto"
    BATCH_PARSE = False
    KEEP_PDF_SUBDIR = True
    MODE = "hybrid"
    HISTORY_TURNS = None
    MODULE = sys.argv[1] # : "parse" | "onehop" | "multihop" | "chat"
    if MODULE == "parse":
        # 支持：
        # 1) parse <pdf_or_dir> <mineru_output_dir>
        #    - PDF 自动推断 stage=md
        # 2) parse <pdf_or_dir> <mineru_output_dir> <project_dir>
        #    - PDF 自动推断 stage=all/rag（有 md 即 rag，否则 all）
        # 3) parse <pdf_or_dir> <mineru_output_dir> [project_dir] [stage]
        #    - PDF 可选手动覆盖 stage（auto/all/md/rag）
        # 4) parse <wide_table_or_dir> <project_dir> [stage]
        #    - 宽表文件直接建图，stage 仅接受 auto/all/rag
        # 5) parse <wide_table_or_dir> <unused_output_dir> <project_dir> [stage]
        #    - 兼容沿用 PDF 三参数写法；第二个参数会被忽略
        if len(sys.argv) < 4:
            raise ValueError(
                "Usage: parse <pdf_or_dir> <mineru_output_dir> [project_dir] [stage]\n"
                "   or: parse <wide_table_or_dir> <project_dir> [stage]"
            )

        PDF_FILE_PATH = sys.argv[2] # "path/to/your/document.pdf"
        valid_stages = {"auto", "all", "md", "rag"}
        input_is_wide_table = os.path.isfile(PDF_FILE_PATH) and _is_wide_table_path(PDF_FILE_PATH)

        if os.path.isdir(PDF_FILE_PATH):
            has_pdf = False
            has_wide_table = False
            for root, dirs, files in os.walk(PDF_FILE_PATH):
                for name in files:
                    ext = os.path.splitext(name)[1].lower()
                    if ext == ".pdf":
                        has_pdf = True
                    elif ext in _WIDE_TABLE_EXTENSIONS:
                        has_wide_table = True
                if has_pdf and has_wide_table:
                    break

            if has_wide_table and not has_pdf:
                arg3 = sys.argv[3]
                arg4 = sys.argv[4] if len(sys.argv) > 4 else None
                arg5 = sys.argv[5] if len(sys.argv) > 5 else None

                if arg4 in valid_stages or arg4 is None:
                    PROJECT_DIR = arg3
                    stage = arg4 if arg4 else "auto"
                    MINERU_OUTPUT_DIR = None
                else:
                    MINERU_OUTPUT_DIR = arg3
                    PROJECT_DIR = arg4
                    stage = arg5 if arg5 else "auto"
            else:
                MINERU_OUTPUT_DIR = sys.argv[3] # "mineru_out"  # 存储解析结果的目录
                arg4 = sys.argv[4] if len(sys.argv) > 4 else None
                arg5 = sys.argv[5] if len(sys.argv) > 5 else None

                if arg4 in valid_stages:
                    stage = arg4
                    PROJECT_DIR = None
                else:
                    PROJECT_DIR = arg4
                    stage = arg5 if arg5 else "auto"
        elif input_is_wide_table:
            arg3 = sys.argv[3]
            arg4 = sys.argv[4] if len(sys.argv) > 4 else None
            arg5 = sys.argv[5] if len(sys.argv) > 5 else None

            if arg4 in valid_stages or arg4 is None:
                PROJECT_DIR = arg3
                stage = arg4 if arg4 else "auto"
                MINERU_OUTPUT_DIR = None
            else:
                MINERU_OUTPUT_DIR = arg3
                PROJECT_DIR = arg4
                stage = arg5 if arg5 else "auto"
        else:
            MINERU_OUTPUT_DIR = sys.argv[3] # "mineru_out"  # 存储解析结果的目录
            arg4 = sys.argv[4] if len(sys.argv) > 4 else None
            arg5 = sys.argv[5] if len(sys.argv) > 5 else None

            if arg4 in valid_stages:
                stage = arg4
                PROJECT_DIR = None
            else:
                PROJECT_DIR = arg4
                stage = arg5 if arg5 else "auto"

        if stage not in valid_stages:
            raise ValueError(f"Invalid stage: {stage}. Use one of: auto | all | md | rag")
        # 如果传入的是目录，则批量遍历解析其中的 PDF 文档
        if os.path.isdir(PDF_FILE_PATH):
            BATCH_PARSE = True
            KEEP_PDF_SUBDIR = True
            valid_exts = {".pdf", *_WIDE_TABLE_EXTENSIONS}
            file_list = []
            for root, dirs, files in os.walk(PDF_FILE_PATH):
                for name in files:
                    ext = os.path.splitext(name)[1].lower()
                    if ext in valid_exts:
                        file_list.append(os.path.join(root, name))
            if not file_list:
                logger.info(f"未在目录中找到可解析文件: {PDF_FILE_PATH}")
            else:
                logger.info(f"在目录中找到 {len(file_list)} 个待解析文件")
            for idx, fp in enumerate(sorted(file_list)):
                logger.info(f"[{idx + 1}/{len(file_list)}] 开始解析: {fp}")
                try:
                    if _is_wide_table_path(fp):
                        if stage == "md":
                            logger.info(f"跳过宽表文件（md 阶段不适用）: {fp}")
                            continue
                        per_file_stage = "rag" if stage in {"auto", "all", "rag"} else stage
                    else:
                        # 目录模式下逐文件自动推断：
                        # 无 project_dir -> md；有 project_dir 时，已有 md -> rag，否则 all
                        per_file_stage = stage
                        if stage == "auto":
                            if PROJECT_DIR:
                                existing_md = RagentApp._resolve_existing_md_path(
                                    fp,
                                    MINERU_OUTPUT_DIR,
                                    keep_pdf_subdir=True,
                                )
                                per_file_stage = "rag" if existing_md else "all"
                            else:
                                per_file_stage = "md"
                    asyncio.run(
                        main(
                            "parse",
                            fp,
                            MINERU_OUTPUT_DIR,
                            PROJECT_DIR,
                            stage=per_file_stage,
                            keep_pdf_subdir=True,
                        )
                    )
                except Exception as e:
                    log_exception(f"解析失败: {fp}", e)
        else:
            KEEP_PDF_SUBDIR = False
    elif MODULE == "onehop":
        if len(sys.argv) < 4:
            raise ValueError("Usage: onehop <project_dir> <query> [mode]")
        PROJECT_DIR = sys.argv[2] # "my_ragent_project"  # 存储知识库的目录
        simple_query = sys.argv[3] # "文档的主要主题是什么？"
        MODE = _normalize_query_mode(sys.argv[4] if len(sys.argv) > 4 else "hybrid")
    elif MODULE == "chat":
        if len(sys.argv) < 5:
            raise ValueError(
                "Usage: chat <project_dir> <history_json> <query> [mode] [history_turns]"
            )
        PROJECT_DIR = sys.argv[2]
        history_path = sys.argv[3]
        simple_query = sys.argv[4]
        MODE = _normalize_query_mode(sys.argv[5] if len(sys.argv) > 5 else "hybrid")
        HISTORY_TURNS = _parse_history_turns(sys.argv[6] if len(sys.argv) > 6 else None)
    elif MODULE == "multihop":
        if len(sys.argv) < 4:
            raise ValueError("Usage: multihop <project_dir> <query>")
        PROJECT_DIR = sys.argv[2] # "my_ragent_project"  # 存储知识库的目录
        complex_query = sys.argv[3] # "比较第2节和第3节中描述的方法，它们的主要区别是什么？"
    else:
        raise ValueError(f"Invalid module: {MODULE}")
    # 仅当不是目录批量模式时才调用一次
    if not BATCH_PARSE:
        asyncio.run(
            main(
                MODULE,
                PDF_FILE_PATH,
                MINERU_OUTPUT_DIR,
                PROJECT_DIR,
                simple_query,
                complex_query,
                history_path,
                stage,
                MODE,
                HISTORY_TURNS,
                keep_pdf_subdir=KEEP_PDF_SUBDIR,
            )
        )
