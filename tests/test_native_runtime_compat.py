from __future__ import annotations

from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from ragent import native_runtime_compat


def _fake_find_spec(faiss_dir: Path, torch_dir: Path | None):
    def fake_find_spec(name: str):
        if name == "faiss":
            return SimpleNamespace(submodule_search_locations=[str(faiss_dir)])
        if name == "torch" and torch_dir is not None:
            return SimpleNamespace(submodule_search_locations=[str(torch_dir)])
        return None

    return fake_find_spec


def test_openmp_check_reports_missing_torch(monkeypatch, tmp_path: Path):
    faiss_dir = tmp_path / "site-packages" / "faiss"
    faiss_dir.mkdir(parents=True)
    (faiss_dir / "_swigfaiss.abi3.so").write_bytes(b"faiss")

    monkeypatch.setattr(native_runtime_compat.sys, "platform", "linux")
    monkeypatch.setattr(
        native_runtime_compat.importlib.util,
        "find_spec",
        _fake_find_spec(faiss_dir, None),
    )

    result = native_runtime_compat.check_native_openmp_compatibility()

    assert result["status"] == "torch_missing"
    assert result["platform"] == "linux"


def test_openmp_check_detects_darwin_private_faiss_torch_split(
    monkeypatch, tmp_path: Path
):
    faiss_dir = tmp_path / "site-packages" / "faiss"
    torch_dir = tmp_path / "site-packages" / "torch"
    faiss_dir.mkdir(parents=True)
    torch_dir.mkdir(parents=True)
    faiss_extension = faiss_dir / "_swigfaiss.abi3.so"
    torch_extension = torch_dir / "_C.cpython-313-darwin.so"
    faiss_extension.write_bytes(b"faiss")
    torch_extension.write_bytes(b"torch")

    def fake_run(command, **kwargs):
        assert kwargs["check"] is True
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        if command[-1] == str(faiss_extension):
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=(
                    f"{faiss_extension}:\n"
                    "\t@loader_path/.dylibs/libomp.dylib "
                    "(compatibility version 5.0.0, current version 5.0.0)\n"
                ),
            )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                f"{torch_extension}:\n"
                "\t@rpath/libomp.dylib "
                "(compatibility version 5.0.0, current version 5.0.0)\n"
            ),
        )

    monkeypatch.setattr(native_runtime_compat.sys, "platform", "darwin")
    monkeypatch.setattr(
        native_runtime_compat.importlib.util,
        "find_spec",
        _fake_find_spec(faiss_dir, torch_dir),
    )
    monkeypatch.setattr(native_runtime_compat.subprocess, "run", fake_run)

    result = native_runtime_compat.check_native_openmp_compatibility()

    assert result["status"] == "known_incompatible"


def test_faiss_import_guard_errors_for_known_darwin_split(monkeypatch, tmp_path: Path):
    faiss_dir = tmp_path / "site-packages" / "faiss"
    torch_dir = tmp_path / "site-packages" / "torch"
    faiss_dir.mkdir(parents=True)
    torch_dir.mkdir(parents=True)
    faiss_extension = faiss_dir / "_swigfaiss.abi3.so"
    torch_extension = torch_dir / "_C.cpython-313-darwin.so"
    faiss_extension.write_bytes(b"faiss")
    torch_extension.write_bytes(b"torch")

    def fake_run(command, **_kwargs):
        if command[-1] == str(faiss_extension):
            stdout = "\t@loader_path/.dylibs/libomp.dylib\n"
        else:
            stdout = "\t@loader_path/../torch/lib/libomp.dylib\n"
        return subprocess.CompletedProcess(command, 0, stdout=stdout)

    monkeypatch.delenv("RAG_FAISS_OPENMP_COMPAT_POLICY", raising=False)
    monkeypatch.setattr(native_runtime_compat.sys, "platform", "darwin")
    monkeypatch.setattr(
        native_runtime_compat.importlib.util,
        "find_spec",
        _fake_find_spec(faiss_dir, torch_dir),
    )
    monkeypatch.setattr(native_runtime_compat.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="incompatible OpenMP runtimes"):
        native_runtime_compat.ensure_faiss_import_compatibility()


def test_linux_mixed_openmp_warns_but_does_not_block(monkeypatch, tmp_path: Path):
    faiss_dir = tmp_path / "site-packages" / "faiss"
    torch_dir = tmp_path / "site-packages" / "torch"
    faiss_dir.mkdir(parents=True)
    torch_dir.mkdir(parents=True)
    faiss_extension = faiss_dir / "_swigfaiss.abi3.so"
    torch_extension = torch_dir / "_C.cpython-313-x86_64-linux-gnu.so"
    faiss_extension.write_bytes(b"faiss")
    torch_extension.write_bytes(b"torch")

    def fake_run(command, **_kwargs):
        if command[-1] == str(faiss_extension):
            stdout = "\tlibgomp.so.1 => /lib/libgomp.so.1\n"
        else:
            stdout = "\tlibiomp5.so => /opt/intel/libiomp5.so\n"
        return subprocess.CompletedProcess(command, 0, stdout=stdout)

    monkeypatch.delenv("RAG_FAISS_OPENMP_COMPAT_POLICY", raising=False)
    monkeypatch.setattr(native_runtime_compat.sys, "platform", "linux")
    monkeypatch.setattr(
        native_runtime_compat.importlib.util,
        "find_spec",
        _fake_find_spec(faiss_dir, torch_dir),
    )
    monkeypatch.setattr(native_runtime_compat.subprocess, "run", fake_run)

    result = native_runtime_compat.ensure_faiss_import_compatibility()

    assert result["status"] == "mixed_openmp"


def test_error_policy_blocks_linux_mixed_openmp(monkeypatch, tmp_path: Path):
    faiss_dir = tmp_path / "site-packages" / "faiss"
    torch_dir = tmp_path / "site-packages" / "torch"
    faiss_dir.mkdir(parents=True)
    torch_dir.mkdir(parents=True)
    faiss_extension = faiss_dir / "_swigfaiss.abi3.so"
    torch_extension = torch_dir / "_C.cpython-313-x86_64-linux-gnu.so"
    faiss_extension.write_bytes(b"faiss")
    torch_extension.write_bytes(b"torch")

    def fake_run(command, **_kwargs):
        if command[-1] == str(faiss_extension):
            stdout = "\tlibgomp.so.1 => /lib/libgomp.so.1\n"
        else:
            stdout = "\tlibiomp5.so => /opt/intel/libiomp5.so\n"
        return subprocess.CompletedProcess(command, 0, stdout=stdout)

    monkeypatch.setenv("RAG_FAISS_OPENMP_COMPAT_POLICY", "error")
    monkeypatch.setattr(native_runtime_compat.sys, "platform", "linux")
    monkeypatch.setattr(
        native_runtime_compat.importlib.util,
        "find_spec",
        _fake_find_spec(faiss_dir, torch_dir),
    )
    monkeypatch.setattr(native_runtime_compat.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="incompatible OpenMP runtimes"):
        native_runtime_compat.ensure_faiss_import_compatibility()
