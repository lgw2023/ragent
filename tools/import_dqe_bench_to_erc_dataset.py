#!/usr/bin/env python3
"""Audit DQE-Bench gold samples and build an ERC-compatible mapped subset.

The script intentionally keeps DQE source-unit ids separate from ragent chunk
ids. Live ERC metrics should only consume evidence rows backed by real project
chunk metadata.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_ROOT = Path("/Volumes/SSD1/ragent_benchmark")
DEFAULT_GOLD_SAMPLES = DEFAULT_BENCHMARK_ROOT / "benchmark_catalog" / "current_gold_samples.json"
DEFAULT_CURRENT_REPORT = DEFAULT_BENCHMARK_ROOT / "tmp" / "docs" / "current_report.md"
DEFAULT_QUESTION_DETAIL = (
    DEFAULT_BENCHMARK_ROOT
    / ".artifacts"
    / "current_gold_score_detail_20260413"
    / "question_detail.csv"
)
DEFAULT_BENCHMARK_RUNS_ROOT = DEFAULT_BENCHMARK_ROOT / ".artifacts" / "benchmark_runs"
DEFAULT_PROJECT_DIR = REPO_ROOT / "example" / "qwen4b_diet_kg"
QUESTION_TYPE_ORDER = [
    "fact_lookup",
    "comparison",
    "condition_filtering",
    "aggregation_calculation",
    "single_document_text_reasoning",
    "single_document_multimodal_reasoning",
    "multi_document_text_reasoning",
    "multi_document_multimodal_reasoning",
]
DIFFICULTY_RANK = {"hard": 3, "medium": 2, "easy": 1}
GENERIC_ANSWER_MARKERS = (
    "视情况",
    "因人而异",
    "需要结合",
    "无法确定",
    "不能一概而论",
    "没有明确",
)


@dataclass(frozen=True)
class MatchResult:
    source_unit_id: str
    matched: bool
    reason: str
    score: float = 0.0
    method: str = ""
    content_overlap: float = 0.0
    section_overlap: float = 0.0
    chunk_id: str = ""
    source_ref: str = ""
    file_path: str = ""
    page_numbers: tuple[int, ...] = ()
    section_path: str = ""
    source_unit_content: str = ""
    chunk_content_preview: str = ""
    source_type: str = ""
    doc_id: str = ""


def source_id_doc_id(source_unit_id: str) -> str:
    return str(source_unit_id).split("::", 1)[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build DQE-derived ERC dataset audit, mapping, and ERC datasets."
    )
    parser.add_argument("--gold-samples", default=str(DEFAULT_GOLD_SAMPLES))
    parser.add_argument("--current-report", default=str(DEFAULT_CURRENT_REPORT))
    parser.add_argument("--question-detail", default=str(DEFAULT_QUESTION_DETAIL))
    parser.add_argument("--benchmark-runs-root", default=str(DEFAULT_BENCHMARK_RUNS_ROOT))
    parser.add_argument("--project-dir", default=str(DEFAULT_PROJECT_DIR))
    parser.add_argument("--output-root", default=str(REPO_ROOT / "benchmark"))
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--per-type", type=int, default=5)
    parser.add_argument(
        "--selection-mode",
        choices=["balanced", "all"],
        default="balanced",
        help="balanced selects --per-type per question type; all keeps every mapped DQE current-gold question.",
    )
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def compact_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def visible_text_len(value: Any) -> int:
    return len(re.sub(r"[\s，。！？、,.!?;；:：|/\\()[\]{}<>《》\"'`~_-]+", "", str(value or "")))


def preview(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def char_ngrams(value: Any, n: int = 5) -> set[str]:
    text = compact_text(value)
    if not text:
        return set()
    if len(text) < n:
        return {text}
    return {text[index : index + n] for index in range(len(text) - n + 1)}


def overlap_recall(needle: Any, haystack: Any) -> float:
    needle_text = compact_text(needle)
    haystack_text = compact_text(haystack)
    if not needle_text or not haystack_text:
        return 0.0
    if needle_text in haystack_text:
        return 1.0
    n = 3 if len(needle_text) < 80 else 5
    needle_grams = char_ngrams(needle_text, n)
    if not needle_grams:
        return 0.0
    haystack_grams = char_ngrams(haystack_text, n)
    return len(needle_grams & haystack_grams) / len(needle_grams)


def dedupe_preserve_order(values: list[Any]) -> list[Any]:
    seen = set()
    result = []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def dqe_doc_candidates(doc_id: str) -> set[str]:
    raw = str(doc_id or "").strip()
    candidates = {raw} if raw else set()
    if raw.endswith("_md"):
        candidates.add(raw[:-3])
    bases = set(candidates)
    for base in list(bases):
        if base and not base.endswith((".pdf", ".jpg", ".jpeg", ".png")):
            candidates.add(f"{base}.pdf")
    return {item for item in candidates if item}


def chunk_doc_names(chunk: dict[str, Any]) -> set[str]:
    names = set()
    source_ref = str(chunk.get("source_ref") or "")
    if source_ref:
        names.add(Path(source_ref.split("|", 1)[0].strip()).name)
    file_path = str(chunk.get("file_path") or "")
    if file_path:
        file_name = Path(file_path).name
        if file_name.lower().endswith(".pdf"):
            names.add(file_name)
    content = str(chunk.get("content") or "")
    prefix_match = re.match(r"^([^#\n\r]+)#{2,}", content)
    if prefix_match:
        prefix = prefix_match.group(1).strip()
        if prefix:
            names.add(Path(prefix if prefix.endswith(".pdf") else f"{prefix}.pdf").name)
    return {item for item in names if item}


def load_gold_samples(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of gold samples: {path}")
    return [item for item in payload if isinstance(item, dict)]


def load_jsonl_map(paths: list[Path], id_field: str) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    rows: dict[str, dict[str, Any]] = {}
    conflicts = []
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                row = json.loads(stripped)
                row_id = str(row.get(id_field) or "")
                if not row_id:
                    continue
                if row_id not in rows:
                    row["_source_path"] = str(path)
                    row["_source_line"] = line_number
                    rows[row_id] = row
                    continue
                old = rows[row_id]
                if compact_text(old.get("content") or old.get("content_preview")) != compact_text(
                    row.get("content") or row.get("content_preview")
                ):
                    conflicts.append(
                        {
                            "id": row_id,
                            "first_path": old.get("_source_path"),
                            "conflict_path": str(path),
                        }
                    )
    return rows, conflicts


def source_preparation_paths(benchmark_runs_root: Path, file_name: str) -> list[Path]:
    return sorted(benchmark_runs_root.glob(f"*/01_source_preparation/{file_name}"))


def load_project_chunks(project_dir: Path) -> dict[str, dict[str, Any]]:
    chunks: dict[str, dict[str, Any]] = {}
    sqlite_path = project_dir / "kv_store_text_chunks.sqlite"
    if sqlite_path.exists():
        with sqlite3.connect(sqlite_path) as connection:
            for chunk_id, entry_json in connection.execute("select key, entry_json from kv_entries"):
                row = json.loads(entry_json)
                row["_id"] = chunk_id
                chunks[str(chunk_id)] = row
    json_path = project_dir / "kv_store_text_chunks.json"
    if json_path.exists():
        payload = read_json(json_path)
        if isinstance(payload, dict):
            for chunk_id, row in payload.items():
                if isinstance(row, dict) and chunk_id not in chunks:
                    row["_id"] = chunk_id
                    chunks[str(chunk_id)] = row
    vdb_path = project_dir / "vdb_chunks.json"
    if vdb_path.exists():
        payload = read_json(vdb_path)
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, list):
            for row in data:
                if not isinstance(row, dict):
                    continue
                chunk_id = str(row.get("__id__") or row.get("id") or "")
                if not chunk_id:
                    continue
                chunks.setdefault(chunk_id, {"_id": chunk_id})
                for key in (
                    "content",
                    "source_ref",
                    "file_path",
                    "page_numbers",
                    "page_number_start",
                    "page_number_end",
                    "section_path",
                    "full_doc_id",
                ):
                    if key not in chunks[chunk_id] and row.get(key) is not None:
                        chunks[chunk_id][key] = row.get(key)
    return chunks


def index_chunks_by_doc(chunks: dict[str, dict[str, Any]]) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    by_doc: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for chunk_id, chunk in chunks.items():
        for doc_name in chunk_doc_names(chunk):
            by_doc[doc_name].append((chunk_id, chunk))
    return by_doc


def section_overlap(source_unit: dict[str, Any], chunk: dict[str, Any]) -> float:
    source_sections = source_unit.get("section_path") or []
    if not isinstance(source_sections, list):
        source_sections = [source_sections]
    source_terms = [compact_text(term) for term in source_sections if compact_text(term)]
    if not source_terms:
        return 0.0
    haystack = compact_text(
        " ".join(
            [
                str(chunk.get("source_ref") or ""),
                str(chunk.get("section_path") or ""),
                str(chunk.get("content") or ""),
            ]
        )
    )
    if not haystack:
        return 0.0
    hits = sum(1 for term in source_terms if term in haystack)
    return hits / len(source_terms)


def score_chunk_match(
    source_unit: dict[str, Any],
    evidence_meta: dict[str, Any] | None,
    chunk_id: str,
    chunk: dict[str, Any],
) -> tuple[float, str, float, float]:
    unit_content = source_unit.get("content") or ""
    chunk_content = chunk.get("content") or ""
    content_score = overlap_recall(unit_content, chunk_content)
    section_score = section_overlap(source_unit, chunk)
    number_score = 0.0
    extracted_numbers = []
    if evidence_meta:
        extracted_numbers = evidence_meta.get("extracted_numbers") or []
    if extracted_numbers:
        chunk_norm = compact_text(chunk_content)
        hits = sum(1 for value in extracted_numbers if compact_text(value) in chunk_norm)
        number_score = hits / len(extracted_numbers)
    score = 82.0 * content_score + 13.0 * section_score + 5.0 * number_score
    table_like = (
        source_unit.get("source_type") == "table"
        or "<table" in str(unit_content).casefold()
        or "<table" in str(chunk_content).casefold()
    )
    if content_score == 1.0:
        method = "doc_constrained_substring"
    elif content_score >= 0.62:
        method = "doc_constrained_char_ngram"
    elif content_score >= 0.38 and section_score >= 0.5:
        method = "doc_constrained_section_ngram"
    elif table_like and content_score >= 0.25 and section_score >= 0.8:
        method = "doc_constrained_table_section_ngram"
    else:
        method = "below_threshold"
    return score, method, content_score, section_score


def match_source_unit(
    source_unit_id: str,
    source_units: dict[str, dict[str, Any]],
    evidence_index: dict[str, dict[str, Any]],
    chunks_by_doc: dict[str, list[tuple[str, dict[str, Any]]]],
) -> MatchResult:
    source_unit = source_units.get(source_unit_id)
    if not source_unit:
        return MatchResult(
            source_unit_id=source_unit_id,
            matched=False,
            reason="source_unit_missing",
        )
    doc_id = str(source_unit.get("doc_id") or "")
    doc_candidates = dqe_doc_candidates(doc_id)
    candidate_chunks: list[tuple[str, dict[str, Any]]] = []
    seen_chunk_ids = set()
    for doc_name in doc_candidates:
        for chunk_id, chunk in chunks_by_doc.get(doc_name, []):
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            candidate_chunks.append((chunk_id, chunk))
    if not candidate_chunks:
        return MatchResult(
            source_unit_id=source_unit_id,
            matched=False,
            reason="no_project_chunks_for_doc",
            source_unit_content=str(source_unit.get("content") or ""),
            source_type=str(source_unit.get("source_type") or ""),
            doc_id=doc_id,
        )
    evidence_meta = evidence_index.get(source_unit_id)
    best: tuple[float, str, float, float, str, dict[str, Any]] | None = None
    for chunk_id, chunk in candidate_chunks:
        score, method, content_score, section_score = score_chunk_match(
            source_unit,
            evidence_meta,
            chunk_id,
            chunk,
        )
        if best is None or score > best[0]:
            best = (score, method, content_score, section_score, chunk_id, chunk)
    assert best is not None
    score, method, content_score, section_score, chunk_id, chunk = best
    if not (
        content_score >= 0.62
        or (content_score >= 0.38 and section_score >= 0.5)
        or (method == "doc_constrained_table_section_ngram")
        or (method == "doc_constrained_substring")
    ):
        page_numbers = tuple(
            int(page)
            for page in (chunk.get("page_numbers") or [])
            if isinstance(page, int) and page > 0
        )
        return MatchResult(
            source_unit_id=source_unit_id,
            matched=False,
            reason="best_chunk_below_similarity_threshold",
            score=round(score, 4),
            method=method,
            content_overlap=round(content_score, 6),
            section_overlap=round(section_score, 6),
            chunk_id=chunk_id,
            source_ref=str(chunk.get("source_ref") or ""),
            file_path=str(chunk.get("file_path") or ""),
            page_numbers=page_numbers,
            section_path=str(chunk.get("section_path") or ""),
            source_unit_content=str(source_unit.get("content") or ""),
            chunk_content_preview=preview(chunk.get("content")),
            source_type=str(source_unit.get("source_type") or ""),
            doc_id=doc_id,
        )
    page_numbers = tuple(
        int(page)
        for page in (chunk.get("page_numbers") or [])
        if isinstance(page, int) and page > 0
    )
    return MatchResult(
        source_unit_id=source_unit_id,
        matched=True,
        reason="matched",
        score=round(score, 4),
        method=method,
        content_overlap=round(content_score, 6),
        section_overlap=round(section_score, 6),
        chunk_id=chunk_id,
        source_ref=str(chunk.get("source_ref") or ""),
        file_path=str(chunk.get("file_path") or ""),
        page_numbers=page_numbers,
        section_path=str(chunk.get("section_path") or ""),
        source_unit_content=str(source_unit.get("content") or ""),
        chunk_content_preview=preview(chunk.get("content")),
        source_type=str(source_unit.get("source_type") or ""),
        doc_id=doc_id,
    )


def load_replacement_decisions(benchmark_runs_root: Path) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    plans = sorted(benchmark_runs_root.glob("*/08_iteration_replacement/iteration_plan.json"))
    for plan in plans:
        payload = read_json(plan)
        rows = payload.get("replacement_decisions") if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            continue
        marker = (plan.stat().st_mtime, str(plan))
        for row in rows:
            if not isinstance(row, dict):
                continue
            qid = str(row.get("question_id") or "")
            if not qid:
                continue
            current_marker = decisions.get(qid, {}).get("_decision_marker")
            if current_marker is None or marker >= tuple(current_marker):
                copied = dict(row)
                copied["_decision_path"] = str(plan)
                copied["_decision_marker"] = marker
                decisions[qid] = copied
    return decisions


def load_question_detail_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    total = 0
    by_tool = Counter()
    by_question = Counter()
    llm_status = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total += 1
            by_tool[row.get("tool") or ""] += 1
            by_question[row.get("question_id") or ""] += 1
            llm_status[row.get("llm_status") or ""] += 1
    return {
        "path": str(path),
        "exists": True,
        "row_count": total,
        "tool_counts": dict(sorted(by_tool.items())),
        "question_count": len(by_question),
        "llm_status_counts": dict(sorted(llm_status.items())),
    }


def question_flags(sample: dict[str, Any]) -> list[str]:
    flags = []
    if visible_text_len(sample.get("question")) < 8:
        flags.append("short_question")
    if sample.get("answerability") != "answerable":
        flags.append("not_answerable")
    if not sample.get("gold_evidence"):
        flags.append("empty_gold_evidence")
    if not sample.get("answer_key_points"):
        flags.append("empty_answer_key_points")
    gold_answer = str(sample.get("gold_answer") or "")
    if visible_text_len(gold_answer) < 8 or any(marker in gold_answer for marker in GENERIC_ANSWER_MARKERS):
        flags.append("possibly_over_general_gold_answer")
    return flags


def build_dataset_audit(
    samples: list[dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    question_detail: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    duplicate_questions = defaultdict(list)
    for sample in samples:
        duplicate_questions[compact_text(sample.get("question"))].append(sample.get("question_id"))
    duplicate_groups = [
        [qid for qid in qids if qid]
        for text, qids in duplicate_questions.items()
        if text and len(qids) > 1
    ]
    preview_rows = []
    for sample in samples:
        qid = str(sample.get("question_id") or "")
        metadata = sample.get("metadata") if isinstance(sample.get("metadata"), dict) else {}
        decision = decisions.get(qid, {})
        flags = question_flags(sample)
        if any(qid in group for group in duplicate_groups):
            flags.append("duplicate_question_text")
        preview_rows.append(
            {
                "question_id": qid,
                "question_type": sample.get("question_type"),
                "difficulty": sample.get("difficulty"),
                "document_scope": metadata.get("document_scope"),
                "modality": metadata.get("modality"),
                "source_docs": sample.get("source_docs") or [],
                "evidence_source_count": len(sample.get("evidence_source_ids") or []),
                "gold_evidence_count": len(sample.get("gold_evidence") or []),
                "answer_key_point_count": len(sample.get("answer_key_points") or []),
                "answerability": sample.get("answerability"),
                "phase8_action": decision.get("action") or "",
                "quality_flags": flags,
                "question": sample.get("question"),
            }
        )
    counters = {
        "question_type": Counter(sample.get("question_type") for sample in samples),
        "difficulty": Counter(sample.get("difficulty") for sample in samples),
        "answerability": Counter(sample.get("answerability") for sample in samples),
        "document_scope": Counter(
            (sample.get("metadata") or {}).get("document_scope") for sample in samples
        ),
        "modality": Counter((sample.get("metadata") or {}).get("modality") for sample in samples),
        "source_docs": Counter(
            doc for sample in samples for doc in (sample.get("source_docs") or [])
        ),
        "evidence_source_count": Counter(len(sample.get("evidence_source_ids") or []) for sample in samples),
        "phase8_action": Counter(decisions.get(str(sample.get("question_id") or ""), {}).get("action") or "no_decision" for sample in samples),
    }
    audit = {
        "sample_count": len(samples),
        "distributions": {
            key: dict(sorted(counter.items(), key=lambda item: str(item[0])))
            for key, counter in counters.items()
        },
        "quality_counts": {
            "gold_evidence_empty": sum(1 for sample in samples if not sample.get("gold_evidence")),
            "answer_key_points_empty": sum(1 for sample in samples if not sample.get("answer_key_points")),
            "not_answerable": sum(1 for sample in samples if sample.get("answerability") != "answerable"),
            "short_question": sum(1 for sample in samples if visible_text_len(sample.get("question")) < 8),
            "possibly_over_general_gold_answer": sum(
                1 for sample in samples if "possibly_over_general_gold_answer" in question_flags(sample)
            ),
            "duplicate_question_groups": len(duplicate_groups),
        },
        "duplicate_question_groups": duplicate_groups,
        "question_detail_summary": question_detail,
    }
    return audit, preview_rows


def render_dataset_audit_md(audit: dict[str, Any]) -> str:
    lines = [
        "# DQE Gold Dataset Audit",
        "",
        f"- Samples: `{audit['sample_count']}`",
        f"- Empty gold evidence: `{audit['quality_counts']['gold_evidence_empty']}`",
        f"- Empty answer key points: `{audit['quality_counts']['answer_key_points_empty']}`",
        f"- Not answerable: `{audit['quality_counts']['not_answerable']}`",
        f"- Short questions: `{audit['quality_counts']['short_question']}`",
        f"- Possibly over-general gold answers: `{audit['quality_counts']['possibly_over_general_gold_answer']}`",
        f"- Duplicate question groups: `{audit['quality_counts']['duplicate_question_groups']}`",
        "",
        "## Distributions",
        "",
    ]
    for name, values in audit["distributions"].items():
        lines.append(f"### {name}")
        lines.append("")
        for key, count in values.items():
            lines.append(f"- `{key}`: {count}")
        lines.append("")
    qd = audit.get("question_detail_summary") or {}
    lines.extend(
        [
            "## External Score Detail",
            "",
            f"- Path: `{qd.get('path', '')}`",
            f"- Exists: `{qd.get('exists')}`",
            f"- Rows: `{qd.get('row_count', 0)}`",
            f"- Questions: `{qd.get('question_count', 0)}`",
            "",
        ]
    )
    if audit.get("duplicate_question_groups"):
        lines.extend(["## Duplicate Question Groups", ""])
        for group in audit["duplicate_question_groups"][:20]:
            lines.append(f"- {', '.join(group)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def match_required_source_units(
    samples: list[dict[str, Any]],
    source_units: dict[str, dict[str, Any]],
    evidence_index: dict[str, dict[str, Any]],
    chunks: dict[str, dict[str, Any]],
) -> dict[str, MatchResult]:
    required_ids = sorted(
        {
            str(source_id)
            for sample in samples
            for source_id in (sample.get("evidence_source_ids") or [])
            if source_id
        }
    )
    chunks_by_doc = index_chunks_by_doc(chunks)
    return {
        source_unit_id: match_source_unit(source_unit_id, source_units, evidence_index, chunks_by_doc)
        for source_unit_id in required_ids
    }


def index_source_units_by_doc(source_units: dict[str, dict[str, Any]]) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    by_doc: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for source_unit_id, source_unit in source_units.items():
        doc_id = str(source_unit.get("doc_id") or source_id_doc_id(source_unit_id))
        by_doc[doc_id].append((source_unit_id, source_unit))
    return by_doc


def source_unit_gold_overlap(source_unit: dict[str, Any] | None, gold_evidence: str) -> float:
    if not source_unit or not gold_evidence:
        return 0.0
    content = source_unit.get("content") or ""
    return max(overlap_recall(content, gold_evidence), overlap_recall(gold_evidence, content))


def resolve_source_unit_for_gold(
    original_source_unit_id: str,
    gold_evidence: str,
    source_units: dict[str, dict[str, Any]],
    source_units_by_doc: dict[str, list[tuple[str, dict[str, Any]]]],
) -> dict[str, Any]:
    original = source_units.get(original_source_unit_id)
    if not original:
        return {
            "resolved_source_unit_id": original_source_unit_id,
            "source_id_resolution_status": "missing_original_source_unit",
            "source_id_gold_overlap": 0.0,
            "resolved_source_id_gold_overlap": 0.0,
        }
    original_score = source_unit_gold_overlap(original, gold_evidence)
    if original_score >= 0.35 or not gold_evidence:
        return {
            "resolved_source_unit_id": original_source_unit_id,
            "source_id_resolution_status": "verified_original_source_unit",
            "source_id_gold_overlap": round(original_score, 6),
            "resolved_source_id_gold_overlap": round(original_score, 6),
        }
    doc_id = str(original.get("doc_id") or source_id_doc_id(original_source_unit_id))
    best_id = original_source_unit_id
    best_score = original_score
    for candidate_id, candidate in source_units_by_doc.get(doc_id, []):
        score = source_unit_gold_overlap(candidate, gold_evidence)
        if score > best_score:
            best_id = candidate_id
            best_score = score
    if best_id != original_source_unit_id and best_score >= 0.5:
        return {
            "resolved_source_unit_id": best_id,
            "source_id_resolution_status": "repaired_from_gold_evidence",
            "source_id_gold_overlap": round(original_score, 6),
            "resolved_source_id_gold_overlap": round(best_score, 6),
        }
    return {
        "resolved_source_unit_id": original_source_unit_id,
        "source_id_resolution_status": "low_confidence_original_source_unit",
        "source_id_gold_overlap": round(original_score, 6),
        "resolved_source_id_gold_overlap": round(best_score, 6),
    }


def match_to_row(match: MatchResult, question_ids: list[str]) -> dict[str, Any]:
    return {
        "source_unit_id": match.source_unit_id,
        "question_ids": question_ids,
        "matched": match.matched,
        "reason": match.reason,
        "match_score": match.score,
        "match_method": match.method,
        "content_overlap": match.content_overlap,
        "section_overlap": match.section_overlap,
        "chunk_id": match.chunk_id,
        "source_ref": match.source_ref,
        "file_path": match.file_path,
        "page_numbers": list(match.page_numbers),
        "section_path": match.section_path,
        "source_type": match.source_type,
        "doc_id": match.doc_id,
        "source_unit_content_preview": preview(match.source_unit_content),
        "chunk_content_preview": match.chunk_content_preview,
    }


def evidence_match_row(
    sample: dict[str, Any],
    evidence_index_in_question: int,
    original_source_unit_id: str,
    gold_evidence: str,
    resolution: dict[str, Any],
    match: MatchResult,
) -> dict[str, Any]:
    row = match_to_row(match, [str(sample.get("question_id") or "")])
    row.update(
        {
            "question_id": str(sample.get("question_id") or ""),
            "evidence_index": evidence_index_in_question,
            "original_source_unit_id": original_source_unit_id,
            "resolved_source_unit_id": resolution["resolved_source_unit_id"],
            "source_id_resolution_status": resolution["source_id_resolution_status"],
            "source_id_gold_overlap": resolution["source_id_gold_overlap"],
            "resolved_source_id_gold_overlap": resolution["resolved_source_id_gold_overlap"],
            "question_type": sample.get("question_type") or "",
            "difficulty": sample.get("difficulty") or "",
            "gold_evidence": gold_evidence,
            "source_unit_content": match.source_unit_content,
        }
    )
    return row


def map_evidence_items(
    samples: list[dict[str, Any]],
    source_units: dict[str, dict[str, Any]],
    evidence_index: dict[str, dict[str, Any]],
    chunks: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, MatchResult]]:
    source_units_by_doc = index_source_units_by_doc(source_units)
    chunks_by_doc = index_chunks_by_doc(chunks)
    match_cache: dict[str, MatchResult] = {}
    rows = []
    for sample in samples:
        source_ids = [str(source_id) for source_id in (sample.get("evidence_source_ids") or [])]
        gold_evidence_rows = [str(item) for item in (sample.get("gold_evidence") or [])]
        for index, original_source_unit_id in enumerate(source_ids):
            gold_evidence = gold_evidence_rows[index] if index < len(gold_evidence_rows) else ""
            resolution = resolve_source_unit_for_gold(
                original_source_unit_id,
                gold_evidence,
                source_units,
                source_units_by_doc,
            )
            resolved_source_unit_id = str(resolution["resolved_source_unit_id"])
            if resolved_source_unit_id not in match_cache:
                match_cache[resolved_source_unit_id] = match_source_unit(
                    resolved_source_unit_id,
                    source_units,
                    evidence_index,
                    chunks_by_doc,
                )
            rows.append(
                evidence_match_row(
                    sample,
                    index,
                    original_source_unit_id,
                    gold_evidence,
                    resolution,
                    match_cache[resolved_source_unit_id],
                )
            )
    return rows, match_cache


def per_question_mapping_stats(
    samples: list[dict[str, Any]],
    matches: dict[str, MatchResult],
) -> dict[str, dict[str, Any]]:
    stats = {}
    for sample in samples:
        source_ids = [str(source_id) for source_id in (sample.get("evidence_source_ids") or [])]
        matched_ids = [source_id for source_id in source_ids if matches.get(source_id, MatchResult(source_id, False, "")).matched]
        stats[str(sample.get("question_id") or "")] = {
            "evidence_source_count": len(source_ids),
            "matched_evidence_count": len(matched_ids),
            "unmatched_evidence_count": len(source_ids) - len(matched_ids),
            "matched_source_unit_ids": matched_ids,
            "unmatched_source_unit_ids": [source_id for source_id in source_ids if source_id not in matched_ids],
        }
    return stats


def per_question_mapping_stats_from_rows(
    samples: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    rows_by_qid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in evidence_rows:
        rows_by_qid[str(row.get("question_id") or "")].append(row)
    stats = {}
    for sample in samples:
        qid = str(sample.get("question_id") or "")
        rows = rows_by_qid.get(qid, [])
        matched_rows = [row for row in rows if row.get("matched")]
        stats[qid] = {
            "evidence_source_count": len(sample.get("evidence_source_ids") or []),
            "matched_evidence_count": len(matched_rows),
            "unmatched_evidence_count": len(rows) - len(matched_rows),
            "matched_source_unit_ids": [row["resolved_source_unit_id"] for row in matched_rows],
            "unmatched_source_unit_ids": [
                row["resolved_source_unit_id"] for row in rows if not row.get("matched")
            ],
            "source_unit_repair_count": sum(
                1
                for row in rows
                if row.get("source_id_resolution_status") == "repaired_from_gold_evidence"
            ),
        }
    return stats


def render_mapping_audit_md(
    samples: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    question_stats: dict[str, dict[str, Any]],
    chunks: dict[str, dict[str, Any]],
    source_unit_conflicts: list[dict[str, Any]],
    evidence_index_conflicts: list[dict[str, Any]],
) -> str:
    total_required = len(evidence_rows)
    matched = sum(1 for item in evidence_rows if item.get("matched"))
    unique_resolved = {row["resolved_source_unit_id"] for row in evidence_rows}
    unique_matched = {row["resolved_source_unit_id"] for row in evidence_rows if row.get("matched")}
    repaired = sum(
        1
        for row in evidence_rows
        if row.get("source_id_resolution_status") == "repaired_from_gold_evidence"
    )
    low_confidence = sum(
        1
        for row in evidence_rows
        if row.get("source_id_resolution_status") == "low_confidence_original_source_unit"
    )
    eligible = sum(1 for item in question_stats.values() if item["matched_evidence_count"] >= 1)
    multi_matched = sum(1 for item in question_stats.values() if item["matched_evidence_count"] >= 2)
    by_type = defaultdict(lambda: Counter({"questions": 0, "eligible": 0, "multi_matched": 0}))
    sample_by_id = {str(sample.get("question_id") or ""): sample for sample in samples}
    for qid, stats in question_stats.items():
        qtype = sample_by_id[qid].get("question_type")
        by_type[qtype]["questions"] += 1
        if stats["matched_evidence_count"] >= 1:
            by_type[qtype]["eligible"] += 1
        if stats["matched_evidence_count"] >= 2:
            by_type[qtype]["multi_matched"] += 1
    lines = [
        "# DQE Source Unit To Ragent Chunk Mapping Audit",
        "",
        f"- Project chunks loaded: `{len(chunks)}`",
        f"- Required DQE evidence items: `{total_required}`",
        f"- Matched evidence items: `{matched}`",
        f"- Unmatched evidence items: `{total_required - matched}`",
        f"- Unique resolved source units: `{len(unique_resolved)}`",
        f"- Unique matched source units: `{len(unique_matched)}`",
        f"- Source id repairs from gold evidence: `{repaired}`",
        f"- Low-confidence original source ids retained: `{low_confidence}`",
        f"- Questions with at least one matched evidence: `{eligible}` / `{len(samples)}`",
        f"- Questions with at least two matched evidence: `{multi_matched}` / `{len(samples)}`",
        f"- Source unit conflicts while merging runs: `{len(source_unit_conflicts)}`",
        f"- Evidence index conflicts while merging runs: `{len(evidence_index_conflicts)}`",
        "",
        "## By Question Type",
        "",
        "| question_type | questions | eligible >=1 | matched >=2 |",
        "|---|---:|---:|---:|",
    ]
    for qtype in QUESTION_TYPE_ORDER:
        row = by_type.get(qtype, Counter())
        lines.append(
            f"| {qtype} | {row.get('questions', 0)} | {row.get('eligible', 0)} | {row.get('multi_matched', 0)} |"
        )
    lines.extend(["", "## Mapping Rules", ""])
    lines.extend(
        [
            "- Document id/source file is constrained before text matching.",
            "- Each evidence_source_id is first checked against its paired gold_evidence text.",
            "- If the source id and gold text disagree, the script searches the same DQE doc for a better source unit and records `repaired_from_gold_evidence`.",
            "- Matching then uses exact substring, character n-gram recall, section overlap, and numeric overlap.",
            "- Page, source_ref, file_path, section_path, and chunk_id are copied only from real project chunk metadata.",
            "- Unmatched source units remain in `unmatched_evidence.jsonl` and are not written as required live evidence.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def extract_required_entities(
    sample: dict[str, Any],
    source_ids: list[str],
    evidence_index: dict[str, dict[str, Any]],
) -> list[str]:
    values: list[str] = []
    for item in sample.get("answer_key_points") or []:
        if visible_text_len(item) >= 2:
            values.append(str(item))
    for source_id in source_ids:
        meta = evidence_index.get(source_id) or {}
        for key in ("keyword_hits", "topic_hints", "unit_tokens"):
            for item in meta.get(key) or []:
                if visible_text_len(item) >= 2:
                    values.append(str(item))
    return dedupe_preserve_order(values)[:16]


def build_required_evidence(match: MatchResult, gold_evidence: list[str]) -> dict[str, Any]:
    return {
        "source_unit_id": match.source_unit_id,
        "source_ref": match.source_ref,
        "chunk_id": match.chunk_id,
        "file_path": match.file_path,
        "page_numbers": list(match.page_numbers),
        "section_path": match.section_path,
        "content": match.source_unit_content,
        "gold_evidence": gold_evidence,
        "annotation_status": "dqe_mapped_project_chunk",
        "match_method": match.method,
        "match_score": match.score,
        "content_overlap": match.content_overlap,
        "section_overlap": match.section_overlap,
    }


def build_required_evidence_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_unit_id": row["resolved_source_unit_id"],
        "original_source_unit_id": row["original_source_unit_id"],
        "source_ref": row["source_ref"],
        "chunk_id": row["chunk_id"],
        "file_path": row["file_path"],
        "page_numbers": list(row.get("page_numbers") or []),
        "section_path": row["section_path"],
        "content": row.get("source_unit_content") or "",
        "gold_evidence": [row.get("gold_evidence") or ""],
        "annotation_status": (
            "dqe_mapped_project_chunk_source_unit_repaired"
            if row.get("source_id_resolution_status") == "repaired_from_gold_evidence"
            else "dqe_mapped_project_chunk"
        ),
        "source_id_resolution_status": row.get("source_id_resolution_status") or "",
        "source_id_gold_overlap": row.get("source_id_gold_overlap", 0.0),
        "resolved_source_id_gold_overlap": row.get("resolved_source_id_gold_overlap", 0.0),
        "match_method": row.get("match_method") or "",
        "match_score": row.get("match_score", 0.0),
        "content_overlap": row.get("content_overlap", 0.0),
        "section_overlap": row.get("section_overlap", 0.0),
    }


def build_erc_record(
    sample: dict[str, Any],
    evidence_rows: list[dict[str, Any]],
    evidence_index: dict[str, dict[str, Any]],
    dataset_id: str,
    selection_reason: str,
) -> dict[str, Any] | None:
    source_ids = [str(source_id) for source_id in (sample.get("evidence_source_ids") or [])]
    matched_rows = [row for row in evidence_rows if row.get("matched")]
    if not matched_rows:
        return None
    required_evidence = [build_required_evidence_from_row(row) for row in matched_rows]
    matched_source_ids = [row["resolved_source_unit_id"] for row in matched_rows]
    metadata = sample.get("metadata") if isinstance(sample.get("metadata"), dict) else {}
    unmatched_source_ids = [
        row["original_source_unit_id"] for row in evidence_rows if not row.get("matched")
    ]
    repair_count = sum(
        1
        for row in evidence_rows
        if row.get("source_id_resolution_status") == "repaired_from_gold_evidence"
    )
    if unmatched_source_ids:
        annotation_status = "dqe_mapped_partial"
    elif repair_count:
        annotation_status = "dqe_mapped_complete_with_source_unit_repairs"
    else:
        annotation_status = "dqe_mapped_complete"
    return {
        "id": str(sample.get("question_id") or ""),
        "dataset": dataset_id,
        "question": sample.get("question") or "",
        "gold_answer": sample.get("gold_answer") or "",
        "gold_reasoning": sample.get("gold_reasoning") or "",
        "answer_key_points": sample.get("answer_key_points") or [],
        "required_source_refs": [item["source_ref"] for item in required_evidence],
        "required_source_unit_ids": matched_source_ids,
        "required_chunk_ids": [item["chunk_id"] for item in required_evidence],
        "required_evidence": required_evidence,
        "required_entities": extract_required_entities(sample, matched_source_ids, evidence_index),
        "required_relations": [],
        "question_type": sample.get("question_type") or "",
        "difficulty": sample.get("difficulty") or "",
        "requires_calculation": sample.get("question_type") == "aggregation_calculation",
        "document_scope": metadata.get("document_scope") or "",
        "modality": metadata.get("modality") or "",
        "annotation_status": annotation_status,
        "relation_annotation_status": "not_available_in_dqe_gold",
        "source_docs": sample.get("source_docs") or [],
        "dqe_template_id": sample.get("template_id") or "",
        "dqe_reasoning_pattern": sample.get("reasoning_pattern") or "",
        "dqe_sample_origin": metadata.get("sample_origin") or "",
        "dqe_original_evidence_source_ids": source_ids,
        "dqe_resolved_evidence_source_ids": matched_source_ids,
        "dqe_unmatched_evidence_source_ids": unmatched_source_ids,
        "dqe_source_unit_repair_count": repair_count,
        "dqe_gold_evidence": sample.get("gold_evidence") or [],
        "selection_reason": selection_reason,
    }


def selection_priority(sample: dict[str, Any], stats: dict[str, Any], decision: dict[str, Any]) -> tuple[Any, ...]:
    metadata = sample.get("metadata") if isinstance(sample.get("metadata"), dict) else {}
    return (
        stats["matched_evidence_count"] >= 2,
        metadata.get("document_scope") == "multi_document",
        DIFFICULTY_RANK.get(str(sample.get("difficulty") or ""), 0),
        stats["matched_evidence_count"],
        len(sample.get("source_docs") or []),
        decision.get("action") == "keep",
        str(sample.get("question_id") or ""),
    )


def select_balanced_subset(
    samples: list[dict[str, Any]],
    question_stats: dict[str, dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    per_type: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    decision_rows = []
    selected_ids = set()
    for sample in samples:
        qid = str(sample.get("question_id") or "")
        qtype = str(sample.get("question_type") or "")
        stats = question_stats.get(qid, {})
        decision = decisions.get(qid, {})
        if stats.get("matched_evidence_count", 0) < 1:
            reason = "excluded: no mapped project evidence"
            action = "exclude"
        elif decision.get("action") == "replace":
            reason = f"excluded: phase 8 replace decision ({decision.get('reason', '')})"
            action = "exclude"
        else:
            reason = "candidate"
            action = "candidate"
            by_type[qtype].append(sample)
        decision_rows.append(
            {
                "question_id": qid,
                "question_type": qtype,
                "phase8_action": decision.get("action") or "",
                "matched_evidence_count": stats.get("matched_evidence_count", 0),
                "original_evidence_source_count": stats.get("evidence_source_count", 0),
                "selection_action": action,
                "selection_reason": reason,
            }
        )
    selected = []
    selected_reasons = {}
    for qtype in QUESTION_TYPE_ORDER:
        candidates = sorted(
            by_type.get(qtype, []),
            key=lambda sample: selection_priority(
                sample,
                question_stats[str(sample.get("question_id") or "")],
                decisions.get(str(sample.get("question_id") or ""), {}),
            ),
            reverse=True,
        )
        for rank, sample in enumerate(candidates[:per_type], start=1):
            qid = str(sample.get("question_id") or "")
            selected.append(sample)
            selected_ids.add(qid)
            stats = question_stats[qid]
            selected_reasons[qid] = (
                f"selected balanced subset rank {rank}/{per_type} for {qtype}; "
                f"matched_evidence={stats['matched_evidence_count']}; "
                f"document_scope={(sample.get('metadata') or {}).get('document_scope')}; "
                f"difficulty={sample.get('difficulty')}"
            )
    for row in decision_rows:
        if row["question_id"] in selected_ids:
            row["selection_action"] = "selected"
            row["selection_reason"] = selected_reasons[row["question_id"]]
        elif row["selection_action"] == "candidate":
            row["selection_action"] = "exclude"
            row["selection_reason"] = "excluded: balanced per-type quota filled"
    return selected, decision_rows


def select_all_mapped_questions(
    samples: list[dict[str, Any]],
    question_stats: dict[str, dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected = []
    decision_rows = []
    for sample in samples:
        qid = str(sample.get("question_id") or "")
        qtype = str(sample.get("question_type") or "")
        stats = question_stats.get(qid, {})
        decision = decisions.get(qid, {})
        matched_count = stats.get("matched_evidence_count", 0)
        if matched_count < 1:
            action = "exclude"
            reason = "excluded: no mapped project evidence"
        else:
            action = "selected"
            selected.append(sample)
            phase8 = decision.get("action") or "no_decision"
            reason = (
                f"selected full DQE current-gold catalog; phase8_action={phase8}; "
                f"matched_evidence={matched_count}; "
                f"document_scope={(sample.get('metadata') or {}).get('document_scope')}; "
                f"difficulty={sample.get('difficulty')}"
            )
        decision_rows.append(
            {
                "question_id": qid,
                "question_type": qtype,
                "phase8_action": decision.get("action") or "",
                "matched_evidence_count": matched_count,
                "original_evidence_source_count": stats.get("evidence_source_count", 0),
                "selection_action": action,
                "selection_reason": reason,
            }
        )
    return selected, decision_rows


def build_capability_tags(
    samples: list[dict[str, Any]],
    mapping_rows_by_qid: dict[str, list[dict[str, Any]]],
    question_stats: dict[str, dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for sample in samples:
        qid = str(sample.get("question_id") or "")
        metadata = sample.get("metadata") if isinstance(sample.get("metadata"), dict) else {}
        mapping_rows = mapping_rows_by_qid.get(qid, [])
        matched_rows = [row for row in mapping_rows if row.get("matched")]
        source_docs = sample.get("source_docs") or []
        source_type_mix = sorted({str(row.get("source_type") or "") for row in matched_rows if row.get("source_type")})
        match_methods = sorted({str(row.get("match_method") or "") for row in matched_rows if row.get("match_method")})
        resolution_statuses = sorted(
            {
                str(row.get("source_id_resolution_status") or "")
                for row in mapping_rows
                if row.get("source_id_resolution_status")
            }
        )
        phase8_action = decisions.get(qid, {}).get("action") or "no_decision"
        matched_count = question_stats.get(qid, {}).get("matched_evidence_count", 0)
        answer_key_point_count = len(sample.get("answer_key_points") or [])
        source_doc_count = len(set(str(doc) for doc in source_docs))
        tags = []
        if matched_count >= 2:
            tags.append("multi_evidence_ge2")
        if matched_count >= 3:
            tags.append("multi_evidence_ge3")
        if metadata.get("document_scope") == "multi_document" or source_doc_count >= 2:
            tags.append("multi_document")
        if metadata.get("modality") == "multimodal_document" or {"table", "image_description"} & set(source_type_mix):
            tags.append("table_or_multimodal")
        if "repaired_from_gold_evidence" in resolution_statuses:
            tags.append("source_unit_repair_review")
        if phase8_action == "replace":
            tags.append("phase8_replace_stress")
        if sample.get("question_type") == "aggregation_calculation":
            tags.append("calculation")
        if sample.get("difficulty") == "hard":
            tags.append("hard")
        if answer_key_point_count >= 5:
            tags.append("keypoint_dense")
        if matched_count >= 2 and answer_key_point_count >= 4:
            tags.append("selection_stress_candidate")
        rows.append(
            {
                "question_id": qid,
                "question_type": sample.get("question_type") or "",
                "difficulty": sample.get("difficulty") or "",
                "document_scope": metadata.get("document_scope") or "",
                "modality": metadata.get("modality") or "",
                "source_docs": source_docs,
                "source_doc_count": source_doc_count,
                "evidence_source_count": len(sample.get("evidence_source_ids") or []),
                "matched_evidence_count": matched_count,
                "source_type_mix": source_type_mix,
                "answer_key_point_count": answer_key_point_count,
                "requires_calculation": sample.get("question_type") == "aggregation_calculation",
                "phase8_action": phase8_action,
                "source_unit_resolution_statuses": resolution_statuses,
                "match_methods": match_methods,
                "capability_tags": sorted(tags),
            }
        )
    return rows


def build_slice_manifest(capability_rows: list[dict[str, Any]]) -> dict[str, Any]:
    def by_tag(tag: str) -> list[str]:
        return [
            row["question_id"]
            for row in capability_rows
            if tag in set(row.get("capability_tags") or [])
        ]

    def by_field(field: str, value: Any) -> list[str]:
        return [row["question_id"] for row in capability_rows if row.get(field) == value]

    slices = {
        "dqe_full_mapped": {
            "criteria": "all selected mapped DQE current-gold questions",
            "question_ids": [row["question_id"] for row in capability_rows],
        },
        "dqe_phase8_keep": {
            "criteria": "phase8_action == keep",
            "question_ids": by_field("phase8_action", "keep"),
        },
        "dqe_phase8_replace_stress": {
            "criteria": "phase8_action == replace; stress/error-analysis only unless manually promoted",
            "question_ids": by_tag("phase8_replace_stress"),
        },
        "dqe_multi_evidence_ge2": {
            "criteria": "matched_evidence_count >= 2",
            "question_ids": by_tag("multi_evidence_ge2"),
        },
        "dqe_multi_evidence_ge3": {
            "criteria": "matched_evidence_count >= 3",
            "question_ids": by_tag("multi_evidence_ge3"),
        },
        "dqe_multi_document": {
            "criteria": "document_scope == multi_document or source_doc_count >= 2",
            "question_ids": by_tag("multi_document"),
        },
        "dqe_table_multimodal_stress": {
            "criteria": "modality == multimodal_document or source_type_mix includes table/image_description",
            "question_ids": by_tag("table_or_multimodal"),
        },
        "dqe_repair_review_set": {
            "criteria": "source unit id repaired by paired gold evidence",
            "question_ids": by_tag("source_unit_repair_review"),
        },
        "dqe_calculation": {
            "criteria": "question_type == aggregation_calculation",
            "question_ids": by_tag("calculation"),
        },
        "dqe_hard": {
            "criteria": "difficulty == hard",
            "question_ids": by_tag("hard"),
        },
        "dqe_selection_stress_candidates": {
            "criteria": "matched_evidence_count >= 2 and answer_key_point_count >= 4",
            "question_ids": by_tag("selection_stress_candidate"),
        },
    }
    return {
        "slice_count": len(slices),
        "slices": {
            name: {
                **payload,
                "count": len(payload["question_ids"]),
            }
            for name, payload in slices.items()
        },
    }


def write_full_experiment_plan(
    path: Path,
    *,
    dataset_path: Path,
    output_dir_pattern: str,
    project_dir: Path,
    mapping_dir: Path,
) -> None:
    content = f"""# Full DQE ERC Experiment Plan

