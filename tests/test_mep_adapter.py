from __future__ import annotations

import json
from pathlib import Path

from ragent.mep_adapter import (
    build_action_query_response,
    build_recommend_success,
    build_result_payload,
    cleanup_runtime_project_layout,
    maybe_write_result_payload,
    normalize_mep_request,
    prepare_runtime_project_layout,
    resolve_component_bundle_paths,
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
    assert (
        normalized.inference_request.conversation_history
        == req_data["data"]["conversation_history"]
    )
    assert normalized.inference_request.history_turns == 4
    assert normalized.inference_request.enable_rerank is False
    assert normalized.inference_request.response_type == "Single Paragraph"
    assert normalized.inference_request.include_trace is True
    assert normalized.generate_path == (tmp_path / "output").resolve()
    assert normalized.result_filename == "gen.json"


def test_normalize_mep_request_reads_process_spec_fallback(tmp_path: Path):
    req_data = {
        "data": {
            "taskId": "100002455",
            "action": "create",
            "basePath": str(tmp_path / "base"),
            "fileInfo": [
                {
                    "generatePath": str(tmp_path / "generate"),
                    "processSpec": [
                        {"query_type": "multihop"},
                        {"key": "query", "value": "比较两类策略。"},
                        {"name": "mode", "value": "graph"},
                        {"fieldName": "include_trace", "fieldValue": "true"},
                    ],
                }
            ],
        }
    }

    normalized = normalize_mep_request(req_data)

    assert normalized.action == "create"
    assert normalized.task_id == "100002455"
    assert normalized.base_path == (tmp_path / "base").resolve()
    assert normalized.generate_path == (tmp_path / "generate").resolve()
    assert normalized.result_filename == "gen.json"
    assert normalized.inference_request.query_type == "multihop"
    assert normalized.inference_request.query == "比较两类策略。"
    assert normalized.inference_request.mode == "graph"
    assert normalized.inference_request.include_trace is True


def test_normalize_mep_request_reads_source_json_fallback(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    input_json = source_dir / "kg_request.json"
    input_json.write_text(
        """
        {
          "data": {
            "query_type": "chat",
            "query": "继续解释。",
            "mode": "hybrid",
            "conversation_history": [
              {"role": "user", "content": "先总结。"}
            ],
            "history_turns": 2,
            "enable_rerank": false,
            "response_type": "Single Paragraph"
          }
        }
        """,
        encoding="utf-8",
    )

    req_data = {
        "data": {
            "generatePath": str(tmp_path / "generate"),
            "fileInfo": [
                {
                    "sourcePath": str(source_dir),
                    "sourceImage": "kg_request.json",
                    "processSpec": [],
                }
            ],
        }
    }

    normalized = normalize_mep_request(req_data)

    assert normalized.inference_request.query_type == "chat"
    assert normalized.inference_request.query == "继续解释。"
    assert normalized.inference_request.conversation_history == [
        {"role": "user", "content": "先总结。"}
    ]
    assert normalized.inference_request.history_turns == 2
    assert normalized.inference_request.enable_rerank is False
    assert normalized.inference_request.response_type == "Single Paragraph"


def test_normalize_mep_request_prefers_direct_fields_over_fallbacks(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    input_json = source_dir / "kg_request.json"
    input_json.write_text(
        '{"query_type": "chat", "query": "json query", "mode": "graph"}',
        encoding="utf-8",
    )
    req_data = {
        "data": {
            "query_type": "onehop",
            "query": "direct query",
            "mode": "hybrid",
            "fileInfo": [
                {
                    "sourcePath": str(source_dir),
                    "sourceImage": "kg_request.json",
                    "processSpec": [
                        {"query_type": "multihop", "query": "process query"}
                    ],
                }
            ],
        }
    }

    normalized = normalize_mep_request(req_data)

    assert normalized.inference_request.query_type == "onehop"
    assert normalized.inference_request.query == "direct query"
    assert normalized.inference_request.mode == "hybrid"


def test_normalize_mep_request_fixes_async_result_filename():
    async_request = normalize_mep_request(
        {
            "data": {
                "action": "create",
                "query_type": "onehop",
                "query": "async query",
                "result_filename": "custom.json",
            }
        }
    )
    direct_request = normalize_mep_request(
        {
            "data": {
                "query_type": "onehop",
                "query": "direct query",
                "result_filename": "custom.json",
            }
        }
    )

    assert async_request.result_filename == "gen.json"
    assert direct_request.result_filename == "custom.json"


def test_resolve_component_bundle_paths_prefers_model_dir_layout(tmp_path: Path):
    process_file = tmp_path / "process.py"
    process_file.write_text("# entry\n", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "model").mkdir()

    paths = resolve_component_bundle_paths(process_file)

    assert paths.data_dir == (tmp_path / "data").resolve()
    assert paths.model_dir == (tmp_path / "model").resolve()


def test_resolve_component_bundle_paths_falls_back_to_parent_layout(tmp_path: Path):
    component_dir = tmp_path / "component"
    component_dir.mkdir()
    process_file = component_dir / "process.py"
    process_file.write_text("# entry\n", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "model").mkdir()

    paths = resolve_component_bundle_paths(process_file)

    assert paths.data_dir == (tmp_path / "data").resolve()
    assert paths.model_dir == (tmp_path / "model").resolve()


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
                "taskId": "100002455",
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

    assert payload["code"] == "0"
    assert payload["des"] == "success"
    assert payload["taskId"] == "100002455"
    assert payload["query"] == "文档的主要主题是什么？"
    assert payload["answer"] == "主题是饮食知识。"
    assert payload["referenced_file_paths"] == ["a.md"]
    assert payload["image_list"] == ["a.png"]
    assert payload["query_type"] == "onehop"
    assert payload["mode"] == "hybrid"
    assert payload["conversation_history_used_count"] == 1
    assert payload["trace"] is None
    assert payload["runtime"]["copied_to_runtime_dir"] is False
    assert payload["runtime"]["runtime_project_dir"] == str(layout.runtime_project_dir)


def test_maybe_write_result_payload_writes_valid_gen_json(tmp_path: Path):
    payload = {"code": "0", "answer": "ok"}
    generate_path = tmp_path / "generate"

    output_path = maybe_write_result_payload(
        payload,
        generate_path=generate_path,
        result_filename="gen.json",
    )

    assert output_path == generate_path / "gen.json"
    assert payload["result_file_path"] == str(output_path)
    written = output_path.read_text(encoding="utf-8")
    assert written.endswith("\n")
    written_payload = json.loads(written)
    assert written_payload["code"] == "0"
    assert written_payload["result_file_path"] == str(output_path)


def test_build_recommend_success_defaults_to_empty_async_content():
    response = build_recommend_success()

    assert response == {
        "recommendResult": {
            "code": "0",
            "des": "success",
            "length": 0,
            "content": [],
        }
    }


def test_build_recommend_success_can_include_direct_debug_payload():
    response = build_recommend_success({"answer": "ok"}, include_content=True)

    assert response["recommendResult"]["code"] == "0"
    assert response["recommendResult"]["length"] == 1
    assert response["recommendResult"]["content"] == [{"answer": "ok"}]


def test_build_action_query_response_checks_generate_path(tmp_path: Path):
    generate_path = tmp_path / "generate"
    generate_path.mkdir()
    req_data = {"data": {"action": "query", "generatePath": str(generate_path)}}

    processing = build_action_query_response(req_data)

    assert processing["recommendResult"]["code"] == "2"
    assert processing["recommendResult"]["des"] == "processing"
    assert processing["recommendResult"]["length"] == 0
    assert processing["recommendResult"]["content"] == []

    (generate_path / "gen.json").write_text('{"code": "0"}\n', encoding="utf-8")

    completed = build_action_query_response(req_data)

    assert completed["recommendResult"]["code"] == "0"
    assert completed["recommendResult"]["length"] == 0
    assert completed["recommendResult"]["content"] == []


def test_build_action_query_response_checks_base_path_generate_subdir(tmp_path: Path):
    base_path = tmp_path / "task"
    result_dir = base_path / "generatePath"
    result_dir.mkdir(parents=True)
    (result_dir / "gen.json").write_text('{"code": "0"}\n', encoding="utf-8")

    response = build_action_query_response(
        {"data": {"action": "query", "basePath": str(base_path)}}
    )

    assert response["recommendResult"]["code"] == "0"


def test_build_action_query_response_returns_missing_path_code_4(tmp_path: Path):
    response = build_action_query_response(
        {"data": {"action": "query", "basePath": str(tmp_path / "missing")}}
    )

    assert response["recommendResult"]["code"] == "4"
    assert response["recommendResult"]["length"] == 0
    assert response["recommendResult"]["content"] == []
