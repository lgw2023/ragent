from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from ragent import mep_embedding_runtime
from ragent.mep_embedding_runtime import (
    bootstrap_local_embedding_runtime,
    build_vllm_command_candidates,
    build_vllm_subprocess_env,
    resolve_embedding_launch_config,
)


def _write_embedding_bundle(model_dir: Path) -> Path:
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "sysconfig.properties").write_text(
        "\n".join(
            [
                "model.name=BAAI/bge-m3",
                "model.relative_path=.",
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
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    return model_dir


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


def test_bootstrap_local_embedding_runtime_uses_transformers_runtime(
    monkeypatch,
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    data_dir = tmp_path / "data"
    (data_dir / "config").mkdir(parents=True)
    (data_dir / "config" / "embedding.properties").write_text(
        "\n".join(
            [
                "model.name=BAAI/bge-m3",
                "model.relative_path=.",
                "embedding.runtime=transformers",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    sentinel = object()
    seen: dict[str, object] = {}

    def fake_bootstrap(config):
        seen["config"] = config
        return sentinel

    monkeypatch.setattr(
        mep_embedding_runtime,
        "_bootstrap_local_transformers_embedding_runtime",
        fake_bootstrap,
    )
    monkeypatch.setattr(
        mep_embedding_runtime,
        "_ensure_vllm_runtime_dependencies",
        lambda _config: (_ for _ in ()).throw(AssertionError("unexpected vLLM setup")),
    )

    runtime = bootstrap_local_embedding_runtime(model_dir, data_dir=data_dir)

    assert runtime is sentinel
    assert seen["config"].runtime == "transformers"


def test_resolve_embedding_launch_config_reads_sysconfig(tmp_path: Path):
    model_dir = tmp_path / "model"
    embedding_root = _write_embedding_bundle(model_dir)

    config = resolve_embedding_launch_config(model_dir)

    assert config.model_dir == model_dir.resolve()
    assert config.model_path == embedding_root.resolve()
    assert config.served_model_name == "BAAI/bge-m3"
    assert config.host == "127.0.0.1"
    assert config.bind_host == "127.0.0.1"
    assert config.runner == "pooling"
    assert config.dimensions == 1024
    assert config.max_token_size == 8192
    assert config.port > 0
    assert config.config_path == (model_dir / "sysconfig.properties").resolve()


def test_resolve_embedding_launch_config_prefers_data_config(tmp_path: Path):
    model_dir = tmp_path / "model"
    embedding_root = model_dir
    embedding_root.mkdir(parents=True, exist_ok=True)
    (embedding_root / "config.json").write_text("{}", encoding="utf-8")
    (embedding_root / "tokenizer.json").write_text("{}", encoding="utf-8")
    (model_dir / "sysconfig.properties").write_text(
        "\n".join(
            [
                "model.name=legacy-name",
                "model.relative_path=.",
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
                "model.relative_path=.",
                "embedding.dimensions=1024",
                "embedding.max_token_size=8192",
                "vllm.bind_host=0.0.0.0",
                "vllm.host=127.0.0.1",
                "vllm.runner=pooling",
                "vllm.port=8000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    config = resolve_embedding_launch_config(model_dir, data_dir=data_dir)

    assert config.model_dir == model_dir.resolve()
    assert config.model_path == embedding_root.resolve()
    assert config.served_model_name == "BAAI/bge-m3-data-config"
    assert config.host == "127.0.0.1"
    assert config.bind_host == "0.0.0.0"
    assert config.port == 8000
    assert config.dimensions == 1024
    assert config.config_path == config_path.resolve()


def test_resolve_embedding_launch_config_reads_transformers_runtime(tmp_path: Path):
    model_dir = tmp_path / "model"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    data_dir = tmp_path / "data"
    (data_dir / "config").mkdir(parents=True)
    (data_dir / "config" / "embedding.properties").write_text(
        "\n".join(
            [
                "model.name=BAAI/bge-m3",
                "model.relative_path=.",
                "embedding.runtime=transformers",
                "embedding.device=npu:0",
                "embedding.batch_size=16",
                "embedding.pooling=cls",
                "embedding.normalize=true",
                "embedding.trust_remote_code=false",
                "embedding.dimensions=256",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    config = resolve_embedding_launch_config(model_dir, data_dir=data_dir)

    assert config.runtime == "transformers"
    assert config.device == "npu:0"
    assert config.batch_size == 16
    assert config.pooling == "cls"
    assert config.normalize_embeddings is True
    assert config.trust_remote_code is False
    assert config.dimensions == 256


def test_resolve_embedding_launch_config_env_overrides_data_config(
    monkeypatch,
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    embedding_root = model_dir
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
                "model.relative_path=.",
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
    embedding_root = model_dir
    embedding_root.mkdir(parents=True, exist_ok=True)
    (embedding_root / "config.json").write_text("{}", encoding="utf-8")
    (embedding_root / "tokenizer.json").write_text("{}", encoding="utf-8")
    data_dir = tmp_path / "data"
    (data_dir / "config").mkdir(parents=True)
    (data_dir / "config" / "embedding.properties").write_text(
        "\n".join(
            [
                "model.name=BAAI/bge-m3",
                "model.relative_path=.",
                "vllm.port=0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    config = resolve_embedding_launch_config(embedding_root, data_dir=data_dir)

    assert config.model_dir == embedding_root.resolve()
    assert config.model_path == embedding_root.resolve()


def test_resolve_embedding_launch_config_defaults_to_model_dir_for_flat_layout(
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    data_dir = tmp_path / "data"
    (data_dir / "config").mkdir(parents=True)
    (data_dir / "config" / "embedding.properties").write_text(
        "\n".join(
            [
                "model.name=BAAI/bge-m3",
                "vllm.port=0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    config = resolve_embedding_launch_config(model_dir, data_dir=data_dir)

    assert config.model_dir == model_dir.resolve()
    assert config.model_path == model_dir.resolve()


def test_resolve_embedding_launch_config_finds_nested_model_dir_like_bge_m3_pack(
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    model_dir.mkdir(parents=True)
    nested = model_dir / "modelDir" / "model"
    nested.mkdir(parents=True)
    (nested / "config.json").write_text("{}", encoding="utf-8")
    (nested / "tokenizer.json").write_text("{}", encoding="utf-8")

    data_dir = tmp_path / "data"
    (data_dir / "config").mkdir(parents=True)
    (data_dir / "config" / "embedding.properties").write_text(
        "\n".join(
            [
                "model.name=BAAI/bge-m3",
                "vllm.port=0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    config = resolve_embedding_launch_config(model_dir, data_dir=data_dir)

    assert config.model_dir == model_dir.resolve()
    assert config.model_path == nested.resolve()


def test_resolve_embedding_launch_config_nested_ambiguous_raises(tmp_path: Path):
    model_dir = tmp_path / "model"
    model_dir.mkdir(parents=True)
    for rel in ("a/model", "b/model"):
        p = model_dir / rel
        p.mkdir(parents=True)
        (p / "config.json").write_text("{}", encoding="utf-8")
        (p / "tokenizer.json").write_text("{}", encoding="utf-8")

    data_dir = tmp_path / "data"
    (data_dir / "config").mkdir(parents=True)
    (data_dir / "config" / "embedding.properties").write_text(
        "model.name=BAAI/bge-m3\nvllm.port=0\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="nested"):
        resolve_embedding_launch_config(model_dir, data_dir=data_dir)


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
    assert commands[0][commands[0].index("--host") + 1] == "127.0.0.1"
    assert "--api-key" not in commands[0]
    assert "--runner" in commands[0]
    assert "pooling" in commands[0]


def test_build_vllm_command_candidates_uses_bind_host_for_server(
    monkeypatch,
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    _write_embedding_bundle(model_dir)
    config_path = model_dir / "sysconfig.properties"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + "\n".join(
            [
                "vllm.bind_host=0.0.0.0",
                "vllm.host=127.0.0.1",
                "vllm.port=8000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config = resolve_embedding_launch_config(model_dir)

    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setattr(importlib.util, "find_spec", lambda _: object())

    commands = build_vllm_command_candidates(config)

    command = commands[0]
    assert command[command.index("--host") + 1] == "0.0.0.0"
    assert command[command.index("--port") + 1] == "8000"
    assert config.base_url == "http://127.0.0.1:8000/v1"


def test_build_vllm_command_candidates_passes_real_api_key(
    monkeypatch,
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    _write_embedding_bundle(model_dir)
    config_path = model_dir / "sysconfig.properties"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + "vllm.api_key=secret-key\n",
        encoding="utf-8",
    )
    config = resolve_embedding_launch_config(model_dir)

    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setattr(importlib.util, "find_spec", lambda _: object())

    command = build_vllm_command_candidates(config)[0]

    assert command[command.index("--api-key") + 1] == "secret-key"


def test_resolve_embedding_launch_config_reads_vllm_subprocess_env(
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    _write_embedding_bundle(model_dir)
    config_path = model_dir / "sysconfig.properties"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + "\n".join(
            [
                "vllm.env.ASCEND_RT_VISIBLE_DEVICES=0",
                "vllm.env.VLLM_LOGGING_LEVEL=DEBUG",
                "vllm.env.VLLM_PLUGINS=ascend",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    config = resolve_embedding_launch_config(model_dir)

    assert config.subprocess_env == (
        ("ASCEND_RT_VISIBLE_DEVICES", "0"),
        ("VLLM_LOGGING_LEVEL", "DEBUG"),
        ("VLLM_PLUGINS", "ascend"),
    )


def test_build_vllm_subprocess_env_defaults_to_spawn(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("VLLM_WORKER_MULTIPROC_METHOD", raising=False)
    monkeypatch.setenv("RAGENT_ASCEND_SET_ENV_SH", str(tmp_path / "missing_set_env.sh"))

    env = build_vllm_subprocess_env()

    assert env["VLLM_WORKER_MULTIPROC_METHOD"] == "spawn"


def test_default_ascend_env_scripts_include_latest_paths():
    assert "/usr/local/Ascend/ascend-toolkit/latest/set_env.sh" in (
        mep_embedding_runtime._DEFAULT_ASCEND_ENV_SCRIPTS
    )
    assert "/usr/local/Ascend/nnal/atb/latest/atb/set_env.sh" in (
        mep_embedding_runtime._DEFAULT_ASCEND_ENV_SCRIPTS
    )


def test_build_vllm_subprocess_env_passes_bootstrapped_pythonpath(
    monkeypatch,
    tmp_path: Path,
):
    deps_dir = tmp_path / "deps"
    existing_dir = tmp_path / "existing"
    monkeypatch.setenv("RAGENT_ASCEND_SET_ENV_SH", str(tmp_path / "missing_set_env.sh"))
    monkeypatch.setenv("RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH", str(deps_dir))
    monkeypatch.setenv("PYTHONPATH", str(existing_dir))

    env = build_vllm_subprocess_env()

    assert env["PYTHONPATH"].split(os.pathsep)[:2] == [
        str(deps_dir),
        str(existing_dir),
    ]


def test_build_vllm_subprocess_env_sources_ascend_set_env(monkeypatch, tmp_path: Path):
    set_env_script = tmp_path / "set_env.sh"
    set_env_script.write_text(
        "\n".join(
            [
                "export RAGENT_TEST_ASCEND_ENV=loaded",
                'export PYTHONPATH="/fake/ascend/python:${PYTHONPATH:-}"',
                'export LD_LIBRARY_PATH="/fake/ascend/lib:${LD_LIBRARY_PATH:-}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAGENT_ASCEND_SET_ENV_SH", str(set_env_script))
    monkeypatch.setenv("RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH", str(tmp_path / "deps"))
    monkeypatch.delenv("RAGENT_TEST_ASCEND_ENV", raising=False)
    monkeypatch.delenv("VLLM_WORKER_MULTIPROC_METHOD", raising=False)

    env = build_vllm_subprocess_env()

    assert env["RAGENT_TEST_ASCEND_ENV"] == "loaded"
    assert env["PYTHONPATH"].split(os.pathsep)[0] == str(tmp_path / "deps")
    assert env["LD_LIBRARY_PATH"].split(":")[0] == "/fake/ascend/lib"
    assert env["VLLM_WORKER_MULTIPROC_METHOD"] == "spawn"


def test_build_vllm_subprocess_env_sources_default_ascend_scripts(
    monkeypatch,
    tmp_path: Path,
):
    toolkit_env = tmp_path / "toolkit_set_env.sh"
    atb_env = tmp_path / "atb_set_env.sh"
    toolkit_env.write_text(
        'export PYTHONPATH="/fake/toolkit:${PYTHONPATH:-}"\n',
        encoding="utf-8",
    )
    atb_env.write_text(
        'export LD_LIBRARY_PATH="/fake/atb:${LD_LIBRARY_PATH:-}"\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("RAGENT_ASCEND_SET_ENV_SH", raising=False)
    monkeypatch.setenv(
        "RAGENT_ASCEND_ENV_SHS",
        f"{toolkit_env}{os.pathsep}{atb_env}",
    )

    env = build_vllm_subprocess_env()

    assert env["PYTHONPATH"].split(os.pathsep)[0] == "/fake/toolkit"
    assert env["LD_LIBRARY_PATH"].split(os.pathsep)[0] == "/fake/atb"


def test_build_vllm_subprocess_env_applies_config_env_overrides(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setenv("RAGENT_ASCEND_SET_ENV_SH", str(tmp_path / "missing_set_env.sh"))
    model_dir = tmp_path / "model"
    _write_embedding_bundle(model_dir)
    config_path = model_dir / "sysconfig.properties"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + "vllm.env.VLLM_PLUGINS=ascend\n",
        encoding="utf-8",
    )
    config = resolve_embedding_launch_config(model_dir)

    env = build_vllm_subprocess_env(config)

    assert env["VLLM_PLUGINS"] == "ascend"


def test_ensure_vllm_runtime_dependencies_installs_from_platform_wheelhouse(
    monkeypatch,
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    data_dir = tmp_path / "data"
    config_dir = data_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "embedding.properties").write_text(
        "\n".join(
            [
                "model.relative_path=.",
                "vllm.install_requirements=cbor2==5.9.0,triton-ascend==3.2.0,vllm==0.13.0,vllm-ascend==0.13.0",
                "vllm.uninstall_packages=vllm,vllm-ascend",
                "vllm.install_no_deps=true",
                "vllm.install_force_reinstall=true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    wheelhouse = data_dir / "deps" / "wheelhouse" / "linux-arm64-py3.10"
    wheelhouse.mkdir(parents=True)
    for wheel_name in (
        "cbor2-5.9.0-cp310-cp310-manylinux_2_28_aarch64.whl",
        "triton_ascend-3.2.0-cp310-cp310-manylinux_2_28_aarch64.whl",
        "vllm-0.13.0-cp38-abi3-manylinux_2_31_aarch64.whl",
        "vllm_ascend-0.13.0-cp310-cp310-manylinux_2_24_aarch64.whl",
    ):
        (wheelhouse / wheel_name).write_bytes(b"fake wheel")
    monkeypatch.setenv("RAGENT_MEP_PLATFORM_TAG", "linux-arm64-py3.10")

    installed_versions = {
        "cbor2": "5.8.0",
        "triton-ascend": "3.1.0",
        "vllm": "0.13.0rc0+h5",
        "vllm-ascend": "0.13.0rc0+h6",
    }

    def fake_version(name):
        return installed_versions[name]

    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, stdout="ok")

    monkeypatch.setattr(mep_embedding_runtime.importlib_metadata, "version", fake_version)
    monkeypatch.setattr(subprocess, "run", fake_run)

    config = resolve_embedding_launch_config(model_dir, data_dir=data_dir)

    mep_embedding_runtime._ensure_vllm_runtime_dependencies(config)

    assert commands[0] == [
        sys.executable,
        "-m",
        "pip",
        "uninstall",
        "vllm",
        "vllm-ascend",
        "-y",
    ]
    assert commands[1][:4] == [sys.executable, "-m", "pip", "install"]
    assert "--no-index" in commands[1]
    assert "--no-deps" in commands[1]
    assert "--force-reinstall" in commands[1]
    assert str(wheelhouse) in commands[1]
    assert commands[1][-4:] == [
        "cbor2==5.9.0",
        "triton-ascend==3.2.0",
        "vllm==0.13.0",
        "vllm-ascend==0.13.0",
    ]


def test_ensure_vllm_runtime_dependencies_can_reinstall_all_wheelhouse_wheels(
    monkeypatch,
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    data_dir = tmp_path / "data"
    config_dir = data_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "embedding.properties").write_text(
        "\n".join(
            [
                "model.relative_path=.",
                "vllm.install_requirements=cbor2==5.9.0,triton-ascend==3.2.0,vllm==0.13.0,vllm-ascend==0.13.0",
                "vllm.install_all_wheelhouse_wheels=true",
                "vllm.install_no_deps=false",
                "vllm.uninstall_packages=vllm,vllm-ascend",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    wheelhouse = data_dir / "deps" / "wheelhouse" / "linux-arm64-py3.10"
    wheelhouse.mkdir(parents=True)
    for wheel_name in (
        "cbor2-5.9.0-py3-none-any.whl",
        "torch-2.8.0-cp310-cp310-manylinux_2_28_aarch64.whl",
        "triton_ascend-3.2.0-cp310-cp310-manylinux_2_28_aarch64.whl",
        "vllm-0.13.0-cp38-abi3-manylinux_2_31_aarch64.whl",
        "vllm_ascend-0.13.0-cp310-cp310-manylinux_2_24_aarch64.whl",
    ):
        (wheelhouse / wheel_name).write_bytes(b"fake wheel")
    monkeypatch.setenv("RAGENT_MEP_PLATFORM_TAG", "linux-arm64-py3.10")

    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, stdout="ok")

    monkeypatch.setattr(subprocess, "run", fake_run)

    config = resolve_embedding_launch_config(model_dir, data_dir=data_dir)

    mep_embedding_runtime._ensure_vllm_runtime_dependencies(config)

    assert config.install_all_wheelhouse_wheels is True
    assert commands[0][-3:] == ["vllm", "vllm-ascend", "-y"]
    assert commands[1][:4] == [sys.executable, "-m", "pip", "install"]
    assert "--no-index" in commands[1]
    assert "--no-deps" in commands[1]
    assert str(wheelhouse) in commands[1]
    installed_wheels = [arg for arg in commands[1] if arg.endswith(".whl")]
    assert installed_wheels == [
        str(wheelhouse / "cbor2-5.9.0-py3-none-any.whl"),
        str(wheelhouse / "torch-2.8.0-cp310-cp310-manylinux_2_28_aarch64.whl"),
        str(wheelhouse / "triton_ascend-3.2.0-cp310-cp310-manylinux_2_28_aarch64.whl"),
        str(wheelhouse / "vllm-0.13.0-cp38-abi3-manylinux_2_31_aarch64.whl"),
        str(wheelhouse / "vllm_ascend-0.13.0-cp310-cp310-manylinux_2_24_aarch64.whl"),
    ]


def test_ensure_vllm_runtime_dependencies_accepts_source_archives(
    monkeypatch,
    tmp_path: Path,
):
    model_dir = tmp_path / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    data_dir = tmp_path / "data"
    config_dir = data_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "embedding.properties").write_text(
        "\n".join(
            [
                "model.relative_path=.",
                "vllm.install_requirements=func-timeout==4.3.5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    wheelhouse = data_dir / "deps" / "wheelhouse" / "linux-arm64-py3.10"
    wheelhouse.mkdir(parents=True)
    (wheelhouse / "func_timeout-4.3.5.tar.gz").write_bytes(b"fake sdist")
    monkeypatch.setenv("RAGENT_MEP_PLATFORM_TAG", "linux-arm64-py3.10")

    def missing_distribution(name):
        raise mep_embedding_runtime.importlib_metadata.PackageNotFoundError(name)

    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, stdout="ok")

    monkeypatch.setattr(
        mep_embedding_runtime.importlib_metadata,
        "distribution",
        missing_distribution,
    )
    monkeypatch.setattr(subprocess, "run", fake_run)

    config = resolve_embedding_launch_config(model_dir, data_dir=data_dir)

    mep_embedding_runtime._ensure_vllm_runtime_dependencies(config)

    assert len(commands) == 1
    assert commands[0][:4] == [sys.executable, "-m", "pip", "install"]
    assert "--no-index" in commands[0]
    assert str(wheelhouse) in commands[0]
    assert commands[0][-1] == "func-timeout==4.3.5"


def test_installed_requirement_check_ignores_wheel_zip_metadata(
    monkeypatch,
    tmp_path: Path,
):
    wheel_path = tmp_path / "vllm-0.13.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as wheel:
        wheel.writestr("vllm/__init__.py", "")
        wheel.writestr(
            "vllm-0.13.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: vllm\nVersion: 0.13.0\n",
        )
        wheel.writestr(
            "vllm-0.13.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
    monkeypatch.setattr(sys, "path", [str(wheel_path), *sys.path])
    importlib.invalidate_caches()

    assert (
        mep_embedding_runtime._installed_requirements_satisfied(("vllm==0.13.0",))
        is False
    )


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
    monkeypatch.setenv("RAGENT_ASCEND_SET_ENV_SH", str(tmp_path / "missing_set_env.sh"))

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
    process = process_holder["process"]
    assert process.kwargs["env"]["VLLM_WORKER_MULTIPROC_METHOD"] == "spawn"
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
