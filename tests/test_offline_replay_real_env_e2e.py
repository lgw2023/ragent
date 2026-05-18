from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


pytestmark = pytest.mark.skipif(
    not _truthy(os.getenv("RAGENT_RUN_REAL_ENV_E2E")),
    reason="set RAGENT_RUN_REAL_ENV_E2E=1 to run real .env PDF E2E",
)


def _load_dotenv() -> dict[str, str]:
    env = os.environ.copy()
    dotenv_path = PROJECT_ROOT / ".env"
    if not dotenv_path.exists():
        return env

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        env.setdefault(key, value)
    return env


def _run(command: list[str], *, env: dict[str, str], timeout: int = 3600) -> None:
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode == 0:
        return

    stdout_tail = result.stdout[-4000:]
    stderr_tail = result.stderr[-4000:]
    raise AssertionError(
        "command failed with exit code "
        f"{result.returncode}: {' '.join(command)}\n"
        f"stdout tail:\n{stdout_tail}\n"
        f"stderr tail:\n{stderr_tail}"
    )


def _raw_jsonl_stats(path: Path) -> dict[str, int]:
    stats = {"units": 0, "chunks": 0, "extracted_nodes": 0, "extracted_edges": 0}
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            payload = json.loads(line)
            stats["units"] += 1
            stats["chunks"] += len(payload.get("chunks") or {})
            for chunk_result in payload.get("chunk_results") or []:
                stats["extracted_nodes"] += len(chunk_result.get("nodes") or {})
                stats["extracted_edges"] += len(chunk_result.get("edges") or [])
    return stats


def _sqlite_json_entries(path: Path) -> dict[str, dict]:
    with sqlite3.connect(path) as connection:
        rows = connection.execute("select key, entry_json from kv_entries").fetchall()
    return {key: json.loads(entry_json) for key, entry_json in rows}


def _vdb_records(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload
    return []


def _graph_counts(path: Path) -> tuple[int, int]:
    root = ET.parse(path).getroot()
    namespace = {"g": "http://graphml.graphdrawing.org/xmlns"}
    return (
        len(root.findall(".//g:node", namespace)),
        len(root.findall(".//g:edge", namespace)),
    )


def _project_snapshot(project_dir: Path) -> dict[str, object]:
    full_docs = _sqlite_json_entries(project_dir / "kv_store_full_docs.sqlite")
    text_chunks = _sqlite_json_entries(project_dir / "kv_store_text_chunks.sqlite")
    doc_status = json.loads(
        (project_dir / "kv_store_doc_status.json").read_text(encoding="utf-8")
    )
    chunk_vdb = _vdb_records(project_dir / "vdb_chunks.json")
    entity_vdb = _vdb_records(project_dir / "vdb_entities.json")
    relationship_vdb = _vdb_records(project_dir / "vdb_relationships.json")
    graph_nodes, graph_edges = _graph_counts(
        project_dir / "graph_chunk_entity_relation.graphml"
    )
    return {
        "full_doc_ids": set(full_docs),
        "text_chunk_ids": set(text_chunks),
        "doc_status_ids": set(doc_status),
        "chunk_vdb_ids": {record["__id__"] for record in chunk_vdb},
        "entity_vdb_count": len(entity_vdb),
        "relationship_vdb_count": len(relationship_vdb),
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
    }


def _usage_call_count(report_text: str, model_type: str) -> int:
    prefix = f"| {model_type} |"
    for line in report_text.splitlines():
        if not line.startswith(prefix):
            continue
        columns = [column.strip() for column in line.strip("|").split("|")]
        if len(columns) >= 2:
            return int(columns[1])
    return 0


def test_real_env_pdf_raw_replay_matches_online_doc_chunk_surface(tmp_path: Path):
    env = _load_dotenv()
    if not env.get("LLM_MODEL"):
        pytest.skip("LLM_MODEL is not configured in environment or .env")

    pdf_path = PROJECT_ROOT / "example" / "GB-31607-2021.pdf"
    if not pdf_path.exists():
        pytest.skip(f"example PDF is missing: {pdf_path}")

    mineru_dir = tmp_path / "mineru"
    raw_dir = tmp_path / "raw"
    offline_project = tmp_path / "offline-replay"
    online_project = tmp_path / "online-reference"
    raw_jsonl = raw_dir / f"{pdf_path.stem}.raw-units.jsonl"

    _run(
        [
            sys.executable,
            "singlefile.py",
            "parse",
            str(pdf_path),
            str(mineru_dir),
            str(raw_dir),
            "raw",
        ],
        env=env,
        timeout=7200,
    )
    assert raw_jsonl.exists()

    raw_stats = _raw_jsonl_stats(raw_jsonl)
    assert raw_stats["units"] > 0
    assert raw_stats["chunks"] >= raw_stats["units"]
    assert raw_stats["extracted_nodes"] > 0
    assert raw_stats["extracted_edges"] > 0

    raw_usage_reports = sorted(raw_dir.glob("model_usage_raw_export_*.md"))
    assert raw_usage_reports
    raw_usage_text = raw_usage_reports[-1].read_text(encoding="utf-8")
    assert _usage_call_count(raw_usage_text, "chat") > 0
    assert _usage_call_count(raw_usage_text, "embedding") > 0

    _run(
        [
            sys.executable,
            "tools/replay_raw_merge_units_to_project.py",
            str(raw_jsonl),
            "-o",
            str(offline_project),
            "--overwrite",
            "--llm-model-max-async",
            "1",
        ],
        env=env,
        timeout=7200,
    )
    replay_usage_reports = sorted(offline_project.glob("model_usage_raw_replay_*.md"))
    assert replay_usage_reports
    replay_usage_text = replay_usage_reports[-1].read_text(encoding="utf-8")
    assert _usage_call_count(replay_usage_text, "embedding") > 0

    _run(
        [
            sys.executable,
            "singlefile.py",
            "parse",
            str(pdf_path),
            str(mineru_dir),
            str(online_project),
            "rag",
        ],
        env=env,
        timeout=7200,
    )

    offline_snapshot = _project_snapshot(offline_project)
    online_snapshot = _project_snapshot(online_project)

    assert offline_snapshot["full_doc_ids"] == online_snapshot["full_doc_ids"]
    assert offline_snapshot["text_chunk_ids"] == online_snapshot["text_chunk_ids"]
    assert offline_snapshot["doc_status_ids"] == online_snapshot["doc_status_ids"]
    assert offline_snapshot["chunk_vdb_ids"] == online_snapshot["chunk_vdb_ids"]
    assert len(offline_snapshot["doc_status_ids"]) == raw_stats["units"]

    assert offline_snapshot["graph_nodes"] > 0
    assert offline_snapshot["graph_edges"] > 0
    assert offline_snapshot["entity_vdb_count"] > 0
    assert offline_snapshot["relationship_vdb_count"] > 0
    assert online_snapshot["graph_nodes"] > 0
    assert online_snapshot["graph_edges"] > 0
