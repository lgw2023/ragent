from __future__ import annotations

import asyncio
import json
import importlib.util
from pathlib import Path


def test_root_component_files_exist():
    repo_root = Path(__file__).resolve().parents[1]

    assert (repo_root / "process.py").exists()
    assert (repo_root / "config.json").exists()
    assert (repo_root / "package.json").exists()

    config = json.loads((repo_root / "config.json").read_text(encoding="utf-8"))
    assert config == {"main_file": "process", "main_class": "CustomerModel"}


def test_root_process_exports_customer_model():
    repo_root = Path(__file__).resolve().parents[1]
    process_path = repo_root / "process.py"

    spec = importlib.util.spec_from_file_location("ragent_root_process_test", process_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.CustomerModel.__name__ == "CustomerModel"


def test_example_mep_requests_exist():
    repo_root = Path(__file__).resolve().parents[1]
    request_dir = repo_root / "example" / "mep_requests"

    assert (request_dir / "onehop_request.json").exists()
    assert (request_dir / "multihop_request.json").exists()
    assert (request_dir / "chat_request.json").exists()
    assert (request_dir / "sfs_create_request.json").exists()


def test_customer_model_calc_create_writes_gen_json_and_returns_async_success(
    monkeypatch,
    tmp_path: Path,
):
    repo_root = Path(__file__).resolve().parents[1]
    process_path = repo_root / "process.py"

    spec = importlib.util.spec_from_file_location("ragent_root_process_create_test", process_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    snapshot_dir = tmp_path / "data" / "demo_kg"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for filename in (
        "graph_chunk_entity_relation.graphml",
        "kv_store_text_chunks.json",
        "vdb_chunks.json",
    ):
        (snapshot_dir / filename).write_text("{}", encoding="utf-8")

    runtime_layout = module.prepare_runtime_project_layout(data_dir=snapshot_dir.parent)

    class FakeLoopRunner:
        def run(self, coro):
            return asyncio.run(coro)

        def close(self):
            pass

    class FakeRuntimeSession:
        async def run(self, inference_request):
            assert inference_request.query_type == "onehop"
            assert inference_request.query == "文档的主要主题是什么？"
            return {
                "answer": "主题是饮食知识。",
                "referenced_file_paths": ["doc.md"],
                "image_list": [],
            }

        async def close(self):
            pass

    monkeypatch.setattr(module, "AsyncLoopThread", FakeLoopRunner)

    model = module.CustomerModel()
    model._runtime_layout = runtime_layout
    model._runtime_session = FakeRuntimeSession()
    generate_path = tmp_path / "generate"

    response = model.calc(
        {
            "version": "1.2",
            "data": {
                "taskId": "100002455",
                "action": "create",
                "basePath": str(tmp_path / "base"),
                "query_type": "onehop",
                "query": "文档的主要主题是什么？",
                "mode": "hybrid",
                "fileInfo": [{"generatePath": str(generate_path), "processSpec": []}],
            },
        }
    )

    assert response == {
        "recommendResult": {
            "code": "0",
            "des": "success",
            "length": 0,
            "content": [],
        }
    }
    output_path = generate_path / "gen.json"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["code"] == "0"
    assert payload["des"] == "success"
    assert payload["taskId"] == "100002455"
    assert payload["query"] == "文档的主要主题是什么？"
    assert payload["query_type"] == "onehop"
    assert payload["mode"] == "hybrid"
    assert payload["answer"] == "主题是饮食知识。"
    assert payload["referenced_file_paths"] == ["doc.md"]
    assert payload["runtime"]["runtime_project_dir"] == str(runtime_layout.runtime_project_dir)


def test_customer_model_calc_query_checks_existing_gen_json_without_loaded_runtime(
    monkeypatch,
    tmp_path: Path,
):
    repo_root = Path(__file__).resolve().parents[1]
    process_path = repo_root / "process.py"

    spec = importlib.util.spec_from_file_location("ragent_root_process_query_test", process_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class FakeLoopRunner:
        def run(self, coro):
            return asyncio.run(coro)

        def close(self):
            pass

    monkeypatch.setattr(module, "AsyncLoopThread", FakeLoopRunner)

    result_dir = tmp_path / "task" / "generatePath"
    result_dir.mkdir(parents=True)
    (result_dir / "gen.json").write_text('{"code": "0"}\n', encoding="utf-8")

    model = module.CustomerModel()
    response = model.calc(
        {
            "data": {
                "taskId": "100002455",
                "action": "query",
                "basePath": str(tmp_path / "task"),
            }
        }
    )

    assert response["recommendResult"]["code"] == "0"
    assert response["recommendResult"]["length"] == 0


def test_customer_model_cleanup_removes_runtime_copy_only(
    monkeypatch,
    tmp_path: Path,
):
    repo_root = Path(__file__).resolve().parents[1]
    process_path = repo_root / "process.py"

    spec = importlib.util.spec_from_file_location("ragent_root_process_cleanup_test", process_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    snapshot_dir = tmp_path / "data" / "demo_kg"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for filename in (
        "graph_chunk_entity_relation.graphml",
        "kv_store_text_chunks.json",
        "vdb_chunks.json",
    ):
        (snapshot_dir / filename).write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "ragent.mep_adapter._directory_is_writable",
        lambda path: False,
    )

    runtime_layout = module.prepare_runtime_project_layout(
        data_dir=snapshot_dir.parent,
        runtime_root=tmp_path / "runtime",
    )

    class FakeLoopRunner:
        def __init__(self):
            self.close_calls = 0

        def run(self, coro):
            return asyncio.run(coro)

        def close(self):
            self.close_calls += 1

    class FakeRuntimeSession:
        def __init__(self):
            self.close_calls = 0

        async def close(self):
            self.close_calls += 1

    class FakeEmbeddingRuntime:
        def __init__(self):
            self.shutdown_calls = 0

        def shutdown(self):
            self.shutdown_calls += 1

    monkeypatch.setattr(module, "AsyncLoopThread", FakeLoopRunner)

    model = module.CustomerModel()
    model._runtime_layout = runtime_layout
    fake_session = FakeRuntimeSession()
    fake_embedding_runtime = FakeEmbeddingRuntime()
    model._runtime_session = fake_session
    model._embedding_runtime = fake_embedding_runtime

    source_project_dir = runtime_layout.source_project_dir
    runtime_temp_root = runtime_layout.runtime_temp_root

    model.cleanup()
    model.cleanup()

    assert runtime_temp_root is not None
    assert not runtime_temp_root.exists()
    assert source_project_dir.exists()
    assert model._runtime_session is None
    assert model._runtime_layout is None
    assert fake_session.close_calls == 1
    assert fake_embedding_runtime.shutdown_calls == 1
    assert model._loop_runner.close_calls == 1
