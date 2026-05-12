from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

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


def _write_component_entry(component_dir: Path, relative_process_path: str = "process.py") -> Path:
    component_dir.mkdir(parents=True, exist_ok=True)
    (component_dir / "config.json").write_text(
        '{"main_file": "process", "main_class": "CustomerModel"}\n',
        encoding="utf-8",
    )
    process_file = component_dir / relative_process_path
    process_file.parent.mkdir(parents=True, exist_ok=True)
    process_file.write_text("# entry\n", encoding="utf-8")
    return process_file


def _write_runtime_bundle_dirs(runtime_root: Path) -> None:
    (runtime_root / "model").mkdir(parents=True, exist_ok=True)
    (runtime_root / "data").mkdir(parents=True, exist_ok=True)
    (runtime_root / "meta").mkdir(parents=True, exist_ok=True)


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


def test_normalize_mep_request_retrieval_only_aliases_enable_trace(tmp_path: Path):
    req_data = {
        "data": {
            "taskId": "retrieval-001",
            "query_type": "onehop",
            "query": "我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？",
            "mode": "hybrid",
            "only_need_context": "true",
            "enable_rerank": "false",
            "high_level_keywords": ["指南"],
            "low_level_keywords": "饮食,营养",
            "generatePath": str(tmp_path / "output"),
        }
    }

    normalized = normalize_mep_request(req_data)

    assert normalized.inference_request.retrieval_only is True
    assert normalized.inference_request.only_need_context is True
    assert normalized.inference_request.include_trace is True
    assert normalized.inference_request.enable_rerank is False
    assert normalized.inference_request.high_level_keywords == ["指南"]
    assert normalized.inference_request.low_level_keywords == ["饮食", "营养"]


def test_normalize_mep_request_defaults_to_retrieval_only_when_unset():
    normalized = normalize_mep_request(
        {
            "data": {
                "query_type": "onehop",
                "query": "我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？",
            }
        }
    )

    assert normalized.inference_request.retrieval_only is True
    assert normalized.inference_request.only_need_context is True
    assert normalized.inference_request.include_trace is True


@pytest.mark.parametrize("field_name", ["retrieval_only", "only_need_context"])
def test_normalize_mep_request_explicit_false_opts_out_of_retrieval_only(
    field_name: str,
):
    normalized = normalize_mep_request(
        {
            "data": {
                "query_type": "onehop",
                "query": "需要生成完整回答。",
                field_name: False,
            }
        }
    )

    assert normalized.inference_request.retrieval_only is False
    assert normalized.inference_request.only_need_context is False
    assert normalized.inference_request.include_trace is False


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


@pytest.mark.parametrize(
    "result_filename",
    [
        "../gen.json",
        "..",
        ".",
        "nested/gen.json",
        "nested\\gen.json",
        "/tmp/gen.json",
        "C:\\tmp\\gen.json",
        "C:gen.json",
    ],
)
def test_normalize_mep_request_rejects_path_like_result_filename(result_filename: str):
    with pytest.raises(ValueError, match="plain file name"):
        normalize_mep_request(
            {
                "data": {
                    "query_type": "onehop",
                    "query": "direct query",
                    "result_filename": result_filename,
                }
            }
        )


def test_normalize_mep_request_create_action_forces_gen_json_for_result_filename():
    normalized = normalize_mep_request(
        {
            "data": {
                "action": "create",
                "query_type": "onehop",
                "query": "async query",
                "result_filename": "../escape.json",
            }
        }
    )

    assert normalized.result_filename == "gen.json"


def test_resolve_component_bundle_paths_prefers_model_dir_layout(tmp_path: Path):
    process_file = tmp_path / "process.py"
    process_file.write_text("# entry\n", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "model").mkdir()
    (tmp_path / "meta").mkdir()

    paths = resolve_component_bundle_paths(process_file)

    assert paths.data_dir == (tmp_path / "data").resolve()
    assert paths.model_dir == (tmp_path / "model").resolve()
    assert paths.meta_dir == (tmp_path / "meta").resolve()


