import sys
import asyncio
import os
import logging
import json
import re
from contextlib import contextmanager
from typing import Any
if __package__:
    # Package execution (e.g., python -m ragent.singlefile)
    from .integrations import (
        pdf_insert,
        build_enhanced_md,
        index_md_to_rag,
        inference_one_hop_problem,
        inference_multi_hop_problem,
        trace_multi_hop_problem,
        trace_one_hop_problem,
    )
    from .ragent.utils import is_exception_logged, log_exception, logger
else:
    # Script execution (e.g., python singlefile.py ...)
    from integrations import (
        pdf_insert,
        build_enhanced_md,
        index_md_to_rag,
        inference_one_hop_problem,
        inference_multi_hop_problem,
        trace_multi_hop_problem,
        trace_one_hop_problem,
    )
    from ragent.utils import is_exception_logged, log_exception, logger


_USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
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


def _print_stage_header(title: str):
    print(f"\n{_section_rule('=')}")
    print(_accent(title))
    print(_section_rule('='))


def _print_subsection_header(title: str):
    print(f"\n{_section_rule('-')}")
    print(_style(title, _BOLD, _MAGENTA))
    print(_section_rule('-'))


def _print_block_header(title: str):
    print(_style(f"[{title}]", _BOLD, _YELLOW))


def _print_item_box(lines: list[str], color: str = _DIM):
    if not lines:
        return
    prefix = _style("  | ", color)
    for line in lines:
        print(f"{prefix}{line}")


def _print_multiline_value(label: str, value: str, color: str = _WHITE):
    lines = value.splitlines() or [""]
    _print_item_box([f"{label}: {lines[0]}", *lines[1:]], color)