## Inputs

- Dataset: `{dataset_path}`
- Project: `{project_dir}`
- Mapping audit: `{mapping_dir / "mapping_audit.md"}`
- Capability tags: `{mapping_dir / "dqe_capability_tags.jsonl"}`
- Slice manifest: `{mapping_dir / "dqe_slice_manifest.json"}`

## Full Live Ablation

```bash
uv run python tools/erc_full_eval.py \\
  --dataset {dataset_path} \\
  --output-dir {output_dir_pattern} \\
  --backend live \\
  --live-project-dir {project_dir} \\
  --skip-live-build \\
  --configs B0 B1 B2 B3 B4 B5 B6 B7 Full \\
  --judge-mode llm \\
  --skip-report
```

## Full Gold-Replay Harness Check

```bash
uv run python tools/erc_full_eval.py \\
  --dataset {dataset_path} \\
  --output-dir benchmark/erc_dqe_full_gold_replay_<timestamp> \\
  --backend gold_replay \\
  --configs B0 B1 B2 B3 B4 B5 B6 B7 Full \\
  --skip-report
```

## Required Post-Run Analysis

- Produce `per_question_component_attribution.jsonl`.
- Produce `dqe_slice_metrics.tsv`.
- Produce `component_delta_by_slice.tsv`.
- Update `docs/research/erc_traceable_rag_report.md` only from the live artifact.
"""
    path.write_text(content, encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Path]:
    timestamp = args.timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = Path(args.output_root)
    audit_dir = output_root / f"erc_dqe_dataset_audit_{timestamp}"
    mapping_dir = output_root / f"erc_dqe_mapping_{timestamp}"
    if args.selection_mode == "all":
        dataset_path = output_root / f"erc_evidence_questions_dqe_full_{timestamp}.jsonl"
    else:
        dataset_path = output_root / f"erc_evidence_questions_dqe_{timestamp}.jsonl"

    gold_samples_path = Path(args.gold_samples)
    current_report_path = Path(args.current_report)
    question_detail_path = Path(args.question_detail)
    benchmark_runs_root = Path(args.benchmark_runs_root)
    project_dir = Path(args.project_dir)

    samples = load_gold_samples(gold_samples_path)
    decisions = load_replacement_decisions(benchmark_runs_root)
    question_detail = load_question_detail_summary(question_detail_path)
    audit, preview_rows = build_dataset_audit(samples, decisions, question_detail)
    audit["inputs"] = {
        "gold_samples": str(gold_samples_path),
        "current_report": str(current_report_path),
        "question_detail": str(question_detail_path),
        "benchmark_runs_root": str(benchmark_runs_root),
    }
    if current_report_path.exists():
        audit["current_report_bytes"] = current_report_path.stat().st_size
    write_json(audit_dir / "dataset_audit.json", audit)
    (audit_dir / "dataset_audit.md").write_text(render_dataset_audit_md(audit), encoding="utf-8")
    write_jsonl(audit_dir / "candidate_questions_preview.jsonl", preview_rows)

    source_units, source_unit_conflicts = load_jsonl_map(
        source_preparation_paths(benchmark_runs_root, "source_units.jsonl"),
        "source_id",
    )
    evidence_index, evidence_index_conflicts = load_jsonl_map(
        source_preparation_paths(benchmark_runs_root, "evidence_index.jsonl"),
        "source_id",
    )
    chunks = load_project_chunks(project_dir)
    mapping_rows, resolved_matches = map_evidence_items(samples, source_units, evidence_index, chunks)
    unmatched_rows = [
        {
            **row,
            "unmatched_reason": row.get("reason") or "",
        }
        for row in mapping_rows
        if not row.get("matched")
    ]
    question_stats = per_question_mapping_stats_from_rows(samples, mapping_rows)
    write_jsonl(mapping_dir / "source_unit_to_chunk_map.jsonl", mapping_rows)
    write_jsonl(mapping_dir / "unmatched_evidence.jsonl", unmatched_rows)
    (mapping_dir / "mapping_audit.md").write_text(
        render_mapping_audit_md(
            samples,
            mapping_rows,
            question_stats,
            chunks,
            source_unit_conflicts,
            evidence_index_conflicts,
        ),
        encoding="utf-8",
    )
    write_json(
        mapping_dir / "mapping_audit.json",
        {
            "project_dir": str(project_dir),
            "project_chunk_count": len(chunks),
            "source_unit_count": len(source_units),
            "evidence_index_count": len(evidence_index),
            "required_evidence_item_count": len(mapping_rows),
            "matched_evidence_item_count": sum(1 for item in mapping_rows if item.get("matched")),
            "unmatched_evidence_item_count": sum(1 for item in mapping_rows if not item.get("matched")),
            "unique_resolved_source_unit_count": len(
                {row["resolved_source_unit_id"] for row in mapping_rows}
            ),
            "unique_matched_source_unit_count": len(
                {row["resolved_source_unit_id"] for row in mapping_rows if row.get("matched")}
            ),
            "source_unit_repair_count": sum(
                1
                for row in mapping_rows
                if row.get("source_id_resolution_status") == "repaired_from_gold_evidence"
            ),
            "low_confidence_original_source_unit_count": sum(
                1
                for row in mapping_rows
                if row.get("source_id_resolution_status") == "low_confidence_original_source_unit"
            ),
            "question_mapping_stats": question_stats,
            "source_unit_conflicts": source_unit_conflicts,
            "evidence_index_conflicts": evidence_index_conflicts,
        },
    )

    if args.selection_mode == "all":
        selected, selection_rows = select_all_mapped_questions(samples, question_stats, decisions)
    else:
        selected, selection_rows = select_balanced_subset(
            samples,
            question_stats,
            decisions,
            args.per_type,
        )
    write_jsonl(mapping_dir / "question_selection_decisions.jsonl", selection_rows)
    selected_reason_by_id = {
        row["question_id"]: row["selection_reason"]
        for row in selection_rows
        if row["selection_action"] == "selected"
    }
    mapping_rows_by_qid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in mapping_rows:
        mapping_rows_by_qid[str(row.get("question_id") or "")].append(row)
    if args.selection_mode == "all":
        dataset_id = f"dqe_gold_mapped_full_{len(selected)}"
    else:
        dataset_id = f"dqe_gold_mapped_balanced_{args.per_type * len(QUESTION_TYPE_ORDER)}"
    erc_records = [
        record
        for sample in selected
        for record in [
            build_erc_record(
                sample,
                mapping_rows_by_qid[str(sample.get("question_id") or "")],
                evidence_index,
                dataset_id,
                selected_reason_by_id.get(str(sample.get("question_id") or ""), ""),
            )
        ]
        if record is not None
    ]
    write_jsonl(dataset_path, erc_records)
    selected_samples_by_id = {str(sample.get("question_id") or ""): sample for sample in selected}
    selected_capability_rows = build_capability_tags(
        [selected_samples_by_id[record["id"]] for record in erc_records],
        mapping_rows_by_qid,
        question_stats,
        decisions,
    )
    write_jsonl(mapping_dir / "dqe_capability_tags.jsonl", selected_capability_rows)
    slice_manifest = build_slice_manifest(selected_capability_rows)
    write_json(mapping_dir / "dqe_slice_manifest.json", slice_manifest)
    output_dir_pattern = (
        f"benchmark/erc_full_eval_dqe_full_{timestamp}"
        if args.selection_mode == "all"
        else f"benchmark/erc_full_eval_dqe_{timestamp}"
    )
    write_full_experiment_plan(
        mapping_dir / "full_experiment_plan.md",
        dataset_path=dataset_path,
        output_dir_pattern=output_dir_pattern,
        project_dir=project_dir,
        mapping_dir=mapping_dir,
    )
    write_json(
        mapping_dir / "dataset_manifest.json",
        {
            "dataset_path": str(dataset_path),
            "dataset_id": dataset_id,
            "record_count": len(erc_records),
            "selection_mode": args.selection_mode,
            "per_type_target": args.per_type,
            "selected_by_type": dict(Counter(record["question_type"] for record in erc_records)),
            "slice_manifest": str(mapping_dir / "dqe_slice_manifest.json"),
            "capability_tags": str(mapping_dir / "dqe_capability_tags.jsonl"),
            "full_experiment_plan": str(mapping_dir / "full_experiment_plan.md"),
            "audit_dir": str(audit_dir),
            "mapping_dir": str(mapping_dir),
        },
    )
    return {"audit_dir": audit_dir, "mapping_dir": mapping_dir, "dataset_path": dataset_path}


def main() -> None:
    outputs = run(parse_args())
    print(json.dumps({key: str(value) for key, value in outputs.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
