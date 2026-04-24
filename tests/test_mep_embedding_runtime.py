from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from ragent.mep_embedding_runtime import (
    bootstrap_local_embedding_runtime,
    build_vllm_command_candidates,
    resolve_embedding_launch_config,
)


def _write_embedding_bundle(model_dir: Path) -> Path:
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "sysconfig.properties").write_text(
        "\n".join(
            [
                "model.name=BAAI/bge-m3",
                "model.relative_path=baai_bge_m3",
                "embedding.dimensions=1024",
                "embedding.max_token_size=8192",
                "vllm.runner=pooling",
                "vllm.port=0",
                "vllm.startup_timeout_seconds=5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    embedding_root = model_dir / "baai_bge_m3"
    embedding_root.mkdir(parents=True, exist_ok=True)
    (embedding_root / "config.json").write_text("{}", encoding="utf-8")
    (embedding_root / "tokenizer.json").write_text("{}", encoding="utf-8")
    return embedding_root


def _write_multi_embedding_bundle(model_dir: Path) -> tuple[Path, Path]:
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "sysconfig.properties").write_text(
        "\n".join(
            [
                "model.name=BAAI/bge-m3",
                "embedding.dimensions=1024",
                "embedding.max_token_size=8192",
                "vllm.runner=pooling",
                "vllm.port=0",
                "vllm.startup_timeout_seconds=5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    primary_root = model_dir / "primary_model"
    primary_root.mkdir(parents=True, exist_ok=True)
    (primary_root / "config.json").write_text("{}", encoding="utf-8")
    (primary_root / "tokenizer.json").write_text("{}", encoding="utf-8")

    appendix_root = model_dir / "appendix_model"
    appendix_root.mkdir(parents=True, exist_ok=True)
    (appendix_root / "config.json").write_text("{}", encoding="utf-8")
    (appendix_root / "tokenizer.json").write_text("{}", encoding="utf-8")
    return primary_root, appendix_root


def test_bootstrap_local_embedding_runtime_skips_when_external_api_is_configured(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setenv("EMBEDDING_MODEL", "remote-model")
    monkeypatch.setenv("EMBEDDING_MODEL_URL", "https://example.com/v1")
    monkeypatch.setenv("EMBEDDING_MODEL_KEY", "remote-key")

    runtime = bootstrap_local_embedding_runtime(tmp_path / "unused-model-dir")

    assert runtime is None


def test_resolve_embedding_launch_config_reads_sysconfig(tmp_path: Path):
    model_dir = tmp_path / "model"
    embedding_root = _write_embedding_bundle(model_dir)

    config = resolve_embedding_launch_config(model_dir)

    assert config.model_dir == model_dir.resolve()
    assert config.model_path == embedding_root.resolve()
    assert config.served_model_name == "BAAI/bge-m3"
    assert config.runner == "pooling"
    assert config.dimensions == 1024
    assert config.max_token_size == 8192
    assert config.port > 0
    assert config.config_path == (model_dir / "sysconfig.properties").resolve()


def test_resolve_embedding_launch_config_prefers_data_config(tmp_path: Path):
    model_dir = tmp_path / "model"
    embedding_root = model_dir / "baai_bge_m3"
    embedding_root.mkdir(parents=True, exist_ok=True)
    (embedding_root / "config.json").write_text("{}", encoding="utf-8")
    (embedding_root / "tokenizer.json").write_text("{}", encoding="utf-8")
    (model_dir / "sysconfig.properties").write_text(
        "\n".join(
            [
                "model.name=legacy-name",
                "model.relative_path=baai_bge_m3",
                "embedding.dimensions=1",
                "vllm.port=0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    data_dir = tmp_path / "data"
    config_dir = data_dir / "config"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "embedding.properties"
    config_path.write_text(
        "\n".join(
            [
                "model.name=BAAI/bge-m3-data-config",
                "model.relative_path=baai_bge_m3",
                "embedding.dimensions=1024",
                "embedding.max_token_size=8192",
                "vllm.runner=pooling",
                "vllm.port=0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    config = resolve_embedding_launch_config(model_dir, data_dir=data_dir)

    assert config.model_dir == model_dir.resolve()
    assert config.model_path == embedding_root.resolve()
    assert config.served_model_name == "BAAI/bge-m3-data-config"
    assert config.dimensions == 1024
    assert config.config_path == config_path.resolve()


def test_resolve_embedding_launch_config_env_overrides_data_config(
    monkeypatch,
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    embedding_root = model_dir / "baai_bge_m3"
    embedding_root.mkdir(parents=True, exist_ok=True)
    (embedding_root / "config.json").write_text("{}", encoding="utf-8")
    (embedding_root / "tokenizer.json").write_text("{}", encoding="utf-8")

    data_dir = tmp_path / "data"
    config_dir = data_dir / "config"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "embedding.properties"
    config_path.write_text(
        "\n".join(
            [
                "model.name=BAAI/bge-m3-data-config",
                "model.relative_path=baai_bge_m3",
                "vllm.port=0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAGENT_MEP_EMBEDDING_MODEL_NAME", "env-model-name")
    monkeypatch.setenv("RAGENT_MEP_EMBEDDING_MODEL_PATH", str(embedding_root))
    monkeypatch.setenv("RAGENT_MEP_VLLM_RUNNER", "embed")

    config = resolve_embedding_launch_config(model_dir, data_dir=data_dir)

    assert config.config_path == config_path.resolve()
    assert config.model_path == embedding_root.resolve()
    assert config.served_model_name == "env-model-name"
    assert config.runner == "embed"


def test_resolve_embedding_launch_config_accepts_direct_model_dir_input(tmp_path: Path):
    model_dir = tmp_path / "model"
    embedding_root = _write_embedding_bundle(model_dir)

    config = resolve_embedding_launch_config(embedding_root)

    assert config.model_dir == model_dir.resolve()
    assert config.model_path == embedding_root.resolve()


def test_resolve_embedding_launch_config_accepts_direct_model_dir_with_data_config(
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    embedding_root = model_dir / "baai_bge_m3"
    embedding_root.mkdir(parents=True, exist_ok=True)
    (embedding_root / "config.json").write_text("{}", encoding="utf-8")
    (embedding_root / "tokenizer.json").write_text("{}", encoding="utf-8")
    data_dir = tmp_path / "data"
    (data_dir / "config").mkdir(parents=True)
    (data_dir / "config" / "embedding.properties").write_text(
        "\n".join(
            [
                "model.name=BAAI/bge-m3",
                "model.relative_path=baai_bge_m3",
                "vllm.port=0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    config = resolve_embedding_launch_config(embedding_root, data_dir=data_dir)

    assert config.model_dir == embedding_root.resolve()
    assert config.model_path == embedding_root.resolve()


def test_resolve_embedding_launch_config_supports_path_appendix(
    monkeypatch,
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    _, appendix_root = _write_multi_embedding_bundle(model_dir)
    monkeypatch.setenv("path_appendix", "appendix_model")

    config = resolve_embedding_launch_config(model_dir)

    assert config.model_dir == model_dir.resolve()
    assert config.model_path == appendix_root.resolve()


def test_build_vllm_command_candidates_supports_module_fallback(
    monkeypatch,
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    _write_embedding_bundle(model_dir)
    config = resolve_embedding_launch_config(model_dir)

    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setattr(importlib.util, "find_spec", lambda _: object())

    commands = build_vllm_command_candidates(config)

    assert len(commands) == 1
    assert commands[0][:3] == (sys.executable, "-m", "vllm.entrypoints.openai.api_server")
    assert "--task" in commands[0]
    assert "embed" in commands[0]


def test_bootstrap_local_embedding_runtime_sets_env_and_shuts_down(
    monkeypatch,
    tmp_path: Path,
):
    for key in (
        "EMBEDDING_MODEL",
        "EMBEDDING_MODEL_KEY",
        "EMBEDDING_MODEL_URL",
        "EMBEDDING_PROVIDER",
    ):
        monkeypatch.delenv(key, raising=False)

    model_dir = tmp_path / "model"
    _write_embedding_bundle(model_dir)

    process_holder: dict[str, object] = {}

    class FakePopen:
        def __init__(self, args, **kwargs):
            self.args = tuple(args)
            self.kwargs = kwargs
            self.pid = 4321
            self._terminated = False
            self._killed = False
            process_holder["process"] = self

        def poll(self):
            if self._killed or self._terminated:
                return 0
            return None

        def terminate(self):
            self._terminated = True

        def wait(self, timeout=None):
            return 0

        def kill(self):
            self._killed = True

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"data": [{"id": "BAAI/bge-m3"}]}

    def _fake_requests_get(url, headers=None, timeout=None):
        assert url.endswith("/v1/models")
        assert headers == {"Authorization": "Bearer EMPTY"}
        assert timeout == 5
        return FakeResponse()

    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/vllm")
    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    monkeypatch.setattr("requests.get", _fake_requests_get)
    monkeypatch.setattr(
        "ragent.mep_embedding_runtime._apply_embedding_function_attributes",
        lambda config: None,
    )

    runtime = bootstrap_local_embedding_runtime(model_dir)

    assert runtime is not None
    assert runtime.launch_command[:2] == ("vllm", "serve")
    assert os.getenv("EMBEDDING_MODEL") == "BAAI/bge-m3"
    assert os.getenv("EMBEDDING_MODEL_KEY") == "EMPTY"
    assert os.getenv("EMBEDDING_MODEL_URL") == runtime.config.base_url
    assert os.getenv("EMBEDDING_PROVIDER") == "custom_openai"

    runtime.shutdown()

    process = process_holder["process"]
    assert isinstance(process, FakePopen)
    assert process._terminated is True
    assert "EMBEDDING_MODEL" not in os.environ
    assert "EMBEDDING_MODEL_KEY" not in os.environ
    assert "EMBEDDING_MODEL_URL" not in os.environ
    assert "EMBEDDING_PROVIDER" not in os.environ
