#!/usr/bin/env python3
"""Run ERC traceable RAG evaluations.

`gold_replay` is a deterministic harness sanity backend. It never represents
paper-ready system performance. `live` runs the configured Ragent retrieval and
answer path, preserves raw traces, and scores answer quality with a fixed judge.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
import os
import platform
import re
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = REPO_ROOT / "benchmark" / "erc_evidence_questions.jsonl"
DEFAULT_REPORT = REPO_ROOT / "docs" / "research" / "erc_traceable_rag_report.md"
DEFAULT_CONFIG_ORDER = ["B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "Full"]
DEFAULT_LIVE_CONFIG_ORDER = ["B0", "B1", "B2", "B5", "Full"]
FULL_CACHE_PHASES = [
    "full_no_cache",
    "retrieval_cache_warm",
    "answer_cache_warm",
    "keyword_candidate_cache_warm",
]
LIVE_PDFS = [
    "成人肥胖食养指南_2024.pdf",
    "成人高血压食养指南_2022.pdf",
    "中国居民膳食指南_2022.pdf",
    "GB-31607-2021.pdf",
    "GB29938-2020.pdf",
    "GB31647-2018.pdf",
    "GBT1354-2018bz.pdf",
    "GBT22106-2008dz.pdf",
]


@dataclass(frozen=True)
class EvalConfig:
    config_id: str
    name: str
    description: str
    uses_chunk: bool
    uses_entity: bool
    uses_relation: bool
    uses_graph_expansion: bool
    uses_query_variants: bool
    uses_rerank: bool
    uses_evidence_selection: bool
    retrieved_ref_ratio: float
    final_ref_ratio: float
    entity_ratio: float
    relation_ratio: float
    distractor_count: int
    base_latency_seconds: float


CONFIGS: dict[str, EvalConfig] = {
    "B0": EvalConfig("B0", "Flat Chunk RAG", "Chunk-vector-only baseline.", True, False, False, False, False, False, False, 0.42, 0.34, 0.0, 0.0, 2, 0.82),
    "B1": EvalConfig("B1", "Chunk + Rerank", "Chunk vector retrieval with rerank ordering.", True, False, False, False, False, True, False, 0.55, 0.45, 0.0, 0.0, 1, 1.02),
    "B2": EvalConfig("B2", "Graph-only", "Entity/relation retrieval plus graph-neighborhood chunks.", False, True, True, True, False, False, False, 0.66, 0.58, 0.78, 0.72, 1, 1.18),
    "B3": EvalConfig("B3", "Chunk + Entity", "Chunk retrieval fused with entity evidence.", True, True, False, False, False, False, False, 0.64, 0.54, 0.78, 0.0, 1, 1.16),
    "B4": EvalConfig("B4", "Chunk + Entity + Relation", "Chunk retrieval fused with entity and relation evidence.", True, True, True, False, False, False, False, 0.74, 0.62, 0.82, 0.82, 1, 1.31),
    "B5": EvalConfig("B5", "+ Graph Expansion", "B4 plus graph-neighborhood expansion.", True, True, True, True, False, False, False, 0.83, 0.72, 0.88, 0.88, 1, 1.46),
    "B6": EvalConfig("B6", "+ Query Variants", "B5 plus query variants for multi-constraint coverage.", True, True, True, True, True, False, False, 0.91, 0.81, 0.93, 0.92, 1, 1.63),
    "B7": EvalConfig("B7", "+ Rerank", "B6 plus rerank.", True, True, True, True, True, True, False, 0.95, 0.87, 0.95, 0.95, 0, 1.79),
    "Full": EvalConfig("Full", "B7 + Evidence Selection", "Full ERC retrieval with coverage-aware final evidence selection.", True, True, True, True, True, True, True, 1.0, 1.0, 1.0, 1.0, 0, 1.94),
}


METRIC_FIELDS = [
    "config_id",
    "config_name",
    "cache_phase",
    "backend",
    "question_count",
    "correctness",
    "completeness",
    "relevance",
    "faithfulness",
    "numerical_accuracy",
    "evidence_recall_at_k",
    "final_evidence_recall",
    "citation_precision",
    "citation_recall",
    "required_evidence_coverage",
    "unsupported_claim_rate",
    "latency_p50_seconds",
    "latency_p95_seconds",
    "latency_mean_seconds",
    "cache_hit_stages",
    "keyword_sources",
    "rerank_used",
]

SECRET_ENV_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD")
ALLOWED_LIVE_LLM_MODEL_URL = "https://api.deepseek.com"
ALLOWED_LIVE_LLM_MODEL = "deepseek-v4-flash"
INTERESTING_ENV_KEYS = [
    "WORKSPACE",
    "LLM_MODEL",
    "LLM_MODEL_URL",
    "EMBEDDING_MODEL",
    "EMBEDDING_MODEL_URL",
    "RERANK_MODEL",
    "RERANK_MODEL_URL",
    "ENABLE_RERANK",
    "TOP_K",
    "CHUNK_TOP_K",
    "QUERY_CACHE_TTL_SECONDS",
    "QUERY_CACHE_MAX_ENTRIES",
    "RAG_ANSWER_PROMPT_MODE",
    "RAG_INDEX_TIMEOUT_SECONDS",
    "RAG_INSERT_BATCH_SIZE",
    "RAG_INSERT_HARD_TIMEOUT",
    "RAG_INSERT_TIMEOUT_SECONDS",
    "MINERU_PARSE_MODE",
]


def _normalize_model_url(value: str | None) -> str:
    return str(value or "").strip().rstrip("/")


def _validate_live_llm_model_policy(
    *,
    backend: str,
    skip_live_build: bool,
    live_query_runner: Callable[..., Any] | None,
    judge_mode: str,
    judge_func: Callable[..., Any] | None,
) -> None:
    if backend != "live":
        return

    external_llm_needed = (
        not skip_live_build
        or live_query_runner is None
        or (judge_mode == "llm" and judge_func is None)
    )
    if not external_llm_needed:
        return

    actual_url = _normalize_model_url(os.getenv("LLM_MODEL_URL"))
    actual_model = str(os.getenv("LLM_MODEL") or "").strip()
    if actual_url == ALLOWED_LIVE_LLM_MODEL_URL and actual_model == ALLOWED_LIVE_LLM_MODEL:
        return

    raise ValueError(
        "ERC live runs that call an external LLM must use "
        f"LLM_MODEL_URL={ALLOWED_LIVE_LLM_MODEL_URL} and "
        f"LLM_MODEL={ALLOWED_LIVE_LLM_MODEL}. "
        f"Current values are LLM_MODEL_URL={actual_url or '<unset>'} and "
        f"LLM_MODEL={actual_model or '<unset>'}."
    )


def _live_llm_model_policy_manifest() -> dict[str, Any]:
    return {
        "allowed_model_url": ALLOWED_LIVE_LLM_MODEL_URL,
        "allowed_model": ALLOWED_LIVE_LLM_MODEL,
        "actual_model_url": _normalize_model_url(os.getenv("LLM_MODEL_URL")),
        "actual_model": str(os.getenv("LLM_MODEL") or "").strip(),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ERC full evaluation.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output-dir", default="")
    parser.add_argument(
        "--backend",
        default="gold_replay",
        choices=["gold_replay", "live"],
        help="gold_replay is sanity-only; live runs Ragent.",
    )
    parser.add_argument(
        "--configs",
        nargs="+",
        default=None,
        help="Config ids to run. Defaults to B0..Full for gold_replay and B0/B1/B2/B5/Full for live.",
    )
    parser.add_argument("--skip-report", action="store_true")
    parser.add_argument("--report-output", default=str(DEFAULT_REPORT))
    parser.add_argument("--live-project-dir", default="", help="Existing live project dir. If omitted, live builds a fresh project.")
    parser.add_argument("--skip-live-build", action="store_true", help="Use --live-project-dir without building fresh projects.")
    parser.add_argument("--judge-mode", choices=["llm", "heuristic"], default="llm")
    parser.add_argument(
        "--resume-partial",
        action="store_true",
        help="For live runs, append to existing results/judge JSONL files and skip completed result rows.",
    )
    parser.add_argument("--live-max-attempts", type=int, default=3, help="Live query attempts per row.")
    parser.add_argument("--live-retry-sleep", type=float, default=15.0, help="Seconds between live query retries.")
    parser.add_argument(
        "--live-concurrency",
        type=int,
        default=1,
        help="Concurrent live rows within one config/cache phase. Cache phase boundaries remain sequential.",
    )
    parser.add_argument(
        "--live-query-timeout",
        type=float,
        default=0.0,
        help="Seconds before timing out one live query attempt; 0 disables the timeout.",
    )
    parser.add_argument(
        "--live-judge-timeout",
        type=float,
        default=0.0,
        help="Seconds before marking one live judge call failed; 0 disables the timeout.",
    )
    parser.add_argument(
        "--clear-cache-per-live-row",
        action="store_true",
        help="For live full_no_cache rows, clear query caches before every request; this forces strict cold-row execution.",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=None,
        help="Optional dataset ids to include, e.g. A_health_nutrition.",
    )
    parser.add_argument("--question-limit", type=int, default=0, help="Debug limit; 0 means all questions.")
    return parser.parse_args()


def _repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else REPO_ROOT / path


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def load_dataset(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            record["_line_number"] = line_number
            records.append(record)
    return records


def _stable_hash(value: Any, length: int = 12) -> str:
    digest = hashlib.sha1(
        json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return digest[:length]


def _source_ref_parts(source_ref: str) -> tuple[str, str]:
    if "|" not in source_ref:
        return source_ref.strip(), ""
    doc, rest = source_ref.split("|", 1)
    return doc.strip(), rest.strip()


def _page_numbers_from_source_ref(source_ref: str) -> list[int]:
    match = re.search(r"\bp\.\s*(\d+)(?:\s*-\s*(\d+))?", source_ref)
    if not match:
        return []
    start = int(match.group(1))
    end = int(match.group(2) or start)
    if end < start or end - start > 50:
        return [start]
    return list(range(start, end + 1))


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def _required_evidence(record: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = record.get("required_evidence")
    if isinstance(evidence, list) and evidence:
        return [dict(item) for item in evidence if isinstance(item, dict)]
    refs = list(record.get("required_source_refs") or [])
    chunk_ids = list(record.get("required_chunk_ids") or [])
    items = []
    for index, source_ref in enumerate(refs):
        doc, section = _source_ref_parts(str(source_ref))
        chunk_id = str(chunk_ids[index]) if index < len(chunk_ids) and chunk_ids[index] else ""
        items.append(
            {
                "source_ref": str(source_ref),
                "chunk_id": chunk_id,
                "file_path": doc,
                "page_numbers": [],
                "section_path": section,
                "annotation_status": "unresolved",
            }
        )
    return items


def _required_chunks_for_gold_replay(record: dict[str, Any]) -> list[dict[str, Any]]:
    chunks = []
    for index, evidence in enumerate(_required_evidence(record)):
        source_ref = str(evidence.get("source_ref") or "")
        doc, section = _source_ref_parts(source_ref)
        chunk_id = evidence.get("chunk_id") or f"gold-replay-{record['id'].lower()}-{_stable_hash(source_ref, 8)}"
        chunks.append(
            {
                "rank": index + 1,
                "chunk_id": str(chunk_id),
                "source_ref": source_ref,
                "file_path": evidence.get("file_path") or doc,
                "page": None,
                "page_numbers": list(evidence.get("page_numbers") or []),
                "section": evidence.get("section_path") or section,
                "section_path": evidence.get("section_path") or section,
                "source": "gold_replay_sanity_evidence",
                "content": f"{source_ref}. Gold replay support: {record['gold_answer']}",
                "entities": list(record.get("required_entities") or []),
                "relations": list(record.get("required_relations") or []),
                "is_required": True,
            }
        )
    return chunks


def _distractor_chunks(records: list[dict[str, Any]], record: dict[str, Any], count: int) -> list[dict[str, Any]]:
    if count <= 0:
        return []
    required_refs = {item.get("source_ref") for item in _required_evidence(record)}
    chunks = []
    for candidate in records:
        if candidate["id"] == record["id"] or candidate.get("dataset") != record.get("dataset"):
            continue
        for evidence in _required_evidence(candidate):
            source_ref = evidence.get("source_ref")
            if source_ref in required_refs:
                continue
            doc, section = _source_ref_parts(str(source_ref))
            chunks.append(
                {
                    "rank": 0,
                    "chunk_id": f"gold-distractor-{_stable_hash([record['id'], source_ref], 8)}",
                    "source_ref": str(source_ref),
                    "file_path": doc,
                    "page": None,
                    "page_numbers": list(evidence.get("page_numbers") or []),
                    "section": section,
                    "section_path": section,
                    "source": "gold_replay_distractor",
                    "content": f"{source_ref}. Distractor support from {candidate['id']}.",
                    "entities": list(candidate.get("required_entities") or [])[:2],
                    "relations": list(candidate.get("required_relations") or [])[:1],
                    "is_required": False,
                }
            )
            if len(chunks) >= count:
                return chunks
    return chunks


def _coverage_count(total: int, ratio: float) -> int:
    if total <= 0 or ratio <= 0:
        return 0
    return min(total, max(1, math.ceil(total * min(ratio, 1.0))))


def _question_penalty(record: dict[str, Any], config: EvalConfig) -> float:
    penalty = 0.0
    question_type = str(record.get("question_type") or "")
    if question_type.startswith("cross_doc") and not config.uses_query_variants:
        penalty += 0.12
    if record.get("requires_calculation") and not config.uses_evidence_selection:
        penalty += 0.08
    if record.get("difficulty") == "hard" and not config.uses_graph_expansion:
        penalty += 0.05
    return penalty


def _effective_ratio(base_ratio: float, record: dict[str, Any], config: EvalConfig) -> float:
    if base_ratio <= 0:
        return 0.0
    if config.config_id == "Full":
        return 1.0
    return max(0.05, base_ratio - _question_penalty(record, config))


def _cache_hit_stages(cache_phase: str) -> list[str]:
    return {
        "full_no_cache": [],
        "retrieval_cache_warm": ["retrieval_cache_hit", "render_cache_hit", "prompt_cache_hit"],
        "answer_cache_warm": ["answer_cache_hit"],
        "keyword_candidate_cache_warm": ["keyword_candidate_cache_hit"],
    }.get(cache_phase, [])


def _stage_timings(record: dict[str, Any], config: EvalConfig, cache_phase: str) -> list[dict[str, Any]]:
    complexity = 1.0 + 0.10 * max(0, len(_required_evidence(record)) - 1)
    complexity += 0.14 if record.get("requires_calculation") else 0.0
    complexity += 0.08 if record.get("difficulty") == "hard" else 0.0
    base = config.base_latency_seconds * complexity
    if cache_phase == "retrieval_cache_warm":
        base *= 0.58
    elif cache_phase == "answer_cache_warm":
        base *= 0.08
    elif cache_phase == "keyword_candidate_cache_warm":
        base *= 0.86
    stages = [{"stage": "keyword_extraction", "label": "keyword extraction", "seconds": round(base * 0.08, 6)}]
    if config.uses_chunk:
        stages.append({"stage": "vector_retrieval", "label": "vector retrieval", "seconds": round(base * 0.18, 6)})
    if config.uses_entity:
        stages.append({"stage": "entity_retrieval", "label": "entity retrieval", "seconds": round(base * 0.11, 6)})
    if config.uses_relation:
        stages.append({"stage": "relation_retrieval", "label": "relation retrieval", "seconds": round(base * 0.12, 6)})
    if config.uses_graph_expansion:
        stages.append({"stage": "graph_expansion", "label": "graph expansion", "seconds": round(base * 0.11, 6)})
    if config.uses_rerank:
        stages.append({"stage": "rerank", "label": "rerank", "seconds": round(base * 0.10, 6)})
    if config.uses_evidence_selection:
        stages.append({"stage": "final_context_selection", "label": "final evidence selection", "seconds": round(base * 0.05, 6)})
    stages.append({"stage": "answer_generation", "label": "answer generation", "seconds": round(base * 0.22, 6)})
    for hit_stage in _cache_hit_stages(cache_phase):
        stages.append({"stage": hit_stage, "label": hit_stage, "seconds": 0.0, "hit_count": 1 if hit_stage == "keyword_candidate_cache_hit" else 0})
    stages.append({"stage": "onehop_total", "label": "OneHop total", "seconds": round(sum(float(item["seconds"]) for item in stages), 6)})
    return stages


def _latency_total(stage_timings: list[dict[str, Any]]) -> float:
    for item in reversed(stage_timings):
        if item.get("stage") == "onehop_total":
            return float(item.get("seconds") or 0.0)
    return sum(float(item.get("seconds") or 0.0) for item in stage_timings)


def _keyword_payload(record: dict[str, Any], config: EvalConfig) -> tuple[str, list[str], list[str]]:
    entities = [str(item) for item in record.get("required_entities") or []]
    relations = [str(item) for item in record.get("required_relations") or []]
    if not (config.uses_entity or config.uses_relation or config.uses_graph_expansion):
        tokens = [token for token in str(record.get("question") or "").replace("，", " ").split() if token][:6]
        return "not_required_chunk_only", [], tokens
    return "gold_request_sanity", relations[:4], entities[:6]


def _select_gold_replay_evidence(records: list[dict[str, Any]], record: dict[str, Any], config: EvalConfig) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], list[str]]:
    required = _required_chunks_for_gold_replay(record)
    retrieved_count = _coverage_count(len(required), _effective_ratio(config.retrieved_ref_ratio, record, config))
    final_count = _coverage_count(len(required), _effective_ratio(config.final_ref_ratio, record, config))
    retrieved = required[:retrieved_count] + _distractor_chunks(records, record, config.distractor_count)
    for rank, chunk in enumerate(retrieved, start=1):
        chunk["rank"] = rank
        if chunk["is_required"]:
            if config.uses_graph_expansion and not config.uses_chunk:
                chunk["source"] = "graph_entity_relation_sanity"
            elif config.uses_graph_expansion:
                chunk["source"] = "chunk_vector+graph_expansion_sanity"
            elif config.uses_entity or config.uses_relation:
                chunk["source"] = "chunk_vector+graph_seed_sanity"
            else:
                chunk["source"] = "chunk_vector_sanity"
    final = [chunk.copy() for chunk in retrieved if chunk.get("is_required")][:final_count]
    if not config.uses_evidence_selection and retrieved and len(final) < len(retrieved):
        final.extend([chunk.copy() for chunk in retrieved if not chunk.get("is_required")][:1])
    for rank, chunk in enumerate(final, start=1):
        chunk["rank"] = rank
    entity_count = _coverage_count(len(record.get("required_entities") or []), _effective_ratio(config.entity_ratio, record, config))
    relation_count = _coverage_count(len(record.get("required_relations") or []), _effective_ratio(config.relation_ratio, record, config))
    entities = [str(item) for item in (record.get("required_entities") or [])[:entity_count]]
    relations = [str(item) for item in (record.get("required_relations") or [])[:relation_count]]
    return retrieved, final, entities, relations


def _ratio(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 1.0
    return round(float(numerator) / float(denominator), 6)


def _mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 6) if values else 0.0


CONTENT_OVERLAP_THRESHOLD = 0.5


def _char_ngrams(value: Any, n: int = 5) -> set[str]:
    text = re.sub(r"\s+", "", str(value or ""))
    if not text:
        return set()
    if len(text) < n:
        return {text}
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def _content_overlap(gold: Any, candidate: Any) -> float:
    gold_grams = _char_ngrams(gold)
    if not gold_grams:
        return 0.0
    cand_grams = _char_ngrams(candidate)
    if not cand_grams:
        return 0.0
    return len(gold_grams & cand_grams) / len(gold_grams)


def _concept_present(concept: str, available: set[str]) -> bool:
    if not concept:
        return False
    if concept in available:
        return True
    return any((concept in item or item in concept) for item in available if len(item) >= 2)


def _relation_endpoints(relation: Any) -> list[str]:
    parts = re.split(r"->|→|-->|—>", str(relation))
    endpoints: list[str] = []
    for part in parts:
        core = re.split(r"[<>=≥≤]+", part)[0]
        norm = _normalize_text(core)
        if norm:
            endpoints.append(norm)
    return endpoints


def _coverage_by_concept(required: list[str], available: set[str]) -> tuple[int, int]:
    hits = 0
    total = 0
    for item in required:
        norm = _normalize_text(item)
        if not norm:
            continue
        total += 1
        if _concept_present(norm, available):
            hits += 1
    return hits, total


def _match_required(evidence: dict[str, Any], chunk: dict[str, Any], *, strict: bool = False) -> bool:
    chunk_id = str(chunk.get("chunk_id") or chunk.get("id") or "").strip()
    required_chunk_id = str(evidence.get("chunk_id") or "").strip()
    if required_chunk_id and chunk_id == required_chunk_id:
        return True

    if strict:
        # Live evidence matching: require an exact chunk id (above) or genuine
        # content overlap. We intentionally do NOT match on filename/section
        # co-occurrence, which would inflate recall whenever any chunk from the
        # same document/section is retrieved instead of the annotated chunk.
        gold_content = evidence.get("content")
        chunk_content = chunk.get("content") or chunk.get("preview")
        if (
            gold_content
            and chunk_content
            and _content_overlap(gold_content, chunk_content) >= CONTENT_OVERLAP_THRESHOLD
        ):
            return True
        return False

    required_ref = str(evidence.get("source_ref") or "")
    chunk_ref = str(chunk.get("source_ref") or chunk.get("source_refs_display") or "")
    required_doc, required_section = _source_ref_parts(required_ref)
    haystack = " ".join(
        [
            chunk_ref,
            str(chunk.get("file_path") or ""),
            str(chunk.get("section") or chunk.get("section_path") or ""),
            str(chunk.get("content") or chunk.get("preview") or ""),
        ]
    )
    if required_doc and Path(required_doc).name not in haystack:
        return False
    section_norm = _normalize_text(required_section)
    if not section_norm:
        return bool(required_doc)
    haystack_norm = _normalize_text(haystack)
    if section_norm in haystack_norm:
        return True
    terms = [term for term in re.split(r"[/|、,，\s]+", required_section) if len(_normalize_text(term)) >= 2]
    if not terms:
        return False
    matched_terms = sum(1 for term in terms if _normalize_text(term) in haystack_norm)
    return matched_terms >= max(1, math.ceil(len(terms) * 0.5))


def _matched_required_count(required: list[dict[str, Any]], chunks: list[dict[str, Any]], *, strict: bool = False) -> int:
    count = 0
    for evidence in required:
        if any(_match_required(evidence, chunk, strict=strict) for chunk in chunks):
            count += 1
    return count


def _metrics_for_result(result: dict[str, Any]) -> dict[str, float]:
    strict = str(result.get("backend_kind")) == "live"
    required = _required_evidence(result)
    retrieved = list(result.get("retrieved_contexts") or [])
    final = list(result.get("final_evidence_chunks") or [])
    citations = list(result.get("citations") or [])
    citation_chunks = [
        {
            "chunk_id": item.get("chunk_id"),
            "source_ref": item.get("source_ref"),
            "file_path": item.get("file_path"),
            "section_path": item.get("section") or item.get("section_path"),
            "content": item.get("content") or item.get("preview"),
        }
        for item in citations
        if isinstance(item, dict)
    ]
    retrieved_matches = _matched_required_count(required, retrieved, strict=strict)
    final_matches = _matched_required_count(required, final, strict=strict)
    citation_matches = _matched_required_count(required, citation_chunks, strict=strict)

    required_entities = [str(item) for item in (result.get("required_entities") or [])]
    required_relations = [str(item) for item in (result.get("required_relations") or [])]
    selected_entities = [str(item) for item in (result.get("entities") or [])]
    selected_relations = [str(item) for item in (result.get("relations") or [])]
    selected_relations_set = set(selected_relations)

    # Build the set of concepts the retrieval actually surfaced (entity names
    # plus relation endpoints), ignoring raw chunk ids that pollute graph hits.
    available_concepts: set[str] = set()
    for entity in selected_entities:
        if entity.startswith("chunk-"):
            continue
        norm = _normalize_text(entity)
        if norm:
            available_concepts.add(norm)
    for relation in selected_relations:
        for endpoint in _relation_endpoints(relation):
            if endpoint.startswith("chunk-"):
                continue
            available_concepts.add(endpoint)

    evidence_recall_at_k = _ratio(retrieved_matches, len(required))
    final_evidence_recall = _ratio(final_matches, len(required))
    citation_precision = _ratio(citation_matches, len(citation_chunks))
    citation_recall = _ratio(citation_matches, len(required))

    entity_hits, entity_total = _coverage_by_concept(required_entities, available_concepts)
    entity_coverage = _ratio(entity_hits, entity_total)

    relation_hits = 0
    for relation in required_relations:
        if relation in selected_relations_set:
            relation_hits += 1
            continue
        endpoints = _relation_endpoints(relation)
        if endpoints and all(_concept_present(endpoint, available_concepts) for endpoint in endpoints):
            relation_hits += 1
    relation_coverage = _ratio(relation_hits, len(required_relations))

    required_evidence_coverage = _mean([final_evidence_recall, citation_recall, entity_coverage, relation_coverage])
    relevance = _ratio(
        sum(1 for chunk in retrieved if any(_match_required(evidence, chunk, strict=strict) for evidence in required)),
        len(retrieved),
    )
    unsupported_claim_rate = round(max(0.0, 1.0 - final_evidence_recall), 6)
    return {
        "correctness": round(min(1.0, 0.25 + 0.75 * required_evidence_coverage), 6),
        "completeness": required_evidence_coverage,
        "relevance": relevance,
        "faithfulness": round(1.0 - unsupported_claim_rate, 6),
        "numerical_accuracy": round(min(final_evidence_recall, relation_coverage), 6) if result.get("requires_calculation") else 1.0,
        "evidence_recall_at_k": evidence_recall_at_k,
        "final_evidence_recall": final_evidence_recall,
        "citation_precision": citation_precision,
        "citation_recall": citation_recall,
        "required_evidence_coverage": required_evidence_coverage,
        "unsupported_claim_rate": unsupported_claim_rate,
    }


def _build_answer(record: dict[str, Any], config: EvalConfig, coverage: float) -> str:
    if config.config_id == "Full" and coverage >= 1.0:
        return str(record["gold_answer"])
    return f"[{config.config_id} sanity coverage={coverage:.2f}] {record['gold_answer']}"


def evaluate_gold_replay_record(records: list[dict[str, Any]], record: dict[str, Any], config: EvalConfig, *, cache_phase: str, backend: str, run_id: str) -> dict[str, Any]:
    retrieved, final, entities, relations = _select_gold_replay_evidence(records, record, config)
    keyword_source, high_level_keywords, low_level_keywords = _keyword_payload(record, config)
    stage_timings = _stage_timings(record, config, cache_phase)
    result = {
        "run_id": run_id,
        "backend": backend,
        "backend_kind": "sanity",
        "cache_phase": cache_phase,
        "config_id": config.config_id,
        "config_name": config.name,
        "question_id": record["id"],
        "dataset": record["dataset"],
        "question": record["question"],
        "gold_answer": record["gold_answer"],
        "required_source_refs": list(record.get("required_source_refs") or []),
        "required_chunk_ids": list(record.get("required_chunk_ids") or []),
        "required_evidence": _required_evidence(record),
        "required_entities": list(record.get("required_entities") or []),
        "required_relations": list(record.get("required_relations") or []),
        "question_type": record["question_type"],
        "difficulty": record["difficulty"],
        "requires_calculation": bool(record.get("requires_calculation")),
        "retrieved_contexts": retrieved,
        "final_evidence_chunks": final,
        "citations": [
            {
                "source_ref": chunk.get("source_ref"),
                "chunk_id": chunk.get("chunk_id"),
                "page": chunk.get("page"),
                "page_numbers": chunk.get("page_numbers") or [],
                "section": chunk.get("section") or chunk.get("section_path"),
                "file_path": chunk.get("file_path"),
            }
            for chunk in final
            if chunk.get("source_ref")
        ],
        "entities": entities,
        "relations": relations,
        "stage_timings": stage_timings,
        "cache_hit_stages": _cache_hit_stages(cache_phase),
        "keyword_source": keyword_source,
        "high_level_keywords": high_level_keywords,
        "low_level_keywords": low_level_keywords,
        "rerank_used": config.uses_rerank,
        "rerank_status": "enabled" if config.uses_rerank else "disabled",
        "mode": "hybrid",
        "retrieval_only": False,
        "evaluation_note": "Gold replay sanity backend; not a live experiment result.",
    }
    metrics = _metrics_for_result(result)
    result["metrics"] = metrics
    result["answer"] = _build_answer(record, config, metrics["required_evidence_coverage"])
    result["latency_seconds"] = _latency_total(stage_timings)
    return result


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 6)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(ordered[int(position)], 6)
    weight = position - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 6)


def aggregate_metrics(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    config_order = [config for config in DEFAULT_CONFIG_ORDER if any(result["config_id"] == config for result in results)]
    phase_order = [phase for phase in FULL_CACHE_PHASES if any(result["cache_phase"] == phase for result in results)]
    for result in results:
        grouped[(result["config_id"], result["cache_phase"])].append(result)
    rows = []
    for config_id in config_order:
        for cache_phase in phase_order:
            group = grouped.get((config_id, cache_phase), [])
            if not group:
                continue
            metrics = defaultdict(list)
            for result in group:
                for metric_name, value in result["metrics"].items():
                    metrics[metric_name].append(float(value))
            latencies = [float(result["latency_seconds"]) for result in group]
            rows.append(
                {
                    "config_id": config_id,
                    "config_name": group[0]["config_name"],
                    "cache_phase": cache_phase,
                    "backend": group[0]["backend"],
                    "question_count": str(len(group)),
                    "correctness": f"{_mean(metrics['correctness']):.4f}",
                    "completeness": f"{_mean(metrics['completeness']):.4f}",
                    "relevance": f"{_mean(metrics['relevance']):.4f}",
                    "faithfulness": f"{_mean(metrics['faithfulness']):.4f}",
                    "numerical_accuracy": f"{_mean(metrics['numerical_accuracy']):.4f}",
                    "evidence_recall_at_k": f"{_mean(metrics['evidence_recall_at_k']):.4f}",
                    "final_evidence_recall": f"{_mean(metrics['final_evidence_recall']):.4f}",
                    "citation_precision": f"{_mean(metrics['citation_precision']):.4f}",
                    "citation_recall": f"{_mean(metrics['citation_recall']):.4f}",
                    "required_evidence_coverage": f"{_mean(metrics['required_evidence_coverage']):.4f}",
                    "unsupported_claim_rate": f"{_mean(metrics['unsupported_claim_rate']):.4f}",
                    "latency_p50_seconds": f"{_percentile(latencies, 0.50):.4f}",
                    "latency_p95_seconds": f"{_percentile(latencies, 0.95):.4f}",
                    "latency_mean_seconds": f"{_mean(latencies):.4f}",
                    "cache_hit_stages": ",".join(sorted({hit for item in group for hit in item.get("cache_hit_stages", [])})),
                    "keyword_sources": ",".join(sorted({str(item.get("keyword_source") or "") for item in group if item.get("keyword_source")})),
                    "rerank_used": str(any(item.get("rerank_used") for item in group)).lower(),
                }
            )
    return rows


def write_metrics_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METRIC_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _sqlite_json_entries(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    with sqlite3.connect(path) as connection:
        rows = connection.execute("select key, entry_json from kv_entries").fetchall()
    return {key: json.loads(entry_json) for key, entry_json in rows}


def _load_json_map(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_project_chunks(project_dir: Path) -> dict[str, dict[str, Any]]:
    json_chunks = _load_json_map(project_dir / "kv_store_text_chunks.json")
    if json_chunks:
        return {key: dict(value, _id=key) for key, value in json_chunks.items() if isinstance(value, dict)}
    sqlite_chunks = _sqlite_json_entries(project_dir / "kv_store_text_chunks.sqlite")
    return {key: dict(value, _id=key) for key, value in sqlite_chunks.items() if isinstance(value, dict)}


def _chunk_match_score(required_ref: str, chunk_id: str, chunk: dict[str, Any]) -> float:
    required_doc, required_section = _source_ref_parts(required_ref)
    required_doc_name = Path(required_doc).name
    haystack = " ".join(
        [
            chunk_id,
            str(chunk.get("source_ref") or ""),
            str(chunk.get("file_path") or ""),
            str(chunk.get("section_path") or ""),
            str(chunk.get("content") or ""),
        ]
    )
    if required_doc_name and required_doc_name not in haystack:
        return -1.0
    score = 50.0
    required_section_norm = _normalize_text(required_section)
    haystack_norm = _normalize_text(haystack)
    if required_section_norm and required_section_norm in haystack_norm:
        score += 50.0
    terms = [term for term in re.split(r"[/|、,，\s]+", required_section) if len(_normalize_text(term)) >= 2]
    for term in terms:
        if _normalize_text(term) in haystack_norm:
            score += 8.0
    if chunk.get("page_numbers"):
        score += 3.0
    return score


def annotate_dataset_with_project(records: list[dict[str, Any]], project_dir: Path) -> list[dict[str, Any]]:
    chunks = load_project_chunks(project_dir)
    annotated = []
    for record in records:
        updated = dict(record)
        existing_evidence = [
            dict(item)
            for item in record.get("required_evidence") or []
            if isinstance(item, dict)
        ]
        if existing_evidence:
            chunk_ids = []
            for evidence in existing_evidence:
                chunk_id = str(evidence.get("chunk_id") or "").strip()
                chunk = chunks.get(chunk_id) if chunk_id else None
                if chunk:
                    evidence.setdefault("source_ref", chunk.get("source_ref") or "")
                    evidence.setdefault("file_path", chunk.get("file_path") or "")
                    evidence.setdefault("page_numbers", list(chunk.get("page_numbers") or []))
                    evidence.setdefault("section_path", chunk.get("section_path") or "")
                    evidence.setdefault("annotation_status", "matched_project_chunk")
                    if chunk.get("content") and not evidence.get("content"):
                        evidence["content"] = chunk.get("content")
                if chunk_id:
                    chunk_ids.append(chunk_id)
            updated["required_evidence"] = existing_evidence
            updated["required_chunk_ids"] = chunk_ids
            annotated.append(updated)
            continue
        evidence_rows = []
        chunk_ids = []
        notes = []
        for required_ref in record.get("required_source_refs") or []:
            best_id = ""
            best_chunk: dict[str, Any] | None = None
            best_score = -1.0
            for chunk_id, chunk in chunks.items():
                score = _chunk_match_score(str(required_ref), chunk_id, chunk)
                if score > best_score:
                    best_id = chunk_id
                    best_chunk = chunk
                    best_score = score
            if best_chunk and best_score >= 58.0:
                page_numbers = list(best_chunk.get("page_numbers") or [])
                source_ref = str(best_chunk.get("source_ref") or required_ref)
                section_path = str(best_chunk.get("section_path") or _source_ref_parts(str(required_ref))[1])
                evidence_rows.append(
                    {
                        "source_ref": source_ref,
                        "chunk_id": best_id,
                        "file_path": best_chunk.get("file_path") or _source_ref_parts(str(required_ref))[0],
                        "page_numbers": page_numbers,
                        "section_path": section_path,
                        "annotation_status": "matched_project_chunk",
                        "required_source_ref": str(required_ref),
                        "match_score": round(best_score, 3),
                    }
                )
                chunk_ids.append(best_id)
            else:
                doc, section = _source_ref_parts(str(required_ref))
                evidence_rows.append(
                    {
                        "source_ref": str(required_ref),
                        "chunk_id": "",
                        "file_path": doc,
                        "page_numbers": [],
                        "section_path": section,
                        "annotation_status": "unmatched_project_chunk",
                        "annotation_reason": "No project chunk passed document/section match threshold.",
                    }
                )
                notes.append(str(required_ref))
        updated["required_evidence"] = evidence_rows
        updated["required_chunk_ids"] = chunk_ids
        if notes:
            updated["provenance_annotation_notes"] = notes
        annotated.append(updated)
    return annotated


def _vdb_count(path: Path) -> int:
    payload = _load_json_map(path)
    data = payload.get("data")
    return len(data) if isinstance(data, list) else 0


def _graph_counts(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    root = ET.parse(path).getroot()
    namespace = {"g": "http://graphml.graphdrawing.org/xmlns"}
    return len(root.findall(".//g:node", namespace)), len(root.findall(".//g:edge", namespace))


def _core_file_digest(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.suffix == ".sqlite":
        entries = _sqlite_json_entries(path)
        payload = json.dumps(entries, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_snapshot(project_dir: Path) -> dict[str, Any]:
    graph_nodes, graph_edges = _graph_counts(project_dir / "graph_chunk_entity_relation.graphml")
    doc_status = _load_json_map(project_dir / "kv_store_doc_status.json")
    full_docs = _sqlite_json_entries(project_dir / "kv_store_full_docs.sqlite") or _load_json_map(project_dir / "kv_store_full_docs.json")
    text_chunks = load_project_chunks(project_dir)
    files = [
        "graph_chunk_entity_relation.graphml",
        "vdb_chunks.json",
        "vdb_entities.json",
        "vdb_relationships.json",
        "kv_store_doc_status.json",
        "kv_store_full_docs.sqlite",
        "kv_store_text_chunks.sqlite",
        "kv_store_index_metadata.sqlite",
    ]
    file_digests = {name: _core_file_digest(project_dir / name) for name in files if (project_dir / name).exists()}
    return {
        "project_dir": _display_path(project_dir),
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
        "entity_vdb": _vdb_count(project_dir / "vdb_entities.json"),
        "relationship_vdb": _vdb_count(project_dir / "vdb_relationships.json"),
        "chunk_vdb": _vdb_count(project_dir / "vdb_chunks.json"),
        "doc_status": len(doc_status),
        "full_docs": len(full_docs),
        "text_chunks": len(text_chunks),
        "file_digests": file_digests,
        "digest": _stable_hash(file_digests, 32),
    }


def remove_query_cache_files(project_dir: Path) -> None:
    for name in (
        "kv_store_llm_response_cache.sqlite",
        "kv_store_llm_response_cache.sqlite-wal",
        "kv_store_llm_response_cache.sqlite-shm",
        "kv_store_llm_response_cache.json",
    ):
        path = project_dir / name
        if path.exists():
            path.unlink()


def write_gold_replay_separation(output_dir: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    separation_dir = output_dir / "build_inference_separation"
    separation_dir.mkdir(parents=True, exist_ok=True)
    raw_units = []
    for record in records:
        raw_units.append(
            {
                "schema_version": 1,
                "question_id": record["id"],
                "source_refs": list(record.get("required_source_refs") or []),
                "chunks": _required_chunks_for_gold_replay(record),
                "metadata": {"dataset": record["dataset"], "backend_kind": "sanity"},
            }
        )
    _write_jsonl(separation_dir / "raw_units.jsonl", raw_units)
    source_refs = sorted({ref for record in records for ref in record.get("required_source_refs") or []})
    entities = sorted({item for record in records for item in record.get("required_entities") or []})
    relations = sorted({item for record in records for item in record.get("required_relations") or []})
    snapshot = {
        "graph_nodes": len(entities),
        "graph_edges": len(relations),
        "entity_vdb": len(entities),
        "relationship_vdb": len(relations),
        "chunk_vdb": sum(len(_required_evidence(record)) for record in records),
        "doc_status": len({_source_ref_parts(ref)[0] for ref in source_refs}),
        "digest": _stable_hash({"source_refs": source_refs, "entities": entities, "relations": relations}, 32),
    }
    summary = {
        "backend_kind": "sanity",
        "raw_units_path": _display_path(separation_dir / "raw_units.jsonl"),
        "raw_units_count": len(raw_units),
        "online_build_snapshot": snapshot,
        "offline_replay_snapshot": dict(snapshot),
        "online_vs_replay_match": True,
        "readonly_before": dict(snapshot),
        "readonly_after": dict(snapshot),
        "readonly_snapshot_unchanged": True,
        "note": "Gold replay sanity snapshot derived from gold question metadata; not a live build/replay validation.",
    }
    for name in ["online_build_snapshot", "offline_replay_snapshot", "readonly_before", "readonly_after"]:
        _write_json(separation_dir / f"{name}.json", summary[name] if name in summary else snapshot)
    _write_json(separation_dir / "separation_summary.json", summary)
    return summary


def _redacted_env_lines() -> list[str]:
    lines = [
        f"cwd={REPO_ROOT}",
        f"python_executable={sys.executable}",
        f"python_version={sys.version.split()[0]}",
        f"platform={platform.platform()}",
    ]
    git_result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if git_result.returncode == 0:
        lines.append(f"git_commit={git_result.stdout.strip()}")
    observed_env = 0
    for key in INTERESTING_ENV_KEYS:
        value = os.getenv(key)
        if value in (None, ""):
            continue
        observed_env += 1
        redacted = "***REDACTED***" if any(marker in key.upper() for marker in SECRET_ENV_MARKERS) else value
        lines.append(f"{key}={redacted}")
    lines.append(f"interesting_env_keys_observed={observed_env}")
    return lines


def _append_command_history(output_dir: Path, entry: dict[str, Any]) -> None:
    history_path = output_dir / "logs" / "command_history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def _read_command_history(output_dir: Path) -> list[dict[str, Any]]:
    history_path = output_dir / "logs" / "command_history.jsonl"
    if not history_path.exists():
        return []
    entries = []
    for line in history_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _completed_command_by_label(output_dir: Path) -> dict[str, dict[str, Any]]:
    completed: dict[str, dict[str, Any]] = {}
    for entry in _read_command_history(output_dir):
        if entry.get("status") == "completed" and entry.get("returncode") == 0:
            completed[str(entry.get("label"))] = entry
    return completed


def _unique_log_path(logs_dir: Path, label: str, stream_name: str) -> Path:
    base = logs_dir / f"{label}.{stream_name}.log"
    if not base.exists():
        return base
    suffix = 2
    while True:
        candidate = logs_dir / f"{label}.{suffix}.{stream_name}.log"
        if not candidate.exists():
            return candidate
        suffix += 1


def _run_command(command: list[str], *, output_dir: Path, label: str, commands: list[dict[str, Any]], timeout: int = 28800) -> None:
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    started_at = time.time()
    stdout_path = _unique_log_path(logs_dir, label, "stdout")
    stderr_path = _unique_log_path(logs_dir, label, "stderr")
    started_entry = {
        "label": label,
        "command": " ".join(command),
        "status": "started",
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "stdout": _display_path(stdout_path),
        "stderr": _display_path(stderr_path),
    }
    _append_command_history(output_dir, started_entry)
    with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_fh, stderr_path.open("w", encoding="utf-8", errors="replace") as stderr_fh:
        try:
            result = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                stdout=stdout_fh,
                stderr=stderr_fh,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            timeout_entry = {
                **started_entry,
                "status": "timeout",
                "seconds": round(time.time() - started_at, 3),
                "timeout_seconds": timeout,
            }
            _append_command_history(output_dir, timeout_entry)
            commands.append(timeout_entry)
            raise
    commands.append(
        {
            "label": label,
            "command": " ".join(command),
            "status": "completed",
            "returncode": result.returncode,
            "seconds": round(time.time() - started_at, 3),
            "stdout": _display_path(stdout_path),
            "stderr": _display_path(stderr_path),
        }
    )
    _append_command_history(output_dir, commands[-1])
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({label}) rc={result.returncode}: {' '.join(command)}")


def build_live_projects(output_dir: Path, *, live_project_dir: Path | None, skip_live_build: bool) -> tuple[Path, dict[str, Any], list[dict[str, Any]]]:
    commands: list[dict[str, Any]] = []
    build_dir = output_dir / "build_inference_separation"
    build_dir.mkdir(parents=True, exist_ok=True)
    if skip_live_build:
        if live_project_dir is None:
            raise ValueError("--skip-live-build requires --live-project-dir")
        working_project = build_dir / "existing_project_copy"
        if working_project.exists():
            shutil.rmtree(working_project)
        shutil.copytree(live_project_dir, working_project)
        remove_query_cache_files(working_project)
        snapshot = project_snapshot(working_project)
        summary = {
            "backend_kind": "live",
            "build_mode": "existing_project_copy",
            "source_project_dir": _display_path(live_project_dir),
            "raw_units_count": 0,
            "online_build_snapshot": snapshot,
            "offline_replay_snapshot": {},
            "online_vs_replay_match": None,
            "readonly_before": snapshot,
            "readonly_after": snapshot,
            "readonly_snapshot_unchanged": True,
            "note": "Existing project was copied into the benchmark directory; fresh build/replay separation was not executed.",
        }
        _write_json(build_dir / "separation_summary.json", summary)
        _write_json(build_dir / "readonly_before.json", snapshot)
        return working_project, summary, commands

    mineru_dir = build_dir / "mineru"
    raw_dir = build_dir / "raw_units"
    online_project = live_project_dir or (build_dir / "online_project")
    offline_project = build_dir / "offline_replay_project"
    for path in [mineru_dir, raw_dir, online_project, offline_project]:
        path.mkdir(parents=True, exist_ok=True)

    completed_commands = _completed_command_by_label(output_dir)
    for index, pdf_name in enumerate(LIVE_PDFS, 1):
        pdf_path = REPO_ROOT / "example" / pdf_name
        if not pdf_path.exists():
            raise FileNotFoundError(f"Missing live PDF: {pdf_path}")
        label = f"online_build_{index:02d}_{pdf_path.stem}"
        if label in completed_commands:
            commands.append({**completed_commands[label], "status": "reused_completed"})
            continue
        _run_command(
            [sys.executable, "singlefile.py", "parse", str(pdf_path), str(mineru_dir), str(online_project), "auto"],
            output_dir=output_dir,
            label=label,
            commands=commands,
        )
    for index, pdf_name in enumerate(LIVE_PDFS, 1):
        pdf_path = REPO_ROOT / "example" / pdf_name
        label = f"raw_export_{index:02d}_{pdf_path.stem}"
        if label in completed_commands:
            commands.append({**completed_commands[label], "status": "reused_completed"})
            continue
        _run_command(
            [sys.executable, "singlefile.py", "parse", str(pdf_path), str(mineru_dir), str(raw_dir), "raw"],
            output_dir=output_dir,
            label=label,
            commands=commands,
        )

    raw_jsonls = sorted(raw_dir.glob("*.jsonl"))
    if not raw_jsonls:
        raise RuntimeError(f"No raw unit JSONL files were exported: {raw_dir}")
    if "offline_replay" in completed_commands:
        commands.append({**completed_commands["offline_replay"], "status": "reused_completed"})
    else:
        _run_command(
            [
                "env",
                "RAG_VECTOR_UPSERT_SEQUENTIAL_EMBEDDING=1",
                "EMBEDDING_TIMEOUT_SECONDS=90",
                sys.executable,
                "tools/replay_raw_merge_units_to_project.py",
                str(raw_dir),
                "-o",
                str(offline_project),
                "--overwrite",
                "--llm-model-max-async",
                "1",
                "--embedding-func-max-async",
                "1",
                "--embedding-batch-num",
                "10",
            ],
            output_dir=output_dir,
            label="offline_replay",
            commands=commands,
        )

    online_snapshot = project_snapshot(online_project)
    offline_snapshot = project_snapshot(offline_project)
    readonly_before = project_snapshot(offline_project)
    readonly_after = project_snapshot(offline_project)
    summary = {
        "backend_kind": "live",
        "build_mode": "fresh_online_and_raw_replay",
        "pdfs": LIVE_PDFS,
        "raw_units_dir": _display_path(raw_dir),
        "raw_units_count": len(raw_jsonls),
        "online_build_snapshot": online_snapshot,
        "offline_replay_snapshot": offline_snapshot,
        "online_vs_replay_match": online_snapshot.get("digest") == offline_snapshot.get("digest"),
        "readonly_before": readonly_before,
        "readonly_after": readonly_after,
        "readonly_snapshot_unchanged": readonly_before.get("digest") == readonly_after.get("digest"),
        "note": "Digest excludes disposable query cache files; raw replay uses a different command path from online build.",
    }
    _write_json(build_dir / "online_build_snapshot.json", online_snapshot)
    _write_json(build_dir / "offline_replay_snapshot.json", offline_snapshot)
    _write_json(build_dir / "readonly_before.json", readonly_before)
    _write_json(build_dir / "readonly_after.json", readonly_after)
    _write_json(build_dir / "separation_summary.json", summary)
    return offline_project, summary, commands


def finalize_readonly_snapshot(
    output_dir: Path,
    project_dir: Path,
    separation_summary: dict[str, Any],
) -> dict[str, Any]:
    build_dir = output_dir / "build_inference_separation"
    readonly_after = project_snapshot(project_dir)
    readonly_before = separation_summary.get("readonly_before") or {}
    separation_summary["readonly_after"] = readonly_after
    separation_summary["readonly_snapshot_unchanged"] = (
        readonly_before.get("digest") == readonly_after.get("digest")
    )
    _write_json(build_dir / "readonly_after.json", readonly_after)
    _write_json(build_dir / "separation_summary.json", separation_summary)
    return separation_summary


def _normalize_live_chunk(item: dict[str, Any], rank: int | None = None) -> dict[str, Any]:
    source_ref = item.get("source_ref") or item.get("source_refs_display") or item.get("file_path") or ""
    page_numbers = item.get("page_numbers") or []
    if not page_numbers:
        page_numbers = _page_numbers_from_source_ref(str(source_ref))
    page = item.get("page") or item.get("page_number_start")
    if page is None and isinstance(page_numbers, list) and page_numbers:
        page = page_numbers[0]
    normalized = {
        "rank": rank if rank is not None else item.get("rank"),
        "chunk_id": item.get("chunk_id") or item.get("id") or "",
        "source_ref": source_ref,
        "file_path": item.get("file_path") or "",
        "page": page,
        "page_numbers": page_numbers,
        "section": item.get("section") or item.get("section_path") or "",
        "section_path": item.get("section_path") or item.get("section") or "",
        "source": item.get("source") or item.get("recall_type") or "",
        "score": item.get("score") or item.get("rerank_score"),
        "content": item.get("content") or item.get("preview") or "",
        "preview": item.get("preview") or str(item.get("content") or "")[:220],
    }
    for key in ("sources", "matched_query_variants", "source_chunk_ids", "source_refs"):
        if item.get(key) not in (None, "", [], {}):
            normalized[key] = item.get(key)
    return normalized


def _dedupe_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped = []
    for chunk in chunks:
        key = (str(chunk.get("chunk_id") or ""), str(chunk.get("source_ref") or ""))
        if key in seen:
            continue
        seen.add(key)
        chunk["rank"] = len(deduped) + 1
        deduped.append(chunk)
    return deduped


def _resolve_final_chunk_ids(debug_payload: dict[str, Any], raw_final_items: list[Any]) -> list[str]:
    """Recover the real project chunk ids for the final evidence chunks.

    The pipeline renumbers final context chunks with display ordinals, so the
    original ``chunk-<hash>`` ids must be recovered from the parallel
    ``results_chunk_ids`` array via ``selected_candidate_indexes`` (primary) or
    a content lookup (fallback).
    """
    results_chunk_ids = [str(cid) for cid in (debug_payload.get("results_chunk_ids") or [])]
    selected = list(debug_payload.get("selected_candidate_indexes") or [])
    results_text = list(debug_payload.get("results_text") or [])
    content_to_id: dict[str, str] = {}
    for text, cid in zip(results_text, results_chunk_ids):
        key = re.sub(r"\s+", "", str(text))[:160]
        if key and key not in content_to_id:
            content_to_id[key] = cid
    resolved: list[str] = []
    for index, item in enumerate(raw_final_items):
        chunk_id = ""
        if isinstance(item, dict):
            existing = str(item.get("chunk_id") or "")
            if existing.startswith("chunk-"):
                chunk_id = existing
        if not chunk_id and index < len(selected):
            idx = selected[index]
            if isinstance(idx, int) and 0 <= idx < len(results_chunk_ids):
                chunk_id = results_chunk_ids[idx]
        if not chunk_id and isinstance(item, dict):
            key = re.sub(r"\s+", "", str(item.get("content") or ""))[:160]
            chunk_id = content_to_id.get(key, "")
        resolved.append(chunk_id)
    return resolved


def _live_config_to_query_param(config: EvalConfig, cache_phase: str):
    from ragent.base import QueryParam

    param = QueryParam(mode="hybrid")
    param.enable_chunk_retrieval = config.uses_chunk
    param.enable_graph_retrieval = bool(config.uses_entity or config.uses_relation)
    param.enable_entity_retrieval = config.uses_entity
    param.enable_relation_retrieval = config.uses_relation
    param.enable_graph_expansion = config.uses_graph_expansion
    param.enable_query_variants = config.uses_query_variants
    param.enable_evidence_selection = config.uses_evidence_selection
    param.enable_rerank = config.uses_rerank
    param.response_type = "Multiple Paragraphs"
    if cache_phase == "keyword_candidate_cache_warm":
        param.keyword_cache_enabled = True
        param.keyword_cache_read_enabled = True
        param.keyword_cache_write_enabled = True
    return param


async def _finish_live_query(rag: Any) -> None:
    try:
        await rag._query_done()
    except Exception:
        pass


async def _run_live_query(rag: Any, record: dict[str, Any], config: EvalConfig, cache_phase: str) -> dict[str, Any]:
    from ragent.operate import hybrid_query

    param = _live_config_to_query_param(config, cache_phase)
    global_config = await rag._build_runtime_global_config()
    started_at = time.perf_counter()
    try:
        answer, referenced_file_paths, debug_payload = await hybrid_query(
            str(record["question"]),
            rag.chunks_vdb,
            rag.chunk_entity_relation_graph,
            rag.relationships_vdb,
            rag.entities_vdb,
            rag.text_chunks,
            param,
            global_config,
            rag.llm_response_cache,
            return_debug=True,
        )
        wall_seconds = round(time.perf_counter() - started_at, 6)
    finally:
        await _finish_live_query(rag)
    trace_chunks = []
    for collection_name in ("vector_candidates", "graph_chunk_candidates", "merged_candidates", "rerank_output_candidates"):
        for item in debug_payload.get(collection_name) or []:
            if isinstance(item, dict):
                trace_chunks.append(_normalize_live_chunk(item))
    raw_final_items = debug_payload.get("final_context_document_chunks") or debug_payload.get("final_context_chunks") or []
    resolved_final_ids = _resolve_final_chunk_ids(debug_payload, raw_final_items)
    final_chunks = []
    for index, item in enumerate(raw_final_items):
        if not isinstance(item, dict):
            continue
        normalized = _normalize_live_chunk(item, rank=index + 1)
        real_id = resolved_final_ids[index] if index < len(resolved_final_ids) else ""
        if real_id:
            normalized["chunk_id"] = real_id
        final_chunks.append(normalized)
    if not final_chunks:
        final_chunks = [_normalize_live_chunk(item) for item in debug_payload.get("text_units_context") or [] if isinstance(item, dict)]
    entity_hits = debug_payload.get("graph_entities") or []
    relation_hits = debug_payload.get("graph_relations") or []
    return {
        "answer": answer,
        "referenced_file_paths": referenced_file_paths,
        "retrieved_contexts": _dedupe_chunks(trace_chunks),
        "final_evidence_chunks": _dedupe_chunks(final_chunks),
        "entities": [str(item.get("entity")) for item in entity_hits if isinstance(item, dict) and item.get("entity")],
        "relations": [
            f"{item.get('entity1')} -> {item.get('entity2')}"
            for item in relation_hits
            if isinstance(item, dict) and item.get("entity1") and item.get("entity2")
        ],
        "stage_timings": list(debug_payload.get("stage_timings") or []),
        "cache_hit_stages": _cache_hit_stages_from_timings(debug_payload.get("stage_timings") or []),
        "keyword_source": debug_payload.get("keyword_source"),
        "high_level_keywords": list(debug_payload.get("high_level_keywords") or []),
        "low_level_keywords": list(debug_payload.get("low_level_keywords") or []),
        "rerank_used": bool(debug_payload.get("rerank_used")),
        "rerank_status": "enabled" if debug_payload.get("rerank_used") else str(debug_payload.get("rerank_skip_reason") or "disabled"),
        "trace": debug_payload,
        "latency_seconds": _latency_total(debug_payload.get("stage_timings") or []) or wall_seconds,
    }


async def _run_live_query_with_retries(
    runner: Callable[[Any, dict[str, Any], EvalConfig, str], Any],
    rag: Any,
    record: dict[str, Any],
    config: EvalConfig,
    cache_phase: str,
    *,
    max_attempts: int,
    retry_sleep_seconds: float,
    timeout_seconds: float = 0.0,
) -> dict[str, Any]:
    attempts = max(1, max_attempts)
    for attempt in range(1, attempts + 1):
        try:
            live_query = runner(rag, record, config, cache_phase)
            if timeout_seconds > 0:
                return await asyncio.wait_for(live_query, timeout=timeout_seconds)
            return await live_query
        except Exception as exc:
            if attempt >= attempts:
                raise
            print(
                (
                    "live query retry "
                    f"{attempt}/{attempts - 1}: "
                    f"question_id={record.get('id')} config={config.config_id} "
                    f"phase={cache_phase} error={type(exc).__name__}: {exc}"
                ),
                file=sys.stderr,
                flush=True,
            )
            if retry_sleep_seconds > 0:
                await asyncio.sleep(retry_sleep_seconds)
    raise RuntimeError("unreachable live retry state")


def _live_result_key(question_id: Any, config_id: Any, cache_phase: Any) -> tuple[str, str, str]:
    return (str(question_id), str(config_id), str(cache_phase))


def _cache_hit_stages_from_timings(stage_timings: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(item.get("stage"))
            for item in stage_timings
            if isinstance(item, dict)
            and item.get("stage")
            in {
                "answer_cache_hit",
                "retrieval_cache_hit",
                "render_cache_hit",
                "prompt_cache_hit",
                "keyword_candidate_cache_hit",
            }
        }
    )


def _heuristic_judge(record: dict[str, Any], answer: str, final_chunks: list[dict[str, Any]], evidence_metrics: dict[str, float]) -> dict[str, Any]:
    recall = evidence_metrics["final_evidence_recall"]
    faithfulness = evidence_metrics["faithfulness"]
    return {
        "correctness": round(min(1.0, 0.35 + recall * 0.65), 4),
        "completeness": round(recall, 4),
        "relevance": evidence_metrics["relevance"],
        "faithfulness": faithfulness,
        "numerical_accuracy": evidence_metrics["numerical_accuracy"],
        "unsupported_claim_rate": evidence_metrics["unsupported_claim_rate"],
        "rationale": "Heuristic fallback used; not paper-ready answer quality.",
    }


async def _llm_judge(record: dict[str, Any], answer: str, final_chunks: list[dict[str, Any]], evidence_metrics: dict[str, float]) -> dict[str, Any]:
    from ragent.llm.openai import env_openai_complete

    evidence_payload = [
        {
            "chunk_id": chunk.get("chunk_id"),
            "source_ref": chunk.get("source_ref"),
            "page_numbers": chunk.get("page_numbers"),
            "content": str(chunk.get("content") or chunk.get("preview") or "")[:800],
        }
        for chunk in final_chunks
    ]
    system_prompt = (
        "You are a strict scientific RAG evaluator. Return only valid JSON. "
        "Score each metric from 0 to 1. Do not reward unsupported claims."
    )
    prompt = json.dumps(
        {
            "rubric": {
                "correctness": "factual agreement with gold answer",
                "completeness": "covers all required aspects",
                "relevance": "answers the question without drift",
                "faithfulness": "claims are supported by supplied evidence",
                "numerical_accuracy": "calculations and thresholds are correct; use 1 if not numerical",
                "unsupported_claim_rate": "fraction of important claims unsupported by supplied evidence",
            },
            "question": record["question"],
            "gold_answer": record["gold_answer"],
            "model_answer": answer,
            "final_evidence": evidence_payload,
            "evidence_metrics": evidence_metrics,
            "required_entities": record.get("required_entities") or [],
            "required_relations": record.get("required_relations") or [],
            "required_evidence": _required_evidence(record),
        },
        ensure_ascii=False,
        indent=2,
    )
    raw = await env_openai_complete(prompt, system_prompt=system_prompt, temperature=0)
    parsed = _parse_json_from_text(raw)
    parsed["raw_judge_response"] = raw
    return parsed


def _parse_json_from_text(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        stripped = text.strip()
        try:
            payload, _ = json.JSONDecoder().raw_decode(stripped)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise
            payload, _ = json.JSONDecoder().raw_decode(match.group(0).strip())
    if not isinstance(payload, dict):
        raise ValueError("judge response is not a JSON object")
    return payload


def _coerce_judge_metrics(payload: dict[str, Any], fallback: dict[str, float]) -> dict[str, float]:
    metrics = dict(fallback)
    for key in ("correctness", "completeness", "relevance", "faithfulness", "numerical_accuracy", "unsupported_claim_rate"):
        try:
            value = float(payload.get(key))
        except (TypeError, ValueError):
            continue
        metrics[key] = round(min(1.0, max(0.0, value)), 6)
    return metrics


async def evaluate_live_records(
    records: list[dict[str, Any]],
    project_dir: Path,
    config_ids: list[str],
    run_id: str,
    *,
    output_dir: Path,
    judge_mode: str,
    live_query_runner: Callable[[Any, dict[str, Any], EvalConfig, str], Any] | None = None,
    judge_func: Callable[[dict[str, Any], str, list[dict[str, Any]], dict[str, float]], Any] | None = None,
    rag_override: Any | None = None,
    resume_partial: bool = False,
    live_max_attempts: int = 3,
    live_retry_sleep_seconds: float = 15.0,
    live_concurrency: int = 1,
    live_query_timeout_seconds: float = 0.0,
    live_judge_timeout_seconds: float = 0.0,
    clear_cache_per_live_row: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from ragent.benchmarking import clear_query_cache_entries
    from ragent.inference_runtime import _close_rag, initialize_rag

    results_path = output_dir / "results.jsonl"
    judge_path = output_dir / "judge_results.jsonl"
    if resume_partial:
        results = _load_jsonl(results_path)
        judge_rows = _load_jsonl(judge_path)
    else:
        results = []
        judge_rows = []
        for path in (results_path, judge_path):
            if path.exists():
                path.unlink()
    completed_keys = {
        _live_result_key(row.get("question_id"), row.get("config_id"), row.get("cache_phase"))
        for row in results
    }
    rag = rag_override or await initialize_rag(str(project_dir), require_llm=True, enable_rerank=True)
    runner = live_query_runner or _run_live_query

    async def evaluate_one(record: dict[str, Any], config: EvalConfig, cache_phase: str) -> None:
        key = _live_result_key(record["id"], config.config_id, cache_phase)
        if key in completed_keys:
            return
        if clear_cache_per_live_row and cache_phase == "full_no_cache":
            clear_query_cache_entries(
                project_dir,
                cache_types=["answer", "retrieval", "render", "prompt", "keyword_candidate"],
                repo_root=REPO_ROOT,
            )
        query_payload = await _run_live_query_with_retries(
            runner,
            rag,
            record,
            config,
            cache_phase,
            max_attempts=live_max_attempts,
            retry_sleep_seconds=live_retry_sleep_seconds,
            timeout_seconds=live_query_timeout_seconds,
        )
        result = _build_live_result(record, config, query_payload, run_id, cache_phase)
        new_judge_rows: list[dict[str, Any]] = []
        await _score_live_result(
            record,
            result,
            new_judge_rows,
            judge_mode,
            judge_func,
            judge_timeout_seconds=live_judge_timeout_seconds,
        )
        results.append(result)
        judge_rows.extend(new_judge_rows)
        completed_keys.add(key)
        _append_jsonl(results_path, result)
        for judge_row in new_judge_rows:
            _append_jsonl(judge_path, judge_row)

    async def evaluate_phase(records_to_run: list[dict[str, Any]], config: EvalConfig, cache_phase: str) -> None:
        phase_concurrency = live_concurrency
        if clear_cache_per_live_row and cache_phase == "full_no_cache":
            phase_concurrency = 1
        if phase_concurrency <= 1:
            for record in records_to_run:
                await evaluate_one(record, config, cache_phase)
            return

        semaphore = asyncio.Semaphore(phase_concurrency)

        async def evaluate_guarded(record: dict[str, Any]) -> None:
            async with semaphore:
                await evaluate_one(record, config, cache_phase)

        await asyncio.gather(*(evaluate_guarded(record) for record in records_to_run))

    try:
        for config_id in config_ids:
            clear_query_cache_entries(project_dir, cache_types=["answer", "retrieval", "render", "prompt", "keyword_candidate"], repo_root=REPO_ROOT)
            config = CONFIGS[config_id]
            await evaluate_phase(records, config, "full_no_cache")

        if "Full" in config_ids:
            full_config = CONFIGS["Full"]
            clear_query_cache_entries(project_dir, cache_types=["answer"], repo_root=REPO_ROOT)
            await evaluate_phase(records, full_config, "retrieval_cache_warm")

            await evaluate_phase(records, full_config, "answer_cache_warm")

            clear_query_cache_entries(project_dir, cache_types=["answer", "retrieval", "render", "prompt"], repo_root=REPO_ROOT)
            await evaluate_phase(records, full_config, "keyword_candidate_cache_warm")
    finally:
        if rag_override is None:
            await _close_rag(rag)

    return results, judge_rows


def _build_live_result(record: dict[str, Any], config: EvalConfig, query_payload: dict[str, Any], run_id: str, cache_phase: str) -> dict[str, Any]:
    final_chunks = list(query_payload.get("final_evidence_chunks") or [])
    result = {
        "run_id": run_id,
        "backend": "live",
        "backend_kind": "live",
        "cache_phase": cache_phase,
        "config_id": config.config_id,
        "config_name": config.name,
        "question_id": record["id"],
        "dataset": record["dataset"],
        "question": record["question"],
        "gold_answer": record["gold_answer"],
        "required_source_refs": list(record.get("required_source_refs") or []),
        "required_chunk_ids": list(record.get("required_chunk_ids") or []),
        "required_evidence": _required_evidence(record),
        "required_entities": list(record.get("required_entities") or []),
        "required_relations": list(record.get("required_relations") or []),
        "question_type": record["question_type"],
        "difficulty": record["difficulty"],
        "requires_calculation": bool(record.get("requires_calculation")),
        "retrieved_contexts": list(query_payload.get("retrieved_contexts") or []),
        "final_evidence_chunks": final_chunks,
        "citations": [
            {
                "source_ref": chunk.get("source_ref"),
                "chunk_id": chunk.get("chunk_id"),
                "page": chunk.get("page"),
                "page_numbers": chunk.get("page_numbers") or [],
                "section": chunk.get("section") or chunk.get("section_path"),
                "file_path": chunk.get("file_path"),
                "content": chunk.get("content") or chunk.get("preview"),
            }
            for chunk in final_chunks
            if chunk.get("source_ref") or chunk.get("chunk_id")
        ],
        "entities": list(query_payload.get("entities") or []),
        "relations": list(query_payload.get("relations") or []),
        "stage_timings": list(query_payload.get("stage_timings") or []),
        "cache_hit_stages": list(query_payload.get("cache_hit_stages") or []),
        "keyword_source": query_payload.get("keyword_source"),
        "high_level_keywords": list(query_payload.get("high_level_keywords") or []),
        "low_level_keywords": list(query_payload.get("low_level_keywords") or []),
        "rerank_used": bool(query_payload.get("rerank_used")),
        "rerank_status": query_payload.get("rerank_status"),
        "mode": "hybrid",
        "retrieval_only": False,
        "answer": str(query_payload.get("answer") or ""),
        "latency_seconds": float(query_payload.get("latency_seconds") or 0.0),
        "trace": query_payload.get("trace"),
        "evaluation_note": "Live backend result. Evidence metrics come from live retrieved/final contexts.",
    }
    result["metrics"] = _metrics_for_result(result)
    return result


async def _score_live_result(
    record: dict[str, Any],
    result: dict[str, Any],
    judge_rows: list[dict[str, Any]],
    judge_mode: str,
    judge_func: Callable[[dict[str, Any], str, list[dict[str, Any]], dict[str, float]], Any] | None,
    judge_timeout_seconds: float = 0.0,
) -> None:
    if result["cache_phase"] != "full_no_cache":
        return
    evidence_metrics = dict(result["metrics"])
    judge_payload: dict[str, Any]
    try:
        if judge_func is not None:
            judge_call = judge_func(record, result["answer"], result["final_evidence_chunks"], evidence_metrics)
            if judge_timeout_seconds > 0:
                judge_payload = await asyncio.wait_for(judge_call, timeout=judge_timeout_seconds)
            else:
                judge_payload = await judge_call
        elif judge_mode == "heuristic":
            judge_payload = _heuristic_judge(record, result["answer"], result["final_evidence_chunks"], evidence_metrics)
        else:
            judge_call = _llm_judge(record, result["answer"], result["final_evidence_chunks"], evidence_metrics)
            if judge_timeout_seconds > 0:
                judge_payload = await asyncio.wait_for(judge_call, timeout=judge_timeout_seconds)
            else:
                judge_payload = await judge_call
        result["metrics"] = _coerce_judge_metrics(judge_payload, evidence_metrics)
        status = "ok"
    except Exception as exc:
        judge_payload = {"error": str(exc), "error_type": type(exc).__name__}
        status = "failed"
    judge_rows.append(
        {
            "run_id": result["run_id"],
            "question_id": result["question_id"],
            "config_id": result["config_id"],
            "judge_mode": judge_mode,
            "status": status,
            "judge": judge_payload,
        }
    )


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return lines


def write_latency_cache_summary(path: Path, metrics_rows: list[dict[str, Any]]) -> None:
    row_map = {(row["config_id"], row["cache_phase"]): row for row in metrics_rows}
    rows = []
    for phase in FULL_CACHE_PHASES:
        row = row_map.get(("Full", phase))
        if row is None:
            continue
        rows.append([phase, row["latency_p50_seconds"], row["latency_p95_seconds"], row["latency_mean_seconds"], row["cache_hit_stages"] or "-", row["keyword_sources"]])
    lines = ["# ERC Latency And Cache Summary", ""]
    if rows:
        lines.extend(
            [
                "Full configuration cache phases over executed questions.",
                "",
                *_markdown_table(["cache_phase", "p50_s", "p95_s", "mean_s", "cache_hit_stages", "keyword_sources"], rows),
                "",
            ]
        )
    else:
        lines.extend(["No Full cache phases were executed for this config subset.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_commands_md(path: Path, commands: list[dict[str, Any]], cli_command: str) -> None:
    lines = ["# ERC Evaluation Commands", "", "## Entry Command", "", "```bash", cli_command, "```", ""]
    if commands:
        lines.extend(["## Build/Replay Commands", ""])
        for item in commands:
            lines.extend(
                [
                    f"### {item['label']}",
                    "",
                    "```bash",
                    item["command"],
                    "```",
                    "",
                    f"- status: `{item.get('status', 'completed')}`",
                    f"- returncode: `{item['returncode']}`",
                    f"- seconds: `{item['seconds']}`",
                    f"- stdout: `{item['stdout']}`",
                    f"- stderr: `{item['stderr']}`",
                    "",
                ]
            )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(
    path: Path,
    *,
    dataset_path: Path,
    records: list[dict[str, Any]],
    metrics_rows: list[dict[str, Any]],
    separation_summary: dict[str, Any],
    results: list[dict[str, Any]],
    backend: str,
    config_ids: list[str],
) -> None:
    dataset_counts = Counter(str(record["dataset"]) for record in records)
    type_counts = Counter(str(record["question_type"]) for record in records)
    row_map = {(row["config_id"], row["cache_phase"]): row for row in metrics_rows}
    main_rows = []
    for config_id in config_ids:
        row = row_map.get((config_id, "full_no_cache"))
        if row:
            main_rows.append([config_id, row["correctness"], row["completeness"], row["faithfulness"], row["numerical_accuracy"], row["required_evidence_coverage"], row["unsupported_claim_rate"]])
    evidence_rows = []
    for config_id in config_ids:
        row = row_map.get((config_id, "full_no_cache"))
        if row:
            evidence_rows.append([config_id, row["evidence_recall_at_k"], row["final_evidence_recall"], row["citation_precision"], row["citation_recall"], row["keyword_sources"], row["rerank_used"]])
    cache_rows = []
    for phase in FULL_CACHE_PHASES:
        row = row_map.get(("Full", phase))
        if row:
            cache_rows.append([phase, row["latency_p50_seconds"], row["latency_p95_seconds"], row["latency_mean_seconds"], row["cache_hit_stages"] or "-"])
    case = next((result for result in results if result["config_id"] == "Full" and result["cache_phase"] == "full_no_cache"), results[0] if results else None)
    case_path = []
    if case:
        case_path = [
            f"Question: {case['question']}",
            f"Keywords: high={case.get('high_level_keywords')} low={case.get('low_level_keywords')} source={case.get('keyword_source')}",
            "Final evidence:",
        ]
        for chunk in case.get("final_evidence_chunks") or []:
            case_path.append(
                f"- {chunk.get('chunk_id')} | {chunk.get('source_ref')} | page={chunk.get('page') or chunk.get('page_numbers')} | section={chunk.get('section') or chunk.get('section_path')}"
            )

    backend_label = "Live Evaluation" if backend == "live" else "Gold Replay Sanity Evaluation"
    lines = [
        f"# ERC {backend_label} Summary",
        "",
        f"- Dataset: `{_display_path(dataset_path)}`",
        f"- Backend: `{backend}`",
        f"- Backend kind: `{'live' if backend == 'live' else 'sanity'}`",
        f"- Questions: `{len(records)}`",
        f"- Main configs: `{', '.join(config_ids)}`",
        f"- Result rows: `{len(results)}`",
        "",
        "## Dataset Statistics",
        "",
        *_markdown_table(["dataset", "count"], [[k, v] for k, v in sorted(dataset_counts.items())]),
        "",
        *_markdown_table(["question_type", "count"], [[k, v] for k, v in sorted(type_counts.items())]),
        "",
        "## Main Quality Results",
        "",
        *_markdown_table(["config", "correctness", "completeness", "faithfulness", "numerical_accuracy", "required_coverage", "unsupported_claim_rate"], main_rows),
        "",
        "## Evidence Coverage",
        "",
        *_markdown_table(["config", "evidence_recall_at_k", "final_evidence_recall", "citation_precision", "citation_recall", "keyword_sources", "rerank_used"], evidence_rows),
        "",
        "## Latency And Cache",
        "",
        *(_markdown_table(["cache_phase", "p50_s", "p95_s", "mean_s", "cache_hit_stages"], cache_rows) if cache_rows else ["No Full cache phases were executed."]),
        "",
        "## Build And Inference Separation",
        "",
        *_markdown_table(
            ["check", "value"],
            [
                ["backend_kind", separation_summary.get("backend_kind")],
                ["build_mode", separation_summary.get("build_mode", "-")],
                ["raw_units_count", separation_summary.get("raw_units_count")],
                ["online_vs_replay_match", separation_summary.get("online_vs_replay_match")],
                ["readonly_snapshot_unchanged", separation_summary.get("readonly_snapshot_unchanged")],
                ["online_digest", (separation_summary.get("online_build_snapshot") or {}).get("digest")],
                ["replay_digest", (separation_summary.get("offline_replay_snapshot") or {}).get("digest")],
            ],
        ),
        "",
        "## ERC Retrieval Path Case",
        "",
        *case_path,
        "",
        "## Result Classification",
        "",
        "- `live`: eligible for paper tables only if build/replay and judge status succeeded.",
        "- `gold_replay`: engineering sanity check only; never report as live model performance.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def run_full_evaluation(
    *,
    dataset_path: Path = DEFAULT_DATASET,
    output_dir: Path | None = None,
    backend: str = "gold_replay",
    config_ids: list[str] | None = None,
    live_project_dir: Path | None = None,
    skip_live_build: bool = False,
    judge_mode: str = "llm",
    datasets: list[str] | None = None,
    question_limit: int = 0,
    live_query_runner: Callable[[Any, dict[str, Any], EvalConfig, str], Any] | None = None,
    judge_func: Callable[[dict[str, Any], str, list[dict[str, Any]], dict[str, float]], Any] | None = None,
    live_rag: Any | None = None,
    resume_partial: bool = False,
    live_max_attempts: int = 3,
    live_retry_sleep_seconds: float = 15.0,
    live_concurrency: int = 1,
    live_query_timeout_seconds: float = 0.0,
    live_judge_timeout_seconds: float = 0.0,
    clear_cache_per_live_row: bool = False,
) -> dict[str, Any]:
    records = load_dataset(dataset_path)
    if datasets:
        selected = set(datasets)
        records = [record for record in records if str(record.get("dataset")) in selected]
    if question_limit > 0:
        records = records[:question_limit]
    default_order = DEFAULT_LIVE_CONFIG_ORDER if backend == "live" else DEFAULT_CONFIG_ORDER
    resolved_config_ids = config_ids or list(default_order)
    unknown_configs = sorted(set(resolved_config_ids) - set(CONFIGS))
    if unknown_configs:
        raise ValueError(f"Unknown config ids: {', '.join(unknown_configs)}")
    _validate_live_llm_model_policy(
        backend=backend,
        skip_live_build=skip_live_build,
        live_query_runner=live_query_runner,
        judge_mode=judge_mode,
        judge_func=judge_func,
    )

    run_id = datetime.now().strftime("erc_full_eval_%Y%m%d_%H%M%S")
    resolved_output_dir = output_dir or (REPO_ROOT / "benchmark" / run_id)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    (resolved_output_dir / "env_snapshot.txt").write_text("\n".join(_redacted_env_lines()) + "\n", encoding="utf-8")

    build_commands: list[dict[str, Any]] = []
    if backend == "live":
        project_dir, separation_summary, build_commands = build_live_projects(
            resolved_output_dir,
            live_project_dir=live_project_dir,
            skip_live_build=skip_live_build,
        )
        records = annotate_dataset_with_project(records, project_dir)
        _write_jsonl(resolved_output_dir / "annotated_dataset.jsonl", records)
        results, judge_rows = asyncio.run(
            evaluate_live_records(
                records,
                project_dir,
                resolved_config_ids,
                run_id,
                output_dir=resolved_output_dir,
                judge_mode=judge_mode,
                live_query_runner=live_query_runner,
                judge_func=judge_func,
                rag_override=live_rag,
                resume_partial=resume_partial,
                live_max_attempts=live_max_attempts,
                live_retry_sleep_seconds=live_retry_sleep_seconds,
                live_concurrency=live_concurrency,
                live_query_timeout_seconds=live_query_timeout_seconds,
                live_judge_timeout_seconds=live_judge_timeout_seconds,
                clear_cache_per_live_row=clear_cache_per_live_row,
            )
        )
        separation_summary = finalize_readonly_snapshot(
            resolved_output_dir,
            project_dir,
            separation_summary,
        )
    else:
        separation_summary = write_gold_replay_separation(resolved_output_dir, records)
        judge_rows = []
        results = []
        for config_id in resolved_config_ids:
            config = CONFIGS[config_id]
            for record in records:
                results.append(
                    evaluate_gold_replay_record(records, record, config, cache_phase="full_no_cache", backend=backend, run_id=run_id)
                )
        if "Full" in resolved_config_ids:
            for cache_phase in FULL_CACHE_PHASES[1:]:
                for record in records:
                    results.append(
                        evaluate_gold_replay_record(records, record, CONFIGS["Full"], cache_phase=cache_phase, backend=backend, run_id=run_id)
                    )
        _write_jsonl(resolved_output_dir / "judge_results.jsonl", judge_rows)

    metrics_rows = aggregate_metrics(results)
    _write_jsonl(resolved_output_dir / "results.jsonl", results)
    write_metrics_tsv(resolved_output_dir / "metrics.tsv", metrics_rows)
    write_latency_cache_summary(resolved_output_dir / "latency_cache_summary.md", metrics_rows)
    write_summary(
        resolved_output_dir / "summary.md",
        dataset_path=dataset_path,
        records=records,
        metrics_rows=metrics_rows,
        separation_summary=separation_summary,
        results=results,
        backend=backend,
        config_ids=resolved_config_ids,
    )
    cli_command = " ".join([sys.executable, *sys.argv])
    write_commands_md(resolved_output_dir / "commands.md", build_commands, cli_command)
    _write_json(
        resolved_output_dir / "run_manifest.json",
        {
            "run_id": run_id,
            "backend": backend,
            "backend_kind": "live" if backend == "live" else "sanity",
            "created_at_epoch": int(time.time()),
            "dataset": _display_path(dataset_path),
            "output_dir": _display_path(resolved_output_dir),
            "configs": resolved_config_ids,
            "dataset_filter": datasets or [],
            "cache_phases": sorted({result["cache_phase"] for result in results}),
            "judge_mode": judge_mode if backend == "live" else "none",
            "llm_model_policy": _live_llm_model_policy_manifest() if backend == "live" else {},
            "live_concurrency": live_concurrency if backend == "live" else 0,
            "clear_cache_per_live_row": clear_cache_per_live_row if backend == "live" else False,
            "artifacts": [
                "results.jsonl",
                "judge_results.jsonl",
                "metrics.tsv",
                "summary.md",
                "latency_cache_summary.md",
                "commands.md",
                "env_snapshot.txt",
                "build_inference_separation/separation_summary.json",
            ],
        },
    )
    return {
        "output_dir": resolved_output_dir,
        "results": results,
        "metrics_rows": metrics_rows,
        "separation_summary": separation_summary,
        "judge_rows": judge_rows,
    }


def _update_report(full_eval_dir: Path, report_output: Path) -> None:
    import importlib.util

    report_tool = REPO_ROOT / "tools" / "erc_research_report.py"
    spec = importlib.util.spec_from_file_location("erc_research_report", report_tool)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load report tool: {report_tool}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        module.render_report(
            dataset_path=DEFAULT_DATASET,
            latency_path=REPO_ROOT / "benchmark" / "latency_smoke_matrix_20260422" / "results.tsv",
            retrieval_path=REPO_ROOT / "benchmark" / "retrieval_cross_no_cache_local_gliner_20260523_190243" / "results.tsv",
            keyword_cache_path=REPO_ROOT / "benchmark" / "keyword_cache_benefit_qwen4b_hybrid" / "results.tsv",
            full_eval_dir=full_eval_dir,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    output_dir = _repo_path(args.output_dir) if args.output_dir else None
    config_ids = list(args.configs) if args.configs else None
    run = run_full_evaluation(
        dataset_path=_repo_path(args.dataset),
        output_dir=output_dir,
        backend=args.backend,
        config_ids=config_ids,
        live_project_dir=_repo_path(args.live_project_dir) if args.live_project_dir else None,
        skip_live_build=args.skip_live_build,
        judge_mode=args.judge_mode,
        datasets=list(args.datasets) if args.datasets else None,
        question_limit=args.question_limit,
        resume_partial=args.resume_partial,
        live_max_attempts=args.live_max_attempts,
        live_retry_sleep_seconds=args.live_retry_sleep,
        live_concurrency=args.live_concurrency,
        live_query_timeout_seconds=args.live_query_timeout,
        live_judge_timeout_seconds=args.live_judge_timeout,
        clear_cache_per_live_row=args.clear_cache_per_live_row,
    )
    if not args.skip_report:
        _update_report(Path(run["output_dir"]), _repo_path(args.report_output))
    print(_display_path(Path(run["output_dir"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
