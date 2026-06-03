#!/usr/bin/env python3
"""Summarize a strict-match ERC live eval into slide-ready tables.

Reads a full-eval output dir (results.jsonl) and prints:
  1. Retrieval-layer table per config (recall@k, final recall, citation p/r,
     required coverage, latency).
  2. Structured-coverage ablation: entity coverage + relation coverage
     (recomputed with the same logic as tools/erc_full_eval.py).
  3. Cross-document evidence breadth.

Usage: python tools/erc_strictmatch_report.py <output_dir> [<output_dir_old>]
"""
from __future__ import annotations

import importlib.util
import json
import re
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load_module():
    spec = importlib.util.spec_from_file_location("ercfe", REPO / "tools" / "erc_full_eval.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["ercfe"] = module
    spec.loader.exec_module(module)
    return module


M = _load_module()


def _docof(chunk: dict) -> str:
    sr = str(chunk.get("source_ref") or chunk.get("file_path") or "")
    hit = re.match(r"\s*([^|]+\.pdf)", sr)
    return hit.group(1).strip() if hit else (sr.split("|")[0].strip() if sr else "")


def _entity_relation_coverage(row: dict) -> tuple[float, float]:
    req_e = [str(x) for x in (row.get("required_entities") or [])]
    req_r = [str(x) for x in (row.get("required_relations") or [])]
    sel_e = [str(x) for x in (row.get("entities") or [])]
    sel_r = [str(x) for x in (row.get("relations") or [])]
    sel_r_set = set(sel_r)
    available: set[str] = set()
    for e in sel_e:
        if e.startswith("chunk-"):
            continue
        n = M._normalize_text(e)
        if n:
            available.add(n)
    for r in sel_r:
        for ep in M._relation_endpoints(r):
            if not ep.startswith("chunk-"):
                available.add(ep)
    e_hits, e_total = M._coverage_by_concept(req_e, available)
    ent = e_hits / e_total if e_total else None
    r_hits = 0
    r_total = 0
    for r in req_r:
        r_total += 1
        if r in sel_r_set:
            r_hits += 1
            continue
        eps = M._relation_endpoints(r)
        if eps and all(M._concept_present(ep, available) for ep in eps):
            r_hits += 1
    rel = r_hits / r_total if r_total else None
    return ent, rel


def summarize(out_dir: Path) -> dict:
    rows = [json.loads(l) for l in (out_dir / "results.jsonl").open() if l.strip()]
    configs = []
    for r in rows:
        if r["config_id"] not in configs:
            configs.append(r["config_id"])
    table = {}
    for cfg in configs:
        items = [r for r in rows if r["config_id"] == cfg and r["cache_phase"] == "full_no_cache"]
        if not items:
            continue

        def mean_metric(key):
            vals = [(r.get("metrics") or {}).get(key) for r in items]
            vals = [v for v in vals if isinstance(v, (int, float))]
            return statistics.fmean(vals) if vals else float("nan")

        ents, rels, breadth = [], [], []
        for r in items:
            e, rl = _entity_relation_coverage(r)
            if e is not None:
                ents.append(e)
            if rl is not None:
                rels.append(rl)
            fc = r.get("final_evidence_chunks") or []
            docs = {_docof(c) for c in fc if _docof(c)}
            breadth.append(len(docs))
        table[cfg] = {
            "evidence_recall_at_k": mean_metric("evidence_recall_at_k"),
            "final_evidence_recall": mean_metric("final_evidence_recall"),
            "required_evidence_coverage": mean_metric("required_evidence_coverage"),
            "citation_precision": mean_metric("citation_precision"),
            "citation_recall": mean_metric("citation_recall"),
            "entity_coverage": statistics.fmean(ents) if ents else float("nan"),
            "relation_coverage": statistics.fmean(rels) if rels else float("nan"),
            "cross_doc_breadth": statistics.fmean(breadth) if breadth else float("nan"),
            "latency_p50": statistics.median([float(r.get("latency_seconds") or 0) for r in items]),
        }
    return table


def main() -> int:
    out_dir = Path(sys.argv[1])
    table = summarize(out_dir)
    print(f"\n=== STRICT-MATCH LIVE RESULTS: {out_dir.name} ===\n")
    cols = [
        ("entity_coverage", "ent_cov"),
        ("relation_coverage", "rel_cov"),
        ("cross_doc_breadth", "xdoc"),
        ("evidence_recall_at_k", "recall@k"),
        ("final_evidence_recall", "final_rec"),
        ("required_evidence_coverage", "req_cov"),
        ("citation_precision", "cite_p"),
        ("citation_recall", "cite_r"),
        ("latency_p50", "lat_p50"),
    ]
    header = f"{'cfg':5}" + "".join(f"{short:>11}" for _, short in cols)
    print(header)
    print("-" * len(header))
    for cfg, vals in table.items():
        line = f"{cfg:5}" + "".join(f"{vals[key]:>11.4f}" for key, _ in cols)
        print(line)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
