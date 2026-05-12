from __future__ import annotations

import asyncio
import json
import importlib.util
import os
import sys
import zipfile
from importlib import metadata as importlib_metadata
from pathlib import Path
from types import SimpleNamespace

import mep_dependency_bootstrap
from mep_dependency_bootstrap import (
    bootstrap_mep_data_dependencies,
    ensure_mep_offline_requirements,
)


def _write_minimal_wheel(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as wheel:
        wheel.writestr("demo_dep/__init__.py", "")


def test_root_component_files_exist():
    repo_root = Path(__file__).resolve().parents[1]

    assert (repo_root / "process.py").exists()
    assert (repo_root / "init.py").exists()
    assert (repo_root / "config.json").exists()
    assert (repo_root / "package.json").exists()
    assert (repo_root / "mep_dependency_bootstrap.py").exists()

    config = json.loads((repo_root / "config.json").read_text(encoding="utf-8"))
    assert config == {"main_file": "process", "main_class": "CustomerModel"}


def test_mep_data_dependency_bootstrap_uses_runtime_sibling_data_dir(
    monkeypatch,
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime"
    component_dir = runtime_root / "component"
    component_dir.mkdir(parents=True)
    (component_dir / "config.json").write_text(
        '{"main_file": "process", "main_class": "CustomerModel"}\n',
        encoding="utf-8",
    )
    pythonpath_dir = runtime_root / "data" / "deps" / "pythonpath"
    pythonpath_dir.mkdir(parents=True)

    monkeypatch.delenv("RAGENT_MEP_DATA_DIR", raising=False)
    monkeypatch.delenv("RAGENT_MEP_EXTRA_PYTHONPATH", raising=False)
    monkeypatch.delenv("RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH", raising=False)
    monkeypatch.setattr(sys, "path", list(sys.path))

    added_paths = bootstrap_mep_data_dependencies(component_dir)

    assert added_paths == (str(pythonpath_dir.resolve()),)
    assert sys.path[0] == str(pythonpath_dir.resolve())
    assert (
        os.environ["RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH"]
        == str(pythonpath_dir.resolve())
    )


def test_mep_data_dependency_bootstrap_configures_keyword_fallback_assets(
    monkeypatch,
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime"
    component_dir = runtime_root / "component"
    component_dir.mkdir(parents=True)
    (component_dir / "config.json").write_text(
        '{"main_file": "process", "main_class": "CustomerModel"}\n',
        encoding="utf-8",
    )
    keyword_model_dir = (
        runtime_root
        / "data"
        / "models"
        / "keyword_extraction"
        / "knowledgator-gliner-x-small"
    )
    keyword_model_dir.mkdir(parents=True)
    (keyword_model_dir / "config.json").write_text("{}", encoding="utf-8")
    (keyword_model_dir / "pytorch_model.bin").write_bytes(b"fake")
    keyword_wheelhouse = (
        runtime_root / "data" / "deps" / "keyword_wheelhouse" / "test-platform"
    )
    keyword_wheelhouse.mkdir(parents=True)
    keyword_wheel = keyword_wheelhouse / "gliner-0.2.26-py3-none-any.whl"
    with zipfile.ZipFile(keyword_wheel, "w") as wheel:
        wheel.writestr("gliner/__init__.py", "")

    monkeypatch.delenv("RAGENT_MEP_DATA_DIR", raising=False)
    monkeypatch.delenv("RAGENT_MEP_EXTRA_PYTHONPATH", raising=False)
    monkeypatch.delenv("RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH", raising=False)
    monkeypatch.delenv("RAG_KEYWORD_FALLBACK_MODEL", raising=False)
    monkeypatch.delenv("RAG_KEYWORD_FALLBACK_DEVICE", raising=False)
    monkeypatch.setenv("RAGENT_MEP_PLATFORM_TAG", "test-platform")
    monkeypatch.setattr(sys, "path", list(sys.path))

    added_paths = bootstrap_mep_data_dependencies(component_dir)

    assert os.environ["RAG_KEYWORD_FALLBACK_MODEL"] == str(
        keyword_model_dir.resolve()
    )
    assert os.environ["RAG_KEYWORD_FALLBACK_DEVICE"] == "cpu"
    assert str(keyword_wheel.resolve()) in added_paths
    assert sys.path[0] == str(keyword_wheel.resolve())


def test_mep_data_dependency_bootstrap_preserves_explicit_keyword_model_env(
    monkeypatch,
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime"
    component_dir = runtime_root / "component"
    component_dir.mkdir(parents=True)
    (component_dir / "config.json").write_text(
        '{"main_file": "process", "main_class": "CustomerModel"}\n',
        encoding="utf-8",
    )
    keyword_model_dir = (
        runtime_root
        / "data"
        / "models"
        / "keyword_extraction"
        / "knowledgator-gliner-x-small"
    )
    keyword_model_dir.mkdir(parents=True)

    monkeypatch.delenv("RAGENT_MEP_DATA_DIR", raising=False)
    monkeypatch.delenv("RAGENT_MEP_EXTRA_PYTHONPATH", raising=False)
    monkeypatch.setenv("RAG_KEYWORD_FALLBACK_MODEL", "/custom/gliner")
    monkeypatch.setenv("RAG_KEYWORD_FALLBACK_DEVICE", "npu")
    monkeypatch.setattr(sys, "path", list(sys.path))

    bootstrap_mep_data_dependencies(component_dir)

    assert os.environ["RAG_KEYWORD_FALLBACK_MODEL"] == "/custom/gliner"
    assert os.environ["RAG_KEYWORD_FALLBACK_DEVICE"] == "npu"


def test_mep_data_dependency_bootstrap_clears_stale_record_when_no_paths(
    monkeypatch,
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime"
    component_dir = runtime_root / "component"
    component_dir.mkdir(parents=True)
    (component_dir / "config.json").write_text(
        '{"main_file": "process", "main_class": "CustomerModel"}\n',
        encoding="utf-8",
    )

    monkeypatch.delenv("RAGENT_MEP_DATA_DIR", raising=False)
    monkeypatch.delenv("RAGENT_MEP_EXTRA_PYTHONPATH", raising=False)
    monkeypatch.setenv("RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH", "stale")
    monkeypatch.setattr(sys, "path", list(sys.path))

    added_paths = bootstrap_mep_data_dependencies(component_dir)

    assert added_paths == ()
    assert "RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH" not in os.environ


def test_mep_data_dependency_bootstrap_uses_platform_wheelhouse(
    monkeypatch,
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime"
    component_dir = runtime_root / "component"
    component_dir.mkdir(parents=True)
    (component_dir / "config.json").write_text(
        '{"main_file": "process", "main_class": "CustomerModel"}\n',
        encoding="utf-8",
    )
    selected_wheelhouse = (
        runtime_root / "data" / "deps" / "wheelhouse" / "linux-arm64-py3.10"
    )
    other_wheelhouse = (
        runtime_root / "data" / "deps" / "wheelhouse" / "linux-amd64-py3.10"
    )
    selected_wheelhouse.mkdir(parents=True)
    other_wheelhouse.mkdir(parents=True)
    selected_wheel = (
        selected_wheelhouse / "definitely_missing_pkg-1.0.0-py3-none-any.whl"
    )
    selected_wheel.write_bytes(b"not a real wheel")
    other_wheel = other_wheelhouse / "other_missing_pkg-1.0.0-py3-none-any.whl"
    other_wheel.write_bytes(b"not a real wheel")

    monkeypatch.delenv("RAGENT_MEP_DATA_DIR", raising=False)
    monkeypatch.delenv("RAGENT_MEP_EXTRA_PYTHONPATH", raising=False)
    monkeypatch.delenv("RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH", raising=False)
    monkeypatch.setenv("RAGENT_MEP_PLATFORM_TAG", "linux-arm64-py3.10")
    monkeypatch.setattr(sys, "path", list(sys.path))

    added_paths = bootstrap_mep_data_dependencies(component_dir)

    assert str(selected_wheel.resolve()) in added_paths
    assert str(other_wheel.resolve()) not in added_paths
    assert sys.path[0] == str(selected_wheel.resolve())


def test_mep_data_dependency_bootstrap_prefers_platform_site_packages(
    monkeypatch,
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime"
    component_dir = runtime_root / "component"
    component_dir.mkdir(parents=True)
    (component_dir / "config.json").write_text(
        '{"main_file": "process", "main_class": "CustomerModel"}\n',
        encoding="utf-8",
    )
    site_packages = (
        runtime_root / "data" / "deps" / "site-packages" / "linux-arm64-py3.10"
    )
    wheelhouse = runtime_root / "data" / "deps" / "wheelhouse" / "linux-arm64-py3.10"
    (site_packages / "litellm").mkdir(parents=True)
    (site_packages / "litellm" / "__init__.py").write_text("", encoding="utf-8")
    dist_info = site_packages / "litellm-1.80.10.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Name: litellm\nVersion: 1.80.10\n",
        encoding="utf-8",
    )
    wheelhouse.mkdir(parents=True)
    litellm_wheel = wheelhouse / "litellm-1.80.10-py3-none-any.whl"
    with zipfile.ZipFile(litellm_wheel, "w") as wheel:
        wheel.writestr("litellm/__init__.py", "")
        wheel.writestr("litellm/types/adapter.py", "")
    other_wheel = wheelhouse / "other_missing_pkg-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(other_wheel, "w") as wheel:
        wheel.writestr("other_missing_pkg/__init__.py", "")

    monkeypatch.delenv("RAGENT_MEP_DATA_DIR", raising=False)
    monkeypatch.delenv("RAGENT_MEP_EXTRA_PYTHONPATH", raising=False)
    monkeypatch.delenv("RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH", raising=False)
    monkeypatch.setenv("RAGENT_MEP_PLATFORM_TAG", "linux-arm64-py3.10")
    monkeypatch.setattr(sys, "path", list(sys.path))

    added_paths = bootstrap_mep_data_dependencies(component_dir)

    assert str(site_packages.resolve()) in added_paths
    assert str(litellm_wheel.resolve()) not in added_paths
    assert str(other_wheel.resolve()) in added_paths
    assert sys.path.index(str(site_packages.resolve())) < sys.path.index(
        str(other_wheel.resolve())
    )


def test_mep_data_dependency_bootstrap_skips_already_installed_wheels(
    monkeypatch,
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime"
    component_dir = runtime_root / "component"
    component_dir.mkdir(parents=True)
    (component_dir / "config.json").write_text(
        '{"main_file": "process", "main_class": "CustomerModel"}\n',
        encoding="utf-8",
    )
    wheelhouse = runtime_root / "data" / "deps" / "wheelhouse" / "test-platform"
    wheelhouse.mkdir(parents=True)
    installed_pip_version = importlib_metadata.version("pip")
    installed_wheel = wheelhouse / f"pip-{installed_pip_version}-py3-none-any.whl"
    installed_wheel.write_bytes(b"not a real wheel")
    mismatched_wheel = wheelhouse / "pip-999.0.0-py3-none-any.whl"
    mismatched_wheel.write_bytes(b"not a real wheel")
    missing_wheel = wheelhouse / "not_installed_by_default-1.0.0-py3-none-any.whl"
    missing_wheel.write_bytes(b"not a real wheel")

    monkeypatch.delenv("RAGENT_MEP_DATA_DIR", raising=False)
    monkeypatch.delenv("RAGENT_MEP_EXTRA_PYTHONPATH", raising=False)
    monkeypatch.delenv("RAGENT_MEP_BOOTSTRAPPED_PYTHONPATH", raising=False)
    monkeypatch.setenv("RAGENT_MEP_PLATFORM_TAG", "test-platform")
    monkeypatch.setattr(sys, "path", list(sys.path))

    added_paths = bootstrap_mep_data_dependencies(component_dir)

    assert str(missing_wheel.resolve()) in added_paths
    assert str(mismatched_wheel.resolve()) in added_paths
    assert str(installed_wheel.resolve()) not in added_paths


def test_mep_data_dependency_bootstrap_skips_native_wheel_zipimport(
    monkeypatch,
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime"
    component_dir = runtime_root / "component"
    component_dir.mkdir(parents=True)
    (component_dir / "config.json").write_text(
        '{"main_file": "process", "main_class": "CustomerModel"}\n',
        encoding="utf-8",
    )
    wheelhouse = runtime_root / "data" / "deps" / "wheelhouse" / "test-platform"
    wheelhouse.mkdir(parents=True)
    pure_wheel = wheelhouse / "pure_pkg-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(pure_wheel, "w") as wheel:
        wheel.writestr("pure_pkg/__init__.py", "")
    native_wheel = wheelhouse / "native_pkg-1.0.0-cp310-cp310-linux_aarch64.whl"
    with zipfile.ZipFile(native_wheel, "w") as wheel:
        wheel.writestr("native_pkg/native_extension.so", b"fake")

    monkeypatch.delenv("RAGENT_MEP_DATA_DIR", raising=False)
    monkeypatch.delenv("RAGENT_MEP_EXTRA_PYTHONPATH", raising=False)
    monkeypatch.delenv("RAGENT_MEP_ALLOW_NATIVE_WHEEL_ZIPIMPORT", raising=False)
    monkeypatch.setenv("RAGENT_MEP_PLATFORM_TAG", "test-platform")
    monkeypatch.setattr(sys, "path", list(sys.path))

    added_paths = bootstrap_mep_data_dependencies(component_dir)

    assert str(pure_wheel.resolve()) in added_paths
    assert str(native_wheel.resolve()) not in added_paths


def test_mep_offline_requirements_install_uses_platform_wheelhouse(
    monkeypatch,
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime"
    component_dir = runtime_root / "component"
    component_dir.mkdir(parents=True)
    (component_dir / "config.json").write_text(
        '{"main_file": "process", "main_class": "CustomerModel"}\n',
        encoding="utf-8",
    )
    deps_dir = runtime_root / "data" / "deps"
    wheelhouse = deps_dir / "wheelhouse" / "test-platform"
    wheelhouse.mkdir(parents=True)
    _write_minimal_wheel(wheelhouse / "demo_dep-1.0.0-py3-none-any.whl")
    requirements = deps_dir / "requirements-test-platform.txt"
    requirements.write_text("demo-dep\n", encoding="utf-8")
    constraints = deps_dir / "constraints-test-platform.txt"
    constraints.write_text("demo-dep==1.0.0\n", encoding="utf-8")

    commands: list[list[str]] = []

    class FakeCompleted:
        returncode = 0
        stdout = "ok"

    def fake_run(command, **kwargs):
        commands.append(command)
        return FakeCompleted()

    monkeypatch.delenv("RAGENT_MEP_DATA_DIR", raising=False)
    monkeypatch.delenv("RAGENT_MEP_OFFLINE_PIP_INSTALL", raising=False)
    monkeypatch.setenv("RAGENT_MEP_PLATFORM_TAG", "test-platform")
    monkeypatch.setattr(mep_dependency_bootstrap, "_OFFLINE_REQUIREMENTS_DONE", set())
    monkeypatch.setattr(mep_dependency_bootstrap.subprocess, "run", fake_run)
    monkeypatch.setattr(mep_dependency_bootstrap.site, "addsitedir", lambda _: None)

    installed = ensure_mep_offline_requirements(component_dir)

    assert installed == (str(requirements.resolve()),)
    assert len(commands) == 1
    command = commands[0]
    assert command[:5] == [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
    ]
    assert "--no-index" in command
    assert command[command.index("--find-links") + 1] == str(wheelhouse.resolve())
    assert command[command.index("-c") + 1] == str(constraints.resolve())
    assert command[command.index("-r") + 1] == str(requirements.resolve())


def test_mep_offline_requirements_install_rejects_corrupt_wheel(
    monkeypatch,
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime"
    component_dir = runtime_root / "component"
    component_dir.mkdir(parents=True)
    (component_dir / "config.json").write_text(
        '{"main_file": "process", "main_class": "CustomerModel"}\n',
        encoding="utf-8",
    )
    deps_dir = runtime_root / "data" / "deps"
    wheelhouse = deps_dir / "wheelhouse" / "test-platform"
    wheelhouse.mkdir(parents=True)
    corrupt_wheel = wheelhouse / "demo_dep-1.0.0-py3-none-any.whl"
    corrupt_wheel.write_bytes(b"not a zip")
    requirements = deps_dir / "requirements-test-platform.txt"
    requirements.write_text("demo-dep\n", encoding="utf-8")

    monkeypatch.delenv("RAGENT_MEP_DATA_DIR", raising=False)
    monkeypatch.delenv("RAGENT_MEP_OFFLINE_PIP_INSTALL", raising=False)
    monkeypatch.setenv("RAGENT_MEP_PLATFORM_TAG", "test-platform")
    monkeypatch.setattr(mep_dependency_bootstrap, "_OFFLINE_REQUIREMENTS_DONE", set())
    monkeypatch.setattr(
        mep_dependency_bootstrap.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected pip")),
    )

    try:
        ensure_mep_offline_requirements(component_dir)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected corrupt wheelhouse to fail before pip")

    assert "offline MEP wheelhouse contains invalid wheel file(s)" in message
    assert str(corrupt_wheel) in message


def test_mep_offline_requirements_install_can_be_disabled(
    monkeypatch,
    tmp_path: Path,
):
    runtime_root = tmp_path / "runtime"
    component_dir = runtime_root / "component"
    component_dir.mkdir(parents=True)
    (component_dir / "config.json").write_text(
        '{"main_file": "process", "main_class": "CustomerModel"}\n',
        encoding="utf-8",
    )
    deps_dir = runtime_root / "data" / "deps"
    wheelhouse = deps_dir / "wheelhouse" / "test-platform"
    wheelhouse.mkdir(parents=True)
    _write_minimal_wheel(wheelhouse / "demo_dep-1.0.0-py3-none-any.whl")
    (deps_dir / "requirements-test-platform.txt").write_text(
        "demo-dep\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("RAGENT_MEP_PLATFORM_TAG", "test-platform")
    monkeypatch.setenv("RAGENT_MEP_OFFLINE_PIP_INSTALL", "0")
    monkeypatch.setattr(
        mep_dependency_bootstrap.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected pip")),
    )

    assert ensure_mep_offline_requirements(component_dir) == ()


def test_package_json_uses_non_placeholder_scope():
    repo_root = Path(__file__).resolve().parents[1]

    package = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))

    assert package["scope"]
    assert package["scope"] != "replace-me"
    assert package["type"] == "aiexplore"
    assert package["name"] == "ragent_inference_mep"


def test_bge_m3_embedding_properties_match_validated_transformers_runtime():
    repo_root = Path(__file__).resolve().parents[1]
    config_path = (
        repo_root
        / "mep"
        / "model_packages"
        / "bge-m3"
        / "modelDir"
        / "data"
        / "config"
        / "embedding.properties"
    )
    properties = {}
    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        properties[key] = value

    assert properties["model.relative_path"] == "."
    assert properties["embedding.runtime"] == "transformers"
    assert properties["embedding.dimensions"] == "256"
    assert properties["embedding.max_token_size"] == "8192"
    assert properties["embedding.device"] == "npu:0"
    assert properties["embedding.pooling"] == "cls"
    assert properties["embedding.normalize"] == "true"
    assert properties["embedding.batch_size"] == "8"


def test_root_process_exports_customer_model():
    repo_root = Path(__file__).resolve().parents[1]
    process_path = repo_root / "process.py"

    spec = importlib.util.spec_from_file_location("ragent_root_process_test", process_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.CustomerModel.__name__ == "CustomerModel"


def test_root_init_exports_platform_probe(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    init_path = repo_root / "init.py"

    monkeypatch.setenv("MODEL_SFS", json.dumps({"sfsBasePath": "/mnt/sfs"}))
    monkeypatch.setenv("MODEL_OBJECT_ID", "object-123")
    monkeypatch.setenv("MODEL_RELATIVE_DIR", "model")
    monkeypatch.setenv("path_appendix", "legacy_model")

    spec = importlib.util.spec_from_file_location("ragent_root_init_test", init_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.COMPONENT_DIR == repo_root
    assert module.MODEL_SFS_BASE_DIR == "/mnt/sfs/object-123"
    assert module.SFS_MODEL_DIR == "/mnt/sfs/object-123/model"
    assert module.PATH_APPENDIX == "legacy_model"
    probe = module.build_runtime_probe()
    assert probe["component_dir"] == str(repo_root)
    assert probe["path_appendix"] == "legacy_model"


def test_example_mep_requests_exist():
    repo_root = Path(__file__).resolve().parents[1]
    request_dir = repo_root / "example" / "mep_requests"

    assert (request_dir / "onehop_request.json").exists()
    assert (request_dir / "multihop_request.json").exists()
    assert (request_dir / "chat_request.json").exists()
    assert (request_dir / "sfs_create_request.json").exists()
    assert (request_dir / "retrieval_only_request.json").exists()


def test_mep_runtime_sources_avoid_python310_only_dataclass_slots():
    repo_root = Path(__file__).resolve().parents[1]
    inference_runtime = repo_root / "ragent" / "inference_runtime.py"

    assert "dataclass(slots=True)" not in inference_runtime.read_text(encoding="utf-8")


def test_mep_runtime_sources_avoid_dynamic_pipmaster_imports():
    repo_root = Path(__file__).resolve().parents[1]
    runtime_sources = [
        repo_root / "ragent" / "kg" / "networkx_impl.py",
        repo_root / "ragent" / "kg" / "nano_vector_db_impl.py",
        repo_root / "ragent" / "kg" / "neo4j_impl.py",
        repo_root / "ragent" / "kg" / "milvus_impl.py",
        repo_root / "ragent" / "llm" / "hf.py",
        repo_root / "ragent" / "llm" / "ollama.py",
    ]

    for source_path in runtime_sources:
        source = source_path.read_text(encoding="utf-8")
        assert "pipmaster" not in source
        assert "pm.install" not in source


def test_offline_full_chain_validation_script_is_exported():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = (
        repo_root
        / "MEP_platform_rule"
        / "Validated_ragent-mep-test_docker_full_chain.sh"
    )
    export_script = repo_root / "tools" / "export_mep_test_bundle_to_udisk.sh"
    validator_script = repo_root / "tools" / "validate_mep_full_chain_result.py"
    wheelhouse_validator_script = repo_root / "tools" / "validate_mep_wheelhouse.py"

    assert script_path.exists()
    script_text = script_path.read_text(encoding="utf-8")
    export_text = export_script.read_text(encoding="utf-8")
    validator_text = validator_script.read_text(encoding="utf-8")

    assert "Validated_ragent-mep-test_docker_full_chain.sh" in export_text
    assert "validate_mep_full_chain_result.py" in export_text
    assert "validate_mep_wheelhouse.py" in export_text
    assert 'DEST="${DEST:-/Volumes/Udisk2/ragent}"' in export_text
    assert 'PLATFORM_TAG="${PLATFORM_TAG:-linux-arm64-py3.9}"' in export_text
    assert 'MEP_REQUEST_NAME="${MEP_REQUEST_NAME:-retrieval_only_request.json}"' in script_text
    assert 'IMAGE="${IMAGE:-}"' in script_text
    assert 'CONTAINER_TEST_DIR="${CONTAINER_TEST_DIR:-/tmp/ragent}"' in script_text
    assert 'MEP_WHEELHOUSE_PLATFORM_TAG="${MEP_WHEELHOUSE_PLATFORM_TAG:-${RAGENT_MEP_PLATFORM_TAG:-linux-arm64-py3.9}}"' in script_text
    assert "validate_host_wheelhouse()" in script_text
    assert "load_ascend_runtime_environment()" in script_text
    assert "sourced Ascend env:" in script_text
    assert "ascend-toolkit/latest/set_env.sh" in script_text
    assert "MEP_REQUIRE_ASCEND_ENV=1" in script_text
    assert "AUTO_START_CONTAINER" in script_text
    assert "start_plain_container()" in script_text
    assert "docker run -d" in script_text
    assert "MEP_REUSE_EXISTING_VLLM=0" in script_text
    assert "requests_require_llm()" in script_text
    assert "validate_mep_full_chain_result.py" in script_text
    assert "retrieval-only payload is missing retrieval_result" in validator_text
    assert "Validate that MEP offline wheelhouse .whl files" in wheelhouse_validator_script.read_text(
        encoding="utf-8"
    )


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


def test_customer_model_calc_retrieval_only_writes_retrieval_result(
    monkeypatch,
    tmp_path: Path,
):
    repo_root = Path(__file__).resolve().parents[1]
    process_path = repo_root / "process.py"

    spec = importlib.util.spec_from_file_location(
        "ragent_root_process_retrieval_only_test",
        process_path,
    )
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
            assert inference_request.retrieval_only is True
            assert inference_request.only_need_context is True
            assert inference_request.include_trace is True
            return {
                "answer": "检索上下文",
                "retrieval_only": True,
                "only_need_context": True,
                "referenced_file_paths": ["doc.md"],
                "image_list": ["doc.md"],
                "retrieval_result": {
                    "rerank_used": False,
                    "rerank_skip_reason": "missing required RERANK_* config",
                    "final_context_text": "检索上下文",
                    "final_context_chunks": [
                        {"content": "检索上下文", "file_path": "doc.md"}
                    ],
                },
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
                "taskId": "retrieval-001",
                "action": "create",
                "query_type": "onehop",
                "query": "文档的主要主题是什么？",
                "mode": "hybrid",
                "retrieval_only": True,
                "fileInfo": [{"generatePath": str(generate_path), "processSpec": []}],
            },
        }
    )

    assert response["recommendResult"]["code"] == "0"
    output_path = generate_path / "gen.json"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["retrieval_only"] is True
    assert payload["answer"] == "检索上下文"
    assert payload["retrieval_result"]["final_context_text"] == "检索上下文"
    assert payload["referenced_file_paths"] == ["doc.md"]


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


def test_customer_model_load_passes_model_root_without_legacy_suffixing(
    monkeypatch,
    tmp_path: Path,
):
    repo_root = Path(__file__).resolve().parents[1]
    process_path = repo_root / "process.py"

    spec = importlib.util.spec_from_file_location("ragent_root_process_load_test", process_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    resolved_calls: dict[str, object] = {}

    class FakeLoopRunner:
        def run(self, coro):
            return asyncio.run(coro)

        def close(self):
            pass

    class FakeRuntimeSession:
        def __init__(self, project_dir):
            resolved_calls["project_dir"] = project_dir

        async def load(self):
            resolved_calls["loaded"] = True

        async def close(self):
            resolved_calls["closed"] = True

    bundle_paths = SimpleNamespace(
        model_dir=(tmp_path / "runtime_root" / "model").resolve(),
        model_source="model_root_model_dir",
        data_dir=(tmp_path / "runtime_root" / "data").resolve(),
        data_source="model_root_data_dir",
        meta_dir=(tmp_path / "runtime_root" / "meta").resolve(),
        meta_source="model_root_meta_dir",
        diagnostics=(),
    )

    runtime_layout = SimpleNamespace(
        data_dir=bundle_paths.data_dir,
        source_project_dir=(tmp_path / "runtime_root" / "data" / "demo_kg").resolve(),
        runtime_project_dir=(tmp_path / "runtime_root" / "runtime_copy").resolve(),
        copied_to_runtime_dir=False,
        runtime_temp_root=None,
    )

    def _fake_resolve_component_bundle_paths(process_file, **kwargs):
        resolved_calls["kwargs"] = kwargs
        return bundle_paths

    monkeypatch.setattr(module, "AsyncLoopThread", FakeLoopRunner)
    monkeypatch.setattr(module, "resolve_component_bundle_paths", _fake_resolve_component_bundle_paths)
    monkeypatch.setattr(
        module,
        "bootstrap_local_embedding_runtime",
        lambda model_dir, **kwargs: None,
    )
    monkeypatch.setattr(module, "prepare_runtime_project_layout", lambda **kwargs: runtime_layout)
    monkeypatch.setattr(module, "InferenceRuntimeSession", FakeRuntimeSession)

    model_root = tmp_path / "runtime_root" / "model"
    model = module.CustomerModel(model_root=model_root)
    model.load()

    assert resolved_calls["kwargs"]["model_root"] == model_root.resolve()
    assert resolved_calls["loaded"] is True


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
