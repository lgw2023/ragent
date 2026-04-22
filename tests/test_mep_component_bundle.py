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

    monkeypatch.setattr(module, "AsyncLoopThread", FakeLoopRunner)

    model = module.CustomerModel()
    model._runtime_layout = runtime_layout
    fake_session = FakeRuntimeSession()
    model._runtime_session = fake_session

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
    assert model._loop_runner.close_calls == 1
