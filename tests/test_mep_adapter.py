from __future__ import annotations

from pathlib import Path

from ragent.mep_adapter import (
    build_result_payload,
    cleanup_runtime_project_layout,
    normalize_mep_request,
    prepare_runtime_project_layout,
    resolve_single_snapshot_from_data_dir,
)


def _write_snapshot(snapshot_dir: Path) -> None:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for filename in (
        "graph_chunk_entity_relation.graphml",
        "kv_store_text_chunks.json",
        "vdb_chunks.json",
    ):
        (snapshot_dir / filename).write_text("{}", encoding="utf-8")


def test_normalize_mep_request_chat_history_passthrough(tmp_path: Path):
    req_data = {
        "data": {
            "query_type": "chat",
            "query": "继续说明这个建议。",
            "mode": "graph",
            "conversation_history": [
                {"role": "user", "content": "先总结文档。"},
                {"role": "assistant", "content": "文档围绕健康饮食建议展开。"},
            ],
            "history_turns": 4,
            "enable_rerank": False,
            "response_type": "Single Paragraph",
            "generatePath": str(tmp_path / "output"),
            "include_trace": True,
        }
    }

    normalized = normalize_mep_request(req_data)

    assert normalized.inference_request.query_type == "chat"
    assert normalized.inference_request.query == "继续说明这个建议。"
    assert normalized.inference_request.mode == "graph"
    assert normalized.inference_request.conversation_history == req_data["data"]["conversation_history"]
    assert normalized.inference_request.history_turns == 4
    assert normalized.inference_request.enable_rerank is False
    assert normalized.inference_request.response_type == "Single Paragraph"
    assert normalized.inference_request.include_trace is True
    assert normalized.generate_path == (tmp_path / "output").resolve()


def test_prepare_runtime_project_layout_copies_read_only_snapshot(
    monkeypatch,
    tmp_path: Path,
):
    data_dir = tmp_path / "data"
    snapshot_dir = data_dir / "demo_kg"
    _write_snapshot(snapshot_dir)
    runtime_root = tmp_path / "runtime"

    monkeypatch.setattr(
        "ragent.mep_adapter._directory_is_writable",
        lambda path: False,
    )

    layout = prepare_runtime_project_layout(
        data_dir=data_dir,
        runtime_root=runtime_root,
    )

    assert layout.copied_to_runtime_dir is True
    assert layout.source_project_dir == snapshot_dir.resolve()
    assert layout.runtime_project_dir != layout.source_project_dir
    assert layout.runtime_project_dir.exists()
    assert layout.runtime_project_dir.parent == layout.runtime_temp_root
    assert layout.runtime_temp_root is not None
    assert layout.runtime_temp_root.parent == runtime_root.resolve()
    assert (layout.runtime_project_dir / "vdb_chunks.json").exists()


def test_cleanup_runtime_project_layout_removes_temp_copy_only(
    monkeypatch,
    tmp_path: Path,
):
    data_dir = tmp_path / "data"
    snapshot_dir = data_dir / "demo_kg"
    _write_snapshot(snapshot_dir)

    monkeypatch.setattr(
        "ragent.mep_adapter._directory_is_writable",
        lambda path: False,
    )

    layout = prepare_runtime_project_layout(data_dir=data_dir, runtime_root=tmp_path / "runtime")

    assert layout.runtime_temp_root is not None
    assert layout.runtime_temp_root.exists()
    assert layout.runtime_project_dir.exists()
    assert layout.source_project_dir.exists()

    cleanup_runtime_project_layout(layout)

    assert not layout.runtime_temp_root.exists()
    assert not layout.runtime_project_dir.exists()
    assert layout.source_project_dir.exists()


def test_example_snapshot_is_accepted():
    repo_root = Path(__file__).resolve().parents[1]
    snapshot_dir = repo_root / "example" / "demo_diet_kg"

    resolved = resolve_single_snapshot_from_data_dir(snapshot_dir)

    assert resolved == snapshot_dir.resolve()


def test_build_result_payload_contains_stable_fields(tmp_path: Path):
    req_data = normalize_mep_request(
        {
            "data": {
                "query_type": "onehop",
                "query": "文档的主要主题是什么？",
                "mode": "hybrid",
                "conversation_history": [{"role": "user", "content": "hello"}],
            }
        }
    )
    snapshot_dir = tmp_path / "data"
    _write_snapshot(snapshot_dir)
    layout = prepare_runtime_project_layout(data_dir=snapshot_dir)
    result = {
        "answer": "主题是饮食知识。",
        "referenced_file_paths": ["a.md"],
        "image_list": ["a.png"],
        "query_type": "onehop",
        "mode": "hybrid",
        "conversation_history_used_count": 1,
        "history_turns": None,
        "enable_rerank": True,
        "response_type": "Multiple Paragraphs",
    }

    payload = build_result_payload(
        request=req_data,
        result=result,
        runtime_layout=layout,
    )

    assert payload["answer"] == "主题是饮食知识。"
    assert payload["referenced_file_paths"] == ["a.md"]
    assert payload["image_list"] == ["a.png"]
    assert payload["query_type"] == "onehop"
    assert payload["mode"] == "hybrid"
    assert payload["conversation_history_used_count"] == 1
    assert payload["copied_to_runtime_dir"] is False
