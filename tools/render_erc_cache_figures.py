#!/usr/bin/env python3
"""Render ERC cache tables and figures from benchmark artifacts."""
from __future__ import annotations

import argparse
import csv
import statistics
import textwrap
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "docs" / "research" / "figures"
DEFAULT_KEYWORD_CACHE = REPO_ROOT / "benchmark" / "keyword_cache_benefit_qwen4b_hybrid" / "results.tsv"
PHASE_LABELS = {
    "full_no_cache": "No cache",
    "retrieval_cache_warm": "Retrieval-cache warm",
    "answer_cache_warm": "Answer-cache warm",
    "keyword_candidate_cache_warm": "Keyword-candidate warm",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-eval-dir", default="", help="benchmark/erc_full_eval_* directory.")
    parser.add_argument("--keyword-cache-results", default=str(DEFAULT_KEYWORD_CACHE))
    parser.add_argument("--output-dir", default=str(OUT))
    return parser.parse_args()


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


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


def load_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def fnum(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fmt(value: Any, digits: int = 3) -> str:
    return f"{fnum(value):.{digits}f}"


def mean(rows: list[dict[str, str]], key: str) -> float:
    values = [fnum(row.get(key)) for row in rows if row.get(key) not in (None, "")]
    return statistics.fmean(values) if values else 0.0


def render_table(
    output_dir: Path,
    name: str,
    title: str,
    columns: list[str],
    rows: list[list[Any]],
    *,
    footnote: str = "",
    fig_w: float = 9.0,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig_h = max(2.7, 1.1 + 0.42 * (len(rows) + 1) + (0.4 if footnote else 0))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=11.5, fontweight="bold", pad=10)
    table = ax.table(
        cellText=[[str(cell) for cell in row] for row in rows],
        colLabels=columns,
        loc="upper left",
        cellLoc="center",
        colLoc="center",
        bbox=[0, 0.14 if footnote else 0.03, 1, 0.80 if footnote else 0.88],
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
        fig.text(0.01, 0.03, textwrap.fill(footnote, width=125), ha="left", va="bottom", fontsize=8.2, color="#444")
    for ext in ("png", "pdf"):
        fig.savefig(output_dir / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.12, facecolor="white")
    plt.close(fig)
    print(f"wrote {output_dir / (name + '.png')}")


def speedup(baseline: float, current: float) -> str:
    if baseline <= 0 or current <= 0:
        return "-"
    return f"{baseline / current:.1f}x"


def render_query_cache_figure(output_dir: Path, query_rows: list[dict[str, str]]) -> None:
    labels = [PHASE_LABELS.get(row["cache_phase"], row["cache_phase"]) for row in query_rows]
    values = [fnum(row.get("latency_p50_seconds")) for row in query_rows]
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    bars = ax.bar(labels, values, color=["#2C6FB5", "#2C6FB5", "#E0852B", "#6AA84F"][: len(values)])
    if values and min(value for value in values if value > 0) < max(values) / 20:
        ax.set_yscale("log")
        ax.set_ylabel("p50 query latency (s, log scale)")
    else:
        ax.set_ylabel("p50 query latency (s)")
    ax.set_title("Query cache latency by cache state", fontsize=11.5, fontweight="bold")
    ax.grid(axis="y", linestyle=":", alpha=0.45)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value * 1.08 if ax.get_yscale() == "log" else value + max(values or [1]) * 0.03,
            f"{value:.3g}s",
            ha="center",
            va="bottom",
            fontsize=9.0,
            fontweight="bold",
        )
    fig.autofmt_xdate(rotation=12)
    for ext in ("png", "pdf"):
        fig.savefig(output_dir / f"fig_query_cache.{ext}", bbox_inches="tight", pad_inches=0.12, facecolor="white")
    plt.close(fig)


def render_keyword_cache_figure(output_dir: Path, rows_by_phase: dict[str, list[dict[str, str]]]) -> None:
    phases = ["baseline_cold", "enabled_prewarm", "warm_hit"]
    labels = ["Cold", "Prewarm", "Warm hit"]
    entity = [mean(rows_by_phase.get(phase, []), "graph_entity_vector_seconds") for phase in phases]
    relation = [mean(rows_by_phase.get(phase, []), "graph_relation_vector_seconds") for phase in phases]
    x = range(len(phases))
    width = 0.36
    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    ax.bar([i - width / 2 for i in x], entity, width, label="Entity-vector", color="#2C6FB5")
    ax.bar([i + width / 2 for i in x], relation, width, label="Relation-vector", color="#E0852B")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Mean graph-vector time (s)")
    ax.set_title("Keyword-candidate cache graph retrieval time", fontsize=11.5, fontweight="bold")
    ax.grid(axis="y", linestyle=":", alpha=0.45)
    ax.legend(frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for ext in ("png", "pdf"):
        fig.savefig(output_dir / f"fig_keyword_cache.{ext}", bbox_inches="tight", pad_inches=0.12, facecolor="white")
    plt.close(fig)


def main() -> int:
    args = parse_args()
    full_eval_dir = repo_path(args.full_eval_dir) if args.full_eval_dir else latest_full_eval_dir()
    output_dir = repo_path(args.output_dir)
    metrics = load_tsv(full_eval_dir / "metrics.tsv")
    full_rows = [
        row
        for row in metrics
        if row.get("config_id") == "Full"
        and row.get("cache_phase") in PHASE_LABELS
    ]
    full_rows.sort(key=lambda row: list(PHASE_LABELS).index(row["cache_phase"]))
    baseline = next((fnum(row.get("latency_p50_seconds")) for row in full_rows if row.get("cache_phase") == "full_no_cache"), 0.0)
    render_table(
        output_dir,
        "table5_query_cache",
        "Table 5. Query-cache acceleration in the selected Full live artifact",
        ["Cache state", "Cache-hit stages", "p50 s", "p95 s", "Speedup"],
        [
            [
                PHASE_LABELS.get(row["cache_phase"], row["cache_phase"]),
                row.get("cache_hit_stages") or "-",
                fmt(row.get("latency_p50_seconds")),
                fmt(row.get("latency_p95_seconds")),
                speedup(baseline, fnum(row.get("latency_p50_seconds"))),
            ]
            for row in full_rows
        ],
        footnote=f"Source: {full_eval_dir.relative_to(REPO_ROOT)}.",
        fig_w=9.8,
    )
    render_query_cache_figure(output_dir, full_rows)

    keyword_rows = load_tsv(repo_path(args.keyword_cache_results))
    by_phase: dict[str, list[dict[str, str]]] = {}
    for row in keyword_rows:
        by_phase.setdefault(row.get("phase", ""), []).append(row)
    keyword_table_rows = []
    for phase, label in [("baseline_cold", "Baseline cold"), ("enabled_prewarm", "Prewarm"), ("warm_hit", "Warm hit")]:
        rows = by_phase.get(phase, [])
        keyword_table_rows.append(
            [
                label,
                f"{mean(rows, 'keyword_candidate_cache_hit_count'):.1f}",
                fmt(mean(rows, "graph_entity_vector_seconds")),
                fmt(mean(rows, "graph_relation_vector_seconds")),
                fmt(mean(rows, "keyword_candidate_cache_lookup_seconds")),
            ]
        )
    render_table(
        output_dir,
        "table6_keyword_cache",
        "Table 6. Keyword-candidate cache retrieval-stage breakdown",
        ["Cache state", "KW-cand hits", "Entity-vec s", "Relation-vec s", "Lookup s"],
        keyword_table_rows,
        footnote=f"Source: {repo_path(args.keyword_cache_results).relative_to(REPO_ROOT)}.",
        fig_w=9.4,
    )
    if keyword_rows:
        render_keyword_cache_figure(output_dir, by_phase)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
