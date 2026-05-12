from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path

import run_mep_local


def test_resolve_bundle_paths_for_local_run_passes_model_root(tmp_path: Path):
    calls: dict[str, object] = {}

    def fake_resolver(process_file, **kwargs):
        calls["process_file"] = process_file
        calls["kwargs"] = kwargs
        return "resolved-paths"

    fake_module = SimpleNamespace(
        __file__=str(tmp_path / "process.py"),
        resolve_component_bundle_paths=fake_resolver,
    )

    resolved = run_mep_local._resolve_bundle_paths_for_local_run(
        fake_module,
        str(tmp_path / "runtime_root"),
    )

    assert resolved == "resolved-paths"
    assert calls["process_file"] == fake_module.__file__
    assert calls["kwargs"] == {"model_root": str(tmp_path / "runtime_root")}


def test_main_passes_model_root_and_prints_resolved_paths(
    monkeypatch,
    capsys,
    tmp_path: Path,
):
    request_path = tmp_path / "request.json"
    request_payload = {
        "data": {
            "query_type": "onehop",
            "query": "我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？",
        }
    }
    request_path.write_text(
        json.dumps(request_payload, ensure_ascii=False),
        encoding="utf-8",
    )

    model_calls: dict[str, object] = {}

    class FakeCustomerModel:
        def __init__(self, model_root=None):
            model_calls["model_root"] = model_root

        def load(self):
            model_calls["loaded"] = True

        def calc(self, payload):
            model_calls["payload"] = payload
            return {"recommendResult": {"code": "0", "des": "success", "length": 0, "content": []}}

    fake_module = SimpleNamespace(
        __file__=str(tmp_path / "component" / "process.py"),
        resolve_component_bundle_paths=lambda process_file, **kwargs: SimpleNamespace(
            model_dir=tmp_path / "runtime" / "model",
            model_source="model_root_model_dir",
            data_dir=tmp_path / "runtime" / "data",
            data_source="model_root_data_dir",
            meta_dir=tmp_path / "runtime" / "meta",
            meta_source="model_root_meta_dir",
        ),
        CustomerModel=FakeCustomerModel,
    )

    monkeypatch.setattr(run_mep_local, "_load_process_module", lambda: fake_module)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_mep_local.py",
            "--request",
            str(request_path),
            "--model-root",
            str(tmp_path / "runtime"),
        ],
    )

    run_mep_local.main()

    captured = capsys.readouterr()
    assert "resolved bundle paths:" in captured.err
    assert str(tmp_path / "runtime" / "model") in captured.err
    assert str(tmp_path / "runtime" / "data") in captured.err
    assert model_calls["model_root"] == str(tmp_path / "runtime")
    assert model_calls["loaded"] is True
    assert model_calls["payload"] == request_payload
    assert '"code": "0"' in captured.out
