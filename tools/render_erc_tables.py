#!/usr/bin/env python3
"""Render ERC DQE result tables to PNG and PDF from benchmark artifacts."""
from __future__ import annotations

import argparse
import csv
import json
import math
import textwrap
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = REPO_ROOT / "benchmark" / "erc_evidence_questions_dqe_full_20260601_000156.jsonl"
OUT = REPO_ROOT / "docs" / "research" / "figures"

CONFIG_COMPONENTS = {
    "B0": ("Y", "", "", "", "", "", ""),
    "B1": ("Y", "", "", "", "", "Y", ""),
    "B2": ("", "Y", "Y", "Y", "", "", ""),
    "B3": ("Y", "Y", "", "", "", "", ""),
    "B4": ("Y", "Y", "Y", "", "", "", ""),
    "B5": ("Y", "Y", "Y", "Y", "", "", ""),
    "B6": ("Y", "Y", "Y", "Y", "Y", "", ""),
    "B7": ("Y", "Y", "Y", "Y", "Y", "Y", ""),
    "Full": ("Y", "Y", "Y", "Y", "Y", "Y", "Y"),
}
CONFIG_ORDER = ["B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "Full"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-eval-dir", default="", help="benchmark/erc_full_eval_* directory.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="DQE JSONL dataset.")
    parser.add_argument("--output-dir", default=str(OUT), help="Figure output directory.")
    return parser.parse_args()


def latest_full_eval_dir() -> Path:
    marker = REPO_ROOT / "benchmark" / ".latest_dqe_fresh_replay_out"
    if marker.exists():
        value = marker.read_text(encoding="utf-8").strip()
        if value:
            path = Path(value)
            return path if path.is_absolute() else REPO_ROOT / path
    candidates = sorted(
        (REPO_ROOT / "benchmark").glob("erc_full_eval_*"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if (candidate / "metrics.tsv").exists():
            return candidate
    raise FileNotFoundError("No benchmark/erc_full_eval_* metrics.tsv found")


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def load_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def fnum(value: Any, digits: int = 3) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.nan
    return round(number, digits)


def fmt(value: Any, digits: int = 3) -> str:
    number = fnum(value, digits)
    if math.isnan(number):
        return "-"
    return f"{number:.{digits}f}"


def pct_delta(a: float, b: float) -> str:
    if math.isnan(a) or math.isnan(b) or b == 0:
        return "-"
    return f"{((a - b) / b) * 100:+.0f}%"


def render_table(
    output_dir: Path,
    name: str,
    title: str,
    columns: list[str],
    rows: list[list[Any]],
    *,
    footnote: str = "",
    fig_w: float = 10.0,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    row_count = len(rows)
    fig_h = max(2.7, 1.1 + 0.38 * (row_count + 1) + (0.35 if footnote else 0))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=11.5, fontweight="bold", pad=10)
    table = ax.table(
        cellText=[[str(cell) for cell in row] for row in rows],
        colLabels=columns,
        loc="upper left",
        cellLoc="center",
        colLoc="center",
        bbox=[0, 0.12 if footnote else 0.03, 1, 0.82 if footnote else 0.88],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.8)
    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor("#D0D7DE")
        if row == 0:
            cell.set_facecolor("#EEF4FA")
            cell.set_text_props(fontweight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#F7F9FB")
    if footnote:
        wrapped = textwrap.fill(footnote, width=130)
        fig.text(0.01, 0.03, wrapped, ha="left", va="bottom", fontsize=8.2, color="#444")
    for ext in ("png", "pdf"):
        fig.savefig(output_dir / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.12, facecolor="white")
    plt.close(fig)
    print(f"wrote {output_dir / (name + '.png')}")


def main() -> int:
    args = parse_args()
    full_eval_dir = repo_path(args.full_eval_dir) if args.full_eval_dir else latest_full_eval_dir()
    output_dir = repo_path(args.output_dir)
    dataset_path = repo_path(args.dataset)

    metrics = load_tsv(full_eval_dir / "metrics.tsv")
    main_rows = {
        row["config_id"]: row
        for row in metrics
        if row.get("cache_phase") == "full_no_cache"
    }
    full_rows = {
        row["cache_phase"]: row
        for row in metrics
        if row.get("config_id") == "Full"
    }
    dataset = load_jsonl(dataset_path)
    annotated = load_jsonl(full_eval_dir / "annotated_dataset.jsonl")
    records_for_stats = annotated or dataset
    separation_path = full_eval_dir / "build_inference_separation" / "separation_summary.json"
    separation = json.loads(separation_path.read_text(encoding="utf-8")) if separation_path.exists() else {}
    snapshot = separation.get("online_build_snapshot") or {}

    docs = sorted(
        {
            Path(str(evidence.get("file_path") or "")).name
            for record in records_for_stats
            for evidence in record.get("required_evidence", [])
            if evidence.get("file_path")
        }
    )
    calc_count = sum(1 for record in records_for_stats if record.get("requires_calculation"))
    multi_count = sum(1 for record in records_for_stats if len(record.get("required_evidence") or []) >= 2)
    difficulty = {
        key: sum(1 for record in records_for_stats if record.get("difficulty") == key)
        for key in ("easy", "medium", "hard")
    }

    render_table(
        output_dir,
        "table1_dataset",
        "Table 1. DQE full benchmark and materialized ERC evidence graph",
        ["Question set", "Value", "ERC evidence graph", "Value"],
        [
            ["Source PDFs", len(docs) or "-", "Graph nodes", snapshot.get("graph_nodes", "-")],
            ["Questions", len(dataset), "Graph edges", snapshot.get("graph_edges", "-")],
            ["Calculation-required", calc_count, "Entity vector store", snapshot.get("entity_vdb", "-")],
            ["Multi-evidence", multi_count, "Relation vector store", snapshot.get("relationship_vdb", "-")],
            [
                "Difficulty E/M/H",
                f"{difficulty['easy']}/{difficulty['medium']}/{difficulty['hard']}",
                "Chunk vector store",
                snapshot.get("chunk_vdb", "-"),
            ],
        ],
        footnote=f"Source: {full_eval_dir.relative_to(REPO_ROOT)}.",
        fig_w=9.6,
    )

    selected = [config_id for config_id in ("B0", "B5", "Full") if config_id in main_rows]
    b0 = main_rows.get("B0", {})
    full = main_rows.get("Full", {})
    main_table_rows = [
        [
            config_id,
            main_rows[config_id].get("config_name", config_id),
            fmt(main_rows[config_id].get("required_evidence_coverage")),
            fmt(main_rows[config_id].get("evidence_recall_at_k")),
            fmt(main_rows[config_id].get("final_evidence_recall")),
            fmt(main_rows[config_id].get("citation_recall")),
            fmt(main_rows[config_id].get("latency_p50_seconds")),
        ]
        for config_id in selected
    ]
    if b0 and full:
        main_table_rows.append(
            [
                "Delta Full vs B0",
                "",
                pct_delta(fnum(full.get("required_evidence_coverage")), fnum(b0.get("required_evidence_coverage"))),
                pct_delta(fnum(full.get("evidence_recall_at_k")), fnum(b0.get("evidence_recall_at_k"))),
                pct_delta(fnum(full.get("final_evidence_recall")), fnum(b0.get("final_evidence_recall"))),
                pct_delta(fnum(full.get("citation_recall")), fnum(b0.get("citation_recall"))),
                "-",
            ]
        )
    render_table(
        output_dir,
        "table2_main",
        "Table 2. Retrieval-layer results on the DQE full live artifact",
        ["Method", "Name", "ReqCov", "R@K", "FinalR", "CiteR", "p50 s"],
        main_table_rows,
        footnote="Answer quality is diagnostic; retrieval-layer coverage and provenance are the primary claims.",
        fig_w=10.6,
    )

    ablation_rows = []
    for config_id in CONFIG_ORDER:
        row = main_rows.get(config_id)
        if not row:
            continue
        ablation_rows.append(
            [
                config_id,
                *CONFIG_COMPONENTS[config_id],
                fmt(row.get("required_evidence_coverage")),
                fmt(row.get("evidence_recall_at_k")),
                fmt(row.get("final_evidence_recall")),
            ]
        )
    render_table(
        output_dir,
        "table3_ablation",
        "Table 3. Component ablation over the ERC retrieval path",
        ["Method", "Chk", "Ent", "Rel", "GExp", "QVar", "ReRk", "Sel", "ReqCov", "R@K", "FinalR"],
        ablation_rows,
        fig_w=11.2,
    )

    quality_rows = []
    for config_id in selected:
        row = main_rows[config_id]
        quality_rows.append(
            [
                config_id,
                row.get("config_name", config_id),
                fmt(row.get("correctness")),
                fmt(row.get("faithfulness")),
                fmt(row.get("unsupported_claim_rate")),
                fmt(row.get("latency_p50_seconds")),
            ]
        )
    if "answer_cache_warm" in full_rows:
        row = full_rows["answer_cache_warm"]
        quality_rows.append(["Full answer-cache warm", "", "-", "-", "-", fmt(row.get("latency_p50_seconds"))])
    render_table(
        output_dir,
        "table4_quality_latency",
        "Table 4. Downstream answer diagnostics and latency",
        ["Method", "Name", "Correct", "Faith", "Unsupported", "p50 s"],
        quality_rows,
        footnote="LLM judge scores are retained as diagnostics for downstream answer generation, not as the main ERC retrieval conclusion.",
        fig_w=10.0,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