def _print_trace_list(title: str, items: list[dict], kind: str):
    _print_block_header(title)
    if not items:
        print(_muted("  - 无"))
        return
    for item in items:
        if kind == "keyword":
            print(f"  - {_style(str(item), _GREEN)}")
            continue
        if kind == "entity":
            _print_item_box(
                [
                    f"{_style(item['entity'], _BOLD, _GREEN)} | type={item['type']} | source={item['file_path']}",
                    item["preview"],
                ],
                _GREEN,
            )
            continue
        if kind == "relation":
            _print_item_box(
                [
                    f"{_style(item['entity1'], _BOLD, _BLUE)} -> {_style(item['entity2'], _BOLD, _BLUE)} | source={item['file_path']}",
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
                    f"#{item['rank']}{source_text}{score_text} | {item['file_path']}",
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
                    f"#{item['rank']}{source_text} | {item['file_path']}",
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
                    f"#{item['rank']}{source_text}{score_text} | {item['file_path']}",
                    f"chunk_id={item.get('chunk_id', 'n/a')}",
                    item["preview"],
                ],
                _YELLOW,
            )
            continue
        if kind == "context_chunk":
            _print_item_box(
                [
                    f"#{item.get('id', 'n/a')} | {item.get('file_path', 'unknown_source')}",
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
            lines = [
                f"id: {item.get('id', 'n/a')}",
                f"file_path: {item.get('file_path', 'unknown_source')}",
            ]
            if "chunk_id" in item:
                lines.append(f"chunk_id: {item.get('chunk_id')}")
            if "content" in item:
                lines.append("content:")
                lines.extend(str(item.get("content", "")).splitlines() or [""])
            else:
                for key, value in item.items():
                    if key in {"id", "file_path", "chunk_id"}:
                        continue
                    lines.append(f"{key}: {value}")
            _print_item_box(lines, _WHITE)
        else:
            _print_item_box([str(item)], _WHITE)


def _print_structured_section(title: str, body: str):
    _print_subsection_header(title)
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


def _print_structured_text_sections(text: str):
    sections = _parse_titled_sections(text)
    if not sections:
        print(_muted("(空)"))
        return
    for title, body in sections:
        _print_structured_section(title, body)


def _print_stage_timing_summary(trace: dict):
    stage_timings = trace.get("stage_timings", [])
    if not stage_timings:
        print(_muted("(未记录阶段耗时)"))
        return
    for item in stage_timings:
        label = item.get("label") or item.get("stage") or "unknown"
        seconds = item.get("seconds")
        if isinstance(seconds, (int, float)):
            print(f"  - {label}: {_style(f'{seconds:.3f}s', _BOLD, _CYAN)}")
        else:
            print(f"  - {label}: {_muted('n/a')}")


def _print_onehop_trace(trace: dict, header: str = "OneHop 图谱检索推理过程"):
    _print_stage_header(header)
    print(f"{_label('[输入问题]')} {trace['query']}")
    print(f"{_label('[检索模式]')} {_style(trace['mode'], _BOLD, _GREEN)}")

    _print_stage_header("阶段 0 / 耗时概览")
    _print_stage_timing_summary(trace)

    _print_stage_header("阶段 1 / 关键词提取")
    _print_trace_list("高层关键词", trace.get("high_level_keywords", []), "keyword")
    _print_trace_list("低层关键词", trace.get("low_level_keywords", []), "keyword")

    _print_stage_header("阶段 2 / 图谱命中")
    _print_trace_list("实体命中 Top", trace.get("graph_entity_hits", []), "entity")
    _print_trace_list("关系命中 Top", trace.get("graph_relation_hits", []), "relation")

    if trace.get("mode") == "hybrid":
        _print_stage_header("阶段 3 / 混合召回")
        _print_trace_list("向量召回候选 Top", trace.get("vector_candidates", []), "chunk")
        _print_trace_list("图谱关联候选 Top", trace.get("graph_chunk_candidates", []), "chunk")
        _print_trace_list("融合候选池（完整）", trace.get("merged_candidates", []), "chunk")
        _print_stage_header("阶段 4 / Rerank 重排")
        print(f"{_label('Rerank 模型:')} {trace.get('rerank_model') or '未配置'}")
        _print_trace_list(
            "送入 Rerank 的候选池",
            trace.get("rerank_input_candidates", []),
            "chunk",
        )
        _print_trace_list(
            "Rerank 后排序结果",
            trace.get("rerank_output_candidates", []),
            "rerank_chunk",
        )
        _print_trace_list("最终送入回答模型的证据", trace.get("final_context_chunks", []), "final_chunk")

    if trace.get("image_list"):
        _print_stage_header("阶段 5 / 引用到的文件")
        for item in trace["image_list"]:
            print(f"  - {_style(item, _MAGENTA)}")

    _print_stage_header("阶段 6 / 最终拼接上下文")
    _print_structured_text_sections(trace.get("final_context_text", ""))

    _print_stage_header("阶段 7 / 最终发送给回答模型的 Prompt")
    _print_structured_text_sections(trace.get("final_prompt_text", ""))

    _print_stage_header("最终答案")
    print(_success(trace["answer"]))


def _print_multihop_trace(trace: dict):
    _print_stage_header("MultiHop 图谱检索推理过程")
    print(f"{_label('[原始问题]')} {trace['query']}")

    _print_stage_header("阶段 1 / 问题拆解")
    reasoning = trace["decomposition"].get("reasoning", "")
    if reasoning:
        print(f"{_label('[拆解理由]')} {reasoning}")
    sub_questions = trace["decomposition"].get("sub_questions", [])
    _print_block_header("子问题列表")
    if not sub_questions:
        print(_muted("  - 无"))
    else:
        for index, sub_question in enumerate(sub_questions, 1):
            print(f"  {index}. {_style(sub_question, _BOLD)}")

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
        )
        print(f"{_label('[内部检索提示]')} {_truncate_console(step.get('internal_query', ''))}")
        print(f"{_label('[当前记忆快照]')} {step.get('memory_snapshot', '')}")

    _print_stage_header("最终答案")
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
            "parse 执行阶段: %s (pdf=%s, mineru_output_dir=%s, project_dir=%s)",
            resolved_stage,
            os.path.abspath(pdf_file_path),
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
            pdf_name = os.path.basename(pdf_file_path).rsplit(".", 1)[0]
            md_path_new = os.path.join(target_output_dir, "txt", f"{pdf_name}.md")
            md_path_old = os.path.join(target_output_dir, pdf_name, "txt", f"{pdf_name}.md")
            raise FileNotFoundError(
                f"未找到最终 md 文件，请先执行 md 阶段: {md_path_new} 或 {md_path_old}"
            )
        logger.info(f"开始基于最终 md 构建知识库: {md_path}")
        await index_md_to_rag(pdf_file_path, target_project_dir, md_path)
        logger.info("知识库构建完成。")

    @staticmethod
    def _resolve_existing_md_path(
        pdf_file_path: str,
        mineru_output_dir: str | None,
        keep_pdf_subdir: bool = True,
    ) -> str | None:
        if not mineru_output_dir:
            return None

        pdf_name = os.path.basename(pdf_file_path).rsplit(".", 1)[0]
        candidate_paths = []
        if keep_pdf_subdir:
            candidate_paths.append(os.path.join(mineru_output_dir, pdf_name, "txt", f"{pdf_name}.md"))
            candidate_paths.append(os.path.join(mineru_output_dir, "txt", f"{pdf_name}.md"))
        else:
            candidate_paths.append(os.path.join(mineru_output_dir, "txt", f"{pdf_name}.md"))
            candidate_paths.append(os.path.join(mineru_output_dir, pdf_name, "txt", f"{pdf_name}.md"))

        for md_path in candidate_paths:
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
        #    - 自动推断 stage=md
        # 2) parse <pdf_or_dir> <mineru_output_dir> <project_dir>
        #    - 自动推断 stage=all/rag（有 md 即 rag，否则 all）
        # 3) parse <pdf_or_dir> <mineru_output_dir> [project_dir] [stage]
        #    - 可选手动覆盖 stage（auto/all/md/rag）
        if len(sys.argv) < 4:
            raise ValueError("Usage: parse <pdf_or_dir> <mineru_output_dir> [project_dir] [stage]")

        PDF_FILE_PATH = sys.argv[2] # "path/to/your/document.pdf"
        MINERU_OUTPUT_DIR = sys.argv[3] # "mineru_out"  # 存储解析结果的目录

        valid_stages = {"auto", "all", "md", "rag"}
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
            valid_exts = {".pdf"}
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