def test_resolve_component_bundle_paths_falls_back_to_parent_layout(tmp_path: Path):
    process_file = _write_component_entry(tmp_path / "component")
    _write_runtime_bundle_dirs(tmp_path)

    paths = resolve_component_bundle_paths(process_file)

    assert paths.data_dir == (tmp_path / "data").resolve()
    assert paths.model_dir == (tmp_path / "model").resolve()
    assert paths.meta_dir == (tmp_path / "meta").resolve()


def test_resolve_component_bundle_paths_prefers_runtime_sibling_layout_over_model_root_and_local_env(
    monkeypatch,
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime"
    process_file = _write_component_entry(runtime_root / "component")
    _write_runtime_bundle_dirs(runtime_root)

    override_root = tmp_path / "override"
    (override_root / "data").mkdir(parents=True)
    (override_root / "model").mkdir()
    (override_root / "meta").mkdir()
    monkeypatch.setenv("RAGENT_MEP_DATA_DIR", str(override_root / "data"))
    monkeypatch.setenv("RAGENT_MEP_MODEL_DIR", str(override_root / "model"))

    model_root = tmp_path / "model_root_runtime"
    (model_root / "data").mkdir(parents=True)
    (model_root / "model").mkdir()
    (model_root / "meta").mkdir()

    paths = resolve_component_bundle_paths(process_file, model_root=model_root)

    assert paths.data_dir == (runtime_root / "data").resolve()
    assert paths.model_dir == (runtime_root / "model").resolve()
    assert paths.meta_dir == (runtime_root / "meta").resolve()


def test_resolve_component_bundle_paths_does_not_treat_source_tree_parent_as_runtime_root(
    tmp_path: Path,
):
    source_root = tmp_path / "repo"
    source_root.mkdir()
    process_file = source_root / "process.py"
    process_file.write_text("# entry\n", encoding="utf-8")

    misleading_parent_model = tmp_path / "model"
    misleading_parent_data = tmp_path / "data"
    misleading_parent_meta = tmp_path / "meta"
    misleading_parent_model.mkdir()
    misleading_parent_data.mkdir()
    misleading_parent_meta.mkdir()

    runtime_root = tmp_path / "runtime_root"
    (runtime_root / "model").mkdir(parents=True)
    (runtime_root / "data").mkdir()
    (runtime_root / "meta").mkdir()

    paths = resolve_component_bundle_paths(process_file, model_root=runtime_root)

    assert paths.model_dir == (runtime_root / "model").resolve()
    assert paths.data_dir == (runtime_root / "data").resolve()
    assert paths.meta_dir == (runtime_root / "meta").resolve()


def test_resolve_component_bundle_paths_ignores_unrelated_component_ancestor(
    tmp_path: Path,
):
    unrelated_component_parent = tmp_path / "component"
    source_root = unrelated_component_parent / "repo"
    source_root.mkdir(parents=True)
    process_file = source_root / "process.py"
    process_file.write_text("# entry\n", encoding="utf-8")

    _write_runtime_bundle_dirs(unrelated_component_parent.parent)

    runtime_root = tmp_path / "runtime_root"
    _write_runtime_bundle_dirs(runtime_root)

    paths = resolve_component_bundle_paths(process_file, model_root=runtime_root)

    assert paths.model_dir == (runtime_root / "model").resolve()
    assert paths.data_dir == (runtime_root / "data").resolve()
    assert paths.meta_dir == (runtime_root / "meta").resolve()


def test_resolve_component_bundle_paths_supports_nested_entry_under_component(
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime_root"
    process_file = _write_component_entry(
        runtime_root / "component",
        "pkg/process.py",
    )
    _write_runtime_bundle_dirs(runtime_root)

    paths = resolve_component_bundle_paths(process_file)

    assert paths.model_dir == (runtime_root / "model").resolve()
    assert paths.data_dir == (runtime_root / "data").resolve()
    assert paths.meta_dir == (runtime_root / "meta").resolve()


def test_resolve_component_bundle_paths_supports_sfs_relative_layout(
    monkeypatch,
    tmp_path: Path,
):
    process_file = _write_component_entry(tmp_path / "component")

    sfs_base = tmp_path / "sfs"
    object_root = sfs_base / "object-123"
    (object_root / "model").mkdir(parents=True)
    (object_root / "data").mkdir()
    (object_root / "meta").mkdir()

    monkeypatch.setenv("MODEL_SFS", json.dumps({"sfsBasePath": str(sfs_base)}))
    monkeypatch.setenv("MODEL_OBJECT_ID", "object-123")
    monkeypatch.setenv("MODEL_RELATIVE_DIR", "model")

    paths = resolve_component_bundle_paths(process_file)

    assert paths.model_dir == (object_root / "model").resolve()
    assert paths.data_dir == (object_root / "data").resolve()
    assert paths.meta_dir == (object_root / "meta").resolve()


def test_resolve_component_bundle_paths_supports_model_absolute_dir(
    monkeypatch,
    tmp_path: Path,
):
    process_file = _write_component_entry(tmp_path / "component")

    sfs_base = tmp_path / "sfs"
    object_root = sfs_base / "object-123"
    absolute_model_dir = tmp_path / "mounted_model"
    absolute_model_dir.mkdir()
    (object_root / "data").mkdir(parents=True)
    (object_root / "meta").mkdir()

    monkeypatch.setenv("MODEL_SFS", json.dumps({"sfsBasePath": str(sfs_base)}))
    monkeypatch.setenv("MODEL_OBJECT_ID", "object-123")
    monkeypatch.setenv("MODEL_ABSOLUTE_DIR", str(absolute_model_dir))

    paths = resolve_component_bundle_paths(process_file)

    assert paths.model_dir == absolute_model_dir.resolve()
    assert paths.data_dir == (object_root / "data").resolve()
    assert paths.meta_dir == (object_root / "meta").resolve()


def test_resolve_component_bundle_paths_infers_data_from_model_absolute_dir_without_sfs(
    monkeypatch,
    tmp_path: Path,
):
    process_file = _write_component_entry(tmp_path / "component")

    runtime_root = tmp_path / "runtime_root"
    model_dir = runtime_root / "model"
    model_dir.mkdir(parents=True)
    (model_dir / "sysconfig.properties").write_text("", encoding="utf-8")
    (runtime_root / "data").mkdir()
    (runtime_root / "meta").mkdir()

    monkeypatch.setenv("MODEL_ABSOLUTE_DIR", str(model_dir))

    paths = resolve_component_bundle_paths(process_file)

    assert paths.model_dir == model_dir.resolve()
    assert paths.data_dir == (runtime_root / "data").resolve()
    assert paths.meta_dir == (runtime_root / "meta").resolve()


def test_resolve_component_bundle_paths_supports_model_root_runtime_root(tmp_path: Path):
    process_file = _write_component_entry(tmp_path / "component")
    runtime_root = tmp_path / "runtime_root"
    _write_runtime_bundle_dirs(runtime_root)

    paths = resolve_component_bundle_paths(process_file, model_root=runtime_root)

    assert paths.model_dir == (runtime_root / "model").resolve()
    assert paths.data_dir == (runtime_root / "data").resolve()
    assert paths.meta_dir == (runtime_root / "meta").resolve()


def test_resolve_component_bundle_paths_supports_model_root_model_dir(tmp_path: Path):
    process_file = _write_component_entry(tmp_path / "component")
    runtime_root = tmp_path / "runtime_root"
    model_dir = runtime_root / "model"
    _write_runtime_bundle_dirs(runtime_root)
    (model_dir / "sysconfig.properties").write_text("", encoding="utf-8")

    paths = resolve_component_bundle_paths(process_file, model_root=model_dir)

    assert paths.model_dir == model_dir.resolve()
    assert paths.data_dir == (runtime_root / "data").resolve()
    assert paths.meta_dir == (runtime_root / "meta").resolve()


def test_prepare_runtime_project_layout_keeps_writable_snapshot_outside_mep(
    monkeypatch,
    tmp_path: Path,
):
    data_dir = tmp_path / "data"
    snapshot_dir = data_dir / "demo_kg"
    _write_snapshot(snapshot_dir)

    monkeypatch.setenv("RAGENT_RUNTIME_ENV", "local")
    monkeypatch.delenv("RAGENT_ENV", raising=False)
    monkeypatch.delenv("RAGENT_MEP_USE_SOURCE_SNAPSHOT", raising=False)

    layout = prepare_runtime_project_layout(
        data_dir=data_dir,
        runtime_root=tmp_path / "runtime",
    )

    assert layout.copied_to_runtime_dir is False
    assert layout.source_project_dir == snapshot_dir.resolve()
    assert layout.runtime_project_dir == layout.source_project_dir
    assert layout.runtime_temp_root is None


def test_resolve_single_snapshot_from_data_dir_supports_data_kg_layout(tmp_path: Path):
    data_dir = tmp_path / "data"
    snapshot_dir = data_dir / "kg" / "demo_kg"
    _write_snapshot(snapshot_dir)

    resolved = resolve_single_snapshot_from_data_dir(data_dir)

    assert resolved == snapshot_dir.resolve()


def test_resolve_single_snapshot_from_data_dir_supports_relative_env_override(
    monkeypatch,
    tmp_path: Path,
):
    data_dir = tmp_path / "data"
    snapshot_dir = data_dir / "kg" / "demo_kg"
    _write_snapshot(snapshot_dir)
    monkeypatch.setenv("RAGENT_MEP_KG_DIR", "kg/demo_kg")

    resolved = resolve_single_snapshot_from_data_dir(data_dir)

    assert resolved == snapshot_dir.resolve()


def test_prepare_runtime_project_layout_copies_writable_snapshot_by_default_in_mep(
    monkeypatch,
    tmp_path: Path,
):
    data_dir = tmp_path / "data"
    snapshot_dir = data_dir / "demo_kg"
    _write_snapshot(snapshot_dir)
    runtime_root = tmp_path / "runtime"

    monkeypatch.setenv("RAGENT_RUNTIME_ENV", "mep")
    monkeypatch.delenv("RAGENT_ENV", raising=False)
    monkeypatch.delenv("RAGENT_MEP_USE_SOURCE_SNAPSHOT", raising=False)

    layout = prepare_runtime_project_layout(
        data_dir=data_dir,
        runtime_root=runtime_root,
    )

    assert layout.copied_to_runtime_dir is True
    assert layout.source_project_dir == snapshot_dir.resolve()
    assert layout.runtime_project_dir != layout.source_project_dir
    assert layout.runtime_project_dir.exists()
    assert layout.runtime_temp_root is not None
    assert layout.runtime_temp_root.parent == runtime_root.resolve()
    assert (layout.runtime_project_dir / "vdb_chunks.json").exists()

    cleanup_runtime_project_layout(layout)


def test_prepare_runtime_project_layout_materializes_sqlite_kv_snapshot_in_mep(
    monkeypatch,
    tmp_path: Path,
):
    data_dir = tmp_path / "data"
    snapshot_dir = data_dir / "demo_kg"
    _write_snapshot(snapshot_dir)
    (snapshot_dir / "kv_store_text_chunks.json").write_text(
        json.dumps(
            {
                "chunk-1": {
                    "content": "图谱证据",
                    "file_path": "doc.md",
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (snapshot_dir / "kv_store_full_docs.json").write_text(
        json.dumps({"doc-1": {"content": "全文"}}, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setenv("RAGENT_RUNTIME_ENV", "mep")
    monkeypatch.delenv("RAGENT_ENV", raising=False)
    monkeypatch.delenv("RAGENT_MEP_USE_SOURCE_SNAPSHOT", raising=False)

    layout = prepare_runtime_project_layout(
        data_dir=data_dir,
        runtime_root=tmp_path / "runtime",
    )

    sqlite_path = layout.runtime_project_dir / "kv_store_text_chunks.sqlite"
    assert sqlite_path.is_file()
    with sqlite3.connect(sqlite_path) as conn:
        row = conn.execute(
            "SELECT entry_json FROM kv_entries WHERE key = ?",
            ("chunk-1",),
        ).fetchone()

    assert row is not None
    entry = json.loads(row[0])
    assert entry["content"] == "图谱证据"
    assert entry["llm_cache_list"] == []

    cleanup_runtime_project_layout(layout)


def test_prepare_runtime_project_layout_mep_escape_hatch_keeps_writable_snapshot(
    monkeypatch,
    tmp_path: Path,
):
    data_dir = tmp_path / "data"
    snapshot_dir = data_dir / "demo_kg"
    _write_snapshot(snapshot_dir)

    monkeypatch.setenv("RAGENT_RUNTIME_ENV", "mep")
    monkeypatch.setenv("RAGENT_MEP_USE_SOURCE_SNAPSHOT", "1")

    layout = prepare_runtime_project_layout(
        data_dir=data_dir,
        runtime_root=tmp_path / "runtime",
    )

    assert layout.copied_to_runtime_dir is False
    assert layout.runtime_project_dir == snapshot_dir.resolve()
    assert layout.runtime_temp_root is None


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


def test_build_result_payload_contains_stable_fields(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("RAGENT_RUNTIME_ENV", "local")
    monkeypatch.delenv("RAGENT_ENV", raising=False)
    monkeypatch.delenv("RAGENT_MEP_USE_SOURCE_SNAPSHOT", raising=False)

    req_data = normalize_mep_request(
        {
            "data": {
                "taskId": "100002455",
                "query_type": "onehop",
                "query": "我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？",
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
    assert payload["query"] == "我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？"
    assert payload["answer"] == "主题是饮食知识。"
    assert payload["referenced_file_paths"] == ["a.md"]
    assert payload["image_list"] == ["a.png"]
    assert payload["query_type"] == "onehop"
    assert payload["mode"] == "hybrid"
    assert payload["conversation_history_used_count"] == 1
    assert payload["trace"] is None
    assert payload["runtime"]["copied_to_runtime_dir"] is False
    assert payload["runtime"]["runtime_project_dir"] == str(layout.runtime_project_dir)


def test_build_result_payload_includes_retrieval_only_result(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("RAGENT_RUNTIME_ENV", "local")
    monkeypatch.delenv("RAGENT_ENV", raising=False)
    monkeypatch.delenv("RAGENT_MEP_USE_SOURCE_SNAPSHOT", raising=False)

    req_data = normalize_mep_request(
        {
            "data": {
                "taskId": "retrieval-001",
                "query_type": "onehop",
                "query": "我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？",
                "mode": "hybrid",
                "retrieval_only": True,
            }
        }
    )
    snapshot_dir = tmp_path / "data"
    _write_snapshot(snapshot_dir)
    layout = prepare_runtime_project_layout(data_dir=snapshot_dir)
    retrieval_result = {
        "rerank_used": False,
        "rerank_skip_reason": "enable_rerank=false",
        "final_context_text": "上下文",
        "final_context_chunks": [{"content": "上下文", "file_path": "doc.md"}],
    }
    result = {
        "answer": "上下文",
        "retrieval_only": True,
        "only_need_context": True,
        "retrieval_result": retrieval_result,
        "referenced_file_paths": ["doc.md"],
        "image_list": ["doc.md"],
        "query_type": "onehop",
        "mode": "hybrid",
    }

    payload = build_result_payload(
        request=req_data,
        result=result,
        runtime_layout=layout,
    )

    assert payload["retrieval_only"] is True
    assert payload["only_need_context"] is True
    assert payload["answer"] == "上下文"
    assert payload["retrieval_result"] == retrieval_result
    assert payload["referenced_file_paths"] == ["doc.md"]


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


def test_maybe_write_result_payload_rejects_path_like_result_filename(tmp_path: Path):
    with pytest.raises(ValueError, match="plain file name"):
        maybe_write_result_payload(
            {"code": "0"},
            generate_path=tmp_path / "generate",
            result_filename="../escape.json",
        )

    assert not (tmp_path / "escape.json").exists()


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
